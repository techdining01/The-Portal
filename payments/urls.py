from django.urls import path
from . import views, webhooks

urlpatterns = [
    path('init-paystack/', views.init_paystack, name='init_paystack'),
    path('webhook/paystack/', webhooks.paystack_webhook, name='paystack_webhook'),
]
