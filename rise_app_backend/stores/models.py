from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction


class Store(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="store_categories", default=1)
    name  = models.CharField(max_length=100, unique=True)  # keep as-is if you already use global unique
    def __str__(self):
        return self.name


class ProductSubCategory(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="subcategories")
    name     = models.CharField(max_length=100)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} ▶ {self.name}"


class InventoryItem(models.Model):
    store           = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="inventory_items", default=1)
    category        = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="inventory_items", null=True, blank=True)
    subcategory     = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE, related_name="inventory_items", null=True, blank=True)
    units_in_stock  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost       = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("store", "category", "subcategory"),)

    def clean(self):
        super().clean()
        if self.subcategory and self.subcategory.category_id != self.category_id:
            raise ValidationError({"subcategory": "Must belong to the selected category."})

    @property
    def total_cost(self):
        return self.units_in_stock * self.unit_cost

    @transaction.atomic
    def receive(self, add_units, cost_per_unit, note="", ref_type="", ref_id=""):
        add  = Decimal(str(add_units))
        cost = Decimal(str(cost_per_unit))

        old_units = self.units_in_stock
        old_cost  = self.unit_cost
        old_total = old_units * old_cost
        new_total = add * cost
        total_units = old_units + add

        raw = (old_total + new_total) / total_units if total_units else Decimal("0")
        self.unit_cost = raw.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        self.units_in_stock = total_units
        self.full_clean()
        self.save()

        InventoryMovement.objects.create(
            item=self,
            direction=InventoryMovement.IN,
            units=add,
            unit_cost=cost,
            total_cost=(add * cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            balance_units_after=self.units_in_stock,
            note=note, ref_type=ref_type, ref_id=ref_id,
        )

    @transaction.atomic
    def issue(self, rm_units, note="", ref_type="", ref_id=""):
        rm = Decimal(str(rm_units))
        if rm > self.units_in_stock:
            raise ValidationError("Insufficient stock to issue.")

        current_cost = self.unit_cost

        self.units_in_stock = self.units_in_stock - rm
        self.full_clean()
        self.save()

        InventoryMovement.objects.create(
            item=self,
            direction=InventoryMovement.OUT,
            units=rm,
            unit_cost=current_cost,
            total_cost=(rm * current_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            balance_units_after=self.units_in_stock,
            note=note, ref_type=ref_type, ref_id=ref_id,
        )

    def __str__(self):
        name = self.subcategory.name if self.subcategory else (self.category.name if self.category else "Uncategorized")
        return f"{self.store.name} – {name}: {self.units_in_stock} @ ₹{self.unit_cost:.4f}"


class InventoryMovement(models.Model):
    IN  = "IN"
    OUT = "OUT"
    DIRECTIONS = [(IN, "Receive"), (OUT, "Issue")]

    item        = models.ForeignKey("InventoryItem", on_delete=models.CASCADE, related_name="movements")
    direction   = models.CharField(max_length=3, choices=DIRECTIONS)
    units       = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unit_cost   = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    total_cost  = models.DecimalField(max_digits=16, decimal_places=2)
    occurred_at = models.DateTimeField(auto_now_add=True)

    balance_units_after = models.DecimalField(max_digits=12, decimal_places=2)
    note        = models.CharField(max_length=255, blank=True)
    ref_type    = models.CharField(max_length=50, blank=True)
    ref_id      = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["occurred_at"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["item", "occurred_at"]),
        ]
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.get_direction_display()} {self.units} of item {self.item_id} @ {self.unit_cost}"
