from django.db import models
from django.core.exceptions import ValidationError

class Vehicle(models.Model):
    name        = models.CharField(max_length=100)
    plate_no    = models.CharField(max_length=50, unique=True)
    seats       = models.PositiveIntegerField()
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.plate_no})"


class Booking(models.Model):
    vehicle    = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    booked_by  = models.CharField(max_length=100)  # link to user/email if you like
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # 1) start < end
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")
        # 2) no overlap
        overlap = Booking.objects.filter(
            vehicle=self.vehicle,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        if overlap.exists():
            raise ValidationError("That time slot is already booked.")

    def save(self, *args, **kwargs):
        self.full_clean()  # calls clean() and raises if invalid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle} from {self.start_time} to {self.end_time}"
