from django.urls import path
from . import views, student_api


app_name = "shop"

urlpatterns = [
     
    # admin dashboard (simple)
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/', views.order_list, name='order_list'),

]

    
    # # Receipts
    # path("checkout-inline/", views.checkout_inline_view, name="checkout_inline"),  # inline flow
    # path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),
    # path("receipt/<slug:slug>/", views.receipt_view, name="receipt"),

urlpatterns += [
    # Storefront
    path("", views.product_list, name="product_list"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart_view"),  # you'll already have or add cart_view below
    path("cart/update-qty/", views.cart_update_qty, name="cart_update_qty"),
    path("cart/remove-item/", views.cart_remove_item, name="cart_remove_item"), path("product/<int:pk>/ajax/", views.product_detail_ajax, name="product_detail_ajax"),
   
    path("purchase/history/", views.parent_purchase_history, name="purchase_history_parent"),
    path("purchase/student/<str:student_reg>/", views.student_purchase_history, name="purchase_history_student"),

    #Student APIs
    path("api/student/search/", student_api.search_student, name="student_search"),
    path("api/student/verify/", student_api.verify_student, name="student_verify"),


    path('admin/shop/dashboard/', views.shop_dashboard, name="shop_admin_dashboard"),
    path("admin/dashboard/", views.management_dashboard, name="admin_dashboard"),

    # Paystack
    path("checkout/inline/init/", views.checkout_inline_init, name="checkout_inline_init"),
    path("checkout/inline/verify/", views.paystack_verify_inline, name="paystack_verify_inline"),
    path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook"),
    path("api/paystack/initialize/", views.api_paystack_initialize, name="api_paystack_init"),
]


   