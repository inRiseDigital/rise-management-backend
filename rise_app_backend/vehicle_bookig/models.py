# vehicle_bookig/models.py

from django.db import models
from django.core.exceptions import ValidationError

class Vehicle(models.Model):
    name      = models.CharField(max_length=100)
    plate_no  = models.CharField(max_length=50, unique=True)
    seats     = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.plate_no})"


class Booking(models.Model):
    vehicle    = models.ForeignKey(
        Vehicle,                 # ← refer directly, no import needed
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    booked_by  = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # validation logic here
        ...

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
