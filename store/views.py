from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F, DecimalField
from django.db.models.functions import TruncMonth, TruncYear, TruncDay
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta, datetime
import json
import logging
from decimal import Decimal
from . import paystack
from django.conf import settings
from users.models import Student, User, Parent, StudentParent
from .models import (
    Payment, Product, Order, OrderItem, Inventory, Cart,
    CartItem, Category, FeePayment, PurchaseOrder, 
    FeeStructure, Attendance
)

from .forms import (
    AddToCartForm, ContactForm, ProductForm, ProductSearchForm,
    create_student_selector_form, CheckoutForm, OrderStatusUpdateForm,
    BulkFeePaymentForm, ExamPaymentVerificationForm,
    FeePaymentForm, FeeStructureForm
    )

from .utils import *



logger = logging.getLogger(__name__)

 
# ==================== UTILITY FUNCTIONS ====================

def is_admin(user):
    """Check if user is admin or superadmin"""
    return user.is_authenticated and user.role in ['admin', 'superadmin']

def is_parent(user):
    """Check if user is parent"""
    return user.is_authenticated and user.role == 'parent'

def is_student(user):
    """Check if user is student"""
    return user.is_authenticated and user.role == 'student'

def is_teacher_or_staff(user):
    """Check if user is teacher or staff"""
    return user.is_authenticated and user.role in ['teacher', 'staff']

# ==================== LANDING & PUBLIC VIEWS ====================

class LandingPageView(TemplateView):
    """Landing page view"""
    template_name = 'store/landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.filter(
            is_featured=True,
            is_active=True
        )[:8]
        context['categories'] = Category.objects.filter(
            is_active=True,
            parent__isnull=True
        )[:6]
        context['new_arrivals'] = Product.objects.filter(
            is_active=True
        ).order_by('-created_at')[:6]
        return context


class AboutView(TemplateView):
    """About page view"""
    template_name = 'store/about.html'


class ContactView(TemplateView):
    """Contact page view"""
    template_name = 'store/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_form'] = ContactForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save contact message (you might want to create a ContactMessage model)
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('store:contact')
        return render(request, self.template_name, {'contact_form': form})


# ==================== PRODUCT VIEWS ====================

class ProductListView(ListView):
    """Product listing page"""
    model = Product
    template_name = 'store/products/list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        
        # Search
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(sku__icontains=search_query)
            )
        
        # Category filter
        category_slug = self.request.GET.get('category', '')
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
                # Get all subcategories
                categories = category.get_descendants()
                categories.append(category)
                queryset = queryset.filter(category__in=categories)
            except Category.DoesNotExist:
                pass
        
        # Price range filter
        min_price = self.request.GET.get('min_price', '')
        max_price = self.request.GET.get('max_price', '')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Sort
        sort_by = self.request.GET.get('sort_by', '-created_at')
        if sort_by in ['name', '-name', 'price', '-price', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True, parent__isnull=True)
        context['search_form'] = ProductSearchForm(self.request.GET)
        context['current_category'] = self.request.GET.get('category', '')
        return context


class ProductDetailView(DetailView):
    """Product detail page"""
    model = Product
    template_name = 'store/products/detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # Increment view count
        product.total_views += 1
        product.save(update_fields=['total_views'])
        
        # Get related products
        context['related_products'] = product.get_related_products()
        
        # Add to cart form
        if self.request.user.is_authenticated:
            context['add_to_cart_form'] = AddToCartForm(
                user=self.request.user,
                product=product
            )
        
        return context


# ==================== CART VIEWS ====================

@login_required
def cart_view(request):
    """Shopping cart view"""
    cart, created = Cart.objects.get_or_create(
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST, user=request.user)
        if form.is_valid():
            product_id = request.POST.get('product_id')
            quantity = form.cleaned_data['quantity']
            student = form.cleaned_data['student']
            
            try:
                product = Product.objects.get(id=product_id)
                cart.add_item(product, quantity, student)
                messages.success(request, f'{product.name} added to cart!')
                return redirect('store:cart_view')
            except Product.DoesNotExist:
                messages.error(request, 'Product not found.')
    
    context = {
        'cart': cart,
        'items': cart.items.all(),
        'total_amount': cart.total_amount,
        'student_form': create_student_selector_form(request.user)()
    }
    return render(request, 'store/cart/view.html', context)


