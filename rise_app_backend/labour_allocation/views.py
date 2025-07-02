# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Task, Labour, TaskAllocation
from .serializers import (
    TaskSerializer, LabourSerializer, TaskAllocationSerializer
)


class TaskListCreate(APIView):
    permission_classes = [AllowAny] 

    def get(self, request):
        qs = Task.objects.all()
        serializer = TaskSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class TaskDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    def put(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        serializer = TaskSerializer(task, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# — Labours CRUD —

class LabourListCreate(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Labour.objects.all()
        serializer = LabourSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LabourSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class LabourDetail(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        labour = get_object_or_404(Labour, pk=pk)
        serializer = LabourSerializer(labour)
        return Response(serializer.data)

    def put(self, request, pk):
        labour = get_object_or_404(Labour, pk=pk)
        serializer = LabourSerializer(labour, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        labour = get_object_or_404(Labour, pk=pk)
        labour.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# — TaskAllocations CRUD — assign multiple labours to tasks —

class TaskAllocationListCreate(APIView):
    permission_classes = [AllowAny] 
    def get(self, request, task_id):
        """
        List all allocations for a given task.
        """
        allocations = TaskAllocation.objects.filter(task_id=task_id)
        serializer = TaskAllocationSerializer(allocations, many=True)
        return Response(serializer.data)

    def post(self, request, task_id):
        """
        Create a new allocation: assign one labour to this task.
        JSON body must include "labour", "mandays", and optionally "meals_cost".
        """
        data = request.data.copy()
        data["task"] = task_id
        serializer = TaskAllocationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class TaskAllocationDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, task_id, pk):
        alloc = get_object_or_404(TaskAllocation, pk=pk, task_id=task_id)
        serializer = TaskAllocationSerializer(alloc)
        return Response(serializer.data)

    def put(self, request, task_id, pk):
        alloc = get_object_or_404(TaskAllocation, pk=pk, task_id=task_id)
        data = request.data.copy()
        data["task"] = task_id
        serializer = TaskAllocationSerializer(alloc, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, task_id, pk):
        alloc = get_object_or_404(TaskAllocation, pk=pk, task_id=task_id)
        alloc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
