# salary/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class SalaryStructure(models.Model):
    PAYMENT_FREQUENCY = [
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
    ]
    
    name = models.CharField(max_length=100)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frequency = models.CharField(max_length=20, choices=PAYMENT_FREQUENCY, default='monthly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def net_salary(self):
        return self.base_salary + self.allowances - self.deductions
    
    def __str__(self):
        return f"{self.name} - ₦{self.net_salary}"

class TeacherSalary(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    salary_structure = models.ForeignKey(SalaryStructure, on_delete=models.CASCADE)
    payment_period = models.CharField(max_length=50)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    paystack_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.net_salary:
            self.net_salary = self.basic_salary + self.allowances - self.deductions
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.payment_period}"

class SalaryPayment(models.Model):
    teacher_salary = models.OneToOneField(TeacherSalary, on_delete=models.CASCADE)
    paystack_reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=TeacherSalary.PAYMENT_STATUS, default='pending')
    gateway_response = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.paystack_reference} - ₦{self.amount}"