@login_required
@require_POST
def add_to_cart(request, product_id):
    """AJAX endpoint to add product to cart"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )
        
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate stock
        if product.stock_quantity < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.stock_quantity} items available.'
            })
        
        # Check if student is required
        if request.user.role in ['parent', 'student']:
            student_id = request.POST.get('student_id')
            if student_id:
                try:
                    student = Student.objects.get(id=student_id)
                    if request.user.role == 'parent':
                        parent = request.user.parent_profile
                        if not parent.students.filter(id=student.id).exists():
                            return JsonResponse({
                                'success': False,
                                'message': 'Student not associated with parent.'
                            })
                    cart.student = student
                    cart.save()
                except Student.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Student not found.'
                    })
        
        cart.add_item(product, quantity)
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_count': cart.total_items,
            'cart_total': f"₦{cart.total_amount:,.2f}"
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found.'})
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return JsonResponse({'success': False, 'message': 'An error occurred.'})


@login_required
@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity < 1:
            cart_item.delete()
            message = 'Item removed from cart.'
        else:
            if quantity > cart_item.product.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {cart_item.product.stock_quantity} items available.'
                })
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart updated successfully.'
        
        cart = cart_item.cart
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart.total_items,
            'cart_total': f"₦{cart.total_amount:,.2f}",
            'item_subtotal': f"₦{cart_item.subtotal:,.2f}"
        })
        
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found in cart.'})


@login_required
@require_POST
def remove_cart_item(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
        cart = cart_item.cart
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart.',
            'cart_count': cart.total_items,
            'cart_total': f"₦{cart.total_amount:,.2f}"
        })
        
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Item not found in cart.'})


@login_required
def cart_count(request):
    """Get cart item count (AJAX endpoint)"""
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(
            user=request.user,
            is_active=True
        ).aggregate(
            total=Sum('items__quantity')
        )['total'] or 0
    else:
        cart_count = 0
    
    return JsonResponse({'count': cart_count})


# ==================== CHECKOUT & ORDER VIEWS ====================

@login_required
def checkout_view(request):
    """Checkout page"""
    cart = get_object_or_404(Cart, user=request.user, is_active=True)
    
    if cart.total_items == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:product_list')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            # Create order
            order = Order.objects.create(
                user=request.user,
                student=cart.student,
                subtotal=cart.total_amount,
                total_amount=cart.total_amount,
                shipping_address=form.cleaned_data.get('shipping_address', request.user.address),
                delivery_date=form.cleaned_data.get('delivery_date'),
                delivery_time=form.cleaned_data.get('delivery_time'),
                payment_method=form.cleaned_data.get('payment_method', 'paystack'),
                notes=form.cleaned_data.get('notes', '')
            )
            
            # Create order items from cart
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
                
                # Update product stock
                cart_item.product.decrease_stock(cart_item.quantity)
                cart_item.product.update_sales(cart_item.quantity)
            
            # Clear cart
            cart.clear()
            cart.is_active = False
            cart.save()
            
            # Redirect to payment
            if order.payment_method == 'paystack':
                return redirect('store:process_payment', order_id=order.id)
            else:
                messages.success(request, 'Order placed successfully!')
                return redirect('store:order_detail', order_id=order.id)
    else:
        form = CheckoutForm(user=request.user)
    
    context = {
        'cart': cart,
        'form': form,
        'items': cart.items.all(),
        'total_amount': cart.total_amount
    }
    return render(request, 'store/checkout/checkout.html', context)


@login_required
def process_payment(request, order_id):
    """Process Paystack payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Initialize Paystack
    paystack_secret_key = settings.PAYSTACK_SECRET_KEY
    paystack_public_key = settings.PAYSTACK_PUBLIC_KEY
    
    if not paystack_secret_key or not paystack_public_key:
        messages.error(request, 'Payment gateway not configured.')
        return redirect('store:checkout')
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        amount=order.total_amount,
        payment_method='paystack',
        payer_email=request.user.email,
        payer_name=request.user.get_full_name(),
        payer_phone=request.user.phone
    )
    
    # Initialize Paystack transaction
    try:
        paystack_api = paystack.Paystack(secret_key=paystack_secret_key)
        
        # Create transaction
        transaction = paystack_api.transaction.initialize(
            amount=int(order.total_amount * 100),  # Convert to kobo
            email=request.user.email,
            reference=payment.reference,
            callback_url=request.build_absolute_uri(
                reverse('store:payment_verify', args=[payment.reference])
            ),
            metadata={
                'order_id': order.id,
                'payment_id': payment.id,
                'user_id': request.user.id,
                'student_id': order.student.id if order.student else None
            }
        )
        
        if transaction['status']:
            payment.paystack_access_code = transaction['data']['access_code']
            payment.paystack_reference = transaction['data']['reference']
            payment.save()
            
            # Redirect to Paystack payment page
            return redirect(transaction['data']['authorization_url'])
        else:
            messages.error(request, 'Failed to initialize payment.')
            return redirect('store:checkout')
            
    except Exception as e:
        logger.error(f"Paystack error: {str(e)}")
        messages.error(request, 'Payment processing error.')
        return redirect('store:checkout')


