from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import  reverse, reverse_lazy
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.db import models
import json
from . import backup_manager, backup_service
from exams.models import Class
from .models import Product, Cart, CartItem, Order, OrderItem, Payment, Category, StockAlert, TransactionBackup, AuditLog
from .forms import ProductForm, StudentSelectionForm, AddToCartForm, CheckoutForm, ManualPaymentForm, StockUpdateForm, CategoryForm
from .paystack_service import PaystackService, generate_payment_reference
from .webhook_handlers import webhook_handler
from django.contrib.auth import get_user_model

User = get_user_model()



# Helper functions
def is_admin_user(user):
    return user.is_authenticated and user.is_admin()

def send_payment_confirmation_email(order, payment):
    """Send payment confirmation email"""
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        subject = f"Payment Confirmation - Order #{order.order_number}"
        
        context = {
            'order': order,
            'payment': payment,
            'user': order.user
        }
        
        html_message = render_to_string('ecommerce/emails/payment_confirmation.html', context)
        plain_message = render_to_string('ecommerce/emails/payment_confirmation.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email='noreply@schoolcommerce.com',
            recipient_list=[order.user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Email sending failed: {e}")

# Public Views
class ProductListView(ListView):
    model = Product
    template_name = 'ecommerce/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True)
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by product type
        product_type = self.request.GET.get('type')
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        
        # Filter by class
        student_class = self.request.GET.get('class')
        if student_class:
            queryset = queryset.filter(applicable_class_id=student_class)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['product_types'] = Product.PRODUCT_TYPES
        context['classes'] = Class.objects.filter(is_active=True)
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'ecommerce/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddToCartForm(parent_user=self.request.user)
        return context

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST, parent_user=request.user)
        
        if form.is_valid():
            student = form.cleaned_data['student']
            quantity = form.cleaned_data['quantity']
            
            # Check stock availability
            if product.track_stock and product.stock_quantity < quantity:
                messages.error(request, f"Only {product.stock_quantity} items available in stock")
                return redirect('ecommerce:product_detail', pk=product.id)
            
            # Get or create cart for user
            cart, created = Cart.objects.get_or_create(
                user=request.user, 
                is_active=True
            )
            
            # Check if item already exists in cart for the same student
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                student=student,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            messages.success(request, f"Added {product.name} to cart for {student.get_full_name()}")
            return redirect('ecommerce:cart_view')
    else:
        form = AddToCartForm(parent_user=request.user)
    
    return render(request, 'ecommerce/product_detail.html', {
        'product': product,
        'form': form
    })

@login_required
def cart_view(request):
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = cart.items.select_related('product', 'student').all()
    except Cart.DoesNotExist:
        cart = None
        cart_items = []
    
    if request.method == 'POST':
        # Handle quantity updates or removals
        for item in cart_items:
            new_quantity = request.POST.get(f'quantity_{item.id}')
            remove = request.POST.get(f'remove_{item.id}')
            
            if remove:
                item.delete()
                messages.success(request, "Item removed from cart")
            elif new_quantity:
                try:
                    quantity = int(new_quantity)
                    if quantity > 0:
                        # Check stock
                        if item.product.track_stock and item.product.stock_quantity < quantity:
                            messages.error(request, f"Only {item.product.stock_quantity} items available for {item.product.name}")
                        else:
                            item.quantity = quantity
                            item.save()
                    else:
                        item.delete()
                        messages.success(request, "Item removed from cart")
                except ValueError:
                    pass
        
        return redirect('ecommerce:cart_view')
    
    return render(request, 'ecommerce/cart.html', {
        'cart': cart,
        'cart_items': cart_items
    })

@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = cart.items.select_related('product', 'student').all()
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty")
        return redirect('ecommerce:product_list')
    
    if not cart_items:
        messages.error(request, "Your cart is empty")
        return redirect('ecommerce:product_list')
    
    # Check stock availability
    for item in cart_items:
        if item.product.track_stock and item.product.stock_quantity < item.quantity:
            messages.error(request, f"Sorry, {item.product.name} only has {item.product.stock_quantity} items left in stock")
            return redirect('ecommerce:cart_view')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        
        if form.is_valid():
            with transaction.atomic():
                # Create order
                order = Order(
                    user=request.user,
                    total_amount=cart.total_amount,
                    payment_method=form.cleaned_data['payment_method'],
                    billing_address=form.cleaned_data['billing_address'],
                    billing_phone=form.cleaned_data['billing_phone']
                )
                order.save()
                
                # Create order items
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price,
                        student=cart_item.student
                    )
                
                # Create payment record
                payment_reference = generate_payment_reference()
                
                # Determine payment gateway
                payment_gateway = 'manual'
                if order.payment_method in ['paystack', 'opay']:
                    payment_gateway = order.payment_method
                
                payment = Payment.objects.create(
                    order=order,
                    amount=order.total_amount,
                    reference=payment_reference,
                    payment_method=order.payment_method,
                    payment_gateway=payment_gateway
                )
                
                # Deactivate cart
                cart.is_active = False
                cart.save()
                
                messages.success(request, f"Order #{order.order_number} created successfully!")
                
                # Redirect based on payment method
                if order.payment_method == 'paystack':
                    return redirect('ecommerce:initiate_paystack_payment', order_id=order.id)
                elif order.payment_method == 'opay':
                    return redirect('ecommerce:initiate_opay_payment', order_id=order.id)
                else:
                    # Manual payment methods
                    return redirect('ecommerce:manual_payment', order_id=order.id)
    else:
        form = CheckoutForm(user=request.user)
    
    return render(request, 'ecommerce/checkout.html', {
        'cart': cart,
        'cart_items': cart_items,
        'form': form
    })

