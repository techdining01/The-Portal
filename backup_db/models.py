
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class DatabaseBackup(models.Model):
    BACKUP_TYPE_CHOICES = [
        ('full', 'Full Database'),
        ('transactions', 'Transactions Only'),
        ('users', 'Users Only'),
        ('products', 'Products Only'),
    ]
    
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveBigIntegerField(help_text="Size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.backup_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class CBTBackup(models.Model):
    """
    Replica of CBT (Computer Based Test) database records
    """
    exam_name = models.CharField(max_length=200)
    exam_date = models.DateTimeField()
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    score = models.DecimalField(max_digits=5, decimal_places=2)
    total_questions = models.PositiveIntegerField()
    time_taken = models.DurationField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "CBT Backup"
        verbose_name_plural = "CBT Backups"
    
    def __str__(self):
        return f"{self.exam_name} - {self.student.get_full_name()}"

class SalesReport(models.Model):
    REPORT_PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    period = models.CharField(max_length=10, choices=REPORT_PERIOD_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_sales = models.DecimalField(max_digits=12, decimal_places=2)
    total_orders = models.PositiveIntegerField()
    total_products_sold = models.PositiveIntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)
    report_file = models.FileField(upload_to='sales_reports/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.period.title()} Report - {self.start_date} to {self.end_date}"