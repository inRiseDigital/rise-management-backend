from django.urls import path
from .views import (LocationListCreateView,LocationDetailView,TaskListCreateView,TaskDetailView, TaskByLocationView, TasksByPeriodGroupedView
                    , TaskReportByPeriodPDFView, SubcategoriesListCreateView, SubcategoriesDetailView, SubcategoriesByLocationView)

urlpatterns = [
    # Add new location
    path('location/', LocationListCreateView.as_view(), name='project_list_create'),
    path('location/<int:pk>/', LocationDetailView.as_view(), name='project_detail'),
    
    # add sub category
    path('sub/', SubcategoriesListCreateView.as_view(), name='project_list_create'),
    path('sub/<int:pk>/', SubcategoriesDetailView.as_view(), name='project_detail'),
    
    #add daily task
    path('daily_task/', TaskListCreateView.as_view(), name='project_list_create'),
    path('daily_task/<int:pk>/', TaskDetailView.as_view(), name='project_detail'),
    
    #tasks done in selected location
    path('task_by_location/<int:location_id>/', TaskByLocationView.as_view(), name='project_detail'),
    
    #tasks done in selected time period
    path('tasks/by-period/', TasksByPeriodGroupedView.as_view(), name='tasks_by_period_grouped'),
    
    #genarate PDF for given time period
    path('tasks/pdf-by-period/', TaskReportByPeriodPDFView.as_view(), name='task_pdf_by_period'),
    
    #subcategories-by-location
    path('locations/subcategories/<int:location_id>/',SubcategoriesByLocationView.as_view(),name='subcategories-by-location'),
   
]