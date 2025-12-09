from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, F
from rangefilter.filters import DateRangeFilter
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from store.models import (
    Order,FeeStructure, FeePayment, Payment, Product,
    Cart, CartItem, Inventory, OrderItem, Category, 
    Transaction, Supplier, PurchaseOrder, Attendance,
    ) 
from users.models import User, Student, Parent, Teacher, Staff
from django.utils import timezone

# ==================== INLINE ADMIN CLASSES ====================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'subtotal')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'quantity', 'get_subtotal')
    readonly_fields = ('get_subtotal',)

    def get_subtotal(self, obj):
        return f"₦{obj.subtotal:,.2f}"
    get_subtotal.short_description = 'Subtotal'

class FeePaymentInline(admin.TabularInline):
    model = FeePayment
    extra = 0
    readonly_fields = ('fee_structure', 'amount_paid', 'payment_date', 'payment_method')
    can_delete = False


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'price', 'stock_quantity', 
                 'sku', 'is_active', 'created_at')
        export_order = fields

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ('id', 'order_number', 'user', 'student', 'total_amount', 
                 'status', 'payment_status', 'created_at')
        

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'product_count', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('product_count',)
    
    def product_count(self, obj):
        count = obj.products.count()
        url = reverse('admin:store_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    product_count.short_description = 'Products'

@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_class = OrderResource
    list_display = ('order_number', 'user', 'student', 'total_amount', 
                    'status', 'payment_status', 'created_at', 'payment_button')
    list_filter = ('status', 'payment_status', 
                   ('created_at', DateRangeFilter), 'payment_method')
    search_fields = ('order_number', 'user__username', 'user__email', 
                     'student__admission_number', 'student__first_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 
                      'total_amount', 'payment_details')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'student', 'status', 'notes')
        }),
        ('Payment Information', {
            'fields': ('total_amount', 'payment_status', 'payment_method', 
                      'payment_reference', 'payment_date', 'payment_details')
        }),
        ('Delivery Information', {
            'fields': ('shipping_address', 'delivery_date', 'delivery_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def payment_button(self, obj):
        if obj.payment_status == 'pending':
            url = reverse('admin:store_payment_process', args=[obj.id])
            return format_html(
                '<a href="{}" class="button" style="background: #4CAF50; color: white; '
                'padding: 5px 10px; border-radius: 3px; text-decoration: none;">'
                'Process Payment</a>',
                url
            )
        elif obj.payment_status == 'completed':
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Paid</span>'
            )
        return obj.get_payment_status_display()
    payment_button.short_description = 'Payment Action'
    
    def payment_details(self, obj):
        payments = obj.payments.all()
        if payments:
            details = []
            for payment in payments:
                details.append(
                    f"{payment.payment_method}: ₦{payment.amount:,.2f} "
                    f"({payment.get_status_display()})"
                )
            return "<br>".join(details)
        return "No payment details"
    payment_details.short_description = 'Payment Details'
    
    actions = ['mark_as_completed', 'mark_as_cancelled', 'export_orders']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} orders marked as completed.')
    mark_as_completed.short_description = "Mark selected orders as completed"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} orders cancelled.')
    mark_as_cancelled.short_description = "Cancel selected orders"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'student', 'item_count', 'total_amount', 
                    'created_at', 'updated_at')
    list_filter = (('created_at', DateRangeFilter),)
    search_fields = ('user__username', 'student__admission_number')
    readonly_fields = ('created_at', 'updated_at', 'total_amount')
    inlines = [CartItemInline]
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
    
    def total_amount(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount.short_description = 'Total'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'order', 'amount', 'payment_method', 
                    'status', 'created_at', 'verified_at', 'receipt_button')
    list_filter = ('status', 'payment_method', ('created_at', DateRangeFilter))
    search_fields = ('reference', 'order__order_number', 'paystack_reference')
    readonly_fields = ('created_at', 'updated_at', 'verified_at', 'receipt_url')
    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'amount', 'payment_method', 'status')
        }),
        ('Payment References', {
            'fields': ('reference', 'paystack_reference', 'transaction_id')
        }),
        ('Receipt', {
            'fields': ('receipt_url', 'receipt_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'verified_at')
        }),
    )
    
    def receipt_button(self, obj):
        if obj.receipt_url:
            return format_html(
                '<a href="{}" target="_blank" class="button" style="background: #2196F3; '
                'color: white; padding: 5px 10px; border-radius: 3px; text-decoration: none;">'
                'View Receipt</a>',
                obj.receipt_url
            )
        return "No receipt"
    receipt_button.short_description = 'Receipt'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'student', 'amount', 
                    'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', ('created_at', DateRangeFilter))
    search_fields = ('transaction_id', 'user__username', 'student__admission_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'student_class', 'term', 
                    'amount', 'due_date', 'is_active')
    list_filter = ('academic_year', 'student_class', 'term', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FeePaymentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'academic_year', 'student_class', 'term')
        }),
        ('Fee Details', {
            'fields': ('amount', 'due_date', 'late_fee', 'late_fee_date')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_structure', 'amount_paid', 
                    'payment_date', 'payment_method', 'receipt_number')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('student__admission_number', 'receipt_number', 
                     'fee_structure__name')
    readonly_fields = ('payment_date', 'receipt_number')
    
    def has_add_permission(self, request):
        return False

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'current_stock', 'minimum_stock', 
                    'maximum_stock', 'last_restocked', 'stock_status')
    list_filter = (('last_restocked', DateRangeFilter),)
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('current_stock', 'last_restocked')
    
    def stock_status(self, obj):
        if obj.current_stock <= obj.minimum_stock:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ Low Stock</span>')
        elif obj.current_stock >= obj.maximum_stock:
            return format_html('<span style="color: blue; font-weight: bold;">🟢 High Stock</span>')
        return format_html('<span style="color: green;">✓ In Stock</span>')
    stock_status.short_description = 'Status'

