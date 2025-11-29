from django.contrib import admin
from .models import Class, Subject, ClassSubject, Quiz, Question, Choice, StudentQuizAttempt, Answer
from .models import StudentQuizAttempt

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


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'arm', 'order', 'is_active', 'students_count']
    list_filter = ['level', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['order', 'is_active']
    
    def students_count(self, obj):
        return obj.students.count()
    students_count.short_description = 'Students'

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'is_active', 'classes_count']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'code', 'description']
    list_editable = ['is_active']
    
    def classes_count(self, obj):
        return obj.classsubject_set.count()
    classes_count.short_description = 'Classes'

@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ['class_obj', 'subject', 'is_compulsory', 'periods_per_week']
    list_filter = ['is_compulsory', 'class_obj__level']
    search_fields = ['class_obj__name', 'subject__name']
    list_editable = ['is_compulsory', 'periods_per_week']