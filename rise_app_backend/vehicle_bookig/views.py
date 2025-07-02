from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Vehicle, Booking
from .serializers import VehicleSerializer,BookingSerializer
from django.core.exceptions import ValidationError

from django.http import HttpResponse
from textwrap import wrap

# --- Vehicle Views ---
class VehicleListCreateView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        vehicles = Vehicle.objects.all()
        serializer = VehicleSerializer(vehicles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VehicleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VehicleDetailView(APIView):
    permission_classes = [AllowAny] 
    def get_object(self, pk):
        return get_object_or_404(Vehicle, pk=pk)

    def get(self, request, pk):
        vehicle = self.get_object(pk)
        serializer = VehicleSerializer(vehicle)
        return Response(serializer.data)

    def put(self, request, pk):
        vehicle = self.get_object(pk)
        serializer = VehicleSerializer(vehicle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        vehicle = self.get_object(pk)
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class VehicleBookingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        """
        List all existing bookings for vehicle=pk
        """
        vehicle = get_object_or_404(Vehicle, pk=pk)
        qs = vehicle.bookings.order_by('start_time')
        serializer = BookingSerializer(qs, many=True)
        return Response(serializer.data)


class BookingCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)