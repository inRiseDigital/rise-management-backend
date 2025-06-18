from rest_framework import serializers
from .models import Location, Task,Subcategories

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(
        source='subcategory.subcategory',
        read_only=True
    )
    class Meta:
        model = Task
        fields = '__all__'

class SubcategoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategories
        fields = '__all__'
