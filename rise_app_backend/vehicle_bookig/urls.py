# urls.py

from django.urls import path
from .views import VehicleList, VehicleAvailability, BookingCreate

urlpatterns = [
    path("vehicles/", VehicleList.as_view(), name="vehicle-list"),
    path("vehicles/<int:vehicle_id>/bookings/", VehicleAvailability.as_view(), name="vehicle-availability"),
    path("bookings/", BookingCreate.as_view(), name="booking-create"),
]
