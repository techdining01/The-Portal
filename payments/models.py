from django.db import models
from django.conf import settings
from django.utils import timezone


class FeeItem(models.Model):
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - ₦{self.amount}"
    

class Payment(models.Model):
    PAYMENT_TYPES = [
        ('registration', 'Registration Fee'),
        ('tuition', 'Tuition Fee'),
        ('textbook', 'Textbook Fee'),
        ('uniform', 'Uniform Fee'),
        ('others', 'Other Charges'),
    ]

    STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    is_paid = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    reference = models.CharField(max_length=120, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def mark_paid(self):
        self.is_paid = True
        self.verified = True
        self.status = 'success'
        self.paid_at = timezone.now()
        self.save(update_fields=['is_paid','verified','status','paid_at'])

    def __str__(self):
        return f"{self.student} - {self.payment_type} - {self.amount}"
    






