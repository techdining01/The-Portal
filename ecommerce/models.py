from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid, json, hashlib



class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Product Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    PRODUCT_TYPES = [
        ('school_fee', 'School Fee'),
        ('registration', 'Registration Form'),
        ('uniform', 'Uniform'),
        ('textbook', 'Textbook'),
        ('stationery', 'Stationery'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Inventory Management
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    is_available = models.BooleanField(default=True)
    track_stock = models.BooleanField(default=False)
    
    # Media
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # For school fees - link to specific class
    applicable_class = models.ForeignKey(
        'exams.Class', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="For school fees - which class this fee applies to"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def in_stock(self):
        if not self.track_stock:
            return True
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        if not self.track_stock:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    def reduce_stock(self, quantity):
        """Reduce stock quantity"""
        if self.track_stock:
            self.stock_quantity -= quantity
            self.save()
    
    def increase_stock(self, quantity):
        """Increase stock quantity"""
        if self.track_stock:
            self.stock_quantity += quantity
            self.save()
    
    def __str__(self):
        return f"{self.name} - ₦{self.price}"

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def item_count(self):
        return self.items.count()
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.items.all().delete()
    
    def __str__(self):
        return f"Cart for {self.user.get_full_name()}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        help_text="Student this purchase is for"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'product', 'student']
    
    @property
    def total_price(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.student.get_full_name()}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('paystack', 'Paystack'),
        ('opay', 'OPay'),
        ('transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]
    
    order_number = models.CharField(max_length=60, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Billing information
    billing_address = models.TextField(blank=True, null=True)
    billing_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def generate_order_number(self):
        timestamp = timezone.now().strftime('%d%m%Y%H%M%S')
        return f"ORD{timestamp}{self.user.id:04d}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @property
    def can_be_cancelled(self):
        return self.status in ['pending', 'processing']
    
    def mark_as_paid(self):
        """Mark order as paid"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()
        
        # Update stock for physical products
        for item in self.items.all():
            if item.product.track_stock:
                item.product.reduce_stock(item.quantity)
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.get_full_name()}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    
    class Meta:
        ordering = ['-id']
    
    @property
    def total_price(self):
        return self.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.student.get_full_name()}"



class StudentFeePayment(models.Model):
    """Track school fee payments for students"""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    academic_session = models.CharField(max_length=20)
    term = models.CharField(max_length=20)
    fee_type = models.ForeignKey(Product, on_delete=models.CASCADE, limit_choices_to={'product_type': 'school_fee'})
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'academic_session', 'term', 'fee_type']
        verbose_name_plural = "Student Fee Payments"
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.academic_session} {self.term} Fee"


class StockAlert(models.Model):
    """Track low stock alerts"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    current_stock = models.PositiveIntegerField()
    alert_type = models.CharField(max_length=20, choices=[('low', 'Low Stock'), ('out', 'Out of Stock')])
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    def mark_resolved(self):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.product.name} - {self.alert_type} Alert"


class TransactionBackup(models.Model):
    """Complete backup of all transaction data"""
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('order', 'Order'),
        ('cart', 'Cart'),
    ]
    
    BACKUP_STATUS = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deleted', 'Soft Deleted'),
    ]
    
    # Core identification
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    original_id = models.CharField(max_length=100)  # ID of the original record
    reference_number = models.CharField(max_length=100, unique=True)
    
    # Complete data snapshot
    data_snapshot = models.JSONField()  # Complete JSON backup of the original record
    related_data = models.JSONField(default=dict)  # Backup of related records
    
    # Metadata
    backup_reason = models.CharField(max_length=200, blank=True, null=True)
    backed_up_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    original_created_at = models.DateTimeField()  # When original was created
    original_updated_at = models.DateTimeField()  # When original was last updated
    
    # Backup management
    backup_status = models.CharField(max_length=20, choices=BACKUP_STATUS, default='active')
    checksum = models.CharField(max_length=64, help_text="SHA256 checksum for data integrity")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transaction_backups'
        indexes = [
            models.Index(fields=['transaction_type', 'original_id']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Backup {self.reference_number} - {self.transaction_type}"
    
    def verify_integrity(self):
        """Verify data integrity using checksum"""
        import hashlib
        data_string = json.dumps(self.data_snapshot, sort_keys=True)
        current_checksum = hashlib.sha256(data_string.encode()).hexdigest()
        return current_checksum == self.checksum
    
    def restore(self, user):
        """Restore this backup (creates a new record)"""
        from .backup_service import BackupService
        return BackupService().restore_backup(self, user)


class AuditLog(models.Model):
    """Comprehensive audit trail for all critical actions"""
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('status_change', 'Status Change'),
        ('stock_update', 'Stock Update'),
        ('user_action', 'User Action'),
    ]
    
    # Core information
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    table_name = models.CharField(max_length=100)  # Which table was affected
    record_id = models.CharField(max_length=100)  # ID of affected record
    
    # User information
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Change details
    old_values = models.JSONField(blank=True, null=True)  # Values before change
    new_values = models.JSONField(blank=True, null=True)  # Values after change
    changed_fields = models.JSONField(blank=True, null=True)  # List of changed fields
    
    # Additional context
    description = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)  # e.g., order number
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['user', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action_type} on {self.table_name} by {self.user}"


class PaymentBackup(models.Model):
    """Specialized backup for payment transactions"""
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='backups')
    backup_type = models.CharField(max_length=20, choices=[
        ('initial', 'Initial Payment'),
        ('status_change', 'Status Change'),
        ('refund', 'Refund'),
        ('verification', 'Verification'),
        ('webhook', 'Webhook Processing'),
    ])
    
    # Complete payment state
    payment_data = models.JSONField()  # Complete payment data snapshot
    gateway_response = models.JSONField(blank=True, null=True)  # Gateway response if any
    order_data = models.JSONField()  # Related order data
    
    # Security
    checksum = models.CharField(max_length=64)
    encrypted_data = models.BinaryField(blank=True, null=True)  # For sensitive data
    
    # Metadata
    reason = models.CharField(max_length=200, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_backups'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment Backup {self.payment.reference} - {self.backup_type}"



class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
        ('processing', 'Processing'),
    ]
    
    PAYMENT_GATEWAYS = [
        ('paystack', 'Paystack'),
        ('opay', 'OPay'),
        ('manual', 'Manual'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50)
    payment_gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAYS)
    
    # Webhook tracking
    webhook_received = models.BooleanField(default=False)
    webhook_processed_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.IntegerField(default=0)
    last_verification_attempt = models.DateTimeField(null=True, blank=True)
    
    # Manual payment fields
    transfer_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    transfer_date = models.DateField(blank=True, null=True)
    transfer_reference = models.CharField(max_length=100, blank=True, null=True)
    
    gateway_response = models.JSONField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    
    # For refunds
    refunded = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    payment_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # backups_archive = models.ManyToManyField('PaymentBackup', through='PaymentBackup', related_name='grand_payment_backups')

    
    class Meta:
        ordering = ['-payment_date']
    
    def mark_as_processing(self):
        """Mark payment as being processed by webhook"""
        self.status = 'processing'
        self.webhook_received = True
        self.save()
    
    def mark_as_paid(self, paystack_reference=None, gateway_data=None):
        """Mark payment as successful"""
        self.status = 'successful'
        self.verified = True
        if paystack_reference:
            self.paystack_reference = paystack_reference
        if gateway_data:
            self.gateway_response = gateway_data
        self.webhook_processed_at = timezone.now()
        self.save()
        
        # Update order status
        self.order.mark_as_paid()
    
    def mark_as_failed(self, gateway_data=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if gateway_data:
            self.gateway_response = gateway_data
        self.save()
    
    def can_retry_verification(self):
        """Check if we can retry API verification"""
        if self.verification_attempts >= 3:
            return False
        if self.last_verification_attempt:
            return timezone.now() - self.last_verification_attempt > timezone.timedelta(minutes=5)
        return True
    
    def record_verification_attempt(self):
        """Record verification attempt"""
        self.verification_attempts += 1
        self.last_verification_attempt = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Payment {self.reference} - {self.status}"
  


class BackupRecord(models.Model):
    """Model to track all backup operations"""
    BACKUP_TYPES = [
        ('database', 'Database'),
        ('transactions', 'Transactions'),
        ('payments', 'Payments'),
        ('audit_logs', 'Audit Logs'),
        ('full_system', 'Full System'),
    ]
    
    BACKUP_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]
    
    # Backup identification
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES)
    backup_name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # File information
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    file_format = models.CharField(max_length=10, default='json')  # json, sql, zip
    
    # Backup metadata
    status = models.CharField(max_length=20, choices=BACKUP_STATUS, default='pending')
    is_automated = models.BooleanField(default=True)
    is_encrypted = models.BooleanField(default=False)
    compression_ratio = models.FloatField(null=True, blank=True, help_text="Compression ratio if applicable")
    
    # Data integrity
    checksum = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 checksum")
    record_count = models.IntegerField(default=0, help_text="Number of records backed up")
    
    # Relationships
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Timestamps with timezone awareness
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'backup_records'
        verbose_name = 'Backup Record'
        verbose_name_plural = 'Backup Records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['backup_type', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.backup_name} ({self.backup_type})"
    
    def save(self, *args, **kwargs):
        if not self.backup_name:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            self.backup_name = f"{self.backup_type}_backup_{timestamp}"
        
        if not self.filename:
            self.filename = f"{self.backup_name}.{self.file_format}"
        
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Calculate backup duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def file_size_display(self):
        """Human readable file size"""
        if self.file_size == 0:
            return "0 B"
        
        sizes = ['B', 'KB', 'MB', 'GB']
        i = 0
        size = float(self.file_size)
        while size >= 1024 and i < len(sizes) - 1:
            size /= 1024
            i += 1
        return f"{size:.2f} {sizes[i]}"
    
    @property
    def can_restore(self):
        """Check if backup can be restored"""
        return self.status == 'completed' and self.checksum
    
    def verify_integrity(self):
        """Verify backup file integrity"""
        if not self.checksum or not self.file_path:
            return False
        
        try:
            import os
            if not os.path.exists(self.file_path):
                return False
            
            with open(self.file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return file_hash == self.checksum
        except Exception:
            return False
    
    def mark_in_progress(self):
        """Mark backup as in progress"""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save()
    
    def mark_completed(self, file_size=0, record_count=0, checksum=None):
        """Mark backup as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.file_size = file_size
        self.record_count = record_count
        if checksum:
            self.checksum = checksum
        self.save()
    
    def mark_failed(self, error_message):
        """Mark backup as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save()

class BackupSchedule(models.Model):
    """Model to manage automated backup schedules"""
    SCHEDULE_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]
    
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    name = models.CharField(max_length=100)
    backup_type = models.CharField(max_length=20, choices=BackupRecord.BACKUP_TYPES)
    schedule_type = models.CharField(max_length=10, choices=SCHEDULE_TYPES)
    
    # Scheduling details
    is_active = models.BooleanField(default=True)
    time_of_day = models.TimeField(default=timezone.now)  # When to run
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, null=True, blank=True)
    day_of_month = models.IntegerField(null=True, blank=True)  # 1-31
    
    # Retention policy
    keep_backups_days = models.IntegerField(default=30, help_text="Keep backups for X days")
    max_backups = models.IntegerField(default=10, help_text="Maximum number of backups to keep")
    
    # Notification settings
    notify_on_success = models.BooleanField(default=False)
    notify_on_failure = models.BooleanField(default=True)
    notification_email = models.EmailField(blank=True, null=True)
    
    # Metadata
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    total_runs = models.IntegerField(default=0)
    total_failures = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'backup_schedules'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.backup_type})"
    
    def calculate_next_run(self):
        """Calculate next run time based on schedule"""
        from datetime import datetime, timedelta
        
        now = timezone.now()
        
        if self.schedule_type == 'daily':
            next_run = datetime.combine(now.date() + timedelta(days=1), self.time_of_day)
        
        elif self.schedule_type == 'weekly' and self.day_of_week is not None:
            days_ahead = self.day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_date = now.date() + timedelta(days=days_ahead)
            next_run = datetime.combine(next_date, self.time_of_day)
        
        elif self.schedule_type == 'monthly' and self.day_of_month is not None:
            # Simple monthly calculation - for production, use a proper scheduler
            next_month = now.month + 1 if now.month < 12 else 1
            next_year = now.year if now.month < 12 else now.year + 1
            next_run = datetime(next_year, next_month, min(self.day_of_month, 28), 
                              self.time_of_day.hour, self.time_of_day.minute)
        else:
            return None
        
        return timezone.make_aware(next_run)
    
    def should_run(self):
        """Check if backup should run now"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        if self.next_run and now >= self.next_run:
            return True
        
        return False

class RestorePoint(models.Model):
    """Model to track system restore operations"""
    RESTORE_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    backup_record = models.ForeignKey(BackupRecord, on_delete=models.CASCADE)
    restore_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Restore configuration
    restore_type = models.CharField(max_length=20, choices=BackupRecord.BACKUP_TYPES)
    options = models.JSONField(default=dict, help_text="Restore options and filters")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=RESTORE_STATUS, default='pending')
    progress = models.IntegerField(default=0, help_text="Progress percentage")
    
    # Results
    records_restored = models.IntegerField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    
    # Audit trail
    restored_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'restore_points'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Restore: {self.restore_name} from {self.backup_record.backup_name}"
    
    @property
    def duration(self):
        """Calculate restore duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

# Add these to your existing models (PaymentBackup was already defined)
class PaymentBackup(models.Model):
    """Specialized backup for payment transactions"""
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='backups')
    backup_type = models.CharField(max_length=20, choices=[
        ('initial', 'Initial Payment'),
        ('status_change', 'Status Change'),
        ('refund', 'Refund'),
        ('verification', 'Verification'),
        ('webhook', 'Webhook Processing'),
    ])
    
    # Complete payment state
    payment_data = models.JSONField()  # Complete payment data snapshot
    gateway_response = models.JSONField(blank=True, null=True)  # Gateway response if any
    order_data = models.JSONField()  # Related order data
    
    # Security
    checksum = models.CharField(max_length=64)
    encrypted_data = models.BinaryField(blank=True, null=True)  # For sensitive data
    
    # Metadata
    reason = models.CharField(max_length=200, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment_backups'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment Backup {self.payment.reference} - {self.backup_type}"