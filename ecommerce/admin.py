# ecommerce/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Category, Product, Cart, CartItem, Order, OrderItem, Payment,
    StudentFeePayment, StockAlert, TransactionBackup, AuditLog,
    BackupRecord, BackupSchedule, RestorePoint, PaymentBackup
) 

# Fix for BackupRecordAdmin - ensure actions is a list, not a method
@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = [
        'backup_name', 'backup_type', 'status', 'file_size_display', 
        'record_count', 'created_at', 'backup_actions'
    ]
    list_filter = [
        'backup_type', 'status', 'is_automated', 'is_encrypted', 'created_at'
    ]
    search_fields = ['backup_name', 'filename', 'description']
    readonly_fields = [
        'created_at', 'started_at', 'completed_at', 'file_size_display',
        'duration', 'checksum', 'retry_count', 'error_message'
    ]
    
    # Define actions as a list, not a method
    actions = ['delete_selected_backups']
    
    def backup_actions(self, obj):
        """Custom method for action buttons in list display"""
        if obj.status == 'completed' and obj.can_restore:
            return format_html(
                '<div class="btn-group">'
                '<a href="{}" class="btn btn-sm btn-info">View</a>'
                '<a href="{}" class="btn btn-sm btn-success">Download</a>'
                '<a href="{}" class="btn btn-sm btn-warning">Verify</a>'
                '</div>',
                reverse('admin:ecommerce_backuprecord_change', args=[obj.pk]),
                reverse('admin_backup_download', args=[obj.pk]),
                reverse('admin_backup_verify', args=[obj.pk])
            )
        return "-"
    backup_actions.short_description = 'Actions'
    
    def delete_selected_backups(self, request, queryset):
        """Custom admin action for deleting backups"""
        for backup in queryset:
            # Add your custom deletion logic here
            backup.delete()
        self.message_user(request, f"Successfully deleted {queryset.count()} backups.")
    delete_selected_backups.short_description = "Delete selected backups"


@admin.register(BackupSchedule)
class BackupScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'backup_type', 'schedule_type', 'is_active', 
        'last_run', 'next_run', 'total_runs'
    ]
    list_filter = ['backup_type', 'schedule_type', 'is_active']
    list_editable = ['is_active']
    readonly_fields = ['last_run', 'next_run', 'total_runs', 'total_failures']
    
    # Define actions as a list
    actions = ['enable_schedules', 'disable_schedules']
    
    def enable_schedules(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Enabled {queryset.count()} schedules.")
    enable_schedules.short_description = "Enable selected schedules"
    
    def disable_schedules(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Disabled {queryset.count()} schedules.")
    disable_schedules.short_description = "Disable selected schedules"


@admin.register(RestorePoint)
class RestorePointAdmin(admin.ModelAdmin):
    list_display = [
        'restore_name', 'backup_record', 'restore_type', 'status', 
        'progress', 'records_restored', 'created_at'
    ]
    list_filter = ['restore_type', 'status', 'created_at']
    readonly_fields = [
        'progress', 'records_restored', 'warnings', 'errors',
        'created_at', 'started_at', 'completed_at', 'duration'
    ]
    
    # Define actions
    actions = ['cancel_restores']

    def cancel_restores(self, request, queryset):
        """Cancel selected restore operations"""
        for restore in queryset:
            if restore.status in ['pending', 'in_progress']:
                restore.status = 'cancelled'
                restore.save()
        self.message_user(request, f"Cancelled {queryset.count()} restore operations.")
    cancel_restores.short_description = "Cancel selected restores"


@admin.register(PaymentBackup)
class PaymentBackupAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'backup_type', 'created_at', 'created_by'
    ]
    list_filter = ['backup_type', 'created_at']
    readonly_fields = ['created_at', 'checksum']
    
    # Define actions
    actions = ['delete_selected_payment_backups']

    def delete_selected_payment_backups(self, request, queryset):
        queryset.delete()
        self.message_user(request, f"Deleted {queryset.count()} payment backups.")
    delete_selected_payment_backups.short_description = "Delete selected payment backups"


@admin.register(TransactionBackup)
class TransactionBackupAdmin(admin.ModelAdmin):
    list_display = [
        'reference_number', 'transaction_type', 'original_id',
        'backup_status', 'created_at'
    ]
    list_filter = ['transaction_type', 'backup_status', 'created_at']
    search_fields = ['reference_number', 'original_id']
    readonly_fields = ['created_at', 'updated_at', 'checksum']
    
    # Define actions
    actions = ['archive_backups', 'delete_selected_backups']

    def archive_backups(self, request, queryset):
        queryset.update(backup_status='archived')
        self.message_user(request, f"Archived {queryset.count()} transaction backups.")
    archive_backups.short_description = "Archive selected backups"

    def delete_selected_backups(self, request, queryset):
        queryset.delete()
        self.message_user(request, f"Deleted {queryset.count()} transaction backups.")
    delete_selected_backups.short_description = "Delete selected backups"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'action_type', 'table_name', 'record_id', 'user', 'created_at'
    ]
    list_filter = ['action_type', 'table_name', 'created_at']
    search_fields = ['record_id', 'description', 'reference']
    readonly_fields = ['created_at']
    
    # Define actions
    actions = ['delete_selected_logs']

    def delete_selected_logs(self, request, queryset):
        if request.user.is_superuser:
            queryset.delete()
            self.message_user(request, f"Deleted {queryset.count()} audit logs.")
        else:
            self.message_user(request, "Only superusers can delete audit logs.", level='error')
    delete_selected_logs.short_description = "Delete selected audit logs (Superuser only)"

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Your existing admin classes for other models
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    search_fields = ['name']
    actions = ['activate_categories', 'deactivate_categories']

    def activate_categories(self, request, queryset):
        queryset.update(is_active=True)
    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_categories.short_description = "Deactivate selected categories"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'product_type', 'price', 'stock_quantity', 'is_available']
    list_filter = ['category', 'product_type', 'is_available']
    search_fields = ['name', 'description']
    list_editable = ['price', 'stock_quantity', 'is_available']
    actions = ['make_available', 'make_unavailable']

    def make_available(self, request, queryset):
        queryset.update(is_available=True)
    make_available.short_description = "Mark selected products as available"

    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    make_unavailable.short_description = "Mark selected products as unavailable"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total_amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username']
    actions = ['mark_as_processing', 'mark_as_completed']

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
    mark_as_processing.short_description = "Mark selected orders as processing"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_as_completed.short_description = "Mark selected orders as completed"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'order', 'amount', 'status', 'payment_gateway', 'payment_date']
    list_filter = ['status', 'payment_gateway', 'payment_date']
    search_fields = ['reference', 'order__order_number']
    actions = ['mark_as_verified', 'mark_as_failed']

    def mark_as_verified(self, request, queryset):
        queryset.update(verified=True, status='successful')
    mark_as_verified.short_description = "Mark selected payments as verified"

    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_as_failed.short_description = "Mark selected payments as failed"