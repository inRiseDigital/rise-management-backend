# vehicles/serializers.py

from rest_framework import serializers
from .models import Vehicle, Booking


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'name', 'plate_no', 'seats', 'updated_at']

# vehicles/serializers.py


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Booking
        fields = ['id', 'vehicle', 'start_time', 'end_time', 'booked_by', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, data):
        """
        Called before .create()/.update() to check the entire payload.
        We look for any existing booking (other than ourselves) that overlaps.
        """
        vehicle    = data['vehicle']
        start_time = data['start_time']
        end_time   = data['end_time']

        if end_time <= start_time:
            raise serializers.ValidationError("End time must be after start time.")

        # Look for any booking that collides
        overlap_qs = Booking.objects.filter(
            vehicle=vehicle,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        # If this is an update, exclude the instance itself
        if self.instance:
            overlap_qs = overlap_qs.exclude(pk=self.instance.pk)

        if overlap_qs.exists():
            raise serializers.ValidationError("That time slot is already booked.")

        return data

