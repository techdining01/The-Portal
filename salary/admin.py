# salary/admin.py
from django.contrib import admin
from .models import SalaryStructure, TeacherSalary, SalaryPayment

@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_salary', 'allowances', 'deductions', 'net_salary', 'frequency', 'is_active']
    list_editable = ['is_active']
    list_filter = ['frequency', 'is_active']

@admin.register(TeacherSalary)
class TeacherSalaryAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'payment_period', 'basic_salary', 'net_salary', 'payment_status', 'paid_at']
    list_filter = ['payment_status', 'paid_at']
    search_fields = ['teacher__first_name', 'teacher__surname', 'payment_period']
    actions = ['process_payments']
    
    def process_payments(self, request, queryset):
        # This would integrate with Paystack for bulk payments
        updated = queryset.filter(payment_status='pending').update(payment_status='processing')
        self.message_user(request, f'{updated} salaries marked for processing.')
    process_payments.short_description = "Process selected salary payments"

@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ['paystack_reference', 'teacher_salary', 'amount', 'payment_status', 'paid_at']
    list_filter = ['payment_status', 'paid_at']
    readonly_fields = ['gateway_response', 'created_at']