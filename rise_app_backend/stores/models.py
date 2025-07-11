from django.db import models
from django.core.exceptions import ValidationError  # Add this import
from decimal import Decimal

class Store(models.Model):
    """A physical or logical store, e.g. Food Store, General Store."""
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    """High-level product type, e.g. “Soap”."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="store_categories")
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ProductSubCategory(models.Model):
    """Sub-SKU under a category, e.g. “Bath Soap”."""
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="subcategories")
    name     = models.CharField(max_length=100)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} ▶ {self.name}"


class InventoryItem(models.Model):
    """
    Tracks stock for one (store, category∖subcategory) combination.
    """
    store        = models.ForeignKey(Store,on_delete=models.CASCADE,related_name="inventory_items")
    category     = models.ForeignKey(ProductCategory,on_delete=models.CASCADE,related_name="inventory_items")
    subcategory  = models.ForeignKey(ProductSubCategory,on_delete=models.CASCADE,related_name="inventory_items")
    units_in_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("store", "category", "subcategory"),)
        constraints = [
            # Exactly one of category or subcategory must be non-null
            models.CheckConstraint(
                check=(
                    models.Q(category__isnull=False, subcategory__isnull=True) |
                    models.Q(category__isnull=True,  subcategory__isnull=False)
                ),
                name="one_of_category_or_subcategory"
            ),
            # If subcategory is set, it must match the category
            models.CheckConstraint(
                check=(
                    models.Q(subcategory__isnull=True) |
                    models.Q(subcategory__category=models.F("category"))
                ),
                name="subcategory_matches_category"
            ),
        ]

    def clean(self):
        super().clean()
        # Enforce in Python as well
        if self.subcategory:
            if self.subcategory.category_id != self.category_id:
                raise ValidationError({"subcategory": "Must belong to the selected category."})

    @property
    def total_cost(self):
        return self.units_in_stock * self.unit_cost

    def receive(self, add_units, cost_per_unit):
        """Increase stock and recompute weighted-average cost."""
        add_units     = Decimal(str(add_units))
        cost_per_unit = Decimal(str(cost_per_unit))

        old_total   = self.units_in_stock * self.unit_cost
        new_total   = add_units * cost_per_unit
        total_units = self.units_in_stock + add_units

        self.unit_cost      = (
            (old_total + new_total) / total_units
            if total_units else Decimal("0")
        )
        self.units_in_stock = total_units
        self.full_clean()
        self.save()

    def issue(self, rm_units):
        """Remove stock; error if insufficient."""
        rm_units = Decimal(str(rm_units))
        if rm_units > self.units_in_stock:
            raise ValidationError("Insufficient stock to issue.")
        self.units_in_stock -= rm_units
        self.full_clean()
        self.save()

    def __str__(self):
        name = (
            self.subcategory.name
            if self.subcategory else
            self.category.name
        )
        return (
            f"{self.store.name} – {name}: "
            f"{self.units_in_stock} @ ₹{self.unit_cost:.2f}"
        )