# ==================== CUSTOM ADMIN VIEWS ====================

class BrillsPayAdminSite(admin.AdminSite):
    site_header = "BrillsPay Administration"
    site_title = "BrillsPay Admin Portal"
    index_title = "Welcome to BrillsPay Admin"
    
    def get_app_list(self, request):
        """
        Customize the admin app list for better organization
        """
        app_list = super().get_app_list(request)
        
        # Reorganize apps
        for app in app_list:
            if app['app_label'] == 'store':
                # Reorder models within store app
                model_order = [
                    'User', 'Student', 'Parent', 'Teacher', 'Staff',
                    'Product', 'Category', 'Order', 'Cart',
                    'Payment', 'Transaction', 'FeeStructure', 'FeePayment',
                    'Inventory', 'Supplier', 'PurchaseOrder', 'Attendance'
                ]
                
                # Sort models according to our order
                app['models'].sort(key=lambda x: model_order.index(x['object_name']) 
                                  if x['object_name'] in model_order else 999)
        
        return app_list

# ==================== ADMIN ACTIONS ====================

def export_as_csv_action(description="Export selected items as CSV"):
    """
    Custom admin action to export selected items as CSV
    """
    def export_as_csv(modeladmin, request, queryset):
        import csv
        from django.http import HttpResponse
        
        model = queryset.model
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={model.__name__}.csv'
        
        writer = csv.writer(response)
        
        # Write headers
        field_names = [field.name for field in model._meta.fields]
        writer.writerow(field_names)
        
        # Write data
        for obj in queryset:
            row = [getattr(obj, field) for field in field_names]
            writer.writerow(row)
        
        return response
    
    export_as_csv.short_description = description
    return export_as_csv

# Register the custom action
admin.site.add_action(export_as_csv_action())

# ==================== ADMIN FILTERS ====================

