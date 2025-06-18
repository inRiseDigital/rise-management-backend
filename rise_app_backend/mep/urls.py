from django.urls import path
from .views import (
    ProjectListCreateView, ProjectDetailView,
    TaskListCreateView, TaskDetailView,
    OngoingTasksView,MepReportPDFExportView
)

urlpatterns = [
    # Project Endpoints
    path('MEP_projects/', ProjectListCreateView.as_view(), name='project_list_create'),
    path('MEP_projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),

    # Task Endpoints
    path('MEP_tasks/', TaskListCreateView.as_view(), name='task_list_create'),
    path('MEP_tasks/<int:pk>/', TaskDetailView.as_view(), name='task_detail'),
    path('MEP_projects/<int:project_id>/tasks/ongoing/', OngoingTasksView.as_view(), name='ongoing_tasks'),

    # Manpower Endpoints
    #path('MEP_manpower/', ManPowerListCreateView.as_view(), name='manpower_list_create'),
    #path('MEP_manpower/<int:pk>/', ManPowerDetailView.as_view(), name='manpower_detail'),
    
    path('MEP/pdf-export/', MepReportPDFExportView.as_view(), name='milk_pdf_export'),
]
