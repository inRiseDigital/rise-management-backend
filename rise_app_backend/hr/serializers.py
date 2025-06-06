from rest_framework import serializers
from .models import staff, leave, department, site, vehicles, expense_category, expenses,desal_purchase, responsible_person,expense_sub_category
from django.contrib.auth.hashers import make_password


class StaffSerializer(serializers.ModelSerializer):
    used_leaves      = serializers.SerializerMethodField()
    available_leaves = serializers.SerializerMethodField()

    class Meta:
        model = staff
        # include all your staff fields plus the two counters
        fields = [
            "staff_id", "staff_name", "staff_email", "staff_phone",
            "staff_department", "staff_position", "staff_joining_date",
            "used_leaves", "available_leaves", "username", "password",
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_used_leaves(self, obj):
        return obj.used_leaves

    def get_available_leaves(self, obj):
        return obj.available_leaves
    
    #def create(self, validated_data):
    #    validated_data['password'] = make_password(validated_data['password'])
    #    return super().create(validated_data)


class LeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = leave
        fields = '__all__'
        

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = department
        fields = '__all__'
        
class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = site
        fields = '__all__'  

class VehiclesSerializer(serializers.ModelSerializer):
    class Meta:
        model = vehicles
        fields = '__all__'
        
class ExpenseSectionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = expense_category
        fields = '__all__'
        
class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = expenses
        fields = '__all__'  
        
class DesalPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = desal_purchase
        fields = '__all__'
        
class ResponsiblePersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = responsible_person
        fields = '__all__'
class ExpenseSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = expense_sub_category
        fields = '__all__'
