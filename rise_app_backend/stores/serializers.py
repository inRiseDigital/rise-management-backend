from rest_framework import serializers
from .models import (
    Store,
    ProductCategory,
    ProductSubCategory,
    InventoryItem
)

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Store
        fields = ["id", "name", "created_at"]


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductCategory
        fields = ["id", "name"]


class ProductSubCategorySerializer(serializers.ModelSerializer):
    # allow writing by primary key
    category = serializers.PrimaryKeyRelatedField(
        queryset=ProductCategory.objects.all()
    )

    class Meta:
        model  = ProductSubCategory
        fields = ["id", "category", "name"]


class InventoryItemSerializer(serializers.ModelSerializer):
    store       = serializers.PrimaryKeyRelatedField(
                      queryset=Store.objects.all()
                  )
    category    = serializers.PrimaryKeyRelatedField(
                      queryset=ProductCategory.objects.all()
                  )
    subcategory = serializers.PrimaryKeyRelatedField(
                      queryset=ProductSubCategory.objects.all(),
                      allow_null=True,
                      required=False
                  )
    total_cost  = serializers.DecimalField(
                      max_digits=14,
                      decimal_places=2,
                      read_only=True
                  )

    class Meta:
        model  = InventoryItem
        fields = [
            "id",
            "store",
            "category",
            "subcategory",
            "units_in_stock",
            "unit_cost",
            "total_cost",
            "updated_at",
        ]
