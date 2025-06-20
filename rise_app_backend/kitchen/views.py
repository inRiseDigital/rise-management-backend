from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Category, Expense
from .serializers import CategorySerializer, ExpenseSerializer
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from textwrap import wrap

# Kitchen categories
class CategoryListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Category.objects.all()
        serializer = CategorySerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Category, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = CategorySerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = CategorySerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Kitchen Expense
class ExpenseListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Expense.objects.all()
        serializer = ExpenseSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExpenseDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Expense, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = ExpenseSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = ExpenseSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
# Get all expenses for a specific category
class CategoryExpensesView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request, category_id):
        try:

            category = get_object_or_404(Category, id=category_id)
            expenses = category.expenses.all().order_by('-date') 
            total_amount = sum(expense.amount for expense in expenses)
            serializer = ExpenseSerializer(expenses, many=True)
            
            return Response({
                'category_id': category.id,
                'category_name': category.name,
                'category_description': category.description,
                'total_amount': total_amount,
                'expense_count': expenses.count(),
                'expenses': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
#report genarate       
class KitchenReportByPeriodPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date required"}, status=400)

        try:
            start = parse_date(start_date)
            end = parse_date(end_date)

            expenses = Expense.objects.filter(date__range=(start, end)).select_related('category').order_by('category__name', '-date')

            # Group expenses by category
            grouped = {}
            total_expenses = 0
            for expense in expenses:
                cat = expense.category
                if cat.id not in grouped:
                    grouped[cat.id] = {
                        'category_name': cat.name,
                        'expenses': [],
                        'total': 0
                    }
                grouped[cat.id]['expenses'].append(expense)
                grouped[cat.id]['total'] += expense.amount
                total_expenses += expense.amount

            # Create PDF response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="kitchen_expense_report_{start_date}_to_{end_date}.pdf"'
            
            pdf = canvas.Canvas(response, pagesize=A4)
            width, height = A4

            
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(width/2, height - 2*cm, "KITCHEN EXPENSE REPORT")
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(width/2, height - 2.7*cm, f"Period: {start_date} to {end_date}")
            pdf.drawRightString(width - 2*cm, height - 3.4*cm, f"Total Expenses: Rs. {total_expenses:,.2f}")

            current_y = height - 4.5*cm

            for category_data in grouped.values():
                if current_y < 4*cm:  
                    pdf.showPage()
                    current_y = height - 4*cm
                
                
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawString(2*cm, current_y, f"{category_data['category_name']}")
                pdf.drawRightString(width - 2*cm, current_y, f"Total: Rs. {category_data['total']:,.2f}")
                current_y -= 1*cm

                
                data = [['No', 'Date', 'Bill No', 'Description', 'Responsible', 'Amount']]
                
                # Table data
                for idx, expense in enumerate(category_data['expenses'], 1):
                    # Wrap description text
                    desc = '\\n'.join(wrap(expense.description, 30)) if expense.description else ''
                    
                    data.append([
                        idx,
                        expense.date.strftime("%Y-%m-%d"),
                        expense.bill_no,
                        desc,
                        expense.responsible_person,
                        f"Rs. {expense.amount:,.2f}"
                    ])

                
                col_widths = [1*cm, 2.5*cm, 2.5*cm, 6*cm, 3*cm, 3*cm]
                
                table = Table(data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (3, 1), (3, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))

                
                table_height = len(data) * 0.6*cm  
                if current_y - table_height < 2*cm:
                    pdf.showPage()
                    current_y = height - 4*cm

                table.wrapOn(pdf, width, height)
                table.drawOn(pdf, 2*cm, current_y - table_height)
                current_y -= (table_height + 2*cm)

            pdf.save()
            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate report: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )