from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView,
    ExpenseListCreateView, ExpenseDetailView,
    CategoryExpensesView, KitchenReportByPeriodPDFView
)       

urlpatterns = [
    path ('category/',CategoryListCreateView.as_view(),name='category_list_create'),
    path ('category/<int:pk>', CategoryDetailView.as_view(),name='category_details'),    path('expense/', ExpenseListCreateView.as_view(), name='expense_list_create'),
    path('expense/<int:pk>', ExpenseDetailView.as_view(), name='expense_details'),
    path('category/expenses/<int:category_id>/', CategoryExpensesView.as_view(), name='category_expenses'),
    path('report/', KitchenReportByPeriodPDFView.as_view(), name='kitchen_report')
]