# urls.py

from django.urls import path
from .views import (ExpenseCategoryListCreateView,ExpenseCategoryDetailView,ExpenseListCreateView,ExpenseDetailView,ExpenseReportPDFView
)

urlpatterns = [
    # Categories
    path('categories/',               ExpenseCategoryListCreateView.as_view(), name='cat-list-create'),
    path('categories/<int:pk>/',      ExpenseCategoryDetailView.as_view(),     name='cat-detail'),

    # Expenses
    path('expenses/',                 ExpenseListCreateView.as_view(),         name='expense-list-create'),
    path('expenses/<int:pk>/',        ExpenseDetailView.as_view(),             name='expense-detail'),

    path("reports/",ExpenseReportPDFView.as_view(),name="expense-report"),
]
