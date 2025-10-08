from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from textwrap import wrap
import logging

logger = logging.getLogger(__name__)

# --- Project Views ---
class ProjectListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProjectDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, id):
        return get_object_or_404(Project, id=id)

    def get(self, request, id):
        project = self.get_object(id)
        serializer = ProjectSerializer(project)
        return Response(serializer.data)

    def put(self, request, id):
        project = self.get_object(id)
        serializer = ProjectSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        project = self.get_object(id)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# --- Task Views ---
class TaskListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        tasks = Task.objects.all()
        serializer = TaskSerializer(tasks, many=True)
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
        return get_object_or_404(Task, pk=pk)

    def get(self, request, pk):
        task = self.get_object(pk)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    def put(self, request, pk):
        task = self.get_object(pk)
        serializer = TaskSerializer(task, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        task = self.get_object(pk)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
'''
# --- ManPower Views ---
#class ManPowerListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        manpower = ManPower.objects.all()
        serializer = ManPowerSerializer(manpower, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ManPowerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#class ManPowerDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(ManPower, pk=pk)

    def get(self, request, pk):
        manpower = self.get_object(pk)
        serializer = ManPowerSerializer(manpower)
        return Response(serializer.data)

    def put(self, request, pk):
        manpower = self.get_object(pk)
        serializer = ManPowerSerializer(manpower, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        manpower = self.get_object(pk)
        manpower.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
'''
#retrieve onging tasks for a project
class OngoingTasksView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, project_id):
        tasks = Task.objects.filter(project_id=project_id, status='ongoing')
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

#retrieve tasks by project name
class TasksByProjectNameView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        project_name = request.GET.get('project_name')

        logger.info(f"🔍 TasksByProjectNameView called with project_name: {project_name}")
        print(f"🔍 TasksByProjectNameView called with project_name: {project_name}")

        if not project_name:
            logger.warning("❌ Missing project_name parameter")
            print("❌ Missing project_name parameter")
            return Response({"error": "project_name parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find project by name (case-insensitive)
            project = Project.objects.get(name__iexact=project_name)
            logger.info(f"✅ Found project: ID={project.id}, Name={project.name}")
            print(f"✅ Found project: ID={project.id}, Name={project.name}")

            # Get all tasks for this project
            tasks = Task.objects.filter(project=project)
            task_count = tasks.count()
            logger.info(f"✅ Found {task_count} tasks for project '{project.name}'")
            print(f"✅ Found {task_count} tasks for project '{project.name}'")

            serializer = TaskSerializer(tasks, many=True)

            return Response({
                "project_id": project.id,
                "project_name": project.name,
                "project_description": project.description,
                "tasks": serializer.data,
                "task_count": task_count
            })
        except Project.DoesNotExist:
            logger.error(f"❌ Project with name '{project_name}' not found")
            print(f"❌ Project with name '{project_name}' not found")
            return Response(
                {"error": f"Project with name '{project_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class MepReportPDFExportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        note = request.GET.get("note")
        signature = request.GET.get("signature")
        designation = request.GET.get("designation")
        
        if not start_date or not end_date:
            return Response({"error": "start_date and end_date required"}, status=400)

        start = parse_date(start_date)
        end = parse_date(end_date)

        task_data = Task.objects.filter(date__range=(start, end)).order_by('update_date')

        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="PROGRESS_REPORT_MEP_{start}_{end}.pdf"'
        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        pdf.setTitle("PROGRESS REPORT - MEP / MAINTENANCE")

        # Title
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width / 2, height - 2 * cm, f"PROGRESS REPORT - MEP / MAINTENANCE ({start} to {end})")

        current_y = height - 3.0 * cm  # start drawing tables below title

        # === Draw Task Progress Table ===
        progress_data = self._build_progress_table_data(task_data)
        progress_col_widths = [2*cm, 9.5*cm, 3.5*cm, 3*cm, 2.5*cm]
        current_y = self._draw_table(pdf, progress_data, progress_col_widths, width, current_y)
        
        if note:
            wrapped_note = wrap(f"Note: {note}", width=140)  # adjust width if needed
            text_object = pdf.beginText()
            text_object.setTextOrigin(0.2 * cm, current_y - 1 * cm)
            text_object.setFont("Helvetica", 10)

            for line in wrapped_note:
                text_object.textLine(line)

        pdf.drawText(text_object)
        current_y -= (len(wrapped_note) * 0.5 * cm)
        
        
        # === Draw Manpower Table ===
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(0.2 * cm, current_y + -2 * cm, "MAN POWER")
        
        manpower_data = self._build_manpower_table_data(task_data)
        manpower_col_widths = [2*cm, 10*cm, 3*cm, 3*cm, 3*cm]
        self._draw_table(pdf, manpower_data, manpower_col_widths, width, current_y - 1 * cm)
        
        # Set bold font for label
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(0.2 * cm, current_y - 10 * cm, "Signature:")

        # Set regular font for signature value
        pdf.setFont("Helvetica", 10)
        pdf.drawString(2 * cm, current_y - 10 * cm, signature or "")
        
        # Set bold font for label
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(0.2 * cm, current_y - 11 * cm, "Designation:")

        # Set regular font for designation value
        pdf.setFont("Helvetica", 11)
        pdf.drawString(2.5 * cm, current_y - 11 * cm, designation or "")
        
        
        pdf.showPage()
        pdf.save()
        return response
        
        
        
    def _build_progress_table_data(self, tasks):
        data = [['No', 'WORK DESCRIPTION', 'Location', 'Status', 'Qty (%)']]
        for i, task in enumerate(tasks, start=1):
            data.append([i, task.description, task.location, task.status, task.qty])
        return data

    def _build_manpower_table_data(self, tasks):
        data = [['No', 'WORK DESCRIPTION', 'Unskilled', 'Semi-skilled', 'Skilled']]
        total_u = total_s = total_sk = 0
        for i, task in enumerate(tasks, start=1):
            data.append([i, task.description, task.unskills, task.semi_skills, task.skills])
            total_u += task.unskills
            total_s += task.semi_skills
            total_sk += task.skills
        data.append(['TOTAL', '', total_u, total_s, total_sk])
        return data

    def _draw_table(self, pdf, data, col_widths, page_width, y_start):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            #('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ]))
        table.wrapOn(pdf, page_width, y_start)
        table_height = len(data) * 0.9 * cm
        table.drawOn(pdf, x=(page_width - sum(col_widths)) / 2, y=y_start - table_height)
        return y_start - table_height  # return new Y for next section
