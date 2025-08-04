from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Machine, ExtractionRecord, OilPurchase
from .serializers import MachineSerializer, ExtractionRecordSerializer, OilPurchaseSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
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