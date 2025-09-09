from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import MilkCollection, CostEntry
from .serializers import MilkCollectionSerializer, CostEntrySerializer
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import permissions
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.utils.dateparse import parse_date
from rest_framework import status
from datetime import date
from django.db.models import Sum

# List & Create
class MilkCollectionListCreateView(APIView):
    permission_classes = [AllowAny]  
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        print(f"Start Date: {start_date}, End Date: {end_date}")
        if start_date and end_date:
            start = parse_date(start_date)
            end = parse_date(end_date)
            if not start or not end:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            milk_qs = MilkCollection.objects.filter(date__range=(start, end))
        else:
            milk_qs = MilkCollection.objects.all()

        serializer = MilkCollectionSerializer(milk_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MilkCollectionSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response({"ok": True, "milk_entry": serializer.data}, status=201)
        return Response({"ok": False, "errors": serializer.errors}, status=400)

# Retrieve, Update, Delete
class MilkCollectionDetailView(APIView):
    permission_classes = [AllowAny]  
    
    def get_object(self, id):
        return get_object_or_404(MilkCollection, id=id)

    def get(self, request, id):
        obj = self.get_object(id)
        serializer = MilkCollectionSerializer(obj)
        return Response(serializer.data)

    def put(self, request, id):
        obj = self.get_object(id)
        serializer = MilkCollectionSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        obj = self.get_object(id)
        obj.delete()
        return Response({'message': f"Milk entry {id} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    
class CostEntryListCreateView(APIView):
    permission_classes = [AllowAny]  
    def get(self, request):
        cost_qs = CostEntry.objects.all()
        serializer = CostEntrySerializer(cost_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CostEntrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CostEntryDetailView(APIView):
    permission_classes = [AllowAny]  
    def get_object(self, id):
        return get_object_or_404(CostEntry, id=id)

    def get(self, request, id):
        obj = self.get_object(id)
        serializer = CostEntrySerializer(obj)
        return Response(serializer.data)

    def put(self, request, id):
        obj = self.get_object(id)
        serializer = CostEntrySerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        obj = self.get_object(id)
        obj.delete()
        return Response({'message': f"Cost entry {id} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

# monthly milk collection report
class MilkCollectionPDFExportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date required"}, status=400)

        start = parse_date(start_date)
        end = parse_date(end_date)

        milk_data = MilkCollection.objects.filter(date__range=(start, end)).order_by('date')
        cost_data = CostEntry.objects.filter(cost_date__range=(start, end)).order_by('cost_date')

        # Initialize totals
        total_local = total_rise = total_all = total_income = 0.0
        total_cost = 0.0

        # Prepare milk collection table data
        milk_table_data = [['Date', 'Local Sale (KG)', 'Rise Kitchen (KG)', 'Total (KG)', 'Rate', 'Day Income']]
        for item in milk_data:
            milk_table_data.append([
                item.date.strftime("%Y-%m-%d"),
                round(item.local_sale_kg, 1),
                round(item.rise_kitchen_kg, 1),
                round(item.total_kg, 1),
                round(item.day_rate, 2),
                round(item.day_total_income, 2)
            ])
            total_local += item.local_sale_kg
            total_rise += item.rise_kitchen_kg
            total_all += item.total_kg
            total_income += item.day_total_income

        milk_table_data.append([
            'TOTAL',
            round(total_local, 1),
            round(total_rise, 1),
            round(total_all, 1),
            '',
            round(total_income, 2)
        ])

        # Prepare cost table data
        cost_table_data = [['Date', 'Description', 'Amount']]
        for cost in cost_data:
            cost_table_data.append([
                cost.cost_date.strftime("%Y-%m-%d"),
                cost.description,
                round(cost.amount, 2)
            ])
            total_cost += cost.amount

        cost_table_data.append(['TOTAL', '', round(total_cost, 2)])

        # Create PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="milk_report_{start}_{end}.pdf"'

        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        pdf.setTitle("Milk Collection Report")

        y = height - 2 * cm
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(5 * cm, y, f"Milk Collection Report ({start} to {end})")
        y -= 2 * cm

        # Draw milk table
        milk_table = Table(milk_table_data, colWidths=[3 * cm] * 6)
        milk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ]))
        milk_table.wrapOn(pdf, width, y)
        milk_table_height = 1 * cm * len(milk_table_data)
        milk_table.drawOn(pdf, x=2 * cm, y=y - milk_table_height)

        # Adjust y position
        y = y - milk_table_height - 1 * cm

        # Draw cost table
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, "Cost Entries")
        y -= 1 * cm

        cost_table = Table(cost_table_data, colWidths=[3 * cm, 7 * cm, 3 * cm])
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightpink),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        cost_table.wrapOn(pdf, width, y)
        cost_table_height = 1 * cm * len(cost_table_data)
        cost_table.drawOn(pdf, x=2 * cm, y=y - cost_table_height)

        y = y - cost_table_height - 1 * cm

        # Show net income
        pdf.setFont("Helvetica-Bold", 12)
        net_income = total_income - total_cost
        pdf.drawString(2 * cm, y, f"Net Income: {round(net_income, 2)}")

        pdf.showPage()
        pdf.save()
        return response
    
class LatestMilkCollectionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        latest = MilkCollection.objects.order_by('-date').first()
        if latest is None:
            return Response({"detail": "No milk collection found"}, status=404)
        serializer = MilkCollectionSerializer(latest)
        return Response(serializer.data)
    
class MonthToDateIncomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        # optional override of "today" for testing
        ds = request.query_params.get("date")  # format: YYYY-MM-DD
        if ds:
            try:
                ref = date.fromisoformat(ds)
            except ValueError:
                return Response({"detail": "Invalid date format; use YYYY-MM-DD"}, status=400)
        else:
            ref = date.today()

        # period start = first day of current month; end = ref
        start_date = date(ref.year, ref.month, 1)
        end_date = ref

        # aggregate income and optionally sums of quantities
        agg = MilkCollection.objects.filter(date__range=(start_date, end_date)).aggregate(
            total_income=Sum("day_total_income"),
            total_kg=Sum("total_kg"),
            total_liters=Sum("total_liters"),
        )

        # fallback to 0 if None
        total_income = agg["total_income"] or 0.0
        total_kg = agg["total_kg"] or 0.0
        total_liters = agg["total_liters"] or 0.0

        return Response({
            "reference_date": ref.isoformat(),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_income": total_income,
            "total_kg": total_kg,
            "total_liters": total_liters,
        })