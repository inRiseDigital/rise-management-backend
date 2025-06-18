from django.db import models

# Create your models here.
class Location(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    update_date = models.DateField(auto_now=True)
    def __str__(self):
        return f"{self.name}: {self.description[:30]}"
    

class Subcategories (models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='subcategories')
    subcategory = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.location} - {self.subcategory[:20]}"
    
class Task(models.Model):

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='tasks')
    subcategory = models.ForeignKey(Subcategories, on_delete=models.CASCADE, related_name='tasks')
    cleaning_type = models.CharField(max_length=100)
    update_date = models.DateField(auto_now=True)
    def __str__(self):
        return f"{self.subcategory} - {self.cleaning_type[:20]}"