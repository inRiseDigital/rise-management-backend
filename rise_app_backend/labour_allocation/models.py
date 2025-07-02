# models.py

from django.db import models

class Task(models.Model):
    department = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    CATEGORY_CHOICES = [
        ("CAPEX", "CAPEX"),
        ("OPEX", "OPEX")
    ]
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.description


class Labour(models.Model):
    name = models.CharField(max_length=100, unique=True)
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Rate per manday"
    )

    def __str__(self):
        return self.name


class TaskAllocation(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    labour = models.ForeignKey(
        Labour,
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    mandays = models.PositiveIntegerField()
    meals_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ("task", "labour")

    @property
    def wage(self):
        return self.labour.hourly_rate * self.mandays

    @property
    def total_cost(self):
        return self.wage + self.meals_cost

    def __str__(self):
        return f"{self.labour.name} on {self.task.description}"
