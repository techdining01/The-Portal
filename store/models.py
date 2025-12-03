
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
    stock = models.PositiveIntegerField(default=0)
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
        return '/static/images/default_product.png' 
    

# models.py - Add these
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @staticmethod
    def get_cart_for_user(user):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=user)
        return cart
    
    @property
    def total_amount(self):
        try:
            return sum(item.total_price for item in self.items.all())
        except:
            return 0
    
    @property
    def items_count(self):
        return self.items.count()
    
    def get_cart_data(self):
        """Get cart data for session"""
        items = []
        for item in self.items.all():
            items.append({
                'product_id': item.product.id,
                'quantity': item.quantity,
                'product_name': item.product.name,
                'product_price': float(item.product.price),
                'product_image': item.product.image_url,
                'total_price': float(item.total_price)
            })
        return {
            'items': items,
            'total': float(self.total_amount),
            'count': self.items_count
        }

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Customer Information
    customer_name = models.CharField(max_length=255, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_address = models.TextField(blank=True)
    customer_email = models.EmailField(blank=True)
    
    # Shipping Information
    shipping_address = models.TextField(blank=True)
    shipping_notes = models.TextField(blank=True)
    
    # Payment Information
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, default='paystack')
    payment_gateway = models.CharField(max_length=50, default='paystack')
    payment_reference = models.CharField(max_length=100, unique=True)
    payment_verified = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"BRP{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.order_number
    
    @property
    def display_status(self):
        """Get formatted status with color"""
        status_colors = {
            'pending': 'warning',
            'paid': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger'
        }
        return {
            'text': self.get_status_display(),
            'color': status_colors.get(self.status, 'secondary')
        }
    
    @property
    def display_payment_status(self):
        """Get formatted payment status with color"""
        payment_colors = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'secondary'
        }
        return {
            'text': self.get_payment_status_display(),
            'color': payment_colors.get(self.payment_status, 'secondary')
        }
    
    @property
    def formatted_date(self):
        """Get formatted date"""
        return self.created_at.strftime("%b %d, %Y")
    
    @property
    def formatted_time(self):
        """Get formatted time"""
        return self.created_at.strftime("%I:%M %p")
    
    @property
    def items_list(self):
        """Get list of item names"""
        items = self.items.all()[:3]  # First 3 items
        names = [item.product.name for item in items]
        if self.items.count() > 3:
            names.append(f"+{self.items.count() - 3} more")
        return names
    

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
        ('abandoned', 'Abandoned'),
        ('reversed', 'Reversed'),
    ]
    
    PAYMENT_METHOD = [
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('ussd', 'USSD'),
        ('qr', 'QR Code'),
        ('bank', 'Bank'),
    ]
    
    # Relationships
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='transaction')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    
    # Payment Information
    payment_reference = models.CharField(max_length=100, unique=True, db_index=True)
    paystack_reference = models.CharField(max_length=100, blank=True)  # Paystack's reference
    gateway_reference = models.CharField(max_length=100, blank=True)   # Other gateway references
    
    # Amount Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='NGN')
    
    # Status Information
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, blank=True)
    payment_gateway = models.CharField(max_length=50, default='paystack')
    is_verified = models.BooleanField(default=False)
    
    # Gateway Response
    gateway_response = models.JSONField(default=dict, blank=True)  # Changed to JSONField
    gateway_message = models.TextField(blank=True)
    
    # Timing Information
    initiated_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    channel = models.CharField(max_length=50, blank=True)
    customer_code = models.CharField(max_length=100, blank=True)
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_reference']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'payment_status']),
        ]
    
    def __str__(self):
        return f"{self.payment_reference} - ₦{self.amount} ({self.payment_status})"
    
    @property
    def is_successful(self):
        return self.payment_status == 'success'
    
    @property
    def is_pending(self):
        return self.payment_status == 'pending'
    
    @property
    def is_failed(self):
        return self.payment_status == 'failed'
    
    @property
    def payment_duration(self):
        """Calculate time taken for payment"""
        if self.paid_at and self.initiated_at:
            return self.paid_at - self.initiated_at
        return None
    
    def mark_as_successful(self, response_data=None):
        """Mark transaction as successful"""
        self.payment_status = 'success'
        self.amount_paid = self.amount
        self.paid_at = timezone.now()
        self.is_verified = True
        self.verified_at = timezone.now()
        
        if response_data:
            self.gateway_response = response_data
            self.gateway_message = response_data.get('message', '')
            self.paystack_reference = response_data.get('reference', '')
            self.payment_method = response_data.get('channel', '')
            self.channel = response_data.get('channel', '')
            self.customer_code = response_data.get('customer', {}).get('customer_code', '')
        
        self.save()
        
        # Update associated order
        if self.order:
            self.order.payment_status = 'completed'
            self.order.status = 'processing'
            self.order.save()
    
    def mark_as_failed(self, error_message=None):
        """Mark transaction as failed"""
        self.payment_status = 'failed'
        self.gateway_message = error_message or 'Payment failed'
        self.save()
        
        # Update associated order
        if self.order:
            self.order.payment_status = 'failed'
            self.order.save()
    
    def mark_as_pending(self):
        """Mark transaction as pending"""
        self.payment_status = 'pending'
        self.save()
    
    def update_from_gateway_response(self, response_data):
        """Update transaction with gateway response"""
        if response_data:
            self.gateway_response = response_data
            
            if response_data.get('status') == 'success':
                self.mark_as_successful(response_data)
            elif response_data.get('status') == 'failed':
                self.mark_as_failed(response_data.get('message', 'Payment failed'))
            
            self.save()
    
    def get_payment_details(self):
        """Get payment details for display"""
        return {
            'reference': self.payment_reference,
            'amount': self.amount,
            'status': self.get_payment_status_display(),
            'method': self.get_payment_method_display() if self.payment_method else 'N/A',
            'paid_at': self.paid_at.strftime('%d-%m-%Y %H:%M:%S') if self.paid_at else 'N/A',
            'gateway': self.payment_gateway,
            'is_verified': self.is_verified,
        }
    


