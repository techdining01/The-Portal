from django.test import TestCase, Client
from django.urls import reverse
import json
import hashlib
import hmac
from django.conf import settings

class WebhookTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_webhook_signature(self):
        payload = {"event": "charge.success", "data": {"reference": "REF123"}}
        body = json.dumps(payload).encode()

        secret = settings.PAYSTACK_SECRET_KEY.encode()
        signature = hmac.new(secret, body, hashlib.sha512).hexdigest()

        response = self.client.post(
            reverse("shop:paystack_webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature
        )

        self.assertNotEqual(response.status_code, 403)
