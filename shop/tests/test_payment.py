from django.test import TestCase, Client, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock
from shop.models import Product, Category, Cart, CartItem, Order, TransactionBackup
from django.contrib.auth import get_user_model
import json, hmac, hashlib
from django.conf import settings

User = get_user_model()

@override_settings(PAYSTACK_PUBLIC_KEY="pk_test_x", PAYSTACK_SECRET_KEY="sk_test_x", PAYSTACK_WEBHOOK_SECRET="whsec_test")
class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Books", slug="books")
        self.prod = Product.objects.create(name="Book A", price=1500, product_type="textbook", category=self.category)
        self.user = User.objects.create_user(username="parent", password="pass", role="parent", email="p@example.com")

    def test_checkout_inline_init_creates_order(self):
        # create cart and add item (simulate session-guest)
        res = self.client.post(reverse("shop:add_to_cart"), data=json.dumps({"product_id": self.prod.id, "quantity": 1}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        # patch requests.post to simulate Paystack initialize success
        init_resp = {"status": True, "data": {"authorization_url": "https://paystack/pay", "reference":"REF123", "access_code":"AC"}} 
        with patch("shop.views.requests.post") as mock_post:
            mock_post.return_value = MagicMock(json=lambda: init_resp)
            r = self.client.post(reverse("shop:checkout_inline_init"), data=json.dumps({"email":"guest@example.com"}), content_type="application/json")
            self.assertEqual(r.status_code, 200)
            j = r.json()
            self.assertIn("public_key", j)
            self.assertIn("reference", j)

    def test_webhook_hmac_verification(self):
        # create an order to match webhook
        order = Order.objects.create(reference="REF_TEST", email="a@b.com", total=1000)
        payload = {"event":"charge.success", "data": {"reference": "REF_TEST"}}
        payload_b = json.dumps(payload).encode("utf-8")
        secret = settings.PAYSTACK_WEBHOOK_SECRET.encode()
        sig = hmac.new(secret, payload_b, digestmod=hashlib.sha512).hexdigest()
        r = self.client.post(reverse("shop:paystack_webhook"), data=payload_b, content_type="application/json", **{"HTTP_X_PAYSTACK_SIGNATURE": sig})
        self.assertEqual(r.status_code, 200)
        rj = r.json()
        self.assertEqual(rj.get("status"), "ok")
        # TransactionBackup created
        self.assertTrue(TransactionBackup.objects.filter(paystack_reference="REF_TEST").exists())
