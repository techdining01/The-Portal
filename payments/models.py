from django.db import models
from django.utils import timezone
from django.conf import settings



class Invoice(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.PositiveIntegerField(help_text="Amount in kobo (store smallest currency unit)")
    currency = models.CharField(max_length=3, default='NGN')
    reference = models.CharField(max_length=128, unique=True, null=True, blank=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice #{self.pk} for {self.STUDENT} - {self.amount}"

class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    gateway = models.CharField(max_length=50, default='paystack')
    gateway_reference = models.CharField(max_length=255, unique=True)
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=50)
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.gateway_reference} - {self.status}"
