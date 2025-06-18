from django.db import models

class Project(models.Model):
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description


class Task(models.Model):

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    description = models.TextField()
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='ongoing')
    qty = models.CharField(max_length=50) 
    date = models.DateField()
    update_date = models.DateField(auto_now=True)
    unskills = models.IntegerField(default=0)
    semi_skills = models.IntegerField(default=0)
    skills = models.IntegerField(default=0)
    def __str__(self):
        return f"{self.description[:30]}... ({self.project.description})"


#class ManPower(models.Model):

#    unit = models.CharField(max_length=100)
#    unskills = models.IntegerField(default=0)
    #semi_skills = models.IntegerField(default=0)
    #skills = models.IntegerField(default=0)
    #date = models.DateField()

   # def __str__(self):
    #    return f"{self.unit.title()} - U:{self.unskills} / SS:{self.semi_skills} / S:{self.skills}"
