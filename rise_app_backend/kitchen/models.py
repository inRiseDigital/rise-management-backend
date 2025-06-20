from django.db import models

class Category(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField()
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Expense(models.Model):
    category = models.ForeignKey(Category,on_delete=models.PROTECT,related_name='expenses')
    date = models.DateField()            
    responsible_person  = models.CharField(max_length=100)
    description = models.TextField(blank=True)  
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    bill_no = models.CharField(max_length=50)
    image = models.ImageField(upload_to='images/kitchen/bills/%Y/%m/',null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bill_no} — {self.category.name}: {self.amount}"
