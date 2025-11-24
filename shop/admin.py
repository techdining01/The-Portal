from django.contrib import admin
from .models import Category, Product, Cart, CartItem, Order, OrderItem, TransactionBackup, Receipt, StudentPurchase
from django.utils import timezone

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "price", "product_type",
        "in_stock", "image_preview", "created_at"
    )
    list_filter = ("category", "product_type", "in_stock", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    list_editable = ("in_stock",)

    # Auto slug
    prepopulated_fields = {"slug": ("name",)}

    # For file/image upload
    readonly_fields = ("image_preview",)

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "slug", "category", "product_type", "active")
        }),
        ("Pricing", {
            "fields": ("price",)
        }),
        ("Image", {
            "fields": ("image", "image_preview")
        }),
        ("Description", {
            "fields": ("description",)
        }),
    )

    # Show thumbnail in list view
    def image_preview(self, obj):
        if not obj.image:
            return "(no image)"
        return f'<img src="{obj.image.url}" width="70" style="border-radius:6px;" />'
    image_preview.allow_tags = True
    image_preview.short_description = "Preview"

    @admin.action(description="Mark selected products as In Stock")
    def mark_in_stock(self, request, queryset):
        queryset.update(in_stock=True)

    @admin.action(description="Mark selected products as Out of Stock")
    def mark_out_stock(self, request, queryset):
        queryset.update(in_stock=False)

    actions = [mark_in_stock, mark_out_stock]



@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id","owner","session_key","item_count","created_at")
    readonly_fields = ("created_at","updated_at")
    def item_count(self, obj): return obj.item_count()

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart","product","quantity","student","added_at")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference","parent","email","total","status","created_at","paid_at")
    readonly_fields = ("reference","created_at","receipt_slug")
    actions = ["mark_paid"]
    def mark_paid(self, request, queryset):
        queryset.update(status="paid", paid_at=timezone.now())
    mark_paid.short_description = "Mark selected orders as paid"

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("order", "created_at")
    readonly_fields = ("html_snapshot", "pdf_file")

@admin.register(StudentPurchase)
class StudentPurchaseAdmin(admin.ModelAdmin):
    list_display = ("student", "order_item", "fulfilled", "fulfilled_at")
    list_filter = ("fulfilled",)

@admin.register(TransactionBackup)
class TransactionBackupAdmin(admin.ModelAdmin):
    list_display = ("paystack_reference", "verified", "created_at")
    readonly_fields = ("raw_payload",)
