from django.contrib import admin
from .models import Class, Subject, ClassSubject, StudentQuizAttempt, Quiz, Question, Choice, StudentQuizAttempt, Answer, Department
from django.urls import reverse
from django.utils.html import format_html
from users.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
import datetime, csv

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'question_type', 'marks')


class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'is_published')
    list_filter = ('subject', 'is_published')


class AnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'is_pending')

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(Answer, AnswerAdmin)


@admin.register(StudentQuizAttempt)
class StudentQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "is_submitted", "score", "retake_allowed", "retake_count")
    list_filter = ("is_submitted", "retake_allowed")
    actions = ["allow_retake"]

    def allow_retake(self, request, queryset):
        updated = queryset.update(retake_allowed=True)
        self.message_user(request, f"{updated} attempt(s) granted retake")
    allow_retake.short_description = "Grant retake to selected students"


# @admin.register(Class)
# class ClassAdmin(admin.ModelAdmin):
#     list_display = ['name', 'level', 'arm', 'order', 'is_active', 'students_count']
#     list_filter = ['level', 'is_active']
#     search_fields = ['name', 'description']
#     list_editable = ['order', 'is_active']
    
#     def students_count(self, obj):
#         return obj.students.count()
#     students_count.short_description = 'Students'

# @admin.register(Subject)
# class SubjectAdmin(admin.ModelAdmin):
#     list_display = ['name', 'category', 'is_active', 'classes_count']
#     list_filter = ['category', 'is_active']
#     search_fields = ['name', 'description']
#     list_editable = ['is_active']
    
#     def classes_count(self, obj):
#         return obj.classsubject_set.count()
#     classes_count.short_description = 'Classes'

# @admin.register(ClassSubject)
# class ClassSubjectAdmin(admin.ModelAdmin):
#     list_display = ['class_obj', 'subject', 'is_compulsory', 'periods_per_week']
#     list_filter = ['is_compulsory', 'class_obj__level']
#     search_fields = ['class_obj__name', 'subject__name']
#     list_editable = ['is_compulsory', 'periods_per_week']


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin for Class model"""
    
    list_display = ('name', 'grade_level', 'teacher', 'student_count', 'created_at')
    list_filter = ('grade_level', 'created_at')
    search_fields = ('name', 'teacher__first_name', 'teacher__last_name')
    
    fieldsets = (
        ('Class Information', {
            'fields': ('name', 'grade_level', 'description')
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
    
    # def student_count(self, obj):
    #     """Count students in class"""
    #     count = User.objects.filter(student_class=obj, role='student').count()
    #     return format_html(
    #         '<a href="{}?student_class__id__exact={}">{}</a>',
    #         reverse('users:auth_user_changelist'),
    #         obj.id,
    #         count
    #     )
    # student_count.short_description = 'Students'


    def action_buttons(self, obj):
        links = []
        # If the user has a related student profile
        if getattr(obj, 'student', None):
            student = obj.student
            url = reverse(f'admin:{student._meta.app_label}_{student._meta.model_name}_change', args=[student.id])
            links.append(f'<a href="{url}" class="button">View Student</a>')
        if getattr(obj, 'parent', None):
            parent = obj.parent
            url = reverse(f'admin:{parent._meta.app_label}_{parent._meta.model_name}_change', args=[parent.id])
            links.append(f'<a href="{url}" class="button">View Parent</a>')

        # link to edit this user in admin (dynamic app_label/model_name)
        url = reverse(f'admin:{User._meta.app_label}_{User._meta.model_name}_change', args=[obj.id])
        links.append(f'<a href="{url}" class="button">Edit</a>')

        return format_html(' '.join(links))
        
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('teacher').annotate(
            student_count=Count('userprofile', filter=Q(userprofile__role='student'))
        )

# ========== SUBJECT ADMIN ==========

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """
    Admin for Subject model.
    """
    list_display = ('name', 'category_badge', 'credits', 'department', 'is_active_badge')
    list_filter = ('category', 'is_active', 'department')
    search_fields = ('name', 'description', 'department')
    ordering = ('name', 'code')
    actions = ['activate_subjects', 'deactivate_subjects', 'export_subjects_csv']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Academic Details', {
            'fields': ('category', 'credits', 'department')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def category_badge(self, obj):
        color_map = {
            'core': 'primary',
            'elective': 'success',
            'language': 'info',
            'arts': 'warning',
            'sports': 'danger',
            'vocational': 'secondary'
        }
        color = color_map.get(obj.category, 'light')
        
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = 'Category'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-danger">Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def activate_subjects(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subject(s) activated.')
    activate_subjects.short_description = "Activate selected subjects"
    
    def deactivate_subjects(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subject(s) deactivated.')
    deactivate_subjects.short_description = "Deactivate selected subjects"
    
    def export_subjects_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="subjects_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Code', 'Name', 'Category', 'Level', 'Credits', 'Department', 'Active'])
        
        for subject in queryset:
            writer.writerow([
                subject.code,
                subject.name,
                subject.get_category_display(),
                subject.get_level_display(),
                subject.credits,
                subject.department,
                'Yes' if subject.is_active else 'No'
            ])
        
        return response
    export_subjects_csv.short_description = "Export selected subjects to CSV"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin for Department model"""
    
    list_display = ('name', 'code', 'head', 'teacher_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'code', 'description')
