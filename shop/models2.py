# from django.db import models
# from django.conf import settings
# from django.utils import timezone
# from decimal import Decimal

# class Product(models.Model):
#     """
#     Products include uniforms, textbooks, fees (if sold as items), stationery, etc.
#     price stored in Naira (Decimal) for readability; convert to kobo for Paystack.
#     """
#     sku = models.CharField(max_length=50, unique=True)  # e.g. UNIFORM-JSS1
#     name = models.CharField(max_length=255)
#     description = models.TextField(blank=True)
#     price = models.DecimalField(max_digits=12, decimal_places=2)  # Naira (e.g. 1500.00)
#     stock = models.IntegerField(default=0)
#     active = models.BooleanField(default=True)
#     image = models.ImageField(upload_to="shop/", null=True, blank=True)

#     def __str__(self):
#         return f"{self.name} — ₦{self.price}"

# class Order(models.Model):
#     STATUS = (('pending','Pending'), ('paid','Paid'), ('failed','Failed'))
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
#     email = models.EmailField()
#     created_at = models.DateTimeField(default=timezone.now)
#     status = models.CharField(max_length=20, choices=STATUS, default='pending')
#     total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))  # Naira
#     reference = models.CharField(max_length=128, unique=True)  # Paystack reference / local ref
#     metadata = models.JSONField(null=True, blank=True)  # extra info (items snapshot)
#     paid_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return f"Order {self.reference} - {self.status} - ₦{self.total_amount}"

# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
#     name = models.CharField(max_length=255)
#     unit_price = models.DecimalField(max_digits=12, decimal_places=2)  # snapshot in Naira
#     quantity = models.PositiveIntegerField(default=1)

#     def line_total(self):
#         return self.unit_price * self.quantity

#     def __str__(self):
#         return f"{self.name} x{self.quantity} ({self.order.reference})"

# class Payment(models.Model):
#     order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
#     gateway = models.CharField(max_length=50, default='paystack')
#     gateway_reference = models.CharField(max_length=255, unique=True)
#     amount = models.PositiveIntegerField()  # in kobo
#     status = models.CharField(max_length=50)
#     raw_response = models.JSONField(null=True, blank=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     def __str__(self):
#         return f"Payment {self.gateway_reference} - {self.status}"
