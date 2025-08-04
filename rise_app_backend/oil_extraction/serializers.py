from rest_framework import serializers
from .models import Machine, ExtractionRecord, OilPurchase

class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = '__all__'

class ExtractionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionRecord
        fields = '__all__'

class OilPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OilPurchase
        fields = '__all__'