class PaymentStatusFilter(admin.SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'
    
    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending Payment'),
            ('completed', 'Payment Completed'),
            ('failed', 'Payment Failed'),
            ('refunded', 'Refunded'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(payment_status='pending')
        if self.value() == 'completed':
            return queryset.filter(payment_status='completed')
        if self.value() == 'failed':
            return queryset.filter(payment_status='failed')
        if self.value() == 'refunded':
            return queryset.filter(payment_status='refunded')
        return queryset
    


# Unregister default Group admin
admin.site.unregister(Group)

# ==================== IMPORT/EXPORT RESOURCES ====================

class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'phone', 'role', 'is_active', 'date_joined')
        export_order = fields

class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = ('id', 'admission_number', 'first_name', 'last_name', 
                 'student_class', 'gender', 'date_of_birth', 'enrollment_date')
        export_order = fields


        export_order = fields

# ==================== CUSTOM FILTERS ====================

class StatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('pending', 'Pending'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(is_active=False)
        if self.value() == 'pending':
            return queryset.filter(status='pending')
        return queryset

# ==================== INLINE ADMIN CLASSES ====================

class StudentInline(admin.StackedInline):
    model = Student
    extra = 0
    fields = ('admission_number', 'student_class', 'date_of_birth', 'gender')
    readonly_fields = ('admission_number',)


# ==================== MAIN ADMIN CLASSES ====================

# @admin.register(User)
class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    list_display = ('username', 'email', 'full_name', 'role', 'phone', 
                    'is_active', 'date_joined', 'last_login', 'action_buttons')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 
                   ('date_joined', DateRangeFilter))
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login', 'profile_completion')
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'phone')
        }),
        ('School Information', {
            'fields': ('role', 'student', 'parent', 'teacher', 'staff')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 
                      'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
        ('Profile', {
            'fields': ('profile_picture', 'address', 'city', 'state', 
                      'country', 'postal_code', 'profile_completion')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
    full_name.short_description = 'Full Name'
    
    def profile_completion(self, obj):
        completed_fields = 0
        total_fields = 5  # Adjust based on your required fields
        
        if obj.first_name and obj.last_name:
            completed_fields += 1
        if obj.email:
            completed_fields += 1
        if obj.phone:
            completed_fields += 1
        if obj.address:
            completed_fields += 1
        if obj.profile_picture:
            completed_fields += 1
            
        percentage = (completed_fields / total_fields) * 100
        color = 'green' if percentage >= 80 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background: #eee; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-weight: bold;">{}%</div></div>',
            percentage, color, int(percentage)
        )
    profile_completion.short_description = 'Profile Completion'
    
    def action_buttons(self, obj):
        links = []
        if obj.role == 'student':
            url = reverse('store:store_student_change', args=[obj.student.id])
            links.append(f'<a href="{url}" class="button">View Student</a>')
        elif obj.role == 'parent':
            url = reverse('store:store_parent_change', args=[obj.parent.id])
            links.append(f'<a href="{url}" class="button">View Parent</a>')
        
        url = reverse('store:auth_user_change', args=[obj.id])
        links.append(f'<a href="{url}" class="button">Edit</a>')
        
        return format_html(' '.join(links))
    action_buttons.short_description = 'Actions'

# @admin.register(Student)
class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource
    list_display = ('admission_number', 'full_name', 'student_class', 
                    'gender', 'enrollment_date', 'get_parents', 'is_active')
    list_filter = ('student_class', 'gender', 'is_active', 
                   ('enrollment_date', DateRangeFilter))
    search_fields = ('admission_number', 'first_name', 'last_name', 
                     'user__email', 'user__phone')
    readonly_fields = ('admission_number', 'enrollment_date', 'total_spent')
    fieldsets = (
        ('Personal Information', {
            'fields': ('admission_number', 'first_name', 'last_name', 
                      'date_of_birth', 'gender')
        }),
        ('Academic Information', {
            'fields': ('student_class', 'section', 'roll_number', 
                      'academic_year', 'enrollment_date')
        }),
        ('Parent Information', {
            'fields': ('parents', 'emergency_contact', 'emergency_phone')
        }),
        ('Financial', {
            'fields': ('total_spent', 'outstanding_balance')
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'
    
    def get_parents(self, obj):
        parents = obj.parents.all()
        if parents:
            return ", ".join([str(p) for p in parents])
        return "No parents"
    get_parents.short_description = 'Parents'
    
    def total_spent(self, obj):
        total = Order.objects.filter(student=obj, payment_status='completed').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        return f"₦{total:,.2f}"
    total_spent.short_description = 'Total Spent'

# @admin.register(Parent)
class ParentAdmin(ImportExportModelAdmin):
    list_display = ('user', 'phone', 'occupation', 'get_students', 
                    'total_spent', 'last_purchase')
    list_filter = ('occupation', ('user__date_joined', DateRangeFilter))
    search_fields = ('user__username', 'user__email', 'user__first_name', 
                     'user__last_name', 'phone')
    readonly_fields = ('total_spent', 'last_purchase')
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'phone', 'occupation', 'employer', 'income_range')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Financial', {
            'fields': ('total_spent', 'last_purchase', 'preferred_payment_method')
        }),
        ('Additional', {
            'fields': ('is_primary', 'notes')
        }),
    )
    
    def get_students(self, obj):
        students = obj.student_set.all()
        if students:
            return ", ".join([str(s) for s in students])
        return "No students"
    get_students.short_description = 'Students'
    
    def total_spent(self, obj):
        total = Order.objects.filter(user=obj.user, payment_status='completed').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        return f"₦{total:,.2f}"
    total_spent.short_description = 'Total Spent'
    
    def last_purchase(self, obj):
        last_order = Order.objects.filter(user=obj.user).order_by('-created_at').first()
        if last_order:
            return last_order.created_at.strftime('%Y-%m-%d %H:%M')
        return "No purchases"
    last_purchase.short_description = 'Last Purchase'



@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'category', 'price', 'stock_quantity', 
                    'low_stock_warning', 'sku', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', StatusFilter, 
                   ('created_at', DateRangeFilter))
    search_fields = ('name', 'description', 'sku', 'barcode')
    readonly_fields = ('created_at', 'updated_at', 'total_sold', 'total_revenue')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description', 'sku', 'barcode')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'cost_price', 'stock_quantity', 
                      'low_stock_threshold', 'is_active')
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3', 'image_4')
        }),
        ('Sales Data', {
            'fields': ('total_sold', 'total_revenue', 'created_at', 'updated_at')
        }),
        ('Additional', {
            'fields': ('size', 'color', 'material', 'weight', 'dimensions')
        }),
    )
    
    def low_stock_warning(self, obj):
        if obj.stock_quantity <= obj.low_stock_threshold:
            return format_html(
                '<span style="color: red; font-weight: bold;">'
                '⚠️ Low Stock ({})</span>',
                obj.stock_quantity
            )
        return obj.stock_quantity
    low_stock_warning.short_description = 'Stock'
    
    def total_sold(self, obj):
        total = OrderItem.objects.filter(product=obj).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        return total
    total_sold.short_description = 'Total Sold'
    
    def total_revenue(self, obj):
        revenue = OrderItem.objects.filter(product=obj).aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0
        return f"₦{revenue:,.2f}"
    total_revenue.short_description = 'Total Revenue'
    
    actions = ['activate_products', 'deactivate_products', 'export_to_csv']
    
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated successfully.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated.')
    deactivate_products.short_description = "Deactivate selected products"


