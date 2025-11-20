from django.urls import path
from . import views
from . import api_views


app_name = "shop"

urlpatterns = [
    path("", views.shop_home, name="shop_home"),
    path("product/<slug:slug>/", views.product_detail, name="detail"),
    # Cart URLs
    path("cart/", views.cart_page, name="cart"),
    path("cart/add/<int:item_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/update/", views.update_cart_ajax, name="update_cart_ajax"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    # Checkout URLs
    path("checkout/", views.checkout, name="checkout"),
    path("paystack/verify/", views.verify_payment, name="verify_payment"),
    # Admin URLs
    path("admin/items/", views.admin_items, name="admin_items"),
    path("admin/items/add/", views.admin_add_item, name="admin_add_item"),
    path("admin/items/<int:item_id>/edit/", views.admin_edit_item, name="admin_edit_item"),
    path("admin/items/<int:item_id>/delete/", views.admin_delete_item, name="admin_delete_item"),
    path("admin/items/<int:item_id>/increase/", views.admin_increase_stock, name="admin_increase_stock"),
    path("admin/items/<int:item_id>/decrease/", views.admin_decrease_stock, name="admin_decrease_stock"),
]



