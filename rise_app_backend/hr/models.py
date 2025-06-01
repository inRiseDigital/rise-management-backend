from django.db import models

# Create your models here.

class staff(models.Model):
    staff_id = models.CharField(max_length=100, unique=True)
    staff_name = models.CharField(max_length=100)
    staff_email = models.EmailField(unique=True)
    staff_phone = models.CharField(max_length=15)
    staff_department = models.CharField(max_length=100)
    staff_position = models.CharField(max_length=100)
    staff_joining_date = models.DateField()
    username = models.CharField(null=True)
    password = models.CharField(null=True)
    
    @property
    def used_leaves(self) -> int:
        """
        Sum up, for every APPROVED leave, the total days between
        leave_start_date and leave_end_date (inclusive).
        """
        total_days = 0
        for lv in self.leaves.filter(leave_status="Approved"):
            days = (lv.leave_end_date - lv.leave_start_date).days + 1
            total_days += days
        return total_days

    @property
    def available_leaves(self) -> int:
        # Monthly allowance is fixed at 8
        return 8 - self.used_leaves

    def __str__(self):
        return self.staff_name

class leave(models.Model):
    leave_type = models.CharField(max_length=100)
    leave_start_date = models.DateField()
    leave_end_date = models.DateField()
    leave_reason = models.TextField()
    leave_status = models.CharField(max_length=50, default='Pending')
    staff = models.ForeignKey(staff,to_field='staff_id',on_delete=models.CASCADE, related_name='leaves'      
    )

    def __str__(self):
        return f"{self.leave_type} - {self.leave_status}"