@login_required
def payment_verify(request, reference):
    """Verify Paystack payment"""
    payment = get_object_or_404(Payment, reference=reference)
    order = payment.order
    
    # Verify with Paystack
    paystack_api = paystack.Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)
    
    try:
        verification = paystack_api.transaction.verify(reference)
        
        if verification['status'] and verification['data']['status'] == 'success':
            # Payment successful
            payment.mark_as_completed(verification)
            messages.success(request, 'Payment successful! Your order has been confirmed.')
            
            # Send notification email
            send_order_confirmation_email(order)
            
            return redirect('store:order_detail', order_id=order.id)
        else:
            # Payment failed
            payment.mark_as_failed('Payment verification failed')
            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('store:checkout')
            
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        messages.error(request, 'Payment verification error.')
        return redirect('store:checkout')


@login_required
def order_list(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'page_obj': page_obj
    }
    return render(request, 'store/orders/list.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'items': order.items.all(),
        'payment': order.payments.first()
    }
    return render(request, 'store/orders/detail.html', context)


# ==================== FEE PAYMENT VIEWS ====================

@login_required
def fee_payment_view(request):
    """School fee payment page"""
    if request.user.role not in ['parent', 'student']:
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')
    
    if request.method == 'POST':
        form = FeePaymentForm(request.POST, user=request.user)
        if form.is_valid():
            student = form.cleaned_data['student']
            fee_structure = form.cleaned_data['fee_structure']
            amount = form.cleaned_data['amount_paid']
            payment_method = form.cleaned_data['payment_method']
            
            # Create fee payment record
            fee_payment = FeePayment.objects.create(
                student=student,
                fee_structure=fee_structure,
                amount_paid=amount,
                payment_method=payment_method,
                notes=form.cleaned_data.get('notes', '')
            )
            
            # Process payment
            if payment_method == 'paystack':
                # Create payment record
                payment = Payment.objects.create(
                    fee_payment=fee_payment,
                    amount=amount,
                    payment_method='paystack',
                    payer_email=request.user.email,
                    payer_name=request.user.get_full_name(),
                    payer_phone=request.user.phone
                )
                
                # Initialize Paystack payment
                return redirect('store:process_fee_payment', payment_id=payment.id)
            else:
                # For other payment methods (cash, transfer)
                fee_payment.mark_as_paid(f'MANUAL-{timezone.now().timestamp()}')
                fee_payment.issue_receipt(request.user)
                
                messages.success(request, 'Fee payment recorded successfully!')
                return redirect('store:fee_payment_history')
    
    else:
        form = FeePaymentForm(user=request.user)
    
    # Get student's unpaid fees
    unpaid_fees = []
    if request.user.role == 'parent':
        try:
            parent = request.user.parent_profile
            for student in parent.students.all():
                unpaid_fees.extend(student.get_unpaid_fees())
        except Parent.DoesNotExist:
            pass
    elif request.user.role == 'student':
        try:
            student = request.user.student
            unpaid_fees = student.get_unpaid_fees()
        except Student.DoesNotExist:
            pass
    
    context = {
        'form': form,
        'unpaid_fees': unpaid_fees,
        'total_unpaid': sum(fee['balance'] for fee in unpaid_fees) if unpaid_fees else 0
    }
    return render(request, 'store/fees/payment.html', context)


@login_required
def process_fee_payment(request, payment_id):
    """Process fee payment via Paystack"""
    payment = get_object_or_404(Payment, id=payment_id, fee_payment__isnull=False)
    
    # Initialize Paystack
    paystack_api = paystack.Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)
    
    try:
        transaction = paystack_api.transaction.initialize(
            amount=int(payment.amount * 100),
            email=request.user.email,
            reference=payment.reference,
            callback_url=request.build_absolute_uri(
                reverse('store:fee_payment_verify', args=[payment.reference])
            ),
            metadata={
                'payment_id': payment.id,
                'fee_payment_id': payment.fee_payment.id,
                'student_id': payment.fee_payment.student.id,
                'user_id': request.user.id
            }
        )
        
        if transaction['status']:
            payment.paystack_access_code = transaction['data']['access_code']
            payment.paystack_reference = transaction['data']['reference']
            payment.save()
            
            return redirect(transaction['data']['authorization_url'])
        else:
            messages.error(request, 'Failed to initialize payment.')
            return redirect('store:fee_payment_view')
            
    except Exception as e:
        logger.error(f"Paystack fee payment error: {str(e)}")
        messages.error(request, 'Payment processing error.')
        return redirect('store:fee_payment_view')