# Payment Views
@login_required
def initiate_paystack_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = get_object_or_404(Payment, order=order)
    
    paystack_service = PaystackService()
    
    # Create callback URL
    callback_url = request.build_absolute_uri(
        reverse('ecommerce:paystack_callback')
    )
    
    # Prepare metadata
    metadata = {
        'order_number': order.order_number,
        'order_id': order.id,
        'payment_id': payment.id,
        'custom_fields': [
            {
                'display_name': "Order Number",
                'variable_name': "order_number",
                'value': order.order_number
            }
        ]
    }
    
    try:
        # Initialize Paystack transaction
        response = paystack_service.initialize_transaction(
            email=request.user.email,
            amount=order.total_amount,
            reference=payment.reference,
            callback_url=callback_url,
            metadata=metadata
        )
        
        if response['status']:
            # Redirect to Paystack payment page
            authorization_url = response['data']['authorization_url']
            return redirect(authorization_url)
        else:
            messages.error(request, "Failed to initialize payment. Please try again.")
            return redirect('ecommerce:order_detail', order_id=order.id)
            
    except Exception as e:
        messages.error(request, f"Payment initialization failed: {str(e)}")
        return redirect('ecommerce:order_detail', order_id=order.id)

@login_required
def paystack_callback(request):
    """Handle Paystack callback after payment"""
    reference = request.GET.get('reference')
    trxref = request.GET.get('trxref')
    
    if not reference:
        messages.error(request, "Invalid payment reference")
        return redirect('ecommerce:order_history')
    
    try:
        payment = Payment.objects.get(reference=reference)
        order = payment.order
        
        # SCENARIO 1: Webhook already processed the payment
        if payment.verified and payment.status == 'successful':
            messages.success(request, "Payment completed successfully!")
            return redirect('ecommerce:order_confirmation', order_id=order.id)
        
        # SCENARIO 2: Webhook is processing
        if payment.status == 'processing':
            messages.info(request, "Payment is being processed. You will receive confirmation shortly.")
            return redirect('ecommerce:order_confirmation', order_id=order.id)
        
        # SCENARIO 3: Fallback API verification
        if payment.can_retry_verification():
            try:
                paystack_service = PaystackService()
                verification = paystack_service.verify_transaction(reference)
                payment.record_verification_attempt()
                
                if verification['status'] and verification['data']['status'] == 'success':
                    payment.mark_as_paid(
                        paystack_reference=verification['data'].get('reference'),
                        gateway_data=verification['data']
                    )
                    messages.success(request, "Payment verified successfully!")
                else:
                    messages.warning(request, "Payment verification in progress. Please check your email.")
                    
            except Exception as e:
                messages.info(request, "Payment received! Please wait for confirmation.")
        else:
            messages.info(request, "Payment is being processed. Please check your email.")
        
        return redirect('ecommerce:order_confirmation', order_id=order.id)
        
    except Payment.DoesNotExist:
        messages.error(request, "Invalid payment reference")
        return redirect('ecommerce:order_history')

