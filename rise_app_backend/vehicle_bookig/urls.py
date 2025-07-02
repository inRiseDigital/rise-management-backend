# vehicles/urls.py

from django.urls import path
from .views import (
    VehicleListCreateView, VehicleDetailView, BookingCreateView, VehicleBookingsView
)

urlpatterns = [
    # Vehicle CRUD
    path('vehicles/',                       VehicleListCreateView.as_view(), name='vehicle-list-create'),
    path('vehicles/<int:pk>/',              VehicleDetailView.as_view(),     name='vehicle-detail'),

    path('vehicles/<int:pk>/bookings/', VehicleBookingsView.as_view(), name='vehicle-bookings'),
    path('bookings/',                 BookingCreateView.as_view(), name='booking-create'),
]
