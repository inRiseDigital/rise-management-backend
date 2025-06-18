from django.db import models

class MilkCollection(models.Model):
    date = models.DateField()
    local_sale_kg = models.FloatField(default=0.0)
    rise_kitchen_kg = models.FloatField(default=0.0)
    total_kg = models.FloatField(default=0.0)
    total_liters = models.FloatField(default=0.0)  # <-- Add this
    day_rate = models.FloatField(default=160.0)
    day_total_income = models.FloatField(default=0.0)

    def __str__(self):
        return f"Milk on {self.date}"

    def save(self, *args, **kwargs):
        self.total_kg = self.local_sale_kg + self.rise_kitchen_kg
        self.total_liters = self.total_kg * 1.027  # <-- Convert to liters
        self.day_total_income = self.total_kg * self.day_rate
        super().save(*args, **kwargs)

class CostEntry(models.Model):
    cost_date = models.DateField()
    description = models.TextField()
    amount = models.FloatField()

    def __str__(self):
        return f"Cost on {self.cost_date}: {self.amount}"