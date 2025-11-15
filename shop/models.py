from django.db import models
from django.conf import settings


class ShopItem(models.Model):
    CATEGORY_CHOICES = [
        ("uniform", "School Uniform"),
        ("textbook", "Textbook"),
        ("fee", "School Fee"),
        ("other", "Other Item"),
    ]

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.PositiveIntegerField()   # price in kobo for Paystack
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="shop/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ₦{self.price/100:,.2f}"


class Order(models.Model):
    STATUS = [
        ("pending", "Pending Payment"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100, unique=True)
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(null=True, blank=True)  # student, class, items list

    def __str__(self):
        return self.reference





