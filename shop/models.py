from django.db import models
from django.conf import settings
from django.utils import timezone
from autoslug import AutoSlugField

User = settings.AUTH_USER_MODEL

class Item(models.Model):
    PRODUCT_TYPES = [
        ('uniform','Uniform'),
        ('textbook','Textbook'),
        ('school fee','School Fee'),
        ('other','Other'),
    ]

    CLASSES = [
        ('playgroup','Playgroup'),
        ('kg1','KG 1'),
        ('kg2','KG 2'),
        ('nursery1','Nursery 1'),
        ('nursery2','Nursery 2'),
        ('nursery3','Nursery 3'),
        ('pry1','Primary 1'),
        ('pry2','Primary 2'),
        ('pry3','Primary 3'),
        ('pry4','Primary 4'),
        ('pry5','Primary 5'),
        ('jss1','JSS 1'),
        ('jss2','JSS 2'),
        ('jss3','JSS 3'),
        ('sss1','SSS 1'),
        ('sss2','SSS 2'),
        ('sss3','SSS 3'),
        ]
    name = models.CharField(max_length=200)
    slug = AutoSlugField(populate_from='name', unique=True)    
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Naira
    applicable_class = models.CharField(max_length=20, choices=CLASSES, default='pry1')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='other')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='shop/', null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)


    def in_stock(self):
        return self.stock > 0


    def __str__(self):
        return self.name


class Cart(models.Model):
    # Anonymous carts can store session_key, registered carts link to user
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total(self):
        return sum(ci.line_total() for ci in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)

    def line_total(self):
        return self.item.price * self.qty


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    reference = models.CharField(max_length=120, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Naira
    status = models.CharField(max_length=20, default='pending')  # pending, success, failed
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.reference} - {self.amount}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)



