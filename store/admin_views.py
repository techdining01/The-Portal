from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, Category, Order, Transaction, PaymentRecord, OrderItem
from .forms import ProductForm, CategoryForm

from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
import json
from datetime import datetime, timedelta

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
    PaymentRecord = getattr(order, 'transaction', None)
    
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




# store/views.py - Add this admin sales report view
@login_required
def admin_sales_reports_view(request):
    """Admin sales reports dashboard"""
    if not request.user.is_staff:
        return HttpResponseForbidden()
    
    # Date filters (default to last 30 days)
    date_range = request.GET.get('range', '30days')
    custom_from = request.GET.get('from')
    custom_to = request.GET.get('to')
    
    # Set date range
    end_date = datetime.now()
    if date_range == '7days':
        start_date = end_date - timedelta(days=7)
    elif date_range == '30days':
        start_date = end_date - timedelta(days=30)
    elif date_range == '90days':
        start_date = end_date - timedelta(days=90)
    elif date_range == 'year':
        start_date = end_date - timedelta(days=365)
    elif date_range == 'custom' and custom_from and custom_to:
        try:
            start_date = datetime.strptime(custom_from, '%Y-%m-%d')
            end_date = datetime.strptime(custom_to, '%Y-%m-%d')
            if start_date > end_date:
                start_date, end_date = end_date, start_date
        except ValueError:
            start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Filter orders by date and payment status
    orders = Order.objects.filter(
        created_at__date__gte=start_date.date(),
        created_at__date__lte=end_date.date(),
        payment_status='completed'
    )
    
    # 1. Overall Stats
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    avg_order_value = orders.aggregate(avg=Avg('total_amount'))['avg'] or 0
    total_products_sold = OrderItem.objects.filter(
        order__in=orders
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # 2. Daily Sales Data (for chart)
    daily_sales = orders.annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')
    
    # Format for chart
    sales_chart_data = {
        'labels': [sale['day'].strftime('%b %d') for sale in daily_sales],
        'datasets': [{
            'label': 'Daily Sales',
            'data': [float(sale['total']) for sale in daily_sales],
            'borderColor': '#4361ee',
            'backgroundColor': 'rgba(67, 97, 238, 0.1)',
            'fill': True
        }]
    }
    
    # 3. Top Products
    top_products = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__name',
        'product__category__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('quantity') * F('price'))
    ).order_by('-quantity_sold')[:10]
    
    # 4. Top Categories
    top_categories = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__category__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('quantity') * F('price'))
    ).order_by('-revenue')
    
    # 5. Payment Methods
    payment_methods = PaymentRecord.objects.filter(
        order__in=orders
    ).values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # 6. Customer Stats
    top_customers = Order.objects.filter(
        created_at__date__gte=start_date.date(),
        created_at__date__lte=end_date.date()
    ).values(
        'user__username',
        'user__email'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-total_spent')[:10]
    
    # 7. Order Status Distribution
    status_distribution = Order.objects.filter(
        created_at__date__gte=start_date.date(),
        created_at__date__lte=end_date.date()
    ).values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 8. Monthly Trends
    monthly_trends = orders.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('total_amount'),
        count=Count('id'),
        avg=Avg('total_amount')
    ).order_by('month')
    
    return render(request, 'store/admin/sales_reports.html', {
        'date_range': date_range,
        'custom_from': custom_from.strftime('%Y-%m-%d') if custom_from else '',
        'custom_to': custom_to.strftime('%Y-%m-%d') if custom_to else '',
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        
        # Stats
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'total_products_sold': total_products_sold,
        
        # Chart data
        'sales_chart_data': json.dumps(sales_chart_data),
        
        # Lists
        'top_products': top_products,
        'top_categories': top_categories,
        'payment_methods': payment_methods,
        'top_customers': top_customers,
        'status_distribution': status_distribution,
        'monthly_trends': monthly_trends,
        
        # Date ranges for filter
        'date_ranges': [
            ('7days', 'Last 7 Days'),
            ('30days', 'Last 30 Days'),
            ('90days', 'Last 90 Days'),
            ('year', 'Last Year'),
            ('custom', 'Custom Range'),
        ]
    })


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



# store/views.py - Add these export views
@login_required
def export_sales_csv_view(request):
    """Export sales data as CSV"""
    if not request.user.is_staff:
        return HttpResponseForbidden()
    
    import csv
    from django.http import HttpResponse
    
    # Get date range from request
    date_range = request.GET.get('range', '30days')
    end_date = datetime.now()
    
    if date_range == '7days':
        start_date = end_date - timedelta(days=7)
    elif date_range == '30days':
        start_date = end_date - timedelta(days=30)
    elif date_range == '90days':
        start_date = end_date - timedelta(days=90)
    elif date_range == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Get completed orders in date range
    orders = Order.objects.filter(
        created_at__date__gte=start_date.date(),
        created_at__date__lte=end_date.date(),
        payment_status='completed'
    ).select_related('user').prefetch_related('items')
    
    # Create HTTP response with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Order Number', 'Date', 'Customer', 'Email', 'Phone',
        'Status', 'Payment Status', 'Items Count', 'Total Amount',
        'Shipping Address'
    ])
    
    # Write data rows
    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.customer_name,
            order.customer_email,
            order.customer_phone,
            order.get_status_display(),
            order.get_payment_status_display(),
            order.items.count(),
            order.total_amount,
            order.shipping_address.replace('\n', ' ')  # Remove line breaks
        ])
    
    return response

@login_required
def export_products_csv_view(request):
    """Export product sales data as CSV"""
    if not request.user.is_staff:
        return HttpResponseForbidden()
    
    import csv
    from django.http import HttpResponse
    
    # Date range
    date_range = request.GET.get('range', '30days')
    end_date = datetime.now()
    
    if date_range == '7days':
        start_date = end_date - timedelta(days=7)
    elif date_range == '30days':
        start_date = end_date - timedelta(days=30)
    elif date_range == '90days':
        start_date = end_date - timedelta(days=90)
    elif date_range == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Get product sales data
    product_sales = OrderItem.objects.filter(
        order__created_at__date__gte=start_date.date(),
        order__created_at__date__lte=end_date.date(),
        order__payment_status='completed'
    ).select_related('product', 'product__category').values(
        'product__name',
        'product__category__name',
        'product__price'
    ).annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price'))
    ).order_by('-quantity_sold')
    
    # Create HTTP response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="product_sales_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Product Name', 'Category', 'Unit Price',
        'Quantity Sold', 'Total Revenue', 'Average Daily Sales'
    ])
    
    # Calculate days in range
    days_in_range = (end_date.date() - start_date.date()).days or 1
    
    # Write data rows
    for product in product_sales:
        avg_daily = product['quantity_sold'] / days_in_range
        writer.writerow([
            product['product__name'],
            product['product__category__name'],
            product['product__price'],
            product['quantity_sold'],
            product['total_revenue'],
            round(avg_daily, 2)
        ])
    
    return response