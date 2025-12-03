# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from .models import (
    UserProfile, StudentParentRelationship, Class,
    Subject, Department, ParentProfile, StudentAcademicRecord
)
import csv
from django.http import HttpResponse
from django.db.models.functions import TruncMonth

# Unregister default User admin to register our custom one
admin.site.unregister(User)

class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('role', 'phone_number', 'profile_picture', 'gender', 'date_of_birth')
        }),
        ('Student Information', {
            'fields': ('student_class', 'grade_level', 'registration_number'),
            'classes': ('collapse',)
        }),
        ('Parent Information', {
            'fields': ('occupation', 'emergency_contact', 'address'),
            'classes': ('collapse',)
        }),
        ('Teacher Information', {
            'fields': ('subject', 'qualification', 'years_of_experience'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('suspended', 'suspended_reason', 'suspended_until'),
            'classes': ('collapse',)
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically show/hide fields based on role"""
        fieldsets = super().get_fieldsets(request, obj)
        
        if obj and hasattr(obj, 'userprofile'):
            role = obj.userprofile.role
            
            # Hide irrelevant fields based on role
            modified_fieldsets = []
            for fieldset_name, fieldset_options in fieldsets:
                if role == 'student' and fieldset_name == 'Parent Information':
                    continue
                elif role == 'parent' and fieldset_name == 'Student Information':
                    continue
                elif role == 'teacher' and fieldset_name in ['Student Information', 'Parent Information']:
                    continue
                elif role in ['admin', 'superadmin'] and fieldset_name in ['Student Information', 'Parent Information', 'Teacher Information']:
                    continue
                
                modified_fieldsets.append((fieldset_name, fieldset_options))
            
            return modified_fieldsets
        
        return fieldsets

class StudentParentRelationshipInline(admin.TabularInline):
    """Inline for student-parent relationships"""
    model = StudentParentRelationship
    fk_name = 'student'
    extra = 0
    verbose_name = 'Linked Parent'
    verbose_name_plural = 'Linked Parents'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = User.objects.filter(userprofile__role='parent')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class ParentChildrenInline(admin.TabularInline):
    """Inline for parent's children"""
    model = StudentParentRelationship
    fk_name = 'parent'
    extra = 0
    verbose_name = 'Linked Student'
    verbose_name_plural = 'Linked Students'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with extended functionality"""
    
    inlines = [UserProfileInline]
    
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'user_role', 'user_status', 'is_active', 'date_joined',
        'last_login', 'quick_actions'
    )
    
    list_filter = (
        'is_active', 'is_staff', 'is_superuser',
        'userprofile__role', 'userprofile__suspended',
        'date_joined', 'last_login'
    )
    
    search_fields = (
        'username', 'email', 'first_name', 'last_name',
        'userprofile__phone_number', 'userprofile__registration_number'
    )
    
    list_per_page = 50
    list_select_related = ('userprofile',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    readonly_fields = ('last_login', 'date_joined')
    
    ordering = ('-date_joined',)
    
    actions = [
        'activate_users', 'deactivate_users', 
        'reset_passwords', 'export_selected_users',
        'send_welcome_email'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('userprofile')
    
    def get_inline_instances(self, request, obj=None):
        """Add role-specific inlines"""
        inlines = super().get_inline_instances(request, obj)
        
        if obj and hasattr(obj, 'userprofile'):
            if obj.userprofile.role == 'student':
                inlines.append(StudentParentRelationshipInline(self.model, self.admin_site))
            elif obj.userprofile.role == 'parent':
                inlines.append(ParentChildrenInline(self.model, self.admin_site))
        
        return inlines
    
    def user_role(self, obj):
        """Display user role with badge"""
        if hasattr(obj, 'userprofile'):
            role = obj.userprofile.role
            role_display = obj.userprofile.get_role_display()
            
            colors = {
                'student': 'info',
                'parent': 'primary',
                'teacher': 'warning',
                'admin': 'success',
                'superadmin': 'danger'
            }
            
            color = colors.get(role, 'secondary')
            return format_html(
                '<span class="badge bg-{}">{}</span>',
                color, role_display
            )
        return '-'
    user_role.short_description = 'Role'
    user_role.admin_order_field = 'userprofile__role'
    
    def user_status(self, obj):
        """Display user status"""
        if not obj.is_active:
            return format_html('<span class="badge bg-danger">Inactive</span>')
        
        if hasattr(obj, 'userprofile'):
            if obj.userprofile.suspended:
                return format_html('<span class="badge bg-warning text-dark">Suspended</span>')
        
        return format_html('<span class="badge bg-success">Active</span>')
    user_status.short_description = 'Status'
    
    def quick_actions(self, obj):
        """Display quick action buttons"""
        actions = []
        
        # View profile button
        actions.append(format_html(
            '<a href="{}" class="btn btn-sm btn-info" title="View Profile" style="margin-right: 5px;">'
            '<i class="fas fa-eye"></i></a>',
            reverse('admin:auth_user_change', args=[obj.id])
        ))
        
        # Reset password button
        actions.append(format_html(
            '<a href="{}" class="btn btn-sm btn-warning" title="Reset Password" style="margin-right: 5px;">'
            '<i class="fas fa-key"></i></a>',
            reverse('admin:password_reset', args=[obj.id])
        ))
        
        # Email button
        if obj.email:
            actions.append(format_html(
                '<a href="mailto:{}" class="btn btn-sm btn-secondary" title="Send Email">'
                '<i class="fas fa-envelope"></i></a>',
                obj.email
            ))
        
        return format_html(''.join(actions))
    quick_actions.short_description = 'Actions'
    
    # Custom Actions
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, 
            f'Successfully activated {updated} user(s).',
            messages.SUCCESS
        )
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, 
            f'Successfully deactivated {updated} user(s).',
            messages.SUCCESS
        )
    deactivate_users.short_description = "Deactivate selected users"
    
    def reset_passwords(self, request, queryset):
        """Send password reset email"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        count = 0
        for user in queryset:
            if user.email:
                # Generate reset token (simplified)
                # In production, use proper password reset flow
                send_mail(
                    subject='Password Reset Request',
                    message=f'Hello {user.get_full_name()},\n\nPlease reset your password.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                count += 1
        
        self.message_user(
            request,
            f'Password reset emails sent to {count} user(s).',
            messages.SUCCESS if count > 0 else messages.WARNING
        )
    reset_passwords.short_description = "Send password reset email"
    
    def export_selected_users(self, request, queryset):
        """Export selected users to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Email', 'First Name', 'Last Name',
            'Role', 'Phone', 'Status', 'Date Joined'
        ])
        
        for user in queryset:
            profile = getattr(user, 'userprofile', None)
            writer.writerow([
                user.username,
                user.email,
                user.first_name or '',
                user.last_name or '',
                profile.role if profile else '',
                profile.phone_number if profile else '',
                'Active' if user.is_active else 'Inactive',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_selected_users.short_description = "Export selected users to CSV"
    
    def send_welcome_email(self, request, queryset):
        """Send welcome email to new users"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        count = 0
        for user in queryset:
            if user.email:
                send_mail(
                    subject=f'Welcome to {settings.SITE_NAME}',
                    message=f'Hello {user.get_full_name()},\n\nWelcome to our platform!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                count += 1
        
        self.message_user(
            request,
            f'Welcome emails sent to {count} user(s).',
            messages.SUCCESS if count > 0 else messages.WARNING
        )
    send_welcome_email.short_description = "Send welcome email"

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for UserProfile model"""
    
    list_display = (
        'user', 'role', 'phone_number', 'get_class', 
        'is_active', 'suspended', 'created_at'
    )
    
    list_filter = (
        'role', 'suspended', 'student_class', 
        'gender', 'created_at'
    )
    
    search_fields = (
        'user__username', 'user__email', 'user__first_name',
        'user__last_name', 'phone_number', 'registration_number'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'phone_number', 'profile_picture')
        }),
        ('Personal Details', {
            'fields': ('gender', 'date_of_birth'),
            'classes': ('collapse',)
        }),
        ('Student Information', {
            'fields': ('student_class', 'grade_level', 'registration_number'),
            'classes': ('collapse',)
        }),
        ('Parent Information', {
            'fields': ('occupation', 'emergency_contact', 'address'),
            'classes': ('collapse',)
        }),
        ('Teacher Information', {
            'fields': ('subject', 'qualification', 'years_of_experience'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('suspended', 'suspended_reason', 'suspended_until')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically show/hide fields based on role"""
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if obj:
            if obj.role == 'student':
                # Show student fields, hide parent/teacher fields
                fieldsets = [
                    fieldsets[0],  # User Information
                    fieldsets[1],  # Personal Details
                    fieldsets[2],  # Student Information
                    fieldsets[5],  # Status
                    fieldsets[6],  # Timestamps
                ]
            elif obj.role == 'parent':
                # Show parent fields, hide student/teacher fields
                fieldsets = [
                    fieldsets[0],  # User Information
                    fieldsets[1],  # Personal Details
                    fieldsets[3],  # Parent Information
                    fieldsets[5],  # Status
                    fieldsets[6],  # Timestamps
                ]
            elif obj.role == 'teacher':
                # Show teacher fields, hide student/parent fields
                fieldsets = [
                    fieldsets[0],  # User Information
                    fieldsets[1],  # Personal Details
                    fieldsets[4],  # Teacher Information
                    fieldsets[5],  # Status
                    fieldsets[6],  # Timestamps
                ]
            elif obj.role in ['admin', 'superadmin']:
                # Show only basic fields for admins
                fieldsets = [
                    fieldsets[0],  # User Information
                    fieldsets[5],  # Status
                    fieldsets[6],  # Timestamps
                ]
        
        return fieldsets
    
    def get_class(self, obj):
        """Display class for students"""
        if obj.role == 'student' and obj.student_class:
            return obj.student_class.name
        return '-'
    get_class.short_description = 'Class'
    
    def is_active(self, obj):
        """Check if user is active"""
        return obj.user.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'

@admin.register(StudentParentRelationship)
class StudentParentRelationshipAdmin(admin.ModelAdmin):
    """Admin for student-parent relationships"""
    
    list_display = (
        'student_name', 'parent_name', 'relationship',
        'is_primary', 'verified', 'created_at'
    )
    
    list_filter = ('relationship', 'is_primary', 'verified', 'created_at')
    
    search_fields = (
        'student__username', 'student__email', 'student__first_name', 'student__last_name',
        'parent__username', 'parent__email', 'parent__first_name', 'parent__last_name'
    )
    
    list_select_related = ('student', 'parent')
    
    fieldsets = (
        ('Relationship Details', {
            'fields': ('student', 'parent', 'relationship', 'is_primary')
        }),
        ('Verification', {
            'fields': ('verified', 'verified_by', 'verified_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def student_name(self, obj):
        """Display student name with link"""
        url = reverse('admin:auth_user_change', args=[obj.student.id])
        return format_html('<a href="{}">{}</a>', url, obj.student.get_full_name())
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'student__first_name'
    
    def parent_name(self, obj):
        """Display parent name with link"""
        url = reverse('admin:auth_user_change', args=[obj.parent.id])
        return format_html('<a href="{}">{}</a>', url, obj.parent.get_full_name())
    parent_name.short_description = 'Parent'
    parent_name.admin_order_field = 'parent__first_name'
    
    actions = ['verify_relationships', 'unverify_relationships', 'mark_as_primary']
    
    def verify_relationships(self, request, queryset):
        """Verify selected relationships"""
        updated = queryset.update(
            verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} relationship(s) verified.',
            messages.SUCCESS
        )
    verify_relationships.short_description = "Verify selected relationships"
    
    def unverify_relationships(self, request, queryset):
        """Unverify selected relationships"""
        updated = queryset.update(
            verified=False,
            verified_by=None,
            verified_at=None
        )
        self.message_user(
            request,
            f'{updated} relationship(s) unverified.',
            messages.SUCCESS
        )
    unverify_relationships.short_description = "Unverify selected relationships"
    
    def mark_as_primary(self, request, queryset):
        """Mark selected relationships as primary"""
        # First, unset primary for all students in the selection
        for obj in queryset:
            StudentParentRelationship.objects.filter(
                student=obj.student,
                is_primary=True
            ).exclude(id=obj.id).update(is_primary=False)
        
        # Mark selected as primary
        updated = queryset.update(is_primary=True)
        self.message_user(
            request,
            f'{updated} relationship(s) marked as primary.',
            messages.SUCCESS
        )
    mark_as_primary.short_description = "Mark as primary relationship"

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin for Class model"""
    
    list_display = ('name', 'code', 'grade_level', 'teacher', 'student_count', 'created_at')
    list_filter = ('grade_level', 'created_at')
    search_fields = ('name', 'code', 'teacher__first_name', 'teacher__last_name')
    
    fieldsets = (
        ('Class Information', {
            'fields': ('name', 'code', 'grade_level', 'description')
        }),
        ('Teacher Assignment', {
            'fields': ('teacher', 'assistant_teacher'),
            'classes': ('collapse',)
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'room_number'),
            'classes': ('collapse',)
        }),
    )
    
    def student_count(self, obj):
        """Count students in class"""
        count = UserProfile.objects.filter(student_class=obj, role='student').count()
        return format_html(
            '<a href="{}?student_class__id__exact={}">{}</a>',
            reverse('admin:auth_user_changelist'),
            obj.id,
            count
        )
    student_count.short_description = 'Students'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('teacher').annotate(
            student_count=Count('userprofile', filter=Q(userprofile__role='student'))
        )

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Admin for Subject model"""
    
    list_display = ('name', 'code', 'department', 'teacher_count', 'created_at')
    list_filter = ('department', 'created_at')
    search_fields = ('name', 'code', 'description')
    
    def teacher_count(self, obj):
        """Count teachers for this subject"""
        count = UserProfile.objects.filter(subject=obj.name, role='teacher').count()
        return format_html(
            '<a href="{}?userprofile__subject__exact={}">{}</a>',
            reverse('admin:auth_user_changelist'),
            obj.name,
            count
        )
    teacher_count.short_description = 'Teachers'

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin for Department model"""
    
    list_display = ('name', 'code', 'head', 'teacher_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'code', 'description')

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    """Admin for ParentProfile model (if separate from UserProfile)"""
    
    list_display = ('user', 'occupation', 'number_of_children', 'emergency_contact', 'created_at')
    list_filter = ('occupation', 'created_at')
    search_fields = ('user__username', 'user__email', 'occupation', 'emergency_contact')
    
    def number_of_children(self, obj):
        """Count number of children"""
        count = StudentParentRelationship.objects.filter(parent=obj.user).count()
        return format_html(
            '<a href="{}?parent__id__exact={}">{}</a>',
            reverse('admin:store_studentparentrelationship_changelist'),
            obj.user.id,
            count
        )
    number_of_children.short_description = 'Children'

@admin.register(StudentAcademicRecord)
class StudentAcademicRecordAdmin(admin.ModelAdmin):
    """Admin for student academic records"""
    
    list_display = ('student', 'subject', 'grade', 'term', 'year', 'created_at')
    list_filter = ('grade', 'term', 'year', 'created_at')
    search_fields = (
        'student__username', 'student__first_name', 'student__last_name',
        'subject__name', 'remarks'
    )
    
    list_select_related = ('student', 'subject')
    
    fieldsets = (
        ('Academic Information', {
            'fields': ('student', 'subject', 'term', 'year')
        }),
        ('Grades', {
            'fields': ('test_score', 'exam_score', 'total_score', 'grade')
        }),
        ('Additional Info', {
            'fields': ('remarks', 'teacher'),
            'classes': ('collapse',)
        }),
    )

# Custom Admin Site Configuration
class CustomAdminSite(admin.AdminSite):
    """Custom admin site with enhanced features"""
    
    site_header = "School Management System"
    site_title = "School Admin"
    index_title = "Dashboard"
    
    def each_context(self, request):
        """Add custom context"""
        context = super().each_context(request)
        
        # Add statistics to context
        if request.user.is_superuser:
            today = timezone.now().date()
            
            context.update({
                'total_users': User.objects.count(),
                'total_students': UserProfile.objects.filter(role='student').count(),
                'total_parents': UserProfile.objects.filter(role='parent').count(),
                'total_teachers': UserProfile.objects.filter(role='teacher').count(),
                'new_users_today': User.objects.filter(date_joined__date=today).count(),
                'inactive_users': User.objects.filter(is_active=False).count(),
                'pending_verifications': StudentParentRelationship.objects.filter(verified=False).count(),
            })
        
        return context
    
    def get_app_list(self, request, app_label=None):
        """Customize app list"""
        app_list = super().get_app_list(request, app_label)
        
        # Reorder apps if needed
        auth_app = None
        for app in app_list:
            if app['app_label'] == 'auth':
                auth_app = app
                app_list.remove(app)
                break
        
        if auth_app:
            # Rename auth app
            auth_app['name'] = 'User Management'
            # Put it first
            app_list.insert(0, auth_app)
        
        return app_list

# Use custom admin site
admin.site = CustomAdminSite(name='customadmin')

# Re-register all models with custom admin site
admin.site.register(User, UserAdmin)
admin.site.register(Group)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(StudentParentRelationship, StudentParentRelationshipAdmin)
admin.site.register(Class, ClassAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(ParentProfile, ParentProfileAdmin)
admin.site.register(StudentAcademicRecord, StudentAcademicRecordAdmin)

# Custom Admin Actions
def export_all_users(modeladmin, request, queryset):
    """Export all users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_users.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Email', 'First Name', 'Last Name', 'Role',
        'Phone', 'Status', 'Class', 'Registration No.', 'Date Joined'
    ])
    
    for user in User.objects.all().select_related('userprofile'):
        profile = user.userprofile
        writer.writerow([
            user.username,
            user.email,
            user.first_name or '',
            user.last_name or '',
            profile.role if profile else '',
            profile.phone_number if profile else '',
            'Active' if user.is_active else 'Inactive',
            profile.student_class.name if profile and profile.student_class else '',
            profile.registration_number if profile else '',
            user.date_joined.strftime('%Y-%m-%d')
        ])
    
    return response
export_all_users.short_description = "Export all users to CSV"

# Add custom views to admin
from django.urls import path
from django.shortcuts import render

class CustomUserAdmin(UserAdmin):
    """Extended UserAdmin with custom views"""
    
    def get_urls(self):
        """Add custom URLs"""
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_site.admin_view(self.user_statistics), name='user_statistics'),
            path('bulk-import/', self.admin_site.admin_view(self.bulk_import), name='bulk_import'),
        ]
        return custom_urls + urls
    
    def user_statistics(self, request):
        """Custom statistics view"""
        # User statistics by role
        role_stats = UserProfile.objects.values('role').annotate(
            count=Count('id'),
            active=Count('id', filter=Q(user__is_active=True))
        ).order_by('-count')
        
        # Monthly registration stats
        monthly_stats = User.objects.annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Active vs Inactive
        active_count = User.objects.filter(is_active=True).count()
        inactive_count = User.objects.filter(is_active=False).count()
        
        context = {
            'title': 'User Statistics',
            'role_stats': role_stats,
            'monthly_stats': monthly_stats,
            'active_count': active_count,
            'inactive_count': inactive_count,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        
        return render(request, 'admin/user_statistics.html', context)
    
    def bulk_import(self, request):
        """Bulk import users view"""
        if request.method == 'POST':
            # Handle CSV import
            pass
        
        context = {
            'title': 'Bulk Import Users',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        
        return render(request, 'admin/bulk_import.html', context)

# Replace the UserAdmin with our extended version
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)