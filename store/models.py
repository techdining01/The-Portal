
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
from django.conf import settings
from decimal import Decimal
User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to='products/',
        default='products/default_product.png'  # Add default image
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    @property
    def image_url(self):
        """Safe method to get image URL"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/images/default_product.png'  # Fallback static image

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def items_count(self):
        return self.items.count()

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    student = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                               limit_choices_to={'role': 'student'})
    
    @property
    def total_price(self):
        return self.product.price * self.quantity
    
    @property
    def total_price(self):
        total = self.quantity * self.product.price
        # Convert to float for JSON compatibility
        return float(total) if isinstance(total, Decimal) else total
    


# class Order(models.Model):
#     ORDER_STATUS = [
#         ('pending', 'Pending'),
#         ('processing', 'Processing'),
#         ('completed', 'Completed'),
#         ('cancelled', 'Cancelled'),
#     ]
    
#     PAYMENT_STATUS = [
#         ('pending', 'Pending'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#         ('refunded', 'Refunded'),
#     ]
    
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_reference = models.CharField(max_length=100, unique=True)
#     payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
#     payment_method = models.CharField(max_length=50, default='paystack')
#     order_status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         ordering = ['-created_at']
    
#     def __str__(self):
#         return f"Order {self.id} - {self.user.username}"
    

# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
#     product = models.ForeignKey('Product', on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     price = models.DecimalField(max_digits=10, decimal_places=2)
    
#     def __str__(self):
#         return f"{self.quantity} x {self.product.name}"
    
    
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, default='paystack')
    payment_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"BRP{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.order_number

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    student = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               limit_choices_to={'role': 'student'})
    
    @property
    def subtotal(self):
        return self.price * self.quantity
    

class Transaction(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    gateway_response = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.paystack_reference} - {self.amount}"
    