# ==================== CUSTOM ADMIN VIEWS ====================

# @admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_id', 'subject', 'class_teacher_of', 'is_active')
    search_fields = ('user__username', 'staff_id', 'subject')
    
# @admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_id', 'department', 'position', 'is_active')
    search_fields = ('user__username', 'staff_id', 'department')

# @admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'rating')
    search_fields = ('name', 'contact_person', 'phone', 'email')

# @admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'total_amount', 'status', 'order_date')
    list_filter = ('status', ('order_date', DateRangeFilter))
    search_fields = ('po_number', 'supplier__name')

# @admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'check_in', 'check_out')
    list_filter = ('status', 'date')
    search_fields = ('student__admission_number', 'student__first_name')

# ==================== ADMIN CUSTOMIZATIONS ====================

# Custom admin site instance
brills_pay_admin = BrillsPayAdminSite(name='brillspay_admin')

# Register models with custom admin site
for model, admin_class in [
    (User, UserAdmin),
    (Student, StudentAdmin),
    (Parent, ParentAdmin),
    (Product, ProductAdmin),
    (Category, CategoryAdmin),
    (Order, OrderAdmin),
    (Cart, CartAdmin),
    (Payment, PaymentAdmin),
    (Transaction, TransactionAdmin),
    (FeeStructure, FeeStructureAdmin),
    (FeePayment, FeePaymentAdmin),
    (Inventory, InventoryAdmin),
    (Teacher, TeacherAdmin),
    (Staff, StaffAdmin),
    (Supplier, SupplierAdmin),
    (PurchaseOrder, PurchaseOrderAdmin),
    (Attendance, AttendanceAdmin),
]:
    brills_pay_admin.register(model, admin_class)


