# The-Portal
School portal, payment and CBT


# File: payments/README.md


# payments (Paystack) Django app


## Quick setup
1. Copy the `payments/` folder into your Django project.
2. Add `'payments.apps.PaymentsConfig'` to `INSTALLED_APPS` in settings.py.
3. Add the following settings (use env vars):


```python
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', 'sk_test_xxx')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', 'pk_test_xxx')
PAYSTACK_BASE_URL = 'https://api.paystack.co'
```



4. Wire URLs in your project `urls.py`:


```python
path('payments/', include('payments.urls')),
```


5. Make migrations and migrate:


```bash
python manage.py makemigrations payments
python manage.py migrate
```


6. For local webhook testing, expose your dev server with `ngrok` and set Paystack webhook URL to `https://<ngrok-id>.ngrok.io/payments/webhook/paystack/` and enable `charge.success` event.


7. Create some `Invoice` records (via admin or fixtures) and visit the `pay_button` template to initiate a payment.


## Notes
- Invoice.amount is stored in kobo (smallest currency unit). Ensure you create invoices with amount * 100 if you start with naira.
- The webhook verifies HMAC SHA512 using `PAYSTACK_SECRET_KEY`. Always use HTTPS in production and use real secret keys.
- For extra safety, after receiving webhook you can call Paystack Verify API `/transaction/verify/<reference>` to double-check.


## Integration with CBT
- In `payments/webhooks.py` after marking invoice paid, call your CBT unlock function or send a signal. Keep that logic idempotent.


---





