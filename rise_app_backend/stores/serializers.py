# serializers.py
from rest_framework import serializers
from .models import (
    Store,
    ProductCategory, ProductSubCategory,
    InventoryItem,
)

class StoreSerializer(serializers.ModelSerializer):
    """
    Serializer for Store model:
    - exposes all fields
    """
    class Meta:
        model = Store
        fields = '__all__'

class ProductCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for ProductCategory:
    - includes 'store' FK as its ID
    """
    class Meta:
        model = ProductCategory
        fields = '__all__'

class ProductSubCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for ProductSubCategory:
    - exposes both 'category' FK and name
    """
    class Meta:
        model = ProductSubCategory
        fields = '__all__'

class InventoryItemSerializer(serializers.ModelSerializer):
    """
    Serializer for InventoryItem:
    - calculates `total_cost` on the fly (read-only)
    - all other fields are read/write
    """
    total_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True,
        source='total_cost'
    )

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'store', 'category', 'subcategory',
            'units_in_stock', 'unit_cost', 'total_cost', 'updated_at'
        ]
        read_only_fields = ['updated_at', 'total_cost']
