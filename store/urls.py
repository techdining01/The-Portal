from django.urls import path
from . import views, admin_views


app_name = 'store'


urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
  
    # Cart URLs
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/', views.update_cart_view, name='update_cart'),
    path('cart/clear/', views.clear_cart_view, name='clear_cart'),

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

    # Payment URLs
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/initialize/', views.initialize_payment_view, name='initialize_payment'),
    path('payment/verify/', views.verify_payment_view, name='verify_payment'),
    path('payment/webhook/', views.payment_webhook_view, name='payment_webhook'),
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),

        
    # Payment URLs
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/initialize/', views.initialize_payment_view, name='initialize_payment'),
    path('payment/verify/', views.verify_payment_view, name='verify_payment'),
    path('payment/webhook/', views.payment_webhook_view, name='payment_webhook'),
    
    # Order URLs
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),

]