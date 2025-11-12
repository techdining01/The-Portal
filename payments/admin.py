from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id','student','payment_type','amount','status','is_paid','verified','created_at')
    list_filter = ('status','payment_type','verified')
    search_fields = ('student__username','reference')
    actions = ['grant_exam_access','revoke_exam_access']

    def grant_exam_access(self, request, queryset):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for p in queryset:
            user = p.student
            user.can_take_exam = True
            user.save(update_fields=['can_take_exam'])
        self.message_user(request, 'Exam access granted for selected students.')
    grant_exam_access.short_description = 'Grant exam access (mercy)'

    def revoke_exam_access(self, request, queryset):
        for p in queryset:
            user = p.student
            user.can_take_exam = False
            user.save(update_fields=['can_take_exam'])
        self.message_user(request, 'Exam access revoked for selected students.')
    revoke_exam_access.short_description = 'Revoke exam access'