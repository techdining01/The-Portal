from django.urls import path
from . import views, backup_views

app_name = 'ecommerce'

urlpatterns = [
    # Public URLs
    path('', views.ProductListView.as_view(), name='product_list'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<int:product_id>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Payment URLs
    path('payment/paystack/<int:order_id>/', views.initiate_paystack_payment, name='initiate_paystack_payment'),
    path('payment/paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('payment/webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('payment/manual/<int:order_id>/', views.manual_payment, name='manual_payment'),
    
    # Order URLs
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Student Lookup
    path('student-lookup/', views.student_lookup, name='student_lookup'),
    
    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/products/add/', views.add_product, name='add_product'),
    path('admin/products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('admin/products/<int:product_id>/update-stock/', views.update_stock, name='update_stock'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/categories/', views.manage_categories, name='manage_categories'),

    # Backup URLs
    path('admin/backups/', views.backup_management, name='backup_management'),
    path('admin/backups/<int:backup_id>/', views.view_backup, name='view_backup'),
    path('admin/backups/create/', views.create_manual_backup, name='create_manual_backup'),
    path('admin/audit-logs/', views.audit_logs, name='audit_logs'),


    path('backup-management/', backup_views.backup_management, name='admin_backup_management'),
    path('backup/create/', backup_views.create_backup, name='admin_backup_create'),
    path('backup/<int:backup_id>/view/', backup_views.view_backup, name='admin_backup_view'),
    path('backup/<int:backup_id>/delete/', backup_views.delete_backup, name='admin_backup_delete'),
    path('backup/<int:backup_id>/verify/', backup_views.verify_backup, name='admin_backup_verify'),
    path('backup/<int:backup_id>/download/', backup_views.download_backup, name='admin_backup_download'),
    path('backup/manual/', backup_views.manual_backup, name='admin_backup_manual'),
    path('audit-logs/', backup_views.audit_logs, name='admin_audit_logs'),
    
    # API endpoints
    path('api/backup-status/', backup_views.api_backup_status, name='api_backup_status'),
    path('api/cleanup-backups/', backup_views.api_cleanup_backups, name='api_cleanup_backups'),
]
