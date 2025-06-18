from django.db import models

# Create your models here.

class Staff(models.Model):
    staff_id = models.CharField(max_length=100, unique=True, primary_key=True)
    staff_name = models.CharField(max_length=100)
    staff_email = models.EmailField(unique=True)
    staff_phone = models.CharField(max_length=15)
    staff_department = models.CharField(max_length=100)
    roll = models.CharField(max_length=100)
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
    staff = models.ForeignKey(Staff,to_field='staff_id',on_delete=models.CASCADE, related_name='leaves'      
    )

    def __str__(self):
        return f"{self.leave_type} - {self.leave_status}"
    
###########################
class responsible_person(models.Model):
    id = models.CharField(max_length=100, unique=True, primary_key=True)
    staff_id = models.ForeignKey(Staff, to_field='staff_id', on_delete=models.CASCADE, related_name='responsible_persons')
    person_name = models.CharField(max_length=100)
    responsibl_section = models.CharField(max_length=100)
    def __str__(self):
        return self.person_name
    
class department(models.Model):
    dpt_id = models.CharField(max_length=100, unique=True, primary_key=True)
    dpt_name = models.CharField(max_length=100, unique=True)
    dpt_description = models.ForeignKey(Staff, to_field='staff_id', on_delete=models.SET_NULL, null=True, related_name='department_head')
    created_at = models.DateTimeField(auto_now_add=True)
    responsible_person = models.ForeignKey(Staff, to_field='staff_id', on_delete=models.SET_NULL, null=True, related_name='responsible_department')

    def __str__(self):
        return self.dpt_id
    
class site(models.Model):
    site_id = models.CharField(max_length=100, unique=True)
    site_name = models.CharField(max_length=100, unique=True)
    site_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.location_name
    
class vehicles(models.Model):
    number_plate = models.CharField(max_length=100, unique=True,primary_key=True)
    Brand = models.CharField(max_length=100, unique=True)
    Model_name = models.CharField(max_length=50)
    fuel_type = models.TextField()
    allocated_department = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number_plate
 
#Income and Expenses

class expense_category(models.Model):
    id = models.CharField(max_length=100, unique=True,primary_key=True)
    projet_department = models.CharField(max_length=100)

    def __str__(self):
        return self.id
class expense_sub_category(models.Model):
    id = models.CharField(max_length=100, unique=True, primary_key=True)
    categiry_id = models.ForeignKey(expense_category, to_field='id', on_delete=models.CASCADE, related_name='sub_categories')
    sub_category = models.CharField(max_length=100) 
    def __str__(self):
        return self.id
    

class expenses (models.Model):
    id = models.CharField(max_length=100, unique=True, primary_key=True)
    expense_category = models.ForeignKey(expense_category, to_field='id', on_delete=models.CASCADE, related_name='expenses')
    expense_sub_category = models.ForeignKey(expense_sub_category, to_field='id', on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField()
    responsible_person = models.ForeignKey(responsible_person, on_delete=models.SET_NULL, null=True, related_name='expenses')
    sub_category = models.CharField(max_length=100) 
    description = models.TextField()
    bill_no = models.CharField(max_length=100, unique=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.date}"
    
#Desal perchesing and usage
class desal_purchase(models.Model):
    purchase_id = models.CharField(max_length=100, unique=True, primary_key=True)
    purchase_date = models.DateField()
    responsible_person = models.ForeignKey(responsible_person, on_delete=models.SET_NULL, null=True, related_name='desal_purchases')
    sub_category = models.CharField(max_length=100) 
    description = models.CharField()
    litters = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.purchase_id} - {self.purchase_date}"