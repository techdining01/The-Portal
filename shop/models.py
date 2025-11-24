import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from autoslug import AutoSlugField

UserModel = settings.AUTH_USER_MODEL

def generate_reference():
    return uuid.uuid4().hex

def generate_receipt_slug():
    return uuid.uuid4().hex[:22]

class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self): return self.name

class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('school_fee','School Fee'),
        ('textbook','Textbook'),
        ('registration_fee','Registration Fee'),
        ('uniform','Uniform'),
        ('other','Other'),
    ]
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPE_CHOICES)
    slug = AutoSlugField(populate_from='name', unique=True)
    image = models.ImageField(upload_to='product/', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    in_stock = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_image_url(self):
        if hasattr(self, 'image') and self.image:
            return self.image.url
        return '/static/images/default_product.png'

    
    def __str__(self): return self.name

class Cart(models.Model):
    owner = models.ForeignKey(UserModel, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    # Link by registration_number (to_field)
    student = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, to_field="registration_number", related_name="student_cart_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product", "student")

    def subtotal(self):
        return self.product.price * self.quantity

class Order(models.Model):
    STATUS = [
        ('pending','Pending'),
        ('paid','Paid'),
        ('failed','Failed'),
        ('cancelled','Cancelled'),
    ]
    reference = models.CharField(max_length=64, unique=True, default=generate_reference)
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, null=True, blank=True)
    parent = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    paystack_payment_ref = models.CharField(max_length=255, blank=True, null=True)
    receipt_slug = models.SlugField(max_length=80, unique=True, default=generate_receipt_slug)

    def __str__(self): return f"Order {self.reference}"

    def get_receipt_url(self):
        return reverse("shop:receipt", args=[self.receipt_slug])

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    student = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, to_field="registration_number", related_name="student_order_items")

    def line_total(self):
        return self.unit_price * self.quantity

class TransactionBackup(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    paystack_reference = models.CharField(max_length=255, blank=True, null=True)
    raw_payload = models.JSONField()
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Receipt(models.Model):
    """
    Persistent receipt record. Keeps a snapshot of the order data for reporting + PDF generation.
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="receipt")
    created_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="receipts/", null=True, blank=True)  # optional store of generated PDF
    html_snapshot = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Receipt for {self.order.reference}"

class StudentPurchase(models.Model):
    """
    Record of each purchased product assigned to a student (useful for student history / inventory)
    """
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name="student_purchase")
    student = models.ForeignKey(UserModel, on_delete=models.CASCADE, to_field="registration_number", related_name="purchases")
    created_at = models.DateTimeField(auto_now_add=True)
    fulfilled = models.BooleanField(default=False)  # e.g., uniform collected
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.order_item.product.name}"

