from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
     StaffListCreateView, StaffDetailView,
     LeaveListView, LeaveListDetails,PendingLeaveListView,
     LeaveApproveView, LeaveDeclineView,StaffSignUpView, LoginView, LabourListCreateView,LabourDetailView,AllocationCreateView,
     DepartmentListCreateView,DepartmentDetailView,AllocationDoneWorkUpdateView, AllocationListCreateView, AllocationDetailView
     
 )
urlpatterns = [
     path('staff', StaffListCreateView.as_view(), name='staff-list'),
     path('staff/<str:pk>', StaffDetailView.as_view(), name='staff-detail'),
     path('leave', LeaveListView.as_view(), name='leave-list'),
     path('leave/<str:pk>', LeaveListDetails.as_view(), name='leave-detail'),
     path('pending_leave', PendingLeaveListView.as_view(), name='leave-detail'),
     path('leave_approval/<int:pk>', LeaveApproveView.as_view(), name='leave-detail'),
     path('leave_decline/<int:pk>', LeaveDeclineView.as_view(), name='leave-detail'),
     
     path('department', DepartmentListCreateView.as_view(), name='staff-list'),
     path('department/<str:pk>', DepartmentDetailView.as_view(), name='staff-detail'),
     
     path('labour', LabourListCreateView.as_view(), name='labour-list'),
     path('labour/<str:pk>', LabourDetailView.as_view(), name='labour-detail'),
     
     path('signup/', StaffSignUpView.as_view(), name='staff-signup'),
     
     path('labour/assignments/', AllocationCreateView.as_view(), name='bulk-assignments'),
     
     #update allocation task progress
     path('labour/allocations/done_work/<int:pk>/',AllocationDoneWorkUpdateView.as_view(),name='allocation-done-work-update'),
     
     # Labour allocation and task management
     path('labour/allocations/',AllocationListCreateView.as_view(),name='allocation-list-create'),
     path('labour/allocations/<int:pk>/',AllocationDetailView.as_view(),name='allocation-detail'),

    # Login (get JWT tokens)
    #path('token/',   TokenObtainPairView.as_view(),   name='token_obtain_pair'),
    #path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('login/', LoginView.as_view(), name='login'),
]