@login_required
def fee_payment_verify(request, reference):
    """Verify fee payment"""
    payment = get_object_or_404(Payment, reference=reference)
    fee_payment = payment.fee_payment
    
    # Verify with Paystack
    paystack_api = paystack.Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)
    
    try:
        verification = paystack_api.transaction.verify(reference)
        
        if verification['status'] and verification['data']['status'] == 'success':
            # Payment successful
            payment.mark_as_completed(verification)
            fee_payment.issue_receipt(request.user)
            
            messages.success(request, 'Fee payment successful! Receipt generated.')
            
            # Send receipt email
            send_fee_receipt_email(fee_payment)
            
            # Check if this enables exam access
            if fee_payment.fee_structure.exam_fee > 0:
                messages.info(request, 
                    'Exam access has been enabled for the student. '
                    'They can now take CBT exams.'
                )
            
            return redirect('store:fee_payment_history')
        else:
            payment.mark_as_failed('Payment verification failed')
            messages.error(request, 'Payment verification failed.')
            return redirect('store:fee_payment_view')
            
    except Exception as e:
        logger.error(f"Fee payment verification error: {str(e)}")
        messages.error(request, 'Payment verification error.')
        return redirect('store:fee_payment_view')


@login_required
def fee_payment_history(request):
    """Fee payment history"""
    fee_payments = FeePayment.objects.none()
    
    if request.user.role == 'parent':
        try:
            parent = request.user.parent_profile
            student_ids = parent.students.values_list('id', flat=True)
            fee_payments = FeePayment.objects.filter(
                student_id__in=student_ids
            ).order_by('-payment_date')
        except Parent.DoesNotExist:
            pass
    elif request.user.role == 'student':
        try:
            student = request.user.student
            fee_payments = FeePayment.objects.filter(
                student=student
            ).order_by('-payment_date')
        except Student.DoesNotExist:
            pass
    elif is_admin(request.user):
        fee_payments = FeePayment.objects.all().order_by('-payment_date')
    
    # Pagination
    paginator = Paginator(fee_payments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'fee_payments': page_obj,
        'page_obj': page_obj
    }
    return render(request, 'store/fees/history.html', context)


@login_required
def fee_receipt(request, receipt_number):
    """Generate fee receipt PDF"""
    fee_payment = get_object_or_404(FeePayment, receipt_number=receipt_number)
    
    # Check permission
    if request.user.role == 'parent':
        parent = request.user.parent_profile
        if not parent.students.filter(id=fee_payment.student.id).exists():
            messages.error(request, 'Access denied.')
            return redirect('store:fee_payment_history')
    elif request.user.role == 'student':
        if fee_payment.student.user != request.user:
            messages.error(request, 'Access denied.')
            return redirect('store:fee_payment_history')
    
    context = {
        'fee_payment': fee_payment,
        'student': fee_payment.student,
        'fee_structure': fee_payment.fee_structure,
        'payment': fee_payment.payment_record
    }
    return render(request, 'store/fees/receipt.html', context)


# ==================== DASHBOARD VIEWS ====================

