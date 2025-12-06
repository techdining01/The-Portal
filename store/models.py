############### VERSION 2 ###################################

import secrets
from django.utils.crypto import get_random_string
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
import uuid
import random
import string
from decimal import Decimal
from PIL import Image
from django.conf import settings


 #==================== PRODUCT & STORE MODELS ====================

class Category(models.Model):
    """Product category model"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def is_parent(self):
        return self.parent is None
    
    @property
    def has_children(self):
        return self.children.exists()
    
    def get_all_products(self):
        """Get all products in this category and subcategories"""
        from django.db.models import Q
        categories = [self]
        categories.extend(self.get_descendants())
        return Product.objects.filter(category__in=categories, is_active=True)
    
    def get_descendants(self):
        """Get all descendant categories"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_ancestors(self):
        """Get all ancestor categories"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        return ancestors[::-1]  # Return in order from top to bottom


class Product(models.Model):
    """Product model for school store"""
    
    # Basic information
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    description = models.TextField(blank=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Inventory
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    sku = models.CharField(max_length=50, unique=True, verbose_name='SKU')
    barcode = models.CharField(max_length=100, blank=True)
    
    # Images
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image_2 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image_3 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image_4 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    
    # Specifications
    size = models.CharField(max_length=50, blank=True)  # e.g., "Small", "Medium", "Large"
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)
    weight = models.CharField(max_length=50, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Sales tracking
    total_sold = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    
    # Metadata
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate product data"""
        if self.cost_price and self.cost_price > self.price:
            raise ValidationError(
                "Cost price cannot be greater than selling price"
            )
    
    @property
    def in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def margin(self):
        """Calculate profit margin"""
        if self.cost_price:
            return ((self.price - self.cost_price) / self.cost_price) * 100
        return 0
    
    @property
    def profit_per_unit(self):
        """Calculate profit per unit"""
        if self.cost_price:
            return self.price - self.cost_price
        return Decimal('0.00')
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('store:product_detail', args=[self.slug])
    
    def increase_stock(self, quantity):
        """Increase stock quantity"""
        self.stock_quantity += quantity
        self.save(update_fields=['stock_quantity'])
    
    def decrease_stock(self, quantity):
        """Decrease stock quantity"""
        if self.stock_quantity < quantity:
            raise ValueError(f"Insufficient stock. Available: {self.stock_quantity}")
        self.stock_quantity -= quantity
        self.save(update_fields=['stock_quantity'])
    
    def update_sales(self, quantity):
        """Update total sold count"""
        self.total_sold += quantity
        self.save(update_fields=['total_sold'])
    
    def get_related_products(self, limit=4):
        """Get related products from same category"""
        return Product.objects.filter(
            category=self.category,
            is_active=True
        ).exclude(id=self.id)[:limit]


# ==================== CART MODELS ====================

class Cart(models.Model):
    """Shopping cart model"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts'
    )
    student = models.ForeignKey(
        'users.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts'
    )
    session_key = models.CharField(max_length=40, blank=True)  
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-created_at']
        unique_together = ['user', 'student']  # One cart per user-student combination
    
    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"
    
    @property
    def total_items(self):
        """Total number of items in cart"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_amount(self):
        """Total amount of cart"""
        total = 0
        for item in self.items.all():
            total += item.subtotal
        return total
    
    def add_item(self, product, quantity=1, student=None):
        """Add item to cart or update quantity if exists"""
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        if student:
            self.student = student
            self.save()
        
        return cart_item
    
    def remove_item(self, product):
        """Remove item from cart"""
        try:
            cart_item = CartItem.objects.get(cart=self, product=product)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def update_item_quantity(self, product, quantity):
        """Update item quantity in cart"""
        try:
            cart_item = CartItem.objects.get(cart=self, product=product)
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
    
    def merge_with_session_cart(self, session_cart):
        """Merge session cart with user cart"""
        if session_cart:
            for item in session_cart.items.all():
                self.add_item(item.product, item.quantity)
            session_cart.delete()


