from django.db import models

class ExpenseCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Expense(models.Model):
    date                = models.DateField()
    responsible_person  = models.CharField(max_length=100)
    category            = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    sub_category        = models.CharField(max_length=100, blank=True)
    description         = models.TextField(blank=True)
    bill_image          = models.ImageField(
        upload_to='images/vehicle_expenses/bills/%Y/%m/',
        null=True,
        blank=True
    )
    bill_no             = models.CharField(max_length=50, blank=True)
    cost                = models.DecimalField(max_digits=10, decimal_places=2)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} – {self.category.name}: {self.cost:.2f}"
