from django.contrib import admin
from .models import Item, Cart, CartItem, Order, OrderItem

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name","product_type","price","is_active")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference","user","amount","status","paid_at")
    readonly_fields = ("reference","amount","created_at","paid_at")

# optionally register Cart and others for debugging
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(OrderItem)
