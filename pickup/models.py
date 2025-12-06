from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
from users.models import User


def pickup_default_expires():
    return timezone.now() + timedelta(days=2)

class PickupAuthorization(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pickup_auths")
    # store student registration number relation via to_field
    student = models.ForeignKey('users.Student', on_delete=models.CASCADE, related_name="pickup_for")
    bearer_name = models.CharField(max_length=200)
    bearer_phone = models.CharField(max_length=20)
    code = models.CharField(max_length=12, unique=True, editable=False)
    signature_image = models.ImageField(upload_to="signatures/", null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pickup_verified")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=pickup_default_expires)

    def save(self, *args, **kwargs):
        if not self.code:
            # simple random code (change algorithm if you want stronger codes)
            self.code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def is_valid(self):
        return (self.verified_at is None) and (timezone.now() <= (self.expires_at or timezone.now()))