@login_required
def manual_payment(request, order_id):
    """Handle manual payment methods (bank transfer, cash)"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        form = ManualPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            # Update payment with manual details
            payment = get_object_or_404(Payment, order=order)
            payment.transfer_date = form.cleaned_data['transfer_date']
            payment.transfer_reference = form.cleaned_data['transfer_reference']
            
            if form.cleaned_data['transfer_proof']:
                payment.transfer_proof = form.cleaned_data['transfer_proof']
            
            payment.status = 'processing'
            payment.save()
            
            messages.success(request, 
                "Payment details submitted! We will verify your payment and update your order status."
            )
            return redirect('ecommerce:order_confirmation', order_id=order.id)
    else:
        form = ManualPaymentForm()
    
    # Bank details for transfer
    bank_details = {
        'bank_name': 'Your School Bank',
        'account_name': 'School E-commerce Account',
        'account_number': '0123456789',
        'amount': order.total_amount,
        'reference': f"ORDER-{order.order_number}"
    }
    
    return render(request, 'ecommerce/manual_payment.html', {
        'order': order,
        'form': form,
        'bank_details': bank_details
    })

# Webhook endpoint
def paystack_webhook(request):
    """Handle Paystack webhook"""
    return webhook_handler.handle_paystack_webhook(request)

# Order Management
@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if payment was completed via webhook while user was waiting
    try:
        payment = Payment.objects.get(order=order)
        if payment.verified and payment.status == 'successful' and not order.paid_at:
            order.mark_as_paid()
    except Payment.DoesNotExist:
        pass
    
    return render(request, 'ecommerce/order_confirmation.html', {
        'order': order
    })

@login_required
def order_history(request):
    """User order history"""
    orders = Order.objects.filter(user=request.user).select_related('payment').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'ecommerce/order_history.html', {
        'page_obj': page_obj,
        'orders': page_obj.object_list
    })

@login_required
def order_detail(request, order_id):
    """Order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'ecommerce/order_detail.html', {
        'order': order
    })

# Student Lookup (AJAX)
@login_required
def student_lookup(request):
    """AJAX endpoint for student lookup"""
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        search_type = request.GET.get('search_type')
        query = request.GET.get('query')
        
        students = User.objects.filter(role='student', is_active=True)
        
        if search_type == 'registration_number' and query:
            students = students.filter(registration_number__icontains=query)
        elif search_type == 'name' and query:
            students = students.filter(
                Q(first_name__icontains=query) |
                Q(surname__icontains=query) |
                Q(other_name__icontains=query)
            )
        
        results = []
        for student in students[:10]:
            results.append({
                'id': student.id,
                'name': student.get_full_name(),
                'registration_number': student.registration_number,
                'class': student.student_class.name if student.student_class else 'N/A'
            })
        
        return JsonResponse({'students': results})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# Admin Views
@login_required
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    """Admin dashboard"""
    # Basic statistics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(
        track_stock=True, 
        stock_quantity__lte=models.F('low_stock_threshold')
    ).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Payment statistics
    payment_stats = Payment.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'recent_orders': recent_orders,
        'payment_stats': payment_stats,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin_user)
def admin_products(request):
    """Admin product management"""
    products = Product.objects.select_related('category', 'applicable_class').all()
    
    # Filtering
    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    type_filter = request.GET.get('type')
    if type_filter:
        products = products.filter(product_type=type_filter)
    
    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        products = products.filter(
            track_stock=True,
            stock_quantity__lte=models.F('low_stock_threshold')
        )
    elif stock_filter == 'out':
        products = products.filter(
            track_stock=True,
            stock_quantity=0
        )
    
    categories = Category.objects.filter(is_active=True)
    
    return render(request, 'admin/products.html', {
        'products': products,
        'categories': categories,
        'product_types': Product.PRODUCT_TYPES
    })

@login_required
@user_passes_test(is_admin_user)
def admin_orders(request):
    """Admin order management"""
    orders = Order.objects.select_related('user', 'payment').prefetch_related('items').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    payment_filter = request.GET.get('payment_method')
    if payment_filter:
        orders = orders.filter(payment_method=payment_filter)
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/orders.html', {
        'page_obj': page_obj,
        'orders': page_obj.object_list
    })

@login_required
@user_passes_test(is_admin_user)
def add_product(request):
    """Add new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' added successfully!")
            return redirect('ecommerce:admin_products')
    else:
        form = ProductForm()
    
    return render(request, 'admin/product_form.html', {
        'form': form,
        'title': 'Add New Product'
    })

@login_required
@user_passes_test(is_admin_user)
def edit_product(request, product_id):
    """Edit product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('ecommerce:admin_products')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'admin/product_form.html', {
        'form': form,
        'title': 'Edit Product',
        'product': product
    })

