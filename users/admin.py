from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import User, Student, Parent, Teacher, Staff, StudentParent, Notification, UserStatusLog


# ==================== USER ADMIN ====================

class UserAdmin(BaseUserAdmin):
    """Custom User Admin for BrillsPay system"""
    
    list_display = (
        'username',
        'get_full_name',
        'email',
        'phone',
        'get_role_badge',
        'is_approved',
        'is_active',
        'date_joined'
    )
    list_filter = (
        'role',
        'is_approved',
        'is_active',
        'date_joined'
    )
    search_fields = (
        'username',
        'email',
        'phone',
        'first_name',
        'last_name'
    )
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password', 'email')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone', 'profile_picture')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country'),
            'classes': ('collapse',)
        }),
        ('Role & Status', {
            'fields': ('role', 'is_approved', 'is_active')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('date_joined', 'created_at', 'updated_at', 'last_login')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    def get_full_name(self, obj):
        """Display full name in admin list"""
        return obj.get_full_name() or obj.username
    get_full_name.short_description = 'Full Name'
    
    def get_role_badge(self, obj):
        """Display role with color-coded badge"""
        role_colors = {
            'student': '#3b82f6',      # Blue
            'parent': '#10b981',       # Green
            'teacher': '#f59e0b',      # Amber
            'staff': '#8b5cf6',        # Purple
            'admin': '#ef4444',        # Red
            'superadmin': '#dc2626',   # Dark Red
        }
        color = role_colors.get(obj.role, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 20px; font-weight: 500; display: inline-block;">{}</span>',
            color,
            obj.get_role_display()
        )
    get_role_badge.short_description = 'Role'
    
    actions = ['approve_users', 'deactivate_users', 'activate_users']
    
    def approve_users(self, request, queryset):
        """Bulk approve users"""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} users approved.')
    approve_users.short_description = 'Approve selected users'
    
    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'
    
    def activate_users(self, request, queryset):
        """Bulk activate users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = 'Activate selected users'


# ==================== STUDENT ADMIN ====================

class StudentAdmin(admin.ModelAdmin):
    """Admin interface for Students"""
    
    list_display = (
        'get_name',
        'admission_number',
        'student_class',
        'academic_year',
        'get_age',
        'gender',
        'is_active',
        'total_spent',
        'outstanding_balance'
    )
    list_filter = (
        'is_active',
        'gender',
        'academic_year',
        'student_class',
        'created_at'
    )
    search_fields = (
        'first_name',
        'last_name',
        'admission_number',
        'registration_number'
    )
    ordering = ('student_class', 'first_name')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender')
        }),
        ('Student Identification', {
            'fields': ('admission_number', 'registration_number', 'username')
        }),
        ('Academic Information', {
            'fields': ('student_class', 'section', 'academic_year', 'enrollment_date')
        }),
        ('Family Information', {
            'fields': ('parents', 'emergency_contact', 'emergency_phone')
        }),
        ('Financial Information', {
            'fields': ('total_spent', 'outstanding_balance'),
            'classes': ('collapse',)
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = (
        'admission_number',
        'registration_number',
        'enrollment_date',
        'created_at',
        'updated_at'
    )
    
    filter_horizontal = ('parents',)
    
    def get_name(self, obj):
        """Display student full name"""
        return obj.get_full_name()
    get_name.short_description = 'Student Name'
    
    def get_age(self, obj):
        """Display student age"""
        return obj.get_age()
    get_age.short_description = 'Age'
    
    actions = ['activate_students', 'deactivate_students']
    
    def activate_students(self, request, queryset):
        """Bulk activate students"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} students activated.')
    activate_students.short_description = 'Activate selected students'
    
    def deactivate_students(self, request, queryset):
        """Bulk deactivate students"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} students deactivated.')
    deactivate_students.short_description = 'Deactivate selected students'


# ==================== PARENT ADMIN ====================

class ParentAdmin(admin.ModelAdmin):
    """Admin interface for Parents/Guardians"""
    
    list_display = (
        'get_name',
        'email',
        'phone',
        'get_relationship',
        'get_student_count',
        'occupation',
        'is_primary',
        'created_at'
    )
    list_filter = (
        'relationship',
        'is_primary',
        'income_range',
        'preferred_payment_method',
        'created_at'
    )
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone',
        'occupation'
    )
    ordering = ('user__last_name', 'user__first_name')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('occupation', 'employer', 'phone', 'relationship', 'income_range')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Students & Preferences', {
            'fields': ('students', 'is_primary', 'preferred_payment_method')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('students',)
    
    def get_name(self, obj):
        """Display parent full name"""
        return obj.full_name
    get_name.short_description = 'Parent Name'
    
    def get_relationship(self, obj):
        """Display relationship"""
        return obj.get_relationship_display()
    get_relationship.short_description = 'Relationship'
    
    def get_student_count(self, obj):
        """Display number of students"""
        return obj.students.count()
    get_student_count.short_description = 'Students'


# ==================== TEACHER ADMIN ====================

class TeacherAdmin(admin.ModelAdmin):
    """Admin interface for Teachers"""
    
    list_display = (
        'get_name',
        'staff_id',
        'subject',
        'class_teacher_of',
        'years_of_experience',
        'is_active',
        'joining_date'
    )
    list_filter = (
        'is_active',
        'subject',
        'joining_date'
    )
    search_fields = (
        'user__first_name',
        'user__last_name',
        'staff_id',
        'subject',
        'class_teacher_of'
    )
    ordering = ('user__last_name', 'user__first_name')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user',)
        }),
        ('Staff Information', {
            'fields': ('staff_id', 'subject', 'class_teacher_of', 'qualification', 'years_of_experience')
        }),
        ('Contact Information', {
            'fields': ('phone', 'emergency_contact', 'emergency_phone'),
            'classes': ('collapse',)
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'joining_date', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'joining_date')
    
    def get_name(self, obj):
        """Display teacher full name"""
        return obj.user.get_full_name()
    get_name.short_description = 'Teacher Name'
    
    actions = ['activate_teachers', 'deactivate_teachers']
    
    def activate_teachers(self, request, queryset):
        """Bulk activate teachers"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} teachers activated.')
    activate_teachers.short_description = 'Activate selected teachers'
    
    def deactivate_teachers(self, request, queryset):
        """Bulk deactivate teachers"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} teachers deactivated.')
    deactivate_teachers.short_description = 'Deactivate selected teachers'


# ==================== STAFF ADMIN ====================

class StaffAdmin(admin.ModelAdmin):
    """Admin interface for Non-teaching Staff"""
    
    list_display = (
        'get_name',
        'staff_id',
        'department',
        'position',
        'is_active',
        'joining_date'
    )
    list_filter = (
        'is_active',
        'department',
        'joining_date'
    )
    search_fields = (
        'user__first_name',
        'user__last_name',
        'staff_id',
        'department',
        'position'
    )
    ordering = ('department', 'user__last_name')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user',)
        }),
        ('Staff Information', {
            'fields': ('staff_id', 'department', 'position', 'qualification', 'joining_date')
        }),
        ('Contact Information', {
            'fields': ('phone',),
            'classes': ('collapse',)
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'joining_date')
    
    def get_name(self, obj):
        """Display staff full name"""
        return obj.user.get_full_name()
    get_name.short_description = 'Staff Name'
    
    actions = ['activate_staff', 'deactivate_staff']
    
    def activate_staff(self, request, queryset):
        """Bulk activate staff"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} staff members activated.')
    activate_staff.short_description = 'Activate selected staff'
    
    def deactivate_staff(self, request, queryset):
        """Bulk deactivate staff"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} staff members deactivated.')
    deactivate_staff.short_description = 'Deactivate selected staff'


# ==================== STUDENT-PARENT ADMIN ====================

class StudentParentInline(admin.TabularInline):
    """Inline admin for Student-Parent relationships"""
    model = StudentParent
    extra = 1
    fields = ('student', 'parent', 'is_primary_guardian', 'can_pickup', 'pickup_code')
    readonly_fields = ('pickup_code',)


class StudentParentAdmin(admin.ModelAdmin):
    """Admin interface for Student-Parent Relationships"""
    
    list_display = (
        'get_student_name',
        'get_parent_name',
        'is_primary_guardian',
        'can_pickup',
        'pickup_code'
    )
    list_filter = (
        'is_primary_guardian',
        'can_pickup'
    )
    search_fields = (
        'student__first_name',
        'student__last_name',
        'parent__user__first_name',
        'parent__user__last_name'
    )
    
    def get_student_name(self, obj):
        """Display student name"""
        return obj.student.get_full_name()
    get_student_name.short_description = 'Student'
    
    def get_parent_name(self, obj):
        """Display parent name"""
        return obj.parent.full_name
    get_parent_name.short_description = 'Parent'
    
    actions = ['generate_pickup_codes']
    
    def generate_pickup_codes(self, request, queryset):
        """Generate pickup codes for selected relationships"""
        count = 0
        for relationship in queryset:
            if not relationship.pickup_code:
                relationship.generate_pickup_code()
                count += 1
        self.message_user(request, f'Generated {count} pickup codes.')
    generate_pickup_codes.short_description = 'Generate pickup codes'


# ==================== NOTIFICATION ADMIN ====================

class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notifications"""
    
    list_display = (
        'get_sender_name',
        'get_recipient_name',
        'role',
        'is_broadcast',
        'is_read',
        'created_at'
    )
    list_filter = (
        'is_read',
        'is_broadcast',
        'role',
        'created_at'
    )
    search_fields = (
        'sender__username',
        'recipient__username',
        'message'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def get_sender_name(self, obj):
        """Display sender name"""
        return obj.sender.get_full_name() or obj.sender.username
    get_sender_name.short_description = 'From'
    
    def get_recipient_name(self, obj):
        """Display recipient name"""
        return obj.recipient.get_full_name() or obj.recipient.username
    get_recipient_name.short_description = 'To'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Mark notifications as read"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_unread(self, request, queryset):
        """Mark notifications as unread"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected as unread'


# ==================== USER STATUS LOG ADMIN ====================

class UserStatusLogAdmin(admin.ModelAdmin):
    """Admin interface for User Status Logs"""
    
    list_display = (
        'get_user_name',
        'old_status',
        'new_status',
        'get_changed_by_name',
        'changed_at'
    )
    list_filter = (
        'new_status',
        'changed_at'
    )
    search_fields = (
        'user__username',
        'changed_by__username'
    )
    ordering = ('-changed_at',)
    readonly_fields = ('changed_at',)
    
    def get_user_name(self, obj):
        """Display user name"""
        return obj.user.get_full_name() or obj.user.username
    get_user_name.short_description = 'User'
    
    def get_changed_by_name(self, obj):
        """Display who changed the status"""
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return '—'
    get_changed_by_name.short_description = 'Changed By'


# ==================== REGISTER ADMIN MODELS ====================

admin.site.register(User, UserAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Parent, ParentAdmin)
admin.site.register(Teacher, TeacherAdmin)
admin.site.register(Staff, StaffAdmin)
admin.site.register(StudentParent, StudentParentAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserStatusLog, UserStatusLogAdmin)

# Customize admin site
admin.site.site_header = 'BrillsPay Portal Administration'
admin.site.site_title = 'BrillsPay Admin'
admin.site.index_title = 'Dashboard'