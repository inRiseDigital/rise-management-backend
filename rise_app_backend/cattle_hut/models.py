from django.db import models

class MilkCollection(models.Model):
    date = models.DateField()
    local_sale_kg = models.FloatField(default=0.0)
    rise_kitchen_kg = models.FloatField(default=0.0)
    total_kg = models.FloatField(default=0.0)
    local_sale_liters = models.FloatField(default=0.0)
    kitchen_liters = models.FloatField(default=0.0)
    total_liters = models.FloatField(default=0.0)
    day_rate = models.FloatField(default=160.0)  # per liter rate

    def __str__(self):
        return f"Milk on {self.date}"

class CostEntry(models.Model):
    cost_date = models.DateField()
    description = models.TextField()
    amount = models.FloatField()

    def __str__(self):
        return f"Cost on {self.cost_date}: {self.amount}"