from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import MilkCollection, CostEntry
from .serializers import MilkCollectionSerializer, CostEntrySerializer
from django.utils.dateparse import parse_date

# List & Create
class MilkCollectionListCreateView(APIView):
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

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
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Retrieve, Update, Delete
class MilkCollectionDetailView(APIView):
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