from rest_framework import serializers
from .models import MilkCollection, CostEntry

class MilkCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilkCollection
        fields = '__all__'

class CostEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CostEntry
        fields = '__all__'


