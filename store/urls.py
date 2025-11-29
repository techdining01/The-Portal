from django.urls import path
from . import views, admin_views


app_name = 'store'


urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),

        # Admins
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', admin_views.product_management, name='admin_product_management'),
    path('admin/products/add/', admin_views.add_product, name='admin_add_product'),
    path('admin/products/edit/<int:product_id>/', admin_views.edit_product, name='admin_edit_product'),
    path('admin/products/delete/<int:product_id>/', admin_views.delete_product, name='admin_delete_product'),
    path('admin/products/update-stock/<int:product_id>/', admin_views.update_stock, name='admin_update_stock'),
    path('admin/products/toggle-status/<int:product_id>/', admin_views.toggle_product_status, name='admin_toggle_product_status'),
    path('admin/orders/', admin_views.order_management, name='admin_order_management'),
    path('admin/orders/<int:order_id>/', admin_views.order_detail_admin, name='admin_order_detail'),
    path('admin/orders/update-status/<int:order_id>/', admin_views.update_order_status, name='admin_update_order_status'),
    path('admin/sales-reports/', admin_views.sales_reports, name='admin_sales_reports'),
    path('admin/transactions/', admin_views.transaction_management, name='admin_transaction_management'),

]