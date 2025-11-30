from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, Category, Order, Transaction
from .forms import ProductForm, CategoryForm

def is_admin(user):
    return user.role in ['admin', 'superadmin']

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard with sales analytics"""
    # Sales data
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Sales statistics
    total_sales = Order.objects.filter(payment_verified=True).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    weekly_sales = Order.objects.filter(
        payment_verified=True,
        created_at__date__gte=week_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    monthly_sales = Order.objects.filter(
        payment_verified=True,
        created_at__date__gte=month_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Order statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='delivered').count()
    
    # Product statistics
    low_stock_products = Product.objects.filter(stock_quantity__lt=10).count()
    out_of_stock_products = Product.objects.filter(stock_quantity=0).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')[:10]
    
    # Top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:5]
    
    context = {
        'total_sales': total_sales,
        'weekly_sales': weekly_sales,
        'monthly_sales': monthly_sales,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'recent_orders': recent_orders,
        'top_products': top_products,
    }
    
    return render(request, 'store/admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def product_management(request):
    """Admin product management"""
    products = Product.objects.select_related('category').all()
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/admin/product_management.html', context)

@login_required
@user_passes_test(is_admin)
def add_product(request):
    """Add new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('store:admin_product_management')
    else:
        form = ProductForm()
    
    return render(request, 'store/admin/add_product.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_product(request, product_id):
    """Edit existing product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('store:admin_product_management')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'store/admin/edit_product.html', {'form': form, 'product': product})

@login_required
@user_passes_test(is_admin)
def delete_product(request, product_id):
    """Delete product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('store:admin_product_management')
    
    return render(request, 'store/admin/delete_product.html', {'product': product})

@login_required
@user_passes_test(is_admin)
def update_stock(request, product_id):
    """Update product stock quantity"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        new_stock = request.POST.get('stock_quantity')
        try:
            product.stock_quantity = int(new_stock)
            product.save()
            messages.success(request, f'Stock for "{product.name}" updated to {new_stock}!')
            return JsonResponse({'success': True, 'new_stock': product.stock_quantity})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid stock quantity'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@user_passes_test(is_admin)
def toggle_product_status(request, product_id):
    """Toggle product active status"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.is_active = not product.is_active
        product.save()
        
        action = "activated" if product.is_active else "deactivated"
        messages.success(request, f'Product "{product.name}" {action}!')
        return JsonResponse({'success': True, 'is_active': product.is_active})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@user_passes_test(is_admin)
def order_management(request):
    """Admin order management"""
    orders = Order.objects.select_related('user').prefetch_related('items').all().order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'store/admin/order_management.html', context)

@login_required
@user_passes_test(is_admin)
def order_detail_admin(request, order_id):
    """Admin order detail view"""
    order = get_object_or_404(Order, id=order_id)
    transaction = getattr(order, 'transaction', None)
    
    context = {
        'order': order,
        'transaction': transaction,
    }
    return render(request, 'store/admin/order_detail.html', context)

@login_required
@user_passes_test(is_admin)
def update_order_status(request, order_id):
    """Update order status"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f'Order {order.order_number} status updated to {new_status}!')
            return JsonResponse({'success': True, 'new_status': order.status})
    
    return JsonResponse({'success': False, 'error': 'Invalid status'})

# @login_required
# @user_passes_test(is_admin)
# def sales_reports(request):
#     """Sales reports and analytics"""
#     # Date range filtering
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')
    
#     orders = Order.objects.filter(payment_verified=True)
    
#     if start_date:
#         orders = orders.filter(created_at__date__gte=start_date)
#     if end_date:
#         orders = orders.filter(created_at__date__lte=end_date)
    
#     # Sales data
#     total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
#     total_orders = orders.count()
    
#     # Sales by category
#     category_sales = Category.objects.annotate(
#         total_sales=Sum('product__orderitem__price', filter=Q(product__orderitem__order__in=orders))
#     ).filter(total_sales__isnull=False).order_by('-total_sales')
    
#     # Monthly sales data for chart
#     monthly_sales = Order.objects.filter(payment_verified=True).extra(
#         {'month': "EXTRACT(month FROM created_at)"}
#     ).values('month').annotate(
#         total_sales=Sum('total_amount'),
#         order_count=Count('id')
#     ).order_by('month')
    
#     context = {
#         'total_sales': total_sales,
#         'total_orders': total_orders,
#         'category_sales': category_sales,
#         'monthly_sales': list(monthly_sales),
#         'start_date': start_date,
#         'end_date': end_date,
#     }
    
#     return render(request, 'store/admin/sales_reports.html', context)


@login_required
@user_passes_test(is_admin)
def sales_reports(request):
    """Sales reports and analytics"""
    # Date range filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    orders = Order.objects.filter(payment_verified=True)
    
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    # Sales data
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = orders.count()
    
    # Fixed: Use Django ORM instead of raw SQL for category sales
    from django.db.models import Sum, Q
    category_sales = Category.objects.annotate(
        total_sales=Sum(
            'product__orderitem__price',
            filter=Q(product__orderitem__order__payment_verified=True)
        )
    ).filter(total_sales__isnull=False).order_by('-total_sales')
    
    # Fixed: Monthly sales data using Django ORM (SQLite compatible)
    from django.db.models.functions import ExtractMonth
    monthly_sales = Order.objects.filter(payment_verified=True).annotate(
        month=ExtractMonth('created_at')
    ).values('month').annotate(
        total_sales=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('month')
    
    # Prepare monthly data for template
    monthly_data = []
    for month_data in monthly_sales:
        monthly_data.append({
            'month': month_data['month'],
            'total_sales': month_data['total_sales'] or 0,
            'order_count': month_data['order_count']
        })
    
    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'category_sales': category_sales,
        'monthly_sales': monthly_data,  # Use the processed data
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'store/admin/sales_reports.html', context)




@login_required
@user_passes_test(is_admin)
def transaction_management(request):
    """Transaction management"""
    transactions = Transaction.objects.select_related('order', 'order__user').all().order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        transactions = transactions.filter(payment_status=status_filter)
    
    context = {
        'transactions': transactions,
        'status_filter': status_filter,
    }
    return render(request, 'store/admin/transaction_management.html', context)