@login_required
def dashboard(request):
    """User dashboard"""
    context = {}
    
    if request.user.role == 'parent':
        try:
            parent = request.user.parent_profile
            students = parent.students.all()
            
            # Get recent orders
            recent_orders = Order.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]
            
            # Get fee payments
            recent_fee_payments = FeePayment.objects.filter(
                student__in=students
            ).order_by('-payment_date')[:5]
            
            # Get total spending
            total_spent = Order.objects.filter(
                user=request.user,
                payment_status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            # Get unpaid fees
            unpaid_fees = []
            for student in students:
                unpaid_fees.extend(student.get_unpaid_fees())
            
            context.update({
                'parent': parent,
                'students': students,
                'recent_orders': recent_orders,
                'recent_fee_payments': recent_fee_payments,
                'total_spent': total_spent,
                'unpaid_fees': unpaid_fees,
                'total_unpaid': sum(fee['balance'] for fee in unpaid_fees) if unpaid_fees else 0
            })
            
        except Parent.DoesNotExist:
            pass
            
    elif request.user.role == 'student':
        try:
            student = request.user.student
            
            # Get recent orders
            recent_orders = Order.objects.filter(
                student=student
            ).order_by('-created_at')[:5]
            
            # Get fee payments
            recent_fee_payments = FeePayment.objects.filter(
                student=student
            ).order_by('-payment_date')[:5]
            
            # Get unpaid fees
            unpaid_fees = student.get_unpaid_fees()
            
            context.update({
                'student': student,
                'recent_orders': recent_orders,
                'recent_fee_payments': recent_fee_payments,
                'unpaid_fees': unpaid_fees,
                'total_unpaid': sum(fee['balance'] for fee in unpaid_fees) if unpaid_fees else 0
            })
            
        except Student.DoesNotExist:
            pass
    
    elif is_admin(request.user):
        # Admin dashboard
        today = timezone.now().date()
        
        # Sales stats
        today_sales = Order.objects.filter(
            payment_status='completed',
            created_at__date=today
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_sales = Order.objects.filter(
            payment_status='completed',
            created_at__month=today.month,
            created_at__year=today.year
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        
        # Fee collection
        fee_collection = FeePayment.objects.filter(
            is_verified=True,
            payment_date__month=today.month,
            payment_date__year=today.year
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        # Low stock products
        low_stock_products = Product.objects.filter(
            stock_quantity__lte=F('low_stock_threshold')
        )[:5]
        
        # Recent orders
        recent_orders = Order.objects.all().order_by('-created_at')[:5]
        
        context.update({
            'today_sales': today_sales,
            'monthly_sales': monthly_sales,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'fee_collection': fee_collection,
            'low_stock_products': low_stock_products,
            'recent_orders': recent_orders
        })
    
    return render(request, 'store/dashboard/dashboard.html', context)


# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard"""
    today = timezone.now().date()
    
    # Sales analytics
    sales_data = Order.objects.filter(
        payment_status='completed',
        created_at__date__gte=today - timedelta(days=30)
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')
    
    # Top products
    top_products = Product.objects.annotate(
        total_sales=Sum('order_items__quantity')
    ).filter(
        total_sales__gt=0
    ).order_by('-total_sales')[:10]
    
    # Fee collection by class
    fee_collection = FeePayment.objects.filter(
        is_verified=True,
        payment_date__month=today.month
    ).values(
        'student__current_class'
    ).annotate(
        total=Sum('amount_paid'),
        count=Count('id')
    ).order_by('student__current_class')
    
    context = {
        'sales_data': list(sales_data),
        'top_products': top_products,
        'fee_collection': fee_collection,
        'total_students': Student.objects.count(),
        'total_parents': Parent.objects.count(),
        'total_products': Product.objects.count(),
        'active_orders': Order.objects.filter(status='processing').count()
    }
    return render(request, 'store/admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_products(request):
    """Admin product management"""
    products = Product.objects.all().order_by('-created_at')
    
    # Search and filter
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    elif status_filter == 'low_stock':
        products = products.filter(stock_quantity__lte=F('low_stock_threshold'))
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter
    }
    return render(request, 'store/admin/products/list.html', context)


@login_required
@user_passes_test(is_admin)
def admin_product_create(request):
    """Create new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('store:admin_products')
    else:
        form = ProductForm()
    
    context = {'form': form, 'title': 'Create Product'}
    return render(request, 'store/admin/products/form.html', context)


@login_required
@user_passes_test(is_admin)
def admin_product_edit(request, product_id):
    """Edit product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('store:admin_products')
    else:
        form = ProductForm(instance=product)
    
    context = {'form': form, 'title': 'Edit Product', 'product': product}
    return render(request, 'store/admin/products/form.html', context)


@login_required
@user_passes_test(is_admin)
def admin_orders(request):
    """Admin order management"""
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    payment_filter = request.GET.get('payment_status', '')
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'date_from': date_from,
        'date_to': date_to
    }
    return render(request, 'store/admin/orders/list.html', context)


@login_required
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    """Admin order detail"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Order #{order.order_number} updated successfully.')
            return redirect('store:admin_order_detail', order_id=order.id)
    else:
        form = OrderStatusUpdateForm(instance=order)
    
    context = {
        'order': order,
        'form': form,
        'items': order.items.all(),
        'payment': order.payments.first()
    }
    return render(request, 'store/admin/orders/detail.html', context)


@login_required
@user_passes_test(is_admin)
def admin_fee_management(request):
    """Fee structure management"""
    fee_structures = FeeStructure.objects.all().order_by('-academic_year', 'class_level', 'term')
    
    if request.method == 'POST':
        # Handle bulk fee payment
        form = BulkFeePaymentForm(request.POST)
        if form.is_valid():
            # Process bulk fee payment
            pass
    else:
        form = BulkFeePaymentForm()
    
    context = {
        'fee_structures': fee_structures,
        'form': form
    }
    return render(request, 'store/admin/fees/management.html', context)


@login_required
@user_passes_test(is_admin)
def admin_sales_analytics(request):
    """Sales analytics dashboard"""
    # Date range
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).date())
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # Sales data
    sales_data = Order.objects.filter(
        payment_status='completed',
        created_at__date__range=[date_from, date_to]
    ).annotate(
        period=TruncDay('created_at')
    ).values('period').annotate(
        total_sales=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('period')
    
    # Top products
    top_products = Product.objects.filter(
        order_items__order__payment_status='completed',
        order_items__order__created_at__date__range=[date_from, date_to]
    ).annotate(
        quantity_sold=Sum('order_items__quantity'),
        revenue=Sum(F('order_items__quantity') * F('order_items__price'), output_field=DecimalField())
    ).order_by('-revenue')[:10]
    
    # Sales by category
    sales_by_category = Category.objects.filter(
        products__order_items__order__payment_status='completed',
        products__order_items__order__created_at__date__range=[date_from, date_to]
    ).annotate(
        revenue=Sum(F('products__order_items__quantity') * F('products__order_items__price'), output_field=DecimalField())
    ).values('name', 'revenue').order_by('-revenue')
    
    context = {
        'sales_data': list(sales_data),
        'top_products': top_products,
        'sales_by_category': sales_by_category,
        'date_from': date_from,
        'date_to': date_to,
        'total_sales': sum(item['total_sales'] or 0 for item in sales_data),
        'total_orders': sum(item['order_count'] or 0 for item in sales_data)
    }
    return render(request, 'store/admin/analytics/sales.html', context)


# ==================== STUDENT PICKUP VIEWS ====================

@login_required
def pickup_dashboard(request):
    """Student pickup dashboard"""
    if request.user.role not in ['parent', 'admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')
    
    context = {}
    
    if request.user.role == 'parent':
        try:
            parent = request.user.parent_profile
            student_parents = StudentParent.objects.filter(parent=parent)
            
            context.update({
                'parent': parent,
                'student_parents': student_parents,
                'today_pickups': Attendance.objects.filter(
                    student__parents=parent,
                    date=timezone.now().date(),
                    status='present'
                ).select_related('student')
            })
            
        except Parent.DoesNotExist:
            pass
    
    elif is_admin(request.user) or request.user.role == 'staff':
        # Today's pickups
        today_pickups = Attendance.objects.filter(
            date=timezone.now().date(),
            status='present'
        ).select_related('student')
        
        # Parents with pickup authorization
        parents = Parent.objects.filter(
            studentparent__can_pickup=True
        ).distinct()
        
        context.update({
            'today_pickups': today_pickups,
            'parents': parents
        })
    
    return render(request, 'store/pickup/dashboard.html', context)


@login_required
@require_POST
def generate_pickup_code(request, student_parent_id):
    """Generate pickup code for student"""
    student_parent = get_object_or_404(StudentParent, id=student_parent_id)
    
    # Check permission
    if request.user.role == 'parent' and student_parent.parent.user != request.user:
        messages.error(request, 'Access denied.')
        return redirect('store:pickup_dashboard')
    
    code = student_parent.generate_pickup_code()
    
    return JsonResponse({
        'success': True,
        'code': code,
        'message': 'Pickup code generated successfully.'
    })


@login_required
def verify_pickup_code(request):
    """Verify pickup code (for staff/admin)"""
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        
        try:
            student_parent = StudentParent.objects.get(pickup_code=code)
            student = student_parent.student
            
            # Mark student as picked up
            attendance, created = Attendance.objects.get_or_create(
                student=student,
                date=timezone.now().date(),
                defaults={
                    'status': 'present',
                    'check_out': timezone.now().time()
                }
            )
            
            if not created:
                attendance.check_out = timezone.now().time()
                attendance.save()
            
            # Clear pickup code
            student_parent.pickup_code = ''
            student_parent.save()
            
            messages.success(request, 
                f'Pickup verified for {student.get_full_name()}. '
                f'Parent: {student_parent.parent.user.get_full_name()}'
            )
            
            return redirect('store:pickup_dashboard')
            
        except StudentParent.DoesNotExist:
            messages.error(request, 'Invalid pickup code.')
    
    return render(request, 'store/pickup/verify.html')


# ==================== CBT EXAM INTEGRATION VIEWS ====================

@login_required
def exam_access_view(request):
    """Check exam access based on fee payments"""
    if request.user.role not in ['parent', 'student']:
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')
    
    accessible_exams = []
    pending_exams = []
    
    if request.user.role == 'parent':
        try:
            parent = request.user.parent_profile
            for student in parent.students.all():
                # Check fee payments with exam fee
                fee_payments = FeePayment.objects.filter(
                    student=student,
                    fee_structure__exam_fee__gt=0,
                    is_verified=True
                )
                
                for payment in fee_payments:
                    accessible_exams.append({
                        'student': student,
                        'fee_payment': payment,
                        'subject': payment.fee_structure.name,
                        'term': payment.fee_structure.get_term_display(),
                        'academic_year': payment.fee_structure.academic_year
                    })
                
                # Check pending payments
                unpaid_exam_fees = FeeStructure.objects.filter(
                    class_level=student.class_level,
                    exam_fee__gt=0,
                    is_active=True
                ).exclude(
                    payments__student=student,
                    payments__is_verified=True
                )
                
                for fee in unpaid_exam_fees:
                    pending_exams.append({
                        'student': student,
                        'fee_structure': fee,
                        'amount': fee.exam_fee
                    })
                    
        except Parent.DoesNotExist:
            pass
    
    elif request.user.role == 'student':
        try:
            student = request.user.student
            
            # Get accessible exams
            fee_payments = FeePayment.objects.filter(
                student=student,
                fee_structure__exam_fee__gt=0,
                is_verified=True
            )
            
            for payment in fee_payments:
                accessible_exams.append({
                    'student': student,
                    'fee_payment': payment,
                    'subject': payment.fee_structure.name,
                    'term': payment.fee_structure.get_term_display(),
                    'academic_year': payment.fee_structure.academic_year
                })
            
            # Check pending payments
            unpaid_exam_fees = FeeStructure.objects.filter(
                class_level=student.class_level,
                exam_fee__gt=0,
                is_active=True
            ).exclude(
                payments__student=student,
                payments__is_verified=True
            )
            
            for fee in unpaid_exam_fees:
                pending_exams.append({
                    'student': student,
                    'fee_structure': fee,
                    'amount': fee.exam_fee
                })
                
        except Student.DoesNotExist:
            pass
    
    context = {
        'accessible_exams': accessible_exams,
        'pending_exams': pending_exams
    }
    return render(request, 'store/exams/access.html', context)


@login_required
def exam_payment_verification(request):
    """Verify exam payment before granting access"""
    if request.method == 'POST':
        form = ExamPaymentVerificationForm(request.POST)
        if form.is_valid():
            payment = form.cleaned_data['payment']
            student = form.cleaned_data['student']
            fee_payment = form.cleaned_data['fee_payment']
            
            # Grant exam access
            messages.success(request, 
                f'Exam access granted for {student.get_full_name()}. '
                f'Payment reference: {payment.reference}'
            )
            
            # You would typically create an ExamAccess record here
            # ExamAccess.objects.create(
            #     student=student,
            #     fee_payment=fee_payment,
            #     granted_by=request.user,
            #     expires_at=timezone.now() + timedelta(days=30)
            # )
            
            return redirect('store:exam_access_view')
    else:
        form = ExamPaymentVerificationForm()
    
    context = {'form': form}
    return render(request, 'store/exams/verify_payment.html', context)


##################### AJAX VIEWS ################################


@login_required
def ajax_product_stock(request, product_id):
    """Check product stock (AJAX)"""
    product = get_object_or_404(Product, id=product_id)
    
    return JsonResponse({
        'stock': product.stock_quantity,
        'in_stock': product.in_stock,
        'is_low_stock': product.is_low_stock
    })


@csrf_exempt
def paystack_webhook(request):
    """Paystack webhook for payment notifications"""
    if request.method != 'POST':
        return HttpResponse(status=400)
    
    try:
        # Verify Paystack signature
        paystack_secret = settings.PAYSTACK_SECRET_KEY
        signature = request.headers.get('X-Paystack-Signature', '')
        
        # Validate signature (you should implement proper validation)
        # For now, we'll trust the webhook
        
        payload = json.loads(request.body)
        event = payload.get('event', '')
        data = payload.get('data', {})
        
        if event == 'charge.success':
            reference = data.get('reference', '')
            
            try:
                payment = Payment.objects.get(reference=reference)
                payment.mark_as_completed(data)
                
                logger.info(f"Payment {reference} completed via webhook")
                
            except Payment.DoesNotExist:
                logger.error(f"Payment not found: {reference}")
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(status=500)


# ==================== CATEGORY VIEW ====================

class CategoryDetailView(DetailView):
    """Category detail page"""
    model = Category
    template_name = 'store/categories/detail.html'
    context_object_name = 'category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        context['products'] = Product.objects.filter(
            category=category,
            is_active=True
        )
        context['subcategories'] = category.children.filter(is_active=True)
        return context


# ==================== ORDER RECEIPT ====================

@login_required
def order_receipt(request, order_id):
    """Generate order receipt PDF"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'items': order.items.all(),
        'payment': order.payments.first(),
        'school_name': settings.SCHOOL_NAME,
        'school_address': settings.SCHOOL_ADDRESS,
        'school_phone': settings.SCHOOL_PHONE
    }
    
    # For PDF generation (you'd use a library like ReportLab or WeasyPrint)
    # return render_to_pdf('store/orders/receipt_pdf.html', context)
    
    # For now, return HTML
    return render(request, 'store/orders/receipt.html', context)


# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(is_admin)
def admin_product_delete(request, product_id):
    """Delete product (soft delete)"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{product.name}" has been deactivated.')
        return redirect('store:admin_products')
    
    context = {'product': product}
    return render(request, 'store/admin/products/delete.html', context)


@login_required
@user_passes_test(is_admin)
def admin_fee_create(request):
    """Create new fee structure"""
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            fee = form.save()
            messages.success(request, f'Fee structure "{fee.name}" created successfully.')
            return redirect('store:admin_fee_management')
    else:
        form = FeeStructureForm()
    
    context = {'form': form, 'title': 'Create Fee Structure'}
    return render(request, 'store/admin/fees/form.html', context)


@login_required
@user_passes_test(is_admin)
def admin_fee_edit(request, fee_id):
    """Edit fee structure"""
    fee = get_object_or_404(FeeStructure, id=fee_id)
    
    if request.method == 'POST':
        form = FeeStructureForm(request.POST, instance=fee)
        if form.is_valid():
            form.save()
            messages.success(request, f'Fee structure "{fee.name}" updated successfully.')
            return redirect('store:admin_fee_management')
    else:
        form = FeeStructureForm(instance=fee)
    
    context = {'form': form, 'title': 'Edit Fee Structure', 'fee': fee}
    return render(request, 'store/admin/fees/form.html', context)


@login_required
@user_passes_test(is_admin)
def admin_fee_analytics(request):
    """Fee collection analytics"""
    # Date range
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).date())
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # Fee collection data
    fee_data = FeePayment.objects.filter(
        is_verified=True,
        payment_date__date__range=[date_from, date_to]
    ).annotate(
        period=TruncDay('payment_date')
    ).values('period').annotate(
        total_collected=Sum('amount_paid'),
        payment_count=Count('id')
    ).order_by('period')
    
    # Collection by class
    collection_by_class = FeePayment.objects.filter(
        is_verified=True,
        payment_date__date__range=[date_from, date_to]
    ).values(
        'student__current_class'
    ).annotate(
        total=Sum('amount_paid'),
        count=Count('id')
    ).order_by('-total')
    
    # Collection by term
    collection_by_term = FeePayment.objects.filter(
        is_verified=True,
        payment_date__date__range=[date_from, date_to]
    ).values(
        'fee_structure__term'
    ).annotate(
        total=Sum('amount_paid'),
        count=Count('id')
    )
    
    context = {
        'fee_data': list(fee_data),
        'collection_by_class': collection_by_class,
        'collection_by_term': collection_by_term,
        'date_from': date_from,
        'date_to': date_to,
        'total_collected': sum(item['total_collected'] or 0 for item in fee_data),
        'total_payments': sum(item['payment_count'] or 0 for item in fee_data)
    }
    return render(request, 'store/admin/analytics/fees.html', context)


@login_required
@user_passes_test(is_admin)
def admin_user_management(request):
    """User management"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter
    }
    return render(request, 'store/admin/users/list.html', context)


@login_required
@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    """User detail view"""
    user = get_object_or_404(User, id=user_id)
    
    # Get user's orders
    orders = Order.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get fee payments if applicable
    fee_payments = None
    if user.role == 'parent':
        try:
            parent = user.parent_profile
            student_ids = parent.students.values_list('id', flat=True)
            fee_payments = FeePayment.objects.filter(
                student_id__in=student_ids
            ).order_by('-payment_date')[:10]
        except Parent.DoesNotExist:
            pass
    elif user.role == 'student':
        try:
            student = user.student
            fee_payments = FeePayment.objects.filter(
                student=student
            ).order_by('-payment_date')[:10]
        except Student.DoesNotExist:
            pass
    
    context = {
        'profile_user': user,
        'orders': orders,
        'fee_payments': fee_payments,
        'student': getattr(user, 'student', None),
        'parent': getattr(user, 'parent_profile', None),
        'teacher': getattr(user, 'teacher_profile', None),
        'staff': getattr(user, 'staff_profile', None)
    }
    return render(request, 'store/admin/users/detail.html', context)



# ==================== AJAX VIEWS ====================

@login_required
def ajax_cart_summary(request):
    """Get cart summary (AJAX)"""
    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    
    if cart:
        data = {
            'item_count': cart.total_items,
            'total_amount': str(cart.total_amount),
            'items': list(cart.items.values(
                'id', 'product__name', 'quantity', 'product__price'
            ))
        }
    else:
        data = {
            'item_count': 0,
            'total_amount': '0.00',
            'items': []
        }
    
    return JsonResponse(data)


# ==================== ADDITIONAL VIEWS ====================

@login_required
@require_POST
def clear_cart(request):
    """Clear entire cart"""
    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    if cart:
        cart.clear()
        return JsonResponse({'success': True, 'message': 'Cart cleared successfully.'})
    return JsonResponse({'success': False, 'message': 'Cart not found.'})

@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancel order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.can_cancel:
        order.status = 'cancelled'
        order.save()
        
        # Process refund if payment was made
        if order.payment_status == 'completed':
            payment = order.payments.first()
            if payment:
                payment.process_refund(reason='Order cancelled by customer')
        
        messages.success(request, f'Order #{order.order_number} has been cancelled.')
        return redirect('store:order_detail', order_id=order.id)
    else:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('store:order_detail', order_id=order.id)


# ==================== ERROR VIEWS ====================

def handler404(request, exception):
    """Custom 404 page"""
    return render(request, 'store/errors/404.html', status=404)

def handler500(request):
    """Custom 500 page"""
    return render(request, 'store/errors/500.html', status=500)

def handler403(request, exception):
    """Custom 403 page"""
    return render(request, 'store/errors/403.html', status=403)

def handler400(request, exception):
    """Custom 400 page"""
    return render(request, 'store/errors/400.html', status=400)
