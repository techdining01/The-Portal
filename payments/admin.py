from django.contrib import admin
from .models import Invoice, Payment




@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'amount', 'currency', 'paid', 'created_at')
    list_filter = ('paid', 'currency')
    search_fields = ('student__first_name', 'student__last_name', 'reference')




@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('gateway_reference', 'invoice', 'amount', 'status', 'created_at')
    search_fields = ('gateway_reference', 'invoice__reference')