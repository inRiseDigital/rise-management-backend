# serializers.py

from rest_framework import serializers
from .models import Task, Labour, TaskAllocation

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "department", "description", "category"]


class LabourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Labour
        fields = ["id", "name", "hourly_rate"]


class TaskAllocationSerializer(serializers.ModelSerializer):
    wage = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        source="wage", read_only=True
    )
    total_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        source="total_cost", read_only=True
    )

    class Meta:
        model = TaskAllocation
        fields = [
            "id", "task", "labour", "mandays", "meals_cost",
            "wage", "total_cost"
        ]
