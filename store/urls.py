from django.urls import path
from . import views, admin_views


app_name = 'store'



urlpatterns = [
    # Public views
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # Cart views
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/', views.update_cart_view, name='update_cart'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart_view, name='clear_cart'),

    # For cart only
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path("cart/increase/<int:item_id>/", views.increase_quantity, name="increase_quantity"),
    path("cart/decrease/<int:item_id>/", views.decrease_quantity, name="decrease_quantity"),
    
    # Checkout & Payment
    path('checkout/', views.checkout, name='checkout'),
    path('order/create/', views.create_order, name='create_order'),
    path('payment/verify/<str:reference>/', views.payment_verify, name='payment_verify'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
    
    # Order views
    # path('order/create/', views.create_order_view, name='create_order'),
    path('orders/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('orders/', views.order_list_view, name='order_list'),
    
    # Order History URLs
    path('orders/history/', views.order_history_view, name='order_history'),
    path('orders/<str:order_number>/', views.order_detail_history_view, name='order_detail_history'),
    path('orders/<str:order_number>/cancel/', views.cancel_order_view, name='cancel_order'),
    path('orders/<str:order_number>/reorder/', views.reorder_view, name='reorder'),

    # AJAX helpers
    path('cart/count/', views.get_cart_count_view, name='cart_count'),
    
    # Admin views
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/products/add/', views.add_product, name='add_product'),
    path('admin/users/', views.user_list_view, name='user_list'),
    path('admin/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('admin/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('admin/products/toggle/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
    path('admin/categories/', views.category_management, name='category_management'),
    path('admin/analytics/', views.sales_analytics, name='sales_analytics'),
    path('admin/orders/', views.order_management, name='order_management'),
    path('admin/orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('admin/api/chart-data/', views.get_chart_data, name='chart_data'),
    # urls.py
    path('test/paystack/', views.test_paystack_view, name='test_paystack'),


    path('edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete/<int:user_id>/', views.delete_user, name='delete_user'),

]


urlpatterns += [
     # Admins
    # path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    # path('admin/products/', admin_views.product_management, name='admin_product_management'),
    # path('admin/products/add/', admin_views.add_product, name='admin_add_product'),
    # path('admin/products/edit/<int:product_id>/', admin_views.edit_product, name='admin_edit_product'),
    # path('admin/products/delete/<int:product_id>/', admin_views.delete_product, name='admin_delete_product'),
    # path('admin/products/update-stock/<int:product_id>/', admin_views.update_stock, name='admin_update_stock'),
    # path('admin/products/toggle-status/<int:product_id>/', admin_views.toggle_product_status, name='admin_toggle_product_status'),
    # path('admin/orders/', admin_views.order_management, name='admin_order_management'),
    # path('admin/orders/<int:order_id>/', admin_views.order_detail_admin, name='admin_order_detail'),
    # path('admin/orders/update-status/<int:order_id>/', admin_views.update_order_status, name='admin_update_order_status'),
    # path('admin/sales-reports/', admin_views.sales_reports, name='admin_sales_reports'),
    # path('admin/transactions/', admin_views.transaction_management, name='admin_transaction_management'), 
        
      
]