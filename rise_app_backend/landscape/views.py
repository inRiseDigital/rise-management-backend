from django.shortcuts import render
from .models import Project, Project_Issuce, Maintenance,DailyTask
from .serializers import ProjectSerializer, ProjectIssuceSerializer, MaintenanceSerializer, DailyTaskSerializer
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny

# Project
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
    def get_object(self, pk):
        return get_object_or_404(Project, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = ProjectSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = ProjectSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#Project_Issuce

class Project_IssuceListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Project_Issuce.objects.all()
        serializer = ProjectIssuceSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProjectIssuceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class Project_IssuceDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Project_Issuce, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = ProjectIssuceSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = ProjectIssuceSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
#Maintenance

class MaintenanceListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        projects = Maintenance.objects.all()
        serializer = MaintenanceSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MaintenanceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MaintenanceDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Maintenance, pk=pk)

    def get(self, request, pk):
        project = self.get_object(pk)
        serializer = MaintenanceSerializer(project)
        return Response(serializer.data)

    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = MaintenanceSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
#daily Task
class TaskListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        tasks = DailyTask.objects.all()
        serializer = DailyTaskSerializer(tasks, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DailyTaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(DailyTask, pk=pk)

    def get(self, request, pk):
        task = self.get_object(pk)
        serializer = DailyTaskSerializer(task)
        return Response(serializer.data)

    def put(self, request, pk):
        task = self.get_object(pk)
        serializer = DailyTaskSerializer(task, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        task = self.get_object(pk)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)