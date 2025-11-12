Django payments + landing bundle
--------------------------------
Files included:
- payments/ (Django app)
  - models.py, views.py, urls.py, admin.py, signals.py, templates...
- templates/landing.html (landing + login)
- core/context_processors.py (injects SCHOOL_NAME)

How to install:
1. Copy 'payments' folder into your project root.
2. Copy 'templates/landing.html' into your project's templates folder.
3. Copy 'core/context_processors.py' into an app named 'core' or adjust import.
4. Add 'payments.apps.PaymentsConfig' and 'core' to INSTALLED_APPS.
5. Add context processor 'core.context_processors.school_settings' to TEMPLATES OPTIONS.
6. Set environment variables (PAYSTACK keys, SCHOOL_NAME, etc) and update settings.py to use them.
7. Run migrations: python manage.py makemigrations payments; python manage.py migrate
8. Collect static, add logo at static/images/logo.png
9. Use ngrok for webhook testing and register webhook URL in Paystack dashboard.

Notes:
- No secrets included. Replace PAYSTACK keys in your environment.
- Webhook uses HMAC verification; ensure PAYSTACK_SECRET_KEY is set.