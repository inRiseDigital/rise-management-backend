from django.urls import path
from .views import (
    MachineListCreate, MachineDetail,
    ExtractionRecordListCreate, ExtractionRecordDetail,
    OilPurchaseListCreate, OilPurchaseDetail
)

urlpatterns = [
    # Machine endpoints
    path('machines/', MachineListCreate.as_view(), name='machine-list-create'),
    path('machines/<int:pk>/', MachineDetail.as_view(), name='machine-detail'),

    # ExtractionRecord endpoints
    path('extractions/', ExtractionRecordListCreate.as_view(), name='extraction-list-create'),
    path('extractions/<int:pk>/', ExtractionRecordDetail.as_view(), name='extraction-detail'),

    # OilPurchase endpoints
    path('oil-purchases/', OilPurchaseListCreate.as_view(), name='oilpurchase-list-create'),
    path('oil-purchases/<int:pk>/', OilPurchaseDetail.as_view(), name='oilpurchase-detail'),
]