from django.urls import path
from .views import UniversalReportView, UniversalReportBase64View, UniversalReportFromDataView

urlpatterns = [
    path('universal-report/', UniversalReportView.as_view(), name='universal-report'),
    path('universal-report-base64/', UniversalReportBase64View.as_view(), name='universal-report-base64'),
    path('universal-report-from-data/', UniversalReportFromDataView.as_view(), name='universal-report-from-data'),
]
