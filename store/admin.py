# store/admin.py (Enhanced)
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Transaction

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'created_at']
    search_fields = ['name']
    
    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'stock_quantity', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['subtotal']

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

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['paystack_reference', 'order_link', 'amount', 'payment_status', 'paid_at', 'created_at']
    list_filter = ['payment_status', 'created_at']
    search_fields = ['paystack_reference', 'order__order_number']
    readonly_fields = ['created_at', 'updated_at', 'gateway_response']
    
    def order_link(self, obj):
        return format_html('<a href="/admin/store/order/{}/change/">{}</a>', 
                         obj.order.id, obj.order.order_number)
    order_link.short_description = 'Order'


