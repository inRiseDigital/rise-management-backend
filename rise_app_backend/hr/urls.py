from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
     StaffListCreateView, StaffDetailView,
     LeaveListView, LeaveListDetails,PendingLeaveListView,
     LeaveApproveView, LeaveDeclineView,StaffSignUpView, LoginView
     
 )
urlpatterns = [
     path('staff', StaffListCreateView.as_view(), name='staff-list'),
     path('staff/<str:pk>', StaffDetailView.as_view(), name='staff-detail'),
     path('leave', LeaveListView.as_view(), name='leave-list'),
     path('leave/<str:pk>', LeaveListDetails.as_view(), name='leave-detail'),
     path('pending_leave', PendingLeaveListView.as_view(), name='leave-detail'),
     path('leave_approval/<int:pk>', LeaveApproveView.as_view(), name='leave-detail'),
     path('leave_decline/<int:pk>', LeaveDeclineView.as_view(), name='leave-detail'),
     
     path('signup/', StaffSignUpView.as_view(), name='staff-signup'),

    # Login (get JWT tokens)
    #path('token/',   TokenObtainPairView.as_view(),   name='token_obtain_pair'),
    #path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('login/', LoginView.as_view(), name='login'),
]