from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('init-paystack/', views.init_paystack, name='init_paystack'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('dashboard/', views.payment_dashboard, name='payment_dashboard'),
    path('toggle-access/<int:user_id>/', views.toggle_exam_access, name='toggle_exam_access'),
    path('pay-now/', views.pay_now_page, name='pay_now'),  
    path("", views.payment_page, name="payment_page"),
    path("verify/", views.verify_payment, name="verify_payment"),
]