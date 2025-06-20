# views.py

from rest_framework import generics, status
from rest_framework.response import Response
from .models import Vehicle, Booking
from .serializers import VehicleSerializer, BookingSerializer


class VehicleList(generics.ListAPIView):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class VehicleAvailability(generics.GenericAPIView):
    serializer_class = BookingSerializer

    def get(self, request, vehicle_id):
        """
        Returns all free-time intervals for the next 7 days, or
        simply returns existing bookings so the client can invert.
        """
        # Here we return existing bookings; client can calculate free slots
        bookings = Booking.objects.filter(vehicle_id=vehicle_id).order_by("start_time")
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class BookingCreate(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        # Let save() + clean() enforce no-overlap
        return super().create(request, *args, **kwargs)
