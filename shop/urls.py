from django.urls import path
from . import views
from . import api_views


app_name = "shop"

urlpatterns = [
    path("", views.shop_home, name="home"),
    path("product/<slug:slug>/", views.product_detail, name="detail"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),
    path("checkout/", views.initiate_checkout, name="checkout"),
    path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),
    path("api/items/", api_views.api_items, name="api_items"),
    path("api/order/<str:reference>/", api_views.api_order_status, name="api_order_status"),
    path("shop/paystack/webhook/", views.paystack_webhook, name="shop_paystack_webhook")

]

