from django.urls import path
from . import views
from . import api_views


app_name = "shop"

urlpatterns = [
    path("", views.shop_home, name="shop_home"),
    path("product/<slug:slug>/", views.product_detail, name="detail"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path("checkout/", views.initiate_checkout, name="checkout"),
    path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),
    path("api/items/", api_views.api_items, name="api_items"),
    path("api/order/<str:reference>/", api_views.api_order_status, name="api_order_status"),
    path("shop/paystack/webhook/", views.paystack_webhook, name="shop_paystack_webhook"),
    # Admin URLs
    path("admin/items/", views.admin_items, name="admin_items"),
    path("admin/items/add/", views.admin_add_item, name="admin_add_item"),
    path("admin/items/<int:item_id>/edit/", views.admin_edit_item, name="admin_edit_item"),
    path("admin/items/<int:item_id>/delete/", views.admin_delete_item, name="admin_delete_item"),
    path("admin/items/<int:item_id>/increase/", views.admin_increase_stock, name="admin_increase_stock"),
    path("admin/items/<int:item_id>/decrease/", views.admin_decrease_stock, name="admin_decrease_stock"),
]



