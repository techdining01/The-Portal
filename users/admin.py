from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Parent, Class, Subject

class ParentInline(admin.StackedInline):
    model = Parent
    can_delete = False
    verbose_name_plural = 'Parent Profile'
    fk_name = 'user'

class UserAdmin(BaseUserAdmin):
    list_display = [
        'username', 'email', 'first_name', 'surname', 'role', 
        'registration_number', 'approved', 'is_active'
    ]
    list_filter = ['role', 'approved', 'is_active', 'gender', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'surname', 'registration_number']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Personal Information', {
            'fields': (
                'surname', 'first_name', 'other_name', 'gender', 'age', 
                'date_of_birth', 'profile_picture'
            )
        }),
        ('School Information', {
            'fields': ('role', 'student_class', 'registration_number')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone_number')
        }),
        ('Parent/Guardian Information', {
            'fields': ('parent_name', 'parent_email', 'parent_phone_number'),
            'classes': ('collapse',)
        }),
        ('Staff Information', {
            'fields': (
                'qualification', 'subject_assigned', 'years_of_experience', 
                'next_of_kin', 'next_of_kin_phone'
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('approved', 'can_take_exam', 'is_active')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Personal Information', {
            'fields': ('surname', 'first_name', 'other_name', 'gender', 'age', 'date_of_birth')
        }),
        ('School Information', {
            'fields': ('role', 'student_class')
        }),
    )
    
    def get_inlines(self, request, obj=None):
        if obj and obj.role == 'parent':
            return [ParentInline]
        return []

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['user', 'occupation', 'number_of_wards', 'created_at']
    search_fields = ['user__first_name', 'user__surname', 'user__username']
    list_filter = ['created_at']

