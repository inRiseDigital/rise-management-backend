from rest_framework import serializers
from .models import Project, Project_Issuce, Maintenance, DailyTask

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class ProjectIssuceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_Issuce
        fields = '__all__'

class MaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Maintenance
        fields = '__all__'

class DailyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTask
        fields = '__all__'