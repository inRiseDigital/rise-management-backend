from django.db import models

class Machine(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ExtractionRecord(models.Model):
    machine     = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="extractions")
    date        = models.DateField() 
    leaf_type   = models.CharField(max_length=100)
    input_weight  = models.DecimalField(max_digits=14, decimal_places=4)
    output_volume = models.DecimalField(max_digits=14, decimal_places=4)
    on_time     = models.TimeField()
    on_by       = models.CharField(max_length=100)
    off_time    = models.TimeField()
    off_by      = models.CharField(max_length=100)
    run_duration = models.DurationField()
    remarks     = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.machine.name} extraction on {self.date}"

class OilPurchase(models.Model):
    date          = models.DateField()
    oil_type      = models.CharField(max_length=100)
    volume        = models.DecimalField(max_digits=14, decimal_places=4)
    received_by   = models.CharField(max_length=100)
    location      = models.CharField(max_length=100)
    authorized_by = models.CharField(max_length=100)
    remarks       = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.oil_type} purchase on {self.date}"
