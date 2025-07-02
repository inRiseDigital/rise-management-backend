from rest_framework import serializers
from .models import Staff, leave, Department, site, vehicles, expense_category, expenses,desal_purchase,expense_sub_category, Labour, Allocation
from django.contrib.auth.hashers import make_password


class StaffSerializer(serializers.ModelSerializer):
    used_leaves      = serializers.SerializerMethodField()
    available_leaves = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "staff_id", "staff_name", "staff_email", "staff_phone",
            "staff_department", "roll", "staff_joining_date",
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
        model = Department
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
        
class ExpenseSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = expense_sub_category
        fields = '__all__'

#############

class LabourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Labour
        fields = '__all__'
        
class AllocationSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
        help_text="ID of the Department (optional)."
    )
    labours = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="List of Labour IDs to assign."
    )
    daily_task = serializers.CharField(
        help_text="Name or description of the daily task."
    )
    done_work = serializers.CharField(
        max_length=200, required=False, default='0',
        help_text="Progress of work (e.g. '10%')."
    )
    meal_cost_per_labour = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        write_only=True,
        help_text="Meal cost per labour for this date."
    )

    class Meta:
        model = Allocation
        fields = [
            'id',
            'date',
            'department',
            'daily_task',
            'done_work',
            'labours',
            'meal_cost_per_labour',
            'man_days',
            'wages_total',
            'meals_total',
            'total_amount'
        ]
        read_only_fields = [
            'man_days',
            'wages_total',
            'meals_total',
            'total_amount'
        ]

    def create(self, validated_data):
        labour_ids     = validated_data.pop('labours')
        meal_cost      = validated_data.pop('meal_cost_per_labour')
        task_name      = validated_data.pop('daily_task')
        done_work      = validated_data.pop('done_work', '0')
        department_obj = validated_data.pop('department', None)

        # Create the Allocation with department and done_work
        allocation = Allocation.objects.create(
            date        = validated_data['date'],
            department  = department_obj,
            daily_task  = task_name,
            done_work   = done_work,
            man_days    = 0,
            wages_total = 0,
            meals_total = 0,
            total_amount= 0
        )

        # Assign labours and compute wages
        total_wages = 0
        for labour_id in labour_ids:
            labour = Labour.objects.get(pk=labour_id)
            allocation.labours.add(labour)
            total_wages += labour.day_salary

        # Compute summary fields
        man_days     = allocation.labours.count()
        meals_total  = meal_cost * man_days
        total_amount = total_wages + meals_total

        # Persist computed fields
        allocation.man_days     = man_days
        allocation.wages_total  = total_wages
        allocation.meals_total  = meals_total
        allocation.total_amount = total_amount
        allocation.save()

        return allocation