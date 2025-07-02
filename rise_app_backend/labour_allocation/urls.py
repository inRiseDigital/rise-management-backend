# urls.py

from django.urls import path
from .views import (
    TaskListCreate, TaskDetail,
    LabourListCreate, LabourDetail,
    TaskAllocationListCreate, TaskAllocationDetail
)

urlpatterns = [
    # Tasks
    path("tasks/",            TaskListCreate.as_view(),          name="task-list-create"),
    path("tasks/<int:pk>/",   TaskDetail.as_view(),              name="task-detail"),

    # Labours
    path("labours/",          LabourListCreate.as_view(),        name="labour-list-create"),
    path("labours/<int:pk>/", LabourDetail.as_view(),            name="labour-detail"),

    # Allocations (one task → many labours)
    path("tasks/labour/allocations/<int:task_id>/",TaskAllocationListCreate.as_view(),name="allocation-list-create"
    ),
    path(
      "tasks/allocations/",TaskAllocationDetail.as_view(),name="allocation-detail"
    ),
]
