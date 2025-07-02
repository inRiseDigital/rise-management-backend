# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import ExpenseCategory, Expense
from .serializers import ExpenseCategorySerializer, ExpenseSerializer
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from textwrap import wrap

# ── CATEGORY CRUD ──

class ExpenseCategoryListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cats = ExpenseCategory.objects.all()
        serializer = ExpenseCategorySerializer(cats, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseCategoryDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        return get_object_or_404(ExpenseCategory, pk=pk)

    def get(self, request, pk):
        cat = self.get_object(pk)
        serializer = ExpenseCategorySerializer(cat)
        return Response(serializer.data)

    def put(self, request, pk):
        cat = self.get_object(pk)
        serializer = ExpenseCategorySerializer(cat, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        cat = self.get_object(pk)
        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── EXPENSE CRUD ────────────────────────────────────────────────────────────────

class ExpenseListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        expenses = Expense.objects.select_related('category').all()
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response(
                    {"detail": e.message_dict or e.messages},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        return get_object_or_404(Expense, pk=pk)

    def get(self, request, pk):
        exp = self.get_object(pk)
        serializer = ExpenseSerializer(exp)
        return Response(serializer.data)

    def put(self, request, pk):
        exp = self.get_object(pk)
        serializer = ExpenseSerializer(exp, data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data)
            except ValidationError as e:
                return Response(
                    {"detail": e.message_dict or e.messages},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        exp = self.get_object(pk)
        exp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#------ Genarate PDF Report ------
class ExpenseReportPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date   = request.GET.get("end_date")
        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # parse and validate
        start = parse_date(start_date)
        end   = parse_date(end_date)
        if not start or not end:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # fetch and group
        qs = Expense.objects.filter(date__range=(start, end)) \
                            .select_related('category') \
                            .order_by('category__name', 'date')
        grouped = {}
        overall_total = 0
        for exp in qs:
            cat = exp.category
            grp = grouped.setdefault(cat.id, {
                "category_name": cat.name,
                "items": [],
                "subtotal": 0
            })
            grp["items"].append(exp)
            grp["subtotal"] += float(exp.cost)
            overall_total += float(exp.cost)

        # build PDF
        response = HttpResponse(content_type="application/pdf")
        filename = f"rise_expenses_{start_date}_to_{end_date}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Title
        title = "THE RISE - HEAVY MACHINERY/ LORRY REPAIR EXPENSES"
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width/2, height - 2*cm, title)

        # Period & overall total
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width/2, height - 2.7*cm,
                              f"Period: {start_date} to {end_date}")
        pdf.drawRightString(width - 2*cm, height - 3.4*cm,
                            f"Overall Total: Rs. {overall_total:,.2f}")

        y = height - 4.5*cm

        # For each category
        for cat_data in grouped.values():
            if y < 5*cm:
                pdf.showPage()
                y = height - 4*cm

            # Category header
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(2*cm, y, cat_data["category_name"])
            pdf.drawRightString(width - 1*cm, y,
                                f"Subtotal: Rs. {cat_data['subtotal']:,.2f}")
            y -= 1*cm

            # Table rows
            data = [["Date","Sub Category", "Bill No", "Description", "Person", "Cost (Rs.)"]]
            for exp in cat_data["items"]:
                desc = "\n".join(wrap(exp.description, 30)) if exp.description else ""
                data.append([
                    exp.date.strftime("%Y-%m-%d"),
                    exp.sub_category,
                    exp.bill_no or "",
                    desc,
                    exp.responsible_person,
                    f"{exp.cost:,.2f}"
                ])

            table = Table(data, colWidths=[2*cm, 2.5*cm, 6*cm, 3*cm, 2.5*cm],
                          repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.grey),
                ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,0), 10),
                ("FONTSIZE", (0,1), (-1,-1), 8),
                ("ALIGN", (4,1), (4,-1), "RIGHT"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ]))

            # wrap & draw
            tw = table.wrap(width-4*cm, y)
            table.drawOn(pdf, 2*cm, y - tw[1])
            y -= (tw[1] + 1.5*cm)

        pdf.save()
        return response