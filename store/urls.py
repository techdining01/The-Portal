from django.urls import path
from . import views, admin_views


app_name = 'store'


urlpatterns = [

     # ==================== PUBLIC PAGES ====================
    path('', views.LandingPageView.as_view(), name='landing'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    
      # ==================== PRODUCTS ====================
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    
    # ==================== CART ====================
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/count/', views.cart_count, name='cart_count'),
    
    # ==================== CHECKOUT & ORDERS ====================
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/receipt/', views.order_receipt, name='order_receipt'),
    
    # ==================== PAYMENTS ====================
    path('payment/process/<int:order_id>/', views.process_payment, name='process_payment'),
    path('payment/verify/<str:reference>/', views.payment_verify, name='payment_verify'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    
    # ==================== FEE PAYMENTS ====================
    path('fees/pay/', views.fee_payment_view, name='fee_payment_view'),
    path('fees/pay/process/<int:payment_id>/', views.process_fee_payment, name='process_fee_payment'),
    path('fees/pay/verify/<str:reference>/', views.fee_payment_verify, name='fee_payment_verify'),
    path('fees/history/', views.fee_payment_history, name='fee_payment_history'),
    path('fees/receipt/<str:receipt_number>/', views.fee_receipt, name='fee_receipt'),
    
      # ==================== DASHBOARD ====================
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ==================== ADMIN PANEL ====================
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin/products/<int:product_id>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('admin/products/<int:product_id>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/fees/', views.admin_fee_management, name='admin_fee_management'),
    path('admin/fees/create/', views.admin_fee_create, name='admin_fee_create'),
    path('admin/fees/<int:fee_id>/edit/', views.admin_fee_edit, name='admin_fee_edit'),
    path('admin/analytics/sales/', views.admin_sales_analytics, name='admin_sales_analytics'),
    path('admin/analytics/fees/', views.admin_fee_analytics, name='admin_fee_analytics'),
    path('admin/users/', views.admin_user_management, name='admin_user_management'),
    path('admin/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    
    # ==================== STUDENT PICKUP ====================
    path('pickup/', views.pickup_dashboard, name='pickup_dashboard'),
    path('pickup/generate/<int:student_parent_id>/', views.generate_pickup_code, name='generate_pickup_code'),
    path('pickup/verify/', views.verify_pickup_code, name='verify_pickup_code'),
    
    # ==================== CBT EXAM INTEGRATION ====================
    path('exams/access/', views.exam_access_view, name='exam_access_view'),
    path('exams/verify/', views.exam_payment_verification, name='exam_payment_verification'),
    path('exams/take/<int:exam_id>/', views.take_exam, name='take_exam'),
    
    # ==================== AJAX ENDPOINTS ====================

    path('ajax/product/<int:product_id>/stock/', views.ajax_product_stock, name='ajax_product_stock'),
    path('ajax/cart/summary/', views.ajax_cart_summary, name='ajax_cart_summary'),

]