@login_required
@user_passes_test(is_admin_user)
def update_stock(request, product_id):
    """Update product stock"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = StockUpdateForm(request.POST)
        if form.is_valid():
            new_stock = form.cleaned_data['new_stock']
            reason = form.cleaned_data['reason']
            
            old_stock = product.stock_quantity
            product.stock_quantity = new_stock
            product.save()
            
            # Resolve stock alerts if any
            if new_stock > product.low_stock_threshold:
                StockAlert.objects.filter(product=product, is_resolved=False).update(
                    is_resolved=True,
                    resolved_at=timezone.now()
                )
            
            messages.success(request, 
                f"Stock updated from {old_stock} to {new_stock} for {product.name}"
            )
            return redirect('ecommerce:admin_products')
    else:
        form = StockUpdateForm(initial={'new_stock': product.stock_quantity})
    
    return render(request, 'admin/update_stock.html', {
        'form': form,
        'product': product
    })

@login_required
@user_passes_test(is_admin_user)
def manage_categories(request):
    """Manage product categories"""
    categories = Category.objects.all()
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' added successfully!")
            return redirect('ecommerce:manage_categories')
    else:
        form = CategoryForm()
    
    return render(request, 'admin/categories.html', {
        'categories': categories,
        'form': form
    })


@login_required
@user_passes_test(is_admin_user)
def backup_management(request):
    """Backup management dashboard"""
    # Statistics
    total_backups = TransactionBackup.objects.count()
    payment_backups = TransactionBackup.objects.filter(transaction_type='payment').count()
    order_backups = TransactionBackup.objects.filter(transaction_type='order').count()
    
    # Recent backups
    recent_backups = TransactionBackup.objects.select_related('backed_up_by').order_by('-created_at')[:10]
    
    # Storage size (approximate)
    total_size = TransactionBackup.objects.count() * 2  # Approximate KB per backup
    
    context = {
        'total_backups': total_backups,
        'payment_backups': payment_backups,
        'order_backups': order_backups,
        'recent_backups': recent_backups,
        'total_size_mb': total_size / 1024,
    }
    
    return render(request, 'admin/backup_management.html', context)

@login_required
@user_passes_test(is_admin_user)
def view_backup(request, backup_id):
    """View backup details"""
    backup = get_object_or_404(TransactionBackup, id=backup_id)
    
    # Verify integrity
    integrity_ok = backup.verify_integrity()
    
    return render(request, 'admin/view_backup.html', {
        'backup': backup,
        'integrity_ok': integrity_ok,
        'data_json': json.dumps(backup.data_snapshot, indent=2)
    })

@login_required
@user_passes_test(is_admin_user)
def audit_logs(request):
    """View audit logs"""
    logs = AuditLog.objects.select_related('user').order_by('-created_at')
    
    # Filtering
    action_filter = request.GET.get('action_type')
    if action_filter:
        logs = logs.filter(action_type=action_filter)
    
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/audit_logs.html', {
        'page_obj': page_obj,
        'action_types': AuditLog.ACTION_TYPES
    })

@login_required
@user_passes_test(is_admin_user)
def create_manual_backup(request):
    """Create manual backup of specific records"""
    if request.method == 'POST':
        backup_type = request.POST.get('backup_type')
        record_id = request.POST.get('record_id')
        reason = request.POST.get('reason', 'Manual backup')
        
        try:
            if backup_type == 'payment':
                payment = Payment.objects.get(id=record_id)
                backup_service.backup_payment(payment, 'manual', reason, request.user)
                messages.success(request, f"Payment backup created: {payment.reference}")
                
            elif backup_type == 'order':
                order = Order.objects.get(id=record_id)
                backup_service.backup_order(order, reason, request.user)
                messages.success(request, f"Order backup created: {order.order_number}")
                
            else:
                messages.error(request, "Invalid backup type")
                
        except Exception as e:
            messages.error(request, f"Backup failed: {str(e)}")
        
        return redirect('ecommerce:backup_management')
    
    return render(request, 'admin/manual_backup.html')


@login_required
@user_passes_test(is_admin_user)
def backup_operations(request):
    """Perform backup operations via web interface"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'create_backup':
                from .tasks import perform_daily_backup
                perform_daily_backup.delay()
                messages.success(request, "Backup operation started")
                
            elif action == 'cleanup_backups':
                from .tasks import cleanup_old_backups
                cleanup_old_backups.delay()
                messages.success(request, "Backup cleanup started")
                
            elif action == 'export_transactions':
                days = int(request.POST.get('days', 7))
                end_date = timezone.now()
                start_date = end_date - timezone.timedelta(days=days)
                
                filepath = backup_manager.export_transaction_data(start_date, end_date)
                if filepath:
                    messages.success(request, f"Transactions exported: {filepath}")
                else:
                    messages.error(request, "Export failed")
                    
        except Exception as e:
            messages.error(request, f"Operation failed: {str(e)}")
        
        return redirect('ecommerce:backup_management')
    
    return render(request, 'admin/backup_operations.html')

