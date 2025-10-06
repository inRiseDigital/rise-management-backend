from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Machine, ExtractionRecord, OilPurchase
from .serializers import MachineSerializer, ExtractionRecordSerializer, OilPurchaseSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.utils.dateparse import parse_date
from django.http import HttpResponse
# Machine CRUD
class MachineListCreate(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        machines = Machine.objects.all()
        serializer = MachineSerializer(machines, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MachineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MachineDetail(APIView):
    permission_classes = [AllowAny] 
    def get(self, request, pk):
        machine = get_object_or_404(Machine, pk=pk)
        serializer = MachineSerializer(machine)
        return Response(serializer.data)

    def put(self, request, pk):
        machine = get_object_or_404(Machine, pk=pk)
        serializer = MachineSerializer(machine, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        machine = get_object_or_404(Machine, pk=pk)
        machine.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ExtractionRecord CRUD
class ExtractionRecordListCreate(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        records = ExtractionRecord.objects.all()
        serializer = ExtractionRecordSerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExtractionRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExtractionRecordDetail(APIView):
    permission_classes = [AllowAny] 
    def get(self, request, pk):
        record = get_object_or_404(ExtractionRecord, pk=pk)
        serializer = ExtractionRecordSerializer(record)
        return Response(serializer.data)

    def put(self, request, pk):
        record = get_object_or_404(ExtractionRecord, pk=pk)
        serializer = ExtractionRecordSerializer(record, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        record = get_object_or_404(ExtractionRecord, pk=pk)
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# OilPurchase CRUD
class OilPurchaseListCreate(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        purchases = OilPurchase.objects.all()
        serializer = OilPurchaseSerializer(purchases, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OilPurchaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OilPurchaseDetail(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        purchase = get_object_or_404(OilPurchase, pk=pk)
        serializer = OilPurchaseSerializer(purchase)
        return Response(serializer.data)

    def put(self, request, pk):
        purchase = get_object_or_404(OilPurchase, pk=pk)
        serializer = OilPurchaseSerializer(purchase, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        purchase = get_object_or_404(OilPurchase, pk=pk)
        purchase.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Oil Extraction Report PDF
class OilExtractionReportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        format_type = request.GET.get("format", "pdf")

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date required"}, status=400)

        try:
            start = parse_date(start_date)
            end = parse_date(end_date)

            # Get extraction records
            extraction_records = ExtractionRecord.objects.filter(
                date__range=(start, end)
            ).select_related('machine').order_by('date')

            # Calculate totals
            total_input = sum(float(r.input_weight) for r in extraction_records)
            total_output = sum(float(r.output_volume) for r in extraction_records)
            total_records = extraction_records.count()

            # Return JSON if requested
            if format_type == "json":
                serializer = ExtractionRecordSerializer(extraction_records, many=True)
                return Response({
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_records": total_records,
                    "total_input_weight": total_input,
                    "total_output_volume": total_output,
                    "records": serializer.data
                })

            # Create PDF response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="oil_extraction_report_{start_date}_to_{end_date}.pdf"'

            pdf = canvas.Canvas(response, pagesize=A4)
            width, height = A4

            # Header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(width/2, height - 2*cm, "OIL EXTRACTION REPORT")
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(width/2, height - 2.7*cm, f"Period: {start_date} to {end_date}")
            pdf.drawRightString(width - 2*cm, height - 3.4*cm, f"Total Records: {total_records}")
            pdf.drawRightString(width - 2*cm, height - 4*cm, f"Total Input: {total_input:.2f} kg")
            pdf.drawRightString(width - 2*cm, height - 4.6*cm, f"Total Output: {total_output:.2f} L")

            current_y = height - 5.5*cm

            # Table data
            data = [['Date', 'Machine', 'Leaf Type', 'Input (kg)', 'Output (L)', 'Duration', 'Operated By']]

            for record in extraction_records:
                duration_str = str(record.run_duration) if record.run_duration else 'N/A'
                data.append([
                    record.date.strftime("%Y-%m-%d"),
                    record.machine.name[:15],
                    record.leaf_type[:15],
                    f"{record.input_weight:.2f}",
                    f"{record.output_volume:.2f}",
                    duration_str[:10],
                    f"{record.on_by[:10]}"
                ])

            # Create table
            col_widths = [2.5*cm, 3*cm, 3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm]
            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            # Draw table
            table_height = len(data) * 0.6*cm
            if current_y - table_height < 2*cm:
                pdf.showPage()
                current_y = height - 4*cm

            table.wrapOn(pdf, width, height)
            table.drawOn(pdf, 1.5*cm, current_y - table_height)

            pdf.save()
            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Machine List Report PDF
class MachineListReportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        format_type = request.GET.get("format", "pdf")

        try:
            # Get all machines
            machines = Machine.objects.all().order_by('name')

            # Return JSON if requested
            if format_type == "json":
                serializer = MachineSerializer(machines, many=True)
                return Response({
                    "total_machines": machines.count(),
                    "machines": serializer.data
                })

            # Create PDF response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="oil_extraction_machines_list.pdf"'

            pdf = canvas.Canvas(response, pagesize=A4)
            width, height = A4

            # Header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(width/2, height - 2*cm, "OIL EXTRACTION MACHINES LIST")
            pdf.setFont("Helvetica", 12)
            pdf.drawRightString(width - 2*cm, height - 3*cm, f"Total Machines: {machines.count()}")

            current_y = height - 4.5*cm

            # Table data
            data = [['Machine Name', 'Description', 'Created Date']]

            for machine in machines:
                created_date = machine.created_at.strftime("%Y-%m-%d") if machine.created_at else 'N/A'
                description = machine.description[:40] if machine.description else 'No description'
                data.append([
                    machine.name[:30],
                    description,
                    created_date
                ])

            # Create table
            col_widths = [5*cm, 10*cm, 4*cm]
            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            # Draw table
            table_height = len(data) * 0.6*cm
            if current_y - table_height < 2*cm:
                pdf.showPage()
                current_y = height - 4*cm

            table.wrapOn(pdf, width, height)
            table.drawOn(pdf, 1.5*cm, current_y - table_height)

            pdf.save()
            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate machines report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )