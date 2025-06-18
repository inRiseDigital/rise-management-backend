from django.urls import path
from .views import (LocationListCreateView,LocationDetailView,TaskListCreateView,TaskDetailView, TaskByLocationView, TasksByPeriodGroupedView
                    , TaskReportByPeriodPDFView)

urlpatterns = [
    path('location/', LocationListCreateView.as_view(), name='project_list_create'),
    path('location/<int:pk>/', LocationDetailView.as_view(), name='project_detail'),
    
    path('daily_task/', TaskListCreateView.as_view(), name='project_list_create'),
    path('daily_task/<int:pk>/', TaskDetailView.as_view(), name='project_detail'),
    
    path('task_by_location/<int:location_id>/', TaskByLocationView.as_view(), name='project_detail'),
    path('tasks/by-period/', TasksByPeriodGroupedView.as_view(), name='tasks_by_period_grouped'),
    path('tasks/pdf-by-period/', TaskReportByPeriodPDFView.as_view(), name='task_pdf_by_period'),
]