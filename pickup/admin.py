from django.contrib import admin
from .models import PickupAuthorization
from django.utils import timezone



@admin.register(PickupAuthorization)
class PickupAdmin(admin.ModelAdmin):
    list_display = ("code", "parent", "student", "bearer_name", "verified_at", "expires_at")
    readonly_fields = ("code", "created_at",)
    actions = ["verify_selected"]

    def verify_selected(self, request, queryset):
        for obj in queryset:
            obj.verified_at = timezone.now()
            obj.verified_by = request.user
            obj.save()
    verify_selected.short_description = "Mark selected pickups as verified"
