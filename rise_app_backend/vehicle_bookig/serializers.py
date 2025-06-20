
from rest_framework import serializers
from .models import Vehicle, Booking

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehicle
        fields = ["id", "name", "plate_no", "seats"]

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Booking
        fields = ["id", "vehicle", "start_time", "end_time", "booked_by", "created_at"]
        read_only_fields = ["created_at"]
