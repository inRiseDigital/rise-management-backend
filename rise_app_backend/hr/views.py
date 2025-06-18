from django.shortcuts import render
from rest_framework import viewsets
from .models import Staff, leave, department, site, vehicles, responsible_person
from .serializers import StaffSerializer, LeaveSerializer, DepartmentSerializer, SiteSerializer, VehiclesSerializer, ResponsiblePersonSerializer
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
        staff_qs = Staff.objects.all()
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
        return get_object_or_404(Staff, staff_id=staff_id)

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
            user = Staff.objects.get(email=username, password=password)
            # In production, you should use proper password hashing
            return Response({                'staff_id': user.staff_id,
                'username': user.username,
                'name': user.staff_name,
                'role': user.roll,
                'department': user.staff_department,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)


# -- vehicle Views --
class VehicleListCreateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        staff_qs = vehicles.objects.all()
        serializer = VehiclesSerializer(staff_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VehiclesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VehiclesDetailView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self, number_plate):
        return get_object_or_404(vehicles, number_plate=number_plate)

    def get(self, request, pk):
        staff = self.get_object(pk)
        serializer = VehiclesSerializer(staff)
        return Response(serializer.data)

    def put(self, request, staff_id):
        staff = self.get_object(staff_id)
        serializer = VehiclesSerializer(staff, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        staff = self.get_object(pk)
        staff.delete()
        return Response({'message': f"Staff {pk} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
# -- Department Views --
class DepartmentListCreateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        department_qs = department.objects.all()
        serializer = DepartmentSerializer(department_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class DepartmentDetailView(APIView):    
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self, dpt_id):
        return get_object_or_404(department, dpt_id=dpt_id)

    def get(self, request, pk):
        department_obj = self.get_object(pk)
        serializer = DepartmentSerializer(department_obj)
        return Response(serializer.data)

    def put(self, request, dpt_id):
        department_obj = self.get_object(dpt_id)
        serializer = DepartmentSerializer(department_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        department_obj = self.get_object(pk)
        department_obj.delete()
        return Response({'message': f"Department {pk} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    
# -- Location Views --
class LocationListCreateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        location_qs = site.objects.all()
        serializer = SiteSerializer(location_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SiteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class LocationDetailView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self, location_id):
        return get_object_or_404(site, location_id=location_id)

    def get(self, request, pk):
        location_obj = self.get_object(pk)
        serializer = SiteSerializer(location_obj)
        return Response(serializer.data)

    def put(self, request, location_id):
        location_obj = self.get_object(location_id)
        serializer = SiteSerializer(location_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        location_obj = self.get_object(pk)
        location_obj.delete()
        return Response({'message': f"Location {pk} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
# -- Responsible Person Views --
class ResponsiblePersonListCreateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        responsible_person_qs = responsible_person.objects.all()
        serializer = ResponsiblePersonSerializer(responsible_person_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ResponsiblePersonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ResponsiblePersonDetailView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self, id):
        return get_object_or_404(responsible_person, id=id)

    def get(self, request, pk):
        responsible_person_obj = self.get_object(pk)
        serializer = ResponsiblePersonSerializer(responsible_person_obj)
        return Response(serializer.data)

    def put(self, request, id):
        responsible_person_obj = self.get_object(id)
        serializer = ResponsiblePersonSerializer(responsible_person_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        responsible_person_obj = self.get_object(pk)
        responsible_person_obj.delete()
        return Response({'message': f"Responsible Person {pk} deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
