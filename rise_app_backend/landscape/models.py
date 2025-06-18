from django.db import models

class Project(models.Model):
    project_name = models.CharField()
    project_location = models.CharField(max_length=100)
    start_date = models.DateField()
    progress = models.CharField(max_length=50, default='ongoing') 
    status = models.DateField()
    update_date = models.DateField(auto_now=True)
    
    def __str__(self):
        return f"{self.project_name}... ({self.project_location})"
    
class Project_Issuce (models.Model):
    date = models.DateField()
    issuce = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='issuce')
    
    
class Maintenance(models.Model):
    date = models.DateField()
    project_location = models.CharField(max_length=100)
    work_done = models.DateField()
    update_date = models.DateField(auto_now=True)
    
    def __str__(self):
        return f"{self.project_location}... ({self.work_done})"
    
class DailyTask(models.Model):
    date = models.DateField()
    name = models.CharField()
    work = models.CharField()
    updated_at = models.DateTimeField(auto_now=True)