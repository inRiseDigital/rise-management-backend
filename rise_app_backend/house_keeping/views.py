from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Location, Task, Subcategories
from .serilizer import LocationSerializer, TaskSerializer, SubcategoriesSerializer
from django.utils.dateparse import parse_date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.http import HttpResponse
from django.utils.dateparse import parse_date

# Create your views here.
class LocationListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Location.objects.all()
        serializer = LocationSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LocationDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Location, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = LocationSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = LocationSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    ###################################
# subcategory
class SubcategoriesListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Subcategories.objects.all()
        serializer = SubcategoriesSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SubcategoriesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubcategoriesDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Subcategories, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = SubcategoriesSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = SubcategoriesSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

######################------------
class TaskListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Task.objects.all()
        serializer = TaskSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Location, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = TaskSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = TaskSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
####################
class TaskByLocationView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request, location_id):
        location = get_object_or_404(Location, id=location_id)
        tasks = location.tasks.all()  # related_name='task'
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            'location_id': location.id,
            'location_name': location.name,
            'tasks': serializer.data
        }, status=status.HTTP_200_OK)
        
###########
class TasksByPeriodGroupedView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date are required"}, status=status.HTTP_400_BAD_REQUEST)

        start = parse_date(start_date)
        end = parse_date(end_date)

        if not start or not end:
            return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

        # Get all tasks in the given date range
        tasks = Task.objects.filter(update_date__range=(start, end)).select_related('location')

        # Group tasks by location
        grouped_data = {}
        for task in tasks:
            loc = task.location
            loc_id = loc.id

            if loc_id not in grouped_data:
                grouped_data[loc_id] = {
                    'location_id': loc_id,
                    'location_name': loc.name,
                    'tasks': []
                }

            grouped_data[loc_id]['tasks'].append({
                'subcategory': task.subcategory.subcategory,
                'cleaning_type': task.cleaning_type,
                'update_date': task.update_date
            })

        return Response(list(grouped_data.values()))
    
class TaskReportByPeriodPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date required"}, status=400)

        start = parse_date(start_date)
        end = parse_date(end_date)

        tasks = Task.objects.filter(update_date__range=(start, end)).select_related('location').order_by('location__name', 'update_date')

        # Prepare data grouped by location
        grouped = {}
        for task in tasks:
            loc = task.location
            if loc.id not in grouped:
                grouped[loc.id] = {
                    'location_name': loc.name,
                    'tasks': []
                }
            grouped[loc.id]['tasks'].append(task)

        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="task_report_{start}_{end}.pdf"'
        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width / 2, height - 2 * cm, f"TASK REPORT ({start} to {end})")

        current_y = height - 3 * cm

        for location in grouped.values():
            # Draw location title
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(2 * cm, current_y, f"Location: {location['location_name']}")
            current_y -= 1 * cm

            data = [['No','Location', 'Subcategory', 'Cleaning Type', 'Update Date']]
            for idx, task in enumerate(location['tasks'], start=1):
                data.append([
                    idx,
                    task.location.name,
                    task.subcategory.subcategory,
                    task.cleaning_type,
                    task.update_date.strftime("%Y-%m-%d")
                ])

            col_widths = [1.5*cm, 4*cm, 4*cm, 6*cm, 3*cm]
            table = Table(data, colWidths=col_widths)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
            table.setStyle(style)

            table.wrapOn(pdf, width, current_y)
            table_height = 0.9 * cm * len(data)

            if current_y - table_height < 2 * cm:
                pdf.showPage()
                current_y = height - 2 * cm
                pdf.setFont("Helvetica-Bold", 12)

            table.drawOn(pdf, x=2 * cm, y=current_y - table_height)
            current_y -= (table_height + 1 * cm)

        pdf.showPage()
        pdf.save()
        return response
    
class SubcategoriesByLocationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request,location_id):
        location = get_object_or_404(Location, id=location_id)
        subs = location.subcategories.all()
        serializer = SubcategoriesSerializer(subs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)