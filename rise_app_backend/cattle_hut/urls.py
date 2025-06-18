from django.urls import path
from .views import (
    MilkCollectionListCreateView,
    MilkCollectionDetailView,
    CostEntryListCreateView,
    CostEntryDetailView,
    MilkCollectionPDFExportView
)

urlpatterns = [
    # MilkCollection endpoints
    path('milk/', MilkCollectionListCreateView.as_view(), name='milk_list_create'),
    path('milk/<int:id>/', MilkCollectionDetailView.as_view(), name='milk_detail'),

    # CostEntry endpoints
    path('costs/', CostEntryListCreateView.as_view(), name='cost_list_create'),
    path('costs/<int:id>/', CostEntryDetailView.as_view(), name='cost_detail'),
    
    # PDF Export for Milk Collection
    path('milk/pdf-export/', MilkCollectionPDFExportView.as_view(), name='milk_pdf_export'),
]
