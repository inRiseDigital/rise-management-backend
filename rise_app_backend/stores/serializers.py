# serializers.py
from rest_framework import serializers
from .models import (
    Store,
    ProductCategory, ProductSubCategory,
    InventoryItem,InventoryItem, InventoryMovement
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
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    # extra read-only fields for display
    store_name = serializers.CharField(source="store.name", read_only=True)
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "store", "store_name",          # keep ID + name
            "category", "category_name",    # keep ID + name
            "subcategory", "subcategory_name",
            "units_in_stock", "unit_cost",
            "total_cost", "updated_at",
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None
        


class InventoryMovementSerializer(serializers.ModelSerializer):
    store_id         = serializers.IntegerField(source="item.store_id", read_only=True)
    store_name       = serializers.CharField(source="item.store.name", read_only=True)
    item_id          = serializers.IntegerField(source="item.id", read_only=True)
    category_id      = serializers.IntegerField(source="item.category_id", read_only=True)
    category_name    = serializers.CharField(source="item.category.name", read_only=True, allow_null=True)
    subcategory_id   = serializers.IntegerField(source="item.subcategory_id", read_only=True)
    subcategory_name = serializers.CharField(source="item.subcategory.name", read_only=True, allow_null=True)

    class Meta:
        model = InventoryMovement
        fields = [
            "id", "direction", "units", "unit_cost", "total_cost", "occurred_at",
            "balance_units_after",
            "store_id", "store_name",
            "item_id", "category_id", "category_name",
            "subcategory_id", "subcategory_name",
            "note", "ref_type", "ref_id",
        ]