# ==================== ADMIN SITE CONFIGURATION ====================

# Override default admin site
admin.site.site_header = "BrillsPay School Management System"
admin.site.site_title = "BrillsPay Admin"
admin.site.index_title = "Dashboard"

# Add custom CSS
class Media:
    css = {
        'all': ('css/admin_custom.css',)
    }

# Add custom JavaScript
    js = ('js/admin_custom.js',)

# Register custom actions for all models
def send_email_action(modeladmin, request, queryset):
    from django.core.mail import send_mail
    for obj in queryset:
        if hasattr(obj, 'email') and obj.email:
            send_mail(
                'Notification from BrillsPay',
                'This is a notification message.',
                'noreply@thebrillsschool.com',
                [obj.email],
                fail_silently=False,
            )
    modeladmin.message_user(request, f"Emails sent to {queryset.count()} users.")
send_email_action.short_description = "Send email notification"

# Add to User admin
# UserAdmin.actions.append(send_email_action)

print("BrillsPay Admin Site Initialized Successfully!")

 
 # admin.py
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from .models import PaymentRecord

class PaymentRecordResource(resources.ModelResource):
    """Resource for importing/exporting PaymentRecord"""
    
    payer_email = fields.Field(
        column_name='payer_email',
        attribute='payer__email'
    )
    
    payer_name = fields.Field(
        column_name='payer_name',
        attribute='payer__get_full_name'
    )
    
    class Meta:
        model = PaymentRecord
        fields = (
            'transaction_id',
            'payer_email',
            'payer_name',
            'amount',
            'payment_method',
            'payment_status',
            'payment_date',
            'paystack_reference',
            'description',
        )
        export_order = fields

@admin.register(PaymentRecord)
class PaymentRecordAdmin(ImportExportModelAdmin):
    """Admin configuration for PaymentRecord"""
    
    resource_class = PaymentRecordResource
    
    list_display = (
        'transaction_id',
        'payer',
        'amount_display',
        'payment_method',
        'payment_status_badge',
        'payment_date',
    )
    
    list_filter = (
        'payment_method',
        'payment_status',
        'payment_date',
    )
    
    search_fields = (
        'transaction_id',
        'payer__username',
        'payer__email',
        'payer__first_name',
        'payer__last_name',
        'paystack_reference',
        'description',
    )
    
    readonly_fields = (
        'transaction_id',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('transaction_id', 'payer', 'amount', 'currency', 'description')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_status', 'payment_date', 'processed_date')
        }),
        ('Payment Gateway Details', {
            'fields': ('paystack_reference', 'bank_name', 'account_number', 'deposit_slip_number'),
            'classes': ('collapse',)
        }),
        ('Technical Information', {
            'fields': ('ip_address', 'user_agent', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return f"₦{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def payment_status_badge(self, obj):
        status_colors = {
            'successful': 'success',
            'failed': 'danger',
            'pending': 'warning',
            'processing': 'info',
            'cancelled': 'secondary',
        }
        color = status_colors.get(obj.payment_status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Status'
    payment_status_badge.admin_order_field = 'payment_status'
    
    actions = ['mark_as_successful', 'mark_as_failed']
    
    def mark_as_successful(self, request, queryset):
        """Admin action to mark payments as successful"""
        updated = queryset.update(
            payment_status='successful',
            processed_date=timezone.now()
        )
        self.message_user(request, f"{updated} payments marked as successful.")
    mark_as_successful.short_description = "Mark selected payments as successful"
    
    def mark_as_failed(self, request, queryset):
        """Admin action to mark payments as failed"""
        updated = queryset.update(
            payment_status='failed',
            processed_date=timezone.now()
        )
        self.message_user(request, f"{updated} payments marked as failed.")
    mark_as_failed.short_description = "Mark selected payments as failed"