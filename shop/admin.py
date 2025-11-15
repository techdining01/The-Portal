from django.contrib import admin
from .models import Product, Order, OrderItem, Payment

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','sku','price','stock','active')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('reference','email','status','total_amount','created_at')
    search_fields = ('reference','email')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('gateway_reference','order','amount','status','created_at')
