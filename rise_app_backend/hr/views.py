from django.shortcuts import render
from rest_framework import viewsets
from .models import staff, leave
from .serializers import StaffSerializer, LeaveSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# -- Staff Views --
class StaffListCreateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        staff_qs = staff.objects.all()
        serializer = StaffSerializer(staff_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = StaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StaffDetailView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self, staff_id):
        return get_object_or_404(staff, staff_id=staff_id)

    def get(self, request, pk):
        staff = self.get_object(pk)
        serializer = StaffSerializer(staff)
        return Response(serializer.data)

    def put(self, request, staff_id):
        staff = self.get_object(staff_id)
        serializer = StaffSerializer(staff, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        staff = self.get_object(pk)
        staff.delete()
        return Response({'message': f"Staff {pk} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class LeaveListView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        leaves = leave.objects.all()
        serializer = LeaveSerializer(leaves, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeaveSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LeaveListDetails(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(leave, pk=pk)

    def get(self, request, pk):
        leave_obj = self.get_object(pk)
        serializer = LeaveSerializer(leave_obj)
        return Response(serializer.data)

    def put(self, request, pk):
        leave_obj = self.get_object(pk)
        serializer = LeaveSerializer(leave_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        # Partial update for fields like leave_status
        leave_obj = self.get_object(pk)
        serializer = LeaveSerializer(leave_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        leave_obj = self.get_object(pk)
        leave_obj.delete()
        return Response(
            {'message': f"Leave {pk} deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

# -- Leave Approval/Decline Actions --
class LeaveApproveView(APIView):
    """
    Approve a pending leave: sets leave_status to 'Approved'.
    """
    def post(self, request, pk):
        leave_obj = get_object_or_404(leave, pk=pk)
        if leave_obj.leave_status != "Pending":
            return Response({"detail": "Only pending leaves can be approved."}, status=status.HTTP_400_BAD_REQUEST)
        leave_obj.leave_status = "Approved"
        leave_obj.save()
        serializer = LeaveSerializer(leave_obj)
        return Response(serializer.data)

class LeaveDeclineView(APIView):
    """
    Decline a pending leave: sets leave_status to 'Declined'.
    """
    def post(self, request, pk):
        leave_obj = get_object_or_404(leave, pk=pk)
        if leave_obj.leave_status != "Pending":
            return Response({"detail": "Only pending leaves can be declined."}, status=status.HTTP_400_BAD_REQUEST)
        leave_obj.leave_status = "Declined"
        leave_obj.save()
        serializer = LeaveSerializer(leave_obj)
        return Response(serializer.data)
    
# Pending leave view
class PendingLeaveListView(APIView):
    """
    List all pending leaves.
    """
    def get(self, request):
        pending_leaves = leave.objects.filter(leave_status="Pending")
        serializer = LeaveSerializer(pending_leaves, many=True)
        return Response(serializer.data)
    

#signup
class StaffSignUpView(APIView):
    permission_classes = [AllowAny]  
    def post(self, request):
        serializer = StaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors,  status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('email')
        password = request.data.get('password')
        
        try:
            user = staff.objects.get(email=username, password=password)
            # In production, you should use proper password hashing
            return Response({
                'staff_id': user.staff_id,
                'username': user.username,
                'name': user.staff_name,
                'role': user.staff_position,
                'department': user.staff_department,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        except staff.DoesNotExist:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
