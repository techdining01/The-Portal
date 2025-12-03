from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Transaction
from .models import PaymentRecord

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'created_at']
    search_fields = ['name']
    
    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'stock', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['total_price']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'items_count', 'total_amount', 'created_at']
    inlines = [CartItemInline]
    readonly_fields = ['created_at', 'updated_at']
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total_amount', 'status', 'payment_verified', 'created_at']
    list_filter = ['status', 'payment_verified', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered']
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid', payment_verified=True)
        self.message_user(request, f'{updated} orders marked as paid.')
    mark_as_paid.short_description = "Mark selected orders as paid"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = "Mark selected orders as shipped"
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected orders as delivered"

# @admin.register(Transaction)
# class TransactionAdmin(admin.ModelAdmin):
#     list_display = ['payment_reference', 'order_link', 'amount', 'payment_status', 'paid_at', 'created_at']
#     list_filter = ['payment_status', 'created_at']
#     search_fields = ['payment_reference', 'order__order_number']
#     readonly_fields = ['created_at', 'updated_at', 'gateway_response']
    
#     def order_link(self, obj):
#         return format_html('<a href="/admin/store/order/{}/change/">{}</a>', 
#                          obj.order.id, obj.order.order_number)
#     order_link.short_description = 'Order'



@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('reference', 'order', 'user', 'amount', 'payment_status', 
                    'payment_method', 'paid_at', 'stock_updated', 'initiated_at')
    list_filter = ('payment_status', 'payment_method', 'gateway', 'stock_updated', 'initiated_at')
    search_fields = ('reference', 'gateway_reference', 'user__username', 'user__email', 'order__id')
    readonly_fields = ('initiated_at', 'paid_at', 'gateway_response', 'refunded_at')
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('order', 'user', 'reference', 'gateway_reference', 'gateway')
        }),
        ('Amount & Status', {
            'fields': ('amount', 'amount_paid', 'payment_status', 'payment_method')
        }),
        ('Timing', {
            'fields': ('initiated_at', 'paid_at')
        }),
        ('Refund Info', {
            'fields': ('refund_amount', 'refund_reason', 'refunded_at')
        }),
        ('Stock Management', {
            'fields': ('stock_updated',)
        }),
        ('Gateway Data', {
            'fields': ('gateway_response', 'gateway_message'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_stock_updated', 'export_payments_csv']
    
    def mark_stock_updated(self, request, queryset):
        """Mark selected payments as stock updated"""
        updated = queryset.update(stock_updated=True)
        self.message_user(request, f'{updated} payments marked as stock updated')
    mark_stock_updated.short_description = "Mark as stock updated"
    
    def export_payments_csv(self, request, queryset):
        """Export payments to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Reference', 'Order', 'User', 'Amount', 'Status', 
                         'Method', 'Paid At', 'Stock Updated'])
        
        for payment in queryset:
            writer.writerow([
                payment.reference,
                payment.order.id,
                payment.user.email,
                payment.amount,
                payment.get_payment_status_display(),
                payment.get_payment_method_display(),
                payment.paid_at.strftime('%Y-%m-%d %H:%M') if payment.paid_at else '',
                'Yes' if payment.stock_updated else 'No'
            ])
        
        return response
    export_payments_csv.short_description = "Export selected payments to CSV"