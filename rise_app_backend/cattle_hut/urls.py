from django.urls import path
from .views import (
    MilkCollectionListCreateView,
    MilkCollectionDetailView,
    CostEntryListCreateView,
    CostEntryDetailView,
    MilkCollectionPDFExportView,
    LatestMilkCollectionView,
    MonthToDateIncomeView
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
    path("milk_collection/latest/", LatestMilkCollectionView.as_view(), name="latest-milk-collection"),
    path("milk_collection/month_to_date_income/", MonthToDateIncomeView.as_view(), name="month-to-date-income"), #GET /api/milk_collection/month_to_date_income/--- OR---- GET /api/milk_collection/month_to_date_income/?date=2025-03-10
]
