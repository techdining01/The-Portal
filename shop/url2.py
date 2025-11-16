

# from django.urls import path
# from . import views

# app_name = 'shop'

# urlpatterns = [
#     path('', views.product_list, name='product_list'),
#     path('product/<int:pk>/', views.product_detail, name='product_detail'),
#     path('cart/', views.cart_view, name='cart'),
#     path('cart/add/', views.cart_add, name='cart_add'),          # POST (AJAX)
#     path('cart/update/', views.cart_update, name='cart_update'), # POST (AJAX)
#     path('cart/remove/', views.cart_remove, name='cart_remove'), # POST (AJAX)
#     path('checkout/', views.checkout, name='checkout'),          # shows summary + pay button
#     path('initiate/<str:order_ref>/', views.initiate_payment, name='initiate_payment'),
#     path('verify/<str:order_ref>/', views.verify_payment, name='verify_payment'), # callback redirect
#     path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),   # webhook endpoint
# ]