class CartItem(models.Model):
    """Cart item model"""
    
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this item"""
        return self.product.price * self.quantity
    
    def clean(self):
        """Validate cart item"""
        if self.quantity > self.product.stock_quantity:
            raise ValidationError(
                f"Only {self.product.stock_quantity} items available in stock."
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# ==================== ORDER MODELS ====================

class Order(models.Model):
    """Order model for purchases"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partial', 'Partial'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Debit/Credit Card'),
        ('wallet', 'Wallet'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    student = models.ForeignKey(
        'users.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    
    # Order details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='paystack'
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Shipping information
    shipping_address = models.TextField(blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    delivery_time = models.CharField(max_length=50, blank=True)
    
    # Payment information
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['payment_status', 'status']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{timestamp}-{random_str}"
    
    def calculate_totals(self):
        """Calculate order totals"""
        subtotal = sum(item.subtotal for item in self.items.all())
        self.subtotal = subtotal
        self.total_amount = subtotal + self.tax_amount + self.shipping_fee - self.discount_amount
    
    @property
    def is_paid(self):
        return self.payment_status == 'completed'
    
    @property
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'processing']
    
    @property
    def can_refund(self):
        """Check if order can be refunded"""
        return self.status == 'delivered' and self.payment_status == 'completed'
    
    def mark_as_paid(self, payment_reference, payment_method='paystack'):
        """Mark order as paid"""
        self.payment_status = 'completed'
        self.payment_reference = payment_reference
        self.payment_method = payment_method
        self.payment_date = timezone.now()
        
        # Update student's total spent
        if self.student:
            self.student.update_spending()
        
        self.save()
    
    def create_from_cart(self, cart):
        """Create order from cart"""
        self.user = cart.user
        self.student = cart.student
        
        # Save to get ID for order items
        self.save()
        
        # Create order items from cart items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=self,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            
            # Update product stock
            cart_item.product.decrease_stock(cart_item.quantity)
            cart_item.product.update_sales(cart_item.quantity)
        
        # Clear cart
        cart.clear()
        
        # Calculate totals
        self.calculate_totals()
        self.save()
        
        return self


class OrderItem(models.Model):
    """Order item model"""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # In case product details change
    product_name = models.CharField(max_length=200, blank=True)
    product_sku = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name or self.product.name}"
    
    @property
    def subtotal(self):
        return self.price * self.quantity
    
    def save(self, *args, **kwargs):
        # Store product details at time of order
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        super().save(*args, **kwargs)


# ==================== PAYMENT MODELS ====================

class Payment(models.Model):
    """Payment model for tracking transactions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Debit/Credit Card'),
        ('wallet', 'Wallet'),
    ]
    
    # Payment identification
    reference = models.CharField(max_length=100, unique=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    fee_payment = models.OneToOneField(
        'FeePayment',
        on_delete=models.CASCADE,
        related_name='payment_record',
        null=True,
        blank=True
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Paystack integration
    paystack_reference = models.CharField(max_length=100, blank=True)
    paystack_access_code = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Payer information
    payer_email = models.EmailField()
    payer_phone = models.CharField(max_length=15, blank=True)
    payer_name = models.CharField(max_length=200, blank=True)
    
    # Payment gateway response
    gateway_response = models.JSONField(null=True, blank=True)
    verification_response = models.JSONField(null=True, blank=True)
    
    # Receipt
    receipt_url = models.URLField(blank=True)
    receipt_data = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.reference} - ₦{self.amount:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)
    
    def generate_reference(self):
        """Generate unique payment reference"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"PAY-{timestamp}-{random_str}"
    
    @property
    def is_successful(self):
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    def mark_as_completed(self, verification_data=None):
        """Mark payment as completed"""
        self.status = 'completed'
        self.verified_at = timezone.now()
        if verification_data:
            self.verification_response = verification_data
        
        # Update associated order
        if self.order:
            self.order.mark_as_paid(self.reference, self.payment_method)
        
        # Update associated fee payment
        if self.fee_payment:
            self.fee_payment.mark_as_paid(self.reference)
        
        self.save()
    
    def mark_as_failed(self, failure_reason=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if failure_reason and self.gateway_response:
            self.gateway_response['failure_reason'] = failure_reason
        self.save()
    
    def process_refund(self, amount=None, reason=''):
        """Process refund for payment"""
        refund_amount = amount or self.amount
        Refund.objects.create(
            payment=self,
            amount=refund_amount,
            reason=reason,
            status='pending'
        )
        self.status = 'refunded'
        self.save()


class Transaction(models.Model):
    """Transaction model for financial tracking"""
    
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('fee_payment', 'Fee Payment'),
        ('wallet_topup', 'Wallet Top-up'),
        ('wallet_withdrawal', 'Wallet Withdrawal'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions'
    )
    student = models.ForeignKey(
        'users.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    transaction_id = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    
    # Related objects
    payment = models.ForeignKey(
        'store.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    order = models.ForeignKey(
        'store.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('reversed', 'Reversed'),
        ],
        default='pending'
    )
    
    # Metadata
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - ₦{self.amount:,.2f}"


class Refund(models.Model):
    """Refund model"""
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('processed', 'Processed'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Refund details
    refund_reference = models.CharField(max_length=100, blank=True)
    refund_method = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
    
    def __str__(self):
        return f"Refund for {self.payment.reference} - ₦{self.amount:,.2f}"


# ==================== FEE STRUCTURE MODELS ====================

class FeeStructure(models.Model):
    """Fee structure model for school fees"""
    
    TERM_CHOICES = [
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
        ('annual', 'Annual'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    academic_year = models.CharField(max_length=20)  # e.g., "2024/2025"
    student_class = models.ForeignKey('exams.Class', on_delete=models.CASCADE)  # e.g., "JSS 1", "SSS 3"
    term = models.CharField(max_length=20, choices=TERM_CHOICES)
    
    # Fee amounts
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    late_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    late_fee_date = models.DateField(null=True, blank=True)
    
    # Components (optional breakdown)
    tuition_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    development_levy = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    exam_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    sports_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    other_charges = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_compulsory = models.BooleanField(default=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Fee Structure'
        verbose_name_plural = 'Fee Structures'
        ordering = ['academic_year', 'student_class', 'term']
        unique_together = ['academic_year', 'student_class', 'term', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.student_class} ({self.get_term_display()})"
    
    @property
    def is_overdue(self):
        """Check if fee is overdue"""
        return timezone.now().date() > self.due_date
    
    @property
    def late_fee_applicable(self):
        """Check if late fee is applicable"""
        if self.late_fee_date:
            return timezone.now().date() > self.late_fee_date
        return False
    
    @property
    def total_with_late_fee(self):
        """Calculate total with late fee if applicable"""
        if self.late_fee_applicable:
            return self.amount + self.late_fee
        return self.amount
    
    def get_breakdown(self):
        """Get fee breakdown as dictionary"""
        return {
            'tuition_fee': self.tuition_fee,
            'development_levy': self.development_levy,
            'exam_fee': self.exam_fee,
            'sports_fee': self.sports_fee,
            'other_charges': self.other_charges,
            'total': self.amount
        }


class FeePayment(models.Model):
    """Fee payment model for school fees"""
    
    student = models.ForeignKey(
        'users.Student',
        on_delete=models.CASCADE,
        related_name='fee_payments'
    )
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=20,
        choices=Payment.PAYMENT_METHOD_CHOICES,
        default='paystack'
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Status
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_fee_payments'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Receipt
    receipt_number = models.CharField(max_length=50, blank=True)
    receipt_issued = models.BooleanField(default=False)
    receipt_issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_fee_receipts'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Fee Payment'
        verbose_name_plural = 'Fee Payments'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Fee Payment - {self.student} - ₦{self.amount_paid:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()
        super().save(*args, **kwargs)
    
    def generate_receipt_number(self):
        """Generate unique receipt number"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"FEE-{timestamp}-{random_str}"
    
    @property
    def balance(self):
        """Calculate remaining balance"""
        return self.fee_structure.amount - self.amount_paid
    
    @property
    def is_fully_paid(self):
        """Check if fee is fully paid"""
        return self.amount_paid >= self.fee_structure.amount
    
    @property
    def is_partial_payment(self):
        """Check if payment is partial"""
        return self.amount_paid < self.fee_structure.amount
    
    def mark_as_paid(self, payment_reference):
        """Mark fee payment as paid"""
        self.payment_reference = payment_reference
        self.is_verified = True
        self.verification_date = timezone.now()
        self.save()
        
        # Update student's outstanding balance
        self.student.outstanding_balance -= self.amount_paid
        if self.student.outstanding_balance < 0:
            self.student.outstanding_balance = Decimal('0.00')
        self.student.save(update_fields=['outstanding_balance'])
    
    def issue_receipt(self, issued_by):
        """Issue receipt for fee payment"""
        self.receipt_issued = True
        self.receipt_issued_by = issued_by
        self.save()


# ==================== INVENTORY MODELS ====================

class Inventory(models.Model):
    """Inventory management model"""
    
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    current_stock = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=10)
    maximum_stock = models.IntegerField(default=1000)
    location = models.CharField(max_length=100, blank=True)
    reorder_point = models.IntegerField(default=20)
    last_restocked = models.DateTimeField(null=True, blank=True)
    restock_quantity = models.IntegerField(default=0)
    
    # Status
    is_low_stock = models.BooleanField(default=False)
    needs_restock = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'
    
    def __str__(self):
        return f"Inventory - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Update low stock status
        self.is_low_stock = self.current_stock <= self.minimum_stock
        self.needs_restock = self.current_stock <= self.reorder_point
        
        # Update product stock quantity
        self.product.stock_quantity = self.current_stock
        self.product.save(update_fields=['stock_quantity'])
        
        super().save(*args, **kwargs)
    
    @property
    def stock_status(self):
        """Get stock status"""
        if self.current_stock == 0:
            return 'out_of_stock'
        elif self.is_low_stock:
            return 'low_stock'
        elif self.current_stock >= self.maximum_stock * 0.8:
            return 'high_stock'
        else:
            return 'in_stock'
    
    def increase_stock(self, quantity, restock=False):
        """Increase stock quantity"""
        self.current_stock += quantity
        if restock:
            self.last_restocked = timezone.now()
            self.restock_quantity = quantity
        self.save()
    
    def decrease_stock(self, quantity):
        """Decrease stock quantity"""
        if self.current_stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {self.current_stock}")
        self.current_stock -= quantity
        self.save()


class Supplier(models.Model):
    """Supplier model for inventory"""
    
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = PhoneNumberField()
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    payment_terms = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """Purchase order model for inventory"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    items = models.TextField()  # JSON or text description of items
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Dates
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_orders'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-order_date']
    
    def __str__(self):
        return f"PO #{self.po_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = self.generate_po_number()
        super().save(*args, **kwargs)
    
    def generate_po_number(self):
        """Generate unique purchase order number"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        sequence = PurchaseOrder.objects.filter(
            order_date__year=timezone.now().year
        ).count() + 1
        return f"PO-{timestamp}-{sequence:04d}"
    
    def approve(self, user):
        """Approve purchase order"""
        self.status = 'approved'
        self.approved_by = user
        self.approval_date = timezone.now()
        self.save()
    
    def mark_as_received(self):
        """Mark purchase order as received"""
        self.status = 'received'
        self.actual_delivery = timezone.now().date()
        self.save()


# ==================== ATTENDANCE MODEL ====================

class Attendance(models.Model):
    """Attendance model for students"""
    
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('sick', 'Sick'),
    ]
    
    student = models.ForeignKey(
        'users.Student',
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    
    # Time tracking
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    
    # Late arrival details
    late_minutes = models.IntegerField(default=0)
    late_reason = models.CharField(max_length=200, blank=True)
    
    # Absence details
    absence_reason = models.CharField(max_length=200, blank=True)
    doctor_note = models.BooleanField(default=False)
    
    # Recorded by
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_attendances'
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date', 'student']
        unique_together = ['student', 'date']
    
    def __str__(self):
        return f"{self.student} - {self.date} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Calculate attendance duration"""
        if self.check_in and self.check_out:
            from datetime import datetime
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)
            duration = check_out_dt - check_in_dt
            return duration.total_seconds() / 3600  # Return in hours
        return 0
    
    @property
    def is_full_day(self):
        """Check if it's a full day attendance"""
        return self.duration >= 6  # Assuming 6 hours is a full school day
    
    def mark_present(self, check_in=None, check_out=None):
        """Mark student as present"""
        self.status = 'present'
        if check_in:
            self.check_in = check_in
        if check_out:
            self.check_out = check_out
        self.save()
    
    def mark_absent(self, reason=''):
        """Mark student as absent"""
        self.status = 'absent'
        self.absence_reason = reason
        self.check_in = None
        self.check_out = None
        self.save()
    
    def mark_late(self, minutes, reason=''):
        """Mark student as late"""
        self.status = 'late'
        self.late_minutes = minutes
        self.late_reason = reason
        self.save()


# ==================== SIGNALS (if needed) ====================

# Note: You might want to add signals in a separate signals.py file
# Here's an example of what signals could handle:

def create_user_profile(sender, instance, created, **kwargs):
    """Create corresponding profile when User is created"""
    if created:
        # import related profile models lazily to avoid circular imports
        from users.models import Parent, Teacher, Staff
        if instance.role == 'student':
            # student profile creation handled elsewhere (or leave blank)
            pass
        elif instance.role == 'parent':
            Parent.objects.create(user=instance)
        elif instance.role == 'teacher':
            Teacher.objects.create(user=instance)
        elif instance.role == 'staff':
            Staff.objects.create(user=instance)

def update_inventory_on_order(sender, instance, created, **kwargs):
    """Update inventory when order is completed"""
    if instance.payment_status == 'completed' and instance.status == 'processing':
        for item in instance.items.all():
            inventory = Inventory.objects.filter(product=item.product).first()
            if inventory:
                inventory.decrease_stock(item.quantity)

# Connect signals (you would do this in apps.py or signals.py)
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# 
# @receiver(post_save, sender=User)
# def user_post_save(sender, instance, created, **kwargs):
#     create_user_profile(sender, instance, created, **kwargs)
# 
# @receiver(post_save, sender=Order)
# def order_post_save(sender, instance, created, **kwargs):
#     update_inventory_on_order(sender, instance, created, **kwargs)


# ==================== MODEL UTILITIES ====================

def generate_unique_sku(category=None):
    """Generate unique SKU for products"""
    prefix = category.slug[:3].upper() if category else 'PRO'
    timestamp = timezone.now().strftime('%y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    sku = f"{prefix}-{timestamp}-{random_str}"
    
    # Ensure uniqueness
    while Product.objects.filter(sku=sku).exists():
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        sku = f"{prefix}-{timestamp}-{random_str}"
    
    return sku


def calculate_age(date_of_birth):
    """Calculate age from date of birth"""
    today = timezone.now().date()
    age = today.year - date_of_birth.year
    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


# Export all models for easy import
__all__ = [
    'User', 'Student', 'Parent', 'Teacher', 'Staff',
    'Category', 'Product', 'Cart', 'CartItem', 'Order', 'OrderItem',
    'Payment', 'Transaction', 'Refund', 'FeeStructure', 'FeePayment',
    'Inventory', 'Supplier', 'PurchaseOrder', 'Attendance',
     
]

# models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
import random
import string

class PaymentRecord(models.Model):
    """
    Simplified payment record model for Brillspay.
    Only supports Paystack, Bank, and Naira currency.
    """
    
    class PaymentMethod(models.TextChoices):
        PAYSTACK = 'paystack', _('Paystack')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        BANK_DEPOSIT = 'bank_deposit', _('Bank Deposit')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        SUCCESSFUL = 'successful', _('Successful')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    # Basic Information
    transaction_id = models.CharField(
        _("Transaction ID"),
        max_length=50,
        unique=True,
        help_text="Unique transaction reference"
    )
    
    payer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='payment_records',
        verbose_name=_("Payer")
    )
    
    # Payment Details
    amount = models.DecimalField(
        _("Amount"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Amount in Naira (₦)"
    )
    
    payment_method = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PAYSTACK
    )
    
    payment_status = models.CharField(
        _("Payment Status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    currency = models.CharField(
        _("Currency"),
        max_length=3,
        default='NGN',
        editable=False,
        help_text="Currency code (NGN only)"
    )
    
    # Paystack specific fields
    paystack_reference = models.CharField(
        _("Paystack Reference"),
        max_length=100,
        blank=True,
        help_text="Reference from Paystack"
    )
    
    # Bank specific fields
    bank_name = models.CharField(
        _("Bank Name"),
        max_length=100,
        blank=True,
        help_text="Bank name for bank transfers/deposits"
    )
    
    account_number = models.CharField(
        _("Account Number"),
        max_length=20,
        blank=True,
        help_text="Account number for bank transfers"
    )
    
    deposit_slip_number = models.CharField(
        _("Deposit Slip Number"),
        max_length=50,
        blank=True,
        help_text="Deposit slip number for bank deposits"
    )
    
    # Payment dates
    payment_date = models.DateTimeField(
        _("Payment Date"),
        auto_now_add=True
    )
    
    processed_date = models.DateTimeField(
        _("Processed Date"),
        null=True,
        blank=True
    )
    
    # Description
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text="Payment description"
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(
        _("IP Address"),
        null=True,
        blank=True
    )
    
    user_agent = models.TextField(
        _("User Agent"),
        blank=True
    )
    
    notes = models.TextField(
        _("Admin Notes"),
        blank=True,
        help_text="Internal admin notes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Payment Record')
        verbose_name_plural = _('Payment Records')
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['payer']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['payment_date']),
        ]
    
    def __str__(self):
        return f"Payment {self.transaction_id} - ₦{self.amount:,.2f}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.digits, k=6))
        return f"BRP-{timestamp}-{random_str}"
    
    @property
    def is_paystack(self):
        """Check if payment is via Paystack"""
        return self.payment_method == 'paystack'
    
    @property
    def is_bank_transfer(self):
        """Check if payment is via bank transfer"""
        return self.payment_method == 'bank_transfer'
    
    @property
    def is_bank_deposit(self):
        """Check if payment is via bank deposit"""
        return self.payment_method == 'bank_deposit'
    
    @property
    def is_successful(self):
        """Check if payment is successful"""
        return self.payment_status == 'successful'
    
    @property
    def is_failed(self):
        """Check if payment failed"""
        return self.payment_status == 'failed'
    
    @property
    def is_pending(self):
        """Check if payment is pending"""
        return self.payment_status == 'pending'
    
    def mark_as_successful(self, reference=None):
        """Mark payment as successful"""
        self.payment_status = 'successful'
        self.processed_date = timezone.now()
        
        if reference and self.is_paystack:
            self.paystack_reference = reference
        
        self.save(update_fields=[
            'payment_status', 
            'processed_date', 
            'paystack_reference',
            'updated_at'
        ])
    
    def mark_as_failed(self, notes=''):
        """Mark payment as failed"""
        self.payment_status = 'failed'
        self.processed_date = timezone.now()
        if notes:
            self.notes = f"{self.notes}\nFailed: {notes}"
        
        self.save(update_fields=[
            'payment_status', 
            'processed_date', 
            'notes',
            'updated_at'
        ])
    
    def get_payment_details(self):
        """Get payment details as dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'payer': str(self.payer),
            'amount': f"₦{self.amount:,.2f}",
            'payment_method': self.get_payment_method_display(),
            'payment_status': self.get_payment_status_display(),
            'payment_date': self.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
            'description': self.description,
            'is_successful': self.is_successful,
            'is_pending': self.is_pending,
        }