class PaymentRecord(models.Model):
    """
    SIMPLE payment recording for admin, refunds, and stock management
    """
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_METHOD = [
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('ussd', 'USSD'),
        ('qr', 'QR'),
    ]
    
    # Simple relationships
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='payment')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    
    # Payment References
    reference = models.CharField(max_length=100, unique=True)  # Your reference: PAY_ABC123
    gateway_reference = models.CharField(max_length=100)       # Paystack reference
    gateway = models.CharField(max_length=20, default='paystack')
    
    # Amount & Status
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, blank=True)
    
    # Gateway Data (for admin and refunds)
    gateway_response = models.JSONField(default=dict)  # Store Paystack response
    gateway_message = models.TextField(blank=True)
    
    # Timing for awareness
    initiated_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Refund tracking
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Stock management flag
    stock_updated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['user', 'initiated_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.reference} - ₦{self.amount} ({self.payment_status})"
    
    @property
    def is_successful(self):
        return self.payment_status == 'success'
    
    @property
    def is_refundable(self):
        """Check if payment can be refunded"""
        return self.payment_status == 'success' and self.refund_amount < self.amount_paid
    
    @property
    def remaining_amount(self):
        """Amount available for refund"""
        return self.amount_paid - self.refund_amount
    
    def mark_as_successful(self, gateway_data=None):
        """Mark payment as successful"""
        self.payment_status = 'success'
        self.amount_paid = self.amount
        self.paid_at = timezone.now()
        
        if gateway_data:
            self.gateway_response = gateway_data
            self.gateway_message = gateway_data.get('message', '')
            self.payment_method = gateway_data.get('channel', '')
            self.gateway_reference = gateway_data.get('reference', '')
        
        self.save()
        
        # Update order status
        self.order.payment_status = 'completed'
        self.order.status = 'processing'
        self.order.save()
    
    def initiate_refund(self, amount, reason):
        """Initiate a refund"""
        if amount > self.remaining_amount:
            raise ValueError(f"Cannot refund more than ₦{self.remaining_amount}")
        
        self.refund_amount += amount
        self.refund_reason = reason
        
        if self.refund_amount >= self.amount_paid:
            self.payment_status = 'refunded'
        else:
            self.payment_status = 'partially_refunded'
        
        self.refunded_at = timezone.now()
        self.save()
        
        # Update order status
        self.order.status = 'refunded' if self.payment_status == 'refunded' else 'partially_refunded'
        self.order.save()
        
        return True
    
    def update_stock_status(self, updated=True):
        """Mark if stock has been updated"""
        self.stock_updated = updated
        self.save()
    
    def get_summary(self):
        """Get payment summary for admin"""
        return {
            'reference': self.reference,
            'order_number': self.order.order_number,
            'user': self.user.get_full_name() or self.user.username,
            'amount': self.amount,
            'amount_paid': self.amount_paid,
            'status': self.get_payment_status_display(),
            'method': self.get_payment_method_display() if self.payment_method else 'N/A',
            'paid_at': self.paid_at.strftime('%Y-%m-%d %H:%M') if self.paid_at else 'Pending',
            'gateway': self.gateway,
            'refund_amount': self.refund_amount,
            'stock_updated': 'Yes' if self.stock_updated else 'No',
        }
    

class ActivityLog(models.Model):
    """Track admin activities"""
    ACTIVITY_TYPES = [
        ('order', 'Order'),
        ('payment', 'Payment'),
        ('product', 'Product'),
        ('user', 'User'),
        ('system', 'System'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.description[:50]}"