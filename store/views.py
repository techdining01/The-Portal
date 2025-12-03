
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from .models import Product, Order,PaymentRecord
import json, datetime, requests
from users.models import User
from django.utils import timezone
import secrets
from django.conf import settings

from django.contrib.admin.views.decorators import staff_member_required
from django.db import models




from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db import transaction
from django.views import View
from django.utils.decorators import method_decorator
from django.conf import settings
from django.urls import reverse
import json
import uuid
from decimal import Decimal
from datetime import datetime
from paystackapi.paystack import Paystack
from paystackapi.transaction import Transaction
import logging
from datetime import timedelta
from .models import Product, Category, Cart, CartItem, Order, OrderItem, PaymentRecord
from django.db.models import Sum, Avg, F, Q 



logger = logging.getLogger(__name__)

# Initialize Paystack
paystack = Paystack(secret_key=settings.PAYSTACK_TEST_SECRET_KEY)

# ====================== PRODUCT VIEWS ======================
def product_list(request):
    """Public product listing - accessible to all"""
    categories = Category.objects.all()
    category_id = request.GET.get('category')
    
    products = Product.objects.filter(is_active=True)
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_id
    })

def product_detail(request, pk):
    """Public product detail - accessible to all"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=pk)[:4]
    
    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'is_authenticated': request.user.is_authenticated
    })

# ====================== CART VIEWS ======================
@login_required
def get_or_create_cart(request):
    """Get or create cart for user"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    return cart

@login_required
def cart_view(request):
    """View cart contents"""
    cart = get_or_create_cart(request)
    
    # Calculate totals
    cart_items = cart.items.select_related('product').all()
    cart_total = sum(item.total_price for item in cart_items)
    
    return render(request, 'store/cart.html', {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'item_count': len(cart_items)
    })


@require_POST
@login_required
def add_to_cart_view(request, product_id):
    """Add item to cart with student selection"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Check stock
        if product.stock < 1:
            return JsonResponse({
                'success': False,
                'message': f'Sorry, {product.name} is out of stock'
            }, status=400)
        
        # Get quantity
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            quantity = 1
        
        # Check if we have enough stock
        if quantity > product.stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.stock} units available in stock'
            }, status=400)
        
        # Get student ID if provided
        student_id = request.POST.get('student_id')
        student = None
        if student_id and student_id != '0':
            try:
                from users.models import User
                student = User.objects.get(id=int(student_id), role='student')
                # Verify parent owns this student
                if request.user.role == 'parent' and student not in request.user.children.all():
                    student = None
            except User.DoesNotExist:
                student = None
        
        # Get or create cart
        cart = get_or_create_cart(request)
        
        # Check if item already in cart for same student
        existing_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            student=student
        ).first()
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + quantity
            if new_quantity > product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Maximum stock reached. Only {product.stock - existing_item.quantity} more available'
                }, status=400)
            
            existing_item.quantity = new_quantity
            existing_item.save()
            cart_item = existing_item
        else:
            # Create new cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                student=student
            )
        
        # Get updated cart info
        cart_items = cart.items.all()
        cart_total = sum(item.total_price for item in cart_items)
        item_count = cart_items.count()
        
        # Update session for cart count
        request.session['cart_items_count'] = item_count
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_total': float(cart_total),
            'item_count': item_count,
            'item_id': cart_item.id,
            'item_quantity': cart_item.quantity,
            'student_name': student.get_full_name() if student else 'For yourself'
        })
        
    except Exception as e:
        print(f"Add to cart error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to add item to cart'
        }, status=500)


@require_POST
@login_required
def update_cart_view(request):
    """Update cart quantities - AJAX endpoint"""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id')
        quantity = int(data.get('quantity', 1))
        
        if quantity < 0:
            return JsonResponse({
                'success': False,
                'message': 'Quantity cannot be negative'
            }, status=400)
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        
        if quantity == 0:
            # Remove item
            product_name = cart_item.product.name
            cart_item.delete()
            message = f'{product_name} removed from cart'
        else:
            # Check stock
            if quantity > cart_item.product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {cart_item.product.stock} units available in stock'
                }, status=400)
            
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart updated'
        
        # Get updated cart info
        cart = get_or_create_cart(request)
        cart_items = cart.items.all()
        cart_total = sum(item.total_price for item in cart_items)
        item_count = cart_items.count()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_total': float(cart_total),
            'item_count': item_count,
            'item_quantity': quantity if quantity > 0 else 0,
            'item_total': float(cart_item.total_price) if quantity > 0 else 0
        })
        
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to update cart'
        }, status=500)
    

@require_POST
@login_required
def remove_from_cart_view(request, cart_item_id):
    """Remove item from cart - AJAX endpoint"""
    try:
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        
        # Get updated cart info
        cart = get_or_create_cart(request)
        cart_items = cart.items.all()
        cart_total = sum(item.total_price for item in cart_items)
        item_count = cart_items.count()
        
        return JsonResponse({
            'success': True,
            'message': f'{product_name} removed from cart',
            'cart_total': float(cart_total),
            'item_count': item_count
        })
        
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to remove item from cart'
        }, status=500)


@require_POST
@login_required
def clear_cart_view(request):
    """Clear entire cart"""
    try:
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart cleared successfully',
            'cart_total': 0,
            'item_count': 0
        })
        
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Failed to clear cart'
        }, status=500)


### FOR CART ONLY

@login_required
@require_POST
def update_cart_item(request):
    """Update cart item quantity via AJAX"""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id')
        quantity = int(data.get('quantity', 1))
        
        cart_item = CartItem.objects.get(id=cart_item_id, cart__user=request.user)
        cart_item.quantity = quantity
        cart_item.save()
        
        cart = cart_item.cart
        cart_total = cart.total_amount
        
        return JsonResponse({
            'success': True,
            'item_total': float(cart_item.total_price),
            'cart_total': float(cart_total),
            'items_count': cart.items_count,
            'message': 'Quantity updated successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def remove_cart_item(request, item_id):
    """Remove cart item via AJAX"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
        cart = cart_item.cart
        cart_item.delete()
        
        cart_total = cart.total_amount
        
        return JsonResponse({
            'success': True,
            'cart_total': float(cart_total),
            'items_count': cart.items_count,
            'message': 'Item removed from cart'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def clear_cart(request):
    """Clear entire cart via AJAX"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        
        return JsonResponse({
            'success': True,
            'cart_total': 0,
            'items_count': 0,
            'message': 'Cart cleared successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    

def increase_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.quantity += 1
    item.save()

    cart = item.cart
    return JsonResponse({
        "qty": item.quantity,
        "subtotal": float(item.subtotal()),
        "cart_total": float(cart.total())
    })


def decrease_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)

    if item.quantity > 1:
        item.quantity -= 1
        item.save()

    cart = item.cart
    return JsonResponse({
        "qty": item.quantity,
        "subtotal": float(item.subtotal()),
        "cart_total": float(cart.total())
    })

# ====================== CHECKOUT & PAYMENT VIEWS ======================
# @login_required
# def checkout_view(request):
#     """Checkout page - with student selection"""
#     cart = get_or_create_cart(request)
#     cart_items = cart.items.select_related('product').all()
    
#     if not cart_items:
#         messages.warning(request, 'Your cart is empty')
#         return redirect('store:cart_view')
    
#     # Calculate total
#     cart_total = sum(item.total_price for item in cart_items)
    
#     # Get students/wards for this user
#     students = []
    
#     # If user is a parent, get their children
#     if hasattr(request.user, 'parent_profile'):
#         students = request.user.children.all()
#     # If user is staff/admin, they might be buying for students
#     elif request.user.role in ['admin', 'superadmin', 'teacher']:
#         # Get all active students (or implement your own logic)
#         from users.models import User
#         students = User.objects.filter(role='student', is_active=True)[:10]
    
#     return render(request, 'store/checkout.html', {
#         'cart': cart,
#         'cart_items': cart_items,
#         'cart_total': cart_total,
#         'students': students,
#         'paystack_test_public_key': settings.PAYSTACK_TEST_PUBLIC_KEY,
#         'item_count': len(cart_items),
#     })

# @require_POST
# @login_required
# @transaction.atomic
# def create_order_view(request):
#     """Create order with student selection"""
#     try:
#         data = json.loads(request.body)
        
#         # Validate required fields
#         required_fields = ['customer_name', 'customer_email', 'customer_phone', 'shipping_address']
#         for field in required_fields:
#             if not data.get(field):
#                 return JsonResponse({
#                     'success': False,
#                     'message': f'{field.replace("_", " ").title()} is required'
#                 }, status=400)
        
#         cart = get_or_create_cart(request)
#         cart_items = cart.items.select_related('product').all()
        
#         if not cart_items:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Your cart is empty'
#             }, status=400)
        
#         # Check stock
#         for item in cart_items:
#             if item.quantity > item.product.stock:
#                 return JsonResponse({
#                     'success': False,
#                     'message': f'Not enough stock for {item.product.name}. Only {item.product.stock} available'
#                 }, status=400)
        
#         # Calculate total
#         total_amount = sum(item.total_price for item in cart_items)
        
#         # Create order
#         order = Order.objects.create(
#             user=request.user,
#             total_amount=total_amount,
#             customer_name=data['customer_name'],
#             customer_email=data['customer_email'],
#             customer_phone=data['customer_phone'],
#             shipping_address=data['shipping_address'],
#             shipping_notes=data.get('shipping_notes', ''),
#             payment_reference=f"PAY_{uuid.uuid4().hex[:10].upper()}"
#         )
        
#         # Get student ID if provided
#         student_id = data.get('student_id')
#         student = None
#         if student_id and student_id != '0':
#             try:
#                 from users.models import User
#                 student = User.objects.get(id=int(student_id), role='student')
#             except User.DoesNotExist:
#                 student = None
        
#         # Create order items with student reference
#         order_items = []
#         for cart_item in cart_items:
#             order_items.append(OrderItem(
#                 order=order,
#                 product=cart_item.product,
#                 quantity=cart_item.quantity,
#                 price=cart_item.product.price,
#                 student=student  # Assign student to order item
#             ))
        
#         OrderItem.objects.bulk_create(order_items)
        
#         # Update cart items with student for record
#         if student:
#             cart_items.update(student=student)
        
#         # Create payment record
#         payment = PaymentRecord.objects.create(
#             order=order,
#             user=request.user,
#             reference=order.payment_reference,
#             gateway_reference='',
#             amount=total_amount,
#             payment_method=data.get('payment_method', 'card')
#         )
        
#         # Initialize Paystack payment
#         try:
#             # Convert to kobo
#             amount_in_kobo = int(total_amount * 100)
            
#             response = Transaction.initialize(
#                 amount=amount_in_kobo,
#                 email=data['customer_email'],
#                 reference=order.payment_reference,
#                 callback_url=request.build_absolute_uri(
#                     reverse('store:payment_verify', kwargs={'reference': order.payment_reference})
#                 ),
#                 metadata={
#                     'student_id': student_id,
#                     'parent_id': request.user.id
#                 }
#             )
            
#             if response['status']:
#                 return JsonResponse({
#                     'success': True,
#                     'authorization_url': response['data']['authorization_url'],
#                     'access_code': response['data']['access_code'],
#                     'reference': order.payment_reference,
#                     'order_number': order.order_number
#                 })
#             else:
#                 order.delete()
#                 return JsonResponse({
#                     'success': False,
#                     'message': 'Payment initialization failed'
#                 }, status=500)
                
#         except Exception as e:
#             order.delete()
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Payment service error'
#             }, status=500)
            
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': 'Failed to create order'
#         }, status=500)


# @login_required
# def payment_verify_view(request, reference):
#     """Verify payment callback from Paystack"""
#     try:
#         # Verify payment with Paystack
#         verify_response = Transaction.verify(reference)
        
#         if verify_response['status'] and verify_response['data']['status'] == 'success':
#             # Get payment record
#             payment = PaymentRecord.objects.get(reference=reference)
#             order = payment.order
            
#             # Verify user owns this order
#             if order.user != request.user:
#                 messages.error(request, 'Unauthorized access')
#                 return redirect('store:product_list')
            
#             # Mark payment as successful
#             payment.mark_as_successful(verify_response['data'])
            
#             # Update stock
#             update_stock_after_payment(order)
            
#             # Clear cart
#             cart = get_or_create_cart(request)
#             cart.items.all().delete()
            
#             messages.success(request, f'Payment successful! Order #{order.order_number} has been placed.')
#             return redirect('store:order_detail', order_number=order.order_number)
            
#         else:
#             messages.error(request, 'Payment verification failed')
#             return redirect('store:checkout')
            
#     except PaymentRecord.DoesNotExist:
#         messages.error(request, 'Payment record not found')
#         return redirect('store:product_list')
#     except Exception as e:
#         logger.error(f"Payment verification error: {e}")
#         messages.error(request, 'Payment verification error')
#         return redirect('store:checkout')


# store/views.py
from django.conf import settings
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import uuid
from decimal import Decimal

# store/views.py
@login_required
def checkout(request):
    """Checkout page"""
    try:
        cart = Cart.get_cart_for_user(request.user)
        cart_items = cart.items.select_related('product', 'product__category', 'student').all()
        
        if not cart_items:
            messages.warning(request, "Your cart is empty")
            return redirect('store:view_cart')
        
        # Get students for this user (if parent) - FIXED
        # Method 1: If you have a parent-child relationship
        students = []
        
        # Check if user has role 'parent' or 'guardian'
        if hasattr(request.user, 'role') and request.user.role in ['parent', 'guardian']:
            # Assuming you have a way to get linked students
            # This depends on your User model structure
            try:
                # Option A: If you have a foreign key from User to User for parent
                students = User.objects.filter(parent_namer=request.user, role='student', is_active=True)
            except:
                try:
                    # Option B: If you have a ParentProfile model
                    from users.models import Parent
                    parent_profile = Parent.objects.get(user=request.user)
                    students = parent_profile.students.all()
                except:
                    try:
                        # Option C: If you have a ManyToMany field
                        students = request.user.students.all()
                    except:
                        # Option D: Check for related name
                        students = None #User.objects.filter(teacher=request.user, role='student', is_active=True)
        
        # If no specific student relationship found, show empty list
        # User can still select "For Myself"
        
        # Calculate cart total
        cart_total = cart.total_amount
        
        context = {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'students': students,
            'cart_count': cart.items_count,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        }
        
        return render(request, 'store/checkout.html', context)
    except Exception as e:
        print(f"Error in checkout view: {str(e)}")  # Debug print
        messages.error(request, f"Error loading checkout: {str(e)}")
        return redirect('store:cart_view')
    

@login_required
@require_POST
def create_order(request):
    """Create order and generate Paystack reference"""
    try:
        data = json.loads(request.body)
        
        cart = Cart.get_cart_for_user(request.user)
        cart_items = cart.items.all()
        
        if not cart_items:
            return JsonResponse({
                'success': False,
                'message': 'Your cart is empty'
            })
        
        # Create order number
        order_number = f"BRP{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        
        # Create order
        order = Order.objects.create(
            order_number=order_number,
            user=request.user,
            total_amount=cart.total_amount,
            customer_name=data.get('customer_name', request.user.get_full_name()),
            customer_email=data.get('customer_email', request.user.email),
            customer_phone=data.get('customer_phone', ''),
            customer_address=data.get('shipping_address', ''),
            shipping_address=data.get('shipping_address', ''),
            payment_method='paystack',
            payment_gateway='paystack',
            payment_reference=f"PAY_{order_number}"
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                student=cart_item.student
            )
        
        # Generate Paystack reference
        paystack_ref = f"BRP_{uuid.uuid4().hex[:12].upper()}"
        
        # Save payment record
        payment = PaymentRecord.objects.create(
            order=order,
            user=request.user,
            reference=paystack_ref,
            gateway_reference='',
            amount=order.total_amount,
            payment_status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'reference': paystack_ref,
            'amount': float(order.total_amount),
            'customer_email': order.customer_email,
            'customer_name': order.customer_name,
            'message': 'Order created successfully'
        })
        
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error creating order: {str(e)}'
        })

@login_required
def payment_verify(request, reference):
    """Verify Paystack payment"""
    try:
        # Get payment record
        payment = PaymentRecord.objects.get(reference=reference, user=request.user)
        order = payment.order
        
        # In production, you would verify with Paystack API
        # For now, we'll simulate successful payment
        context = {
            'payment': payment,
            'order': order,
            'success': True,
            'reference': reference,
        }
        
        return render(request, 'store/payment_verify.html', context)
        
    except PaymentRecord.DoesNotExist:
        messages.error(request, "Payment not found")
        return redirect('store:view_cart')
    

@csrf_exempt
def paystack_webhook(request):
    """Paystack webhook for payment verification"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = data.get('event')
            
            if event == 'charge.success':
                reference = data.get('data', {}).get('reference')
                
                try:
                    payment = PaymentRecord.objects.get(reference=reference)
                    
                    # Update payment status
                    payment.payment_status = 'success'
                    payment.gateway_response = data
                    payment.paid_at = timezone.now()
                    payment.amount_paid = Decimal(str(data.get('data', {}).get('amount', 0))) / 100
                    payment.save()
                    
                    # Update order status
                    order = payment.order
                    order.payment_status = 'completed'
                    order.status = 'paid'
                    order.save()
                    
                    # Clear cart
                    cart = Cart.get_cart_for_user(order.user)
                    cart.items.all().delete()
                    
                    print(f"Payment {reference} verified successfully")
                    
                except PaymentRecord.DoesNotExist:
                    print(f"Payment {reference} not found")
                    
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def update_stock_after_payment(order):
    """Update product stock after successful payment"""
    try:
        for order_item in order.items.all():
            product = order_item.product
            product.stock -= order_item.quantity
            product.save()
        
        # Mark payment as stock updated
        payment = order.payment
        payment.update_stock_status(True)
        
    except Exception as e:
        logger.error(f"Stock update error: {e}")

@login_required
def order_detail_view(request, order_number):
    """View order details"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    return render(request, 'store/order_detail.html', {
        'order': order,
        'order_items': order.items.all(),
        'payment': getattr(order, 'payment', None)
    })

@login_required
def order_list_view(request):
    """List user's orders"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'store/order_list.html', {
        'orders': orders
    })

# ====================== AJAX HELPER VIEWS ======================
@require_GET
def get_cart_count_view(request):
    """Get cart item count - AJAX endpoint"""
    if request.user.is_authenticated:
        try:
            cart = get_or_create_cart(request)
            count = cart.items.count()
            total = sum(item.total_price for item in cart.items.all())
        except:
            count = 0
            total = 0
    else:
        count = 0
        total = 0
    
    return JsonResponse({
        'count': count,
        'total': float(total) if total else 0
    })



# ====================== ADMIN VIEWS ======================
# store/views/admin_views.py (or store/views.py)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
import json
from decimal import Decimal
from django.http import JsonResponse
from django.core.paginator import Paginator

# Import settings and get_user_model
from django.conf import settings
from django.contrib.auth import get_user_model

# Import your models
from store.models import (
    Product, Category, Order, OrderItem, 
    PaymentRecord, ActivityLog
)

# Get the custom User model
User = get_user_model()

# Check if user is admin
def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with analytics"""
    # Date range filter
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Calculate metrics
    total_revenue = PaymentRecord.objects.filter(
        payment_status='success',
        paid_at__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_orders = Order.objects.filter(
        created_at__range=[start_date, end_date]
    ).count()
    
    total_customers = User.objects.filter(
        date_joined__range=[start_date, end_date]
    ).count()
    
    avg_order_value = Decimal('0')
    if total_orders > 0 and total_revenue:
        avg_order_value = total_revenue / total_orders
    
    # Sales data for chart
    sales_data = []
    dates = []
    
    # Generate last 7 days data
    for i in range(6, -1, -1):
        date = end_date - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        day_sales = PaymentRecord.objects.filter(
            payment_status='success',
            paid_at__range=[day_start, day_end]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        sales_data.append(float(day_sales))
        dates.append(date.strftime("%a"))
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    # Top products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum(F('orderitem__quantity') * F('orderitem__price'))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]
    
    # Order status counts
    pending_orders = Order.objects.filter(status='pending').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    
    # Low stock products (stock < 10)
    low_stock_products = Product.objects.filter(stock__lt=10, is_active=True).count()
    
    # New customers today
    today = timezone.now().date()
    new_customers_today = User.objects.filter(
        date_joined__date=today
    ).count()
    
    # Recent activity
    recent_activity = ActivityLog.objects.select_related('user').order_by('-created_at')[:5]
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'avg_order_value': avg_order_value,
        'sales_data': json.dumps(sales_data),
        'dates': json.dumps(dates),
        'recent_orders': recent_orders,
        'top_products': top_products,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'low_stock_products': low_stock_products,
        'new_customers_today': new_customers_today,
        'recent_activity': recent_activity,
        'days_filter': days,
    }
    
    return render(request, 'store/admin/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_products(request):
    """Product management page"""
    products = Product.objects.select_related('category').all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    elif status_filter == 'low_stock':
        products = products.filter(stock__lt=10, is_active=True)
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'products': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'page_obj': page_obj,
    }
    
    return render(request, 'store/admin/products.html', context)

@login_required
@user_passes_test(is_admin)
def add_product(request):
    """Add new product"""
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description')
            price = request.POST.get('price')
            category_id = request.POST.get('category')
            stock = request.POST.get('stock', 0)
            is_active = request.POST.get('is_active') == 'on'
            
            # Basic validation
            if not all([name, description, price, category_id]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('store:admin_products')
            
            # Create product
            product = Product(
                name=name,
                description=description,
                price=Decimal(price),
                category_id=category_id,
                stock=int(stock),
                is_active=is_active
            )
            
            # Handle image upload
            if 'image' in request.FILES:
                product.image = request.FILES['image']
            
            product.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='product',
                description=f'Added product: {product.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('store:admin_products')
            
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
    
    return render(request, 'store/admin/add_product.html', {'categories': categories})

@login_required
@user_passes_test(is_admin)
def edit_product(request, product_id):
    """Edit existing product"""
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name', product.name)
            product.description = request.POST.get('description', product.description)
            product.price = Decimal(request.POST.get('price', product.price))
            product.category_id = request.POST.get('category', product.category_id)
            product.stock = int(request.POST.get('stock', product.stock))
            product.is_active = request.POST.get('is_active') == 'on'
            
            # Handle image upload
            if 'image' in request.FILES:
                product.image = request.FILES['image']
            
            product.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='product',
                description=f'Updated product: {product.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('store:admin_products')
            
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    context = {
        'product': product,
        'categories': categories,
    }
    
    return render(request, 'store/admin/edit_product.html', context)

@login_required
@user_passes_test(is_admin)
def delete_product(request, product_id):
    """Delete product"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            product_name = product.name
            product.delete()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='product',
                description=f'Deleted product: {product_name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Product "{product_name}" deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')
    
    return redirect('store:admin_products')

@login_required
@user_passes_test(is_admin)
def toggle_product_status(request, product_id):
    """Toggle product active status"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            product.is_active = not product.is_active
            product.save()
            
            status = "activated" if product.is_active else "deactivated"
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='product',
                description=f'{status.title()} product: {product.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Product "{product.name}" {status} successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating product status: {str(e)}')
    
    return redirect('store:admin_products')

@login_required
@user_passes_test(is_admin)
def category_management(request):
    """Category management"""
    categories = Category.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            
            if name:
                category = Category.objects.create(
                    name=name,
                    description=description
                )
                
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type='product',
                    description=f'Added category: {category.name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Category "{category.name}" added successfully!')
        
        elif action == 'edit':
            category_id = request.POST.get('category_id')
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            
            if category_id and name:
                category = get_object_or_404(Category, id=category_id)
                category.name = name
                category.description = description
                category.save()
                
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type='product',
                    description=f'Updated category: {category.name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Category "{category.name}" updated successfully!')
        
        elif action == 'delete':
            category_id = request.POST.get('category_id')
            
            if category_id:
                category = get_object_or_404(Category, id=category_id)
                category_name = category.name
                
                # Check if category has products
                if category.product_set.exists():
                    messages.error(request, f'Cannot delete category "{category_name}" because it has products.')
                else:
                    category.delete()
                    
                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type='product',
                        description=f'Deleted category: {category_name}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    messages.success(request, f'Category "{category_name}" deleted successfully!')
        
        return redirect('store:category_management')
    
    return render(request, 'store/admin/categories.html', {'categories': categories})

@login_required
@user_passes_test(is_admin)
def sales_analytics(request):
    """Sales analytics with charts"""
    # Date range parameters
    period = request.GET.get('period', 'month')  # day, week, month, year
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    now = timezone.now()
    
    if start_date_str and end_date_str:
        try:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        except:
            start_date = now - timedelta(days=30)
            end_date = now
    else:
        # Default based on period
        if period == 'day':
            start_date = now - timedelta(days=1)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:  # month
            start_date = now - timedelta(days=30)
        end_date = now
    
    # Get successful payments in date range
    payments = PaymentRecord.objects.filter(
        payment_status='success',
        paid_at__range=[start_date, end_date]
    ).select_related('order', 'order__user')
    
    # Calculate metrics
    total_sales = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_orders = Order.objects.filter(
        created_at__range=[start_date, end_date]
    ).count()
    total_customers = payments.values('user').distinct().count()
    avg_order_value = total_sales / total_orders if total_orders > 0 else Decimal('0')
    
    # Sales by day for chart
    sales_by_day = []
    dates = []
    
    if period == 'day':
        # Hourly data for day view
        for hour in range(24):
            hour_start = start_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_sales = payments.filter(
                paid_at__range=[hour_start, hour_end]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            sales_by_day.append(float(hour_sales))
            dates.append(f'{hour:02d}:00')
    else:
        # Daily data for week/month/year
        current = start_date
        while current <= end_date:
            day_end = current.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            day_sales = payments.filter(
                paid_at__range=[current, day_end]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            sales_by_day.append(float(day_sales))
            
            if period == 'week':
                dates.append(current.strftime('%a'))
            elif period == 'month':
                dates.append(current.strftime('%b %d'))
            else:  # year
                dates.append(current.strftime('%b'))
            
            current = current + timedelta(days=1)
    
    # Top products by revenue
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum(F('orderitem__quantity') * F('orderitem__price'))
    ).filter(
        orderitem__order__created_at__range=[start_date, end_date]
    ).order_by('-total_revenue')[:10]
    
    # Sales by category
    sales_by_category = {}
    for product in Product.objects.filter(is_active=True):
        category_sales = OrderItem.objects.filter(
            product=product,
            order__created_at__range=[start_date, end_date]
        ).aggregate(total=Sum(F('quantity') * F('price')))['total'] or Decimal('0')
        
        if category_sales > 0:
            cat_name = product.category.name
            if cat_name in sales_by_category:
                sales_by_category[cat_name] += float(category_sales)
            else:
                sales_by_category[cat_name] = float(category_sales)
    
    # Payment methods distribution
    payment_methods = payments.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'avg_order_value': avg_order_value,
        'sales_data': json.dumps(sales_by_day),
        'dates': json.dumps(dates),
        'sales_by_category': json.dumps(list(sales_by_category.items())),
        'top_products': top_products,
        'payment_methods': payment_methods,
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'today': now.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'store/admin/sales_analytics.html', context)

@login_required
@user_passes_test(is_admin)
def order_management(request):
    """Order management page"""
    orders = Order.objects.select_related('user').all().order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    payment_filter = request.GET.get('payment_status', '')
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)
    
    search_query = request.GET.get('q', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_email__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )
    
    # Date filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(orders, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'store/admin/orders.html', context)

@login_required
@user_passes_test(is_admin)
def update_order_status(request, order_id):
    """Update order status"""
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            new_status = request.POST.get('status')
            notes = request.POST.get('notes', '')
            
            if new_status in dict(Order.STATUS_CHOICES):
                order.status = new_status
                order.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type='order',
                    description=f'Updated order #{order.order_number} status to {new_status}',
                    metadata={'order_id': order.id, 'new_status': new_status, 'notes': notes},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Order #{order.order_number} status updated to {new_status}')
            else:
                messages.error(request, 'Invalid status')
                
        except Exception as e:
            messages.error(request, f'Error updating order: {str(e)}')
    
    return redirect('store:order_management')

@login_required
@user_passes_test(is_admin)
def get_chart_data(request):
    """API endpoint for chart data"""
    chart_type = request.GET.get('type', 'sales')
    period = request.GET.get('period', 'week')
    
    now = timezone.now()
    
    if period == 'day':
        start_date = now - timedelta(days=1)
        interval = 'hour'
    elif period == 'week':
        start_date = now - timedelta(days=7)
        interval = 'day'
    elif period == 'month':
        start_date = now - timedelta(days=30)
        interval = 'day'
    else:  # year
        start_date = now - timedelta(days=365)
        interval = 'month'
    
    data = []
    labels = []
    
    if chart_type == 'sales':
        payments = PaymentRecord.objects.filter(
            payment_status='success',
            paid_at__range=[start_date, now]
        )
        
        if interval == 'hour':
            for hour in range(24):
                hour_start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                amount = payments.filter(
                    paid_at__range=[hour_start, hour_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                data.append(float(amount))
                labels.append(f'{hour:02d}:00')
                
        elif interval == 'day':
            for i in range(7):
                date = now - timedelta(days=i)
                day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                amount = payments.filter(
                    paid_at__range=[day_start, day_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                data.insert(0, float(amount))
                labels.insert(0, date.strftime('%a'))
                
        elif interval == 'month':
            for i in range(12):
                date = now - timedelta(days=30*i)
                month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
                
                amount = payments.filter(
                    paid_at__range=[month_start, month_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                data.insert(0, float(amount))
                labels.insert(0, date.strftime('%b'))
    
    return JsonResponse({
        'labels': labels,
        'data': data,
        'chart_type': chart_type,
        'period': period
    })


@login_required
def admin_order_detail_view(request, order_number):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    
    order = get_object_or_404(Order, order_number=order_number)
    
    return render(request, 'store/admin/order_detail.html', {
        'order': order,
        'order_items': order.items.all(),
        'payment': getattr(order, 'payment', None)
    })


# users/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count
from django.conf import settings
from django.contrib.auth import get_user_model
from store.models import Order, ActivityLog
from django.contrib.auth.hashers import make_password

# Get the custom User model
User = get_user_model()

def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin)
def user_list_view(request):
    """List all users"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search functionality
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
    if role_filter == 'admin':
        users = users.filter(is_superuser=True)
    elif role_filter == 'staff':
        users = users.filter(is_staff=True, is_superuser=False)
    elif role_filter == 'customer':
        users = users.filter(is_staff=False, is_superuser=False)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'store/admin/user_list.html', context)

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """Edit user details"""
    user_obj = get_object_or_404(User, id=user_id)
    
    # Get user stats
    order_count = Order.objects.filter(user=user_obj).count()
    total_spent = Order.objects.filter(
        user=user_obj,
        payment_status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Get recent activity
    recent_activity = ActivityLog.objects.filter(user=user_obj).order_by('-created_at')[:10]
    
    if request.method == 'POST':
        try:
            # Update basic info
            user_obj.first_name = request.POST.get('first_name', '')
            user_obj.last_name = request.POST.get('last_name', '')
            user_obj.email = request.POST.get('email', '')
            user_obj.is_active = request.POST.get('is_active') == 'on'
            
            # Check if email_verified field exists (for custom user model)
            if hasattr(user_obj, 'email_verified'):
                user_obj.email_verified = request.POST.get('email_verified') == 'on'
            
            # Update role
            role = request.POST.get('role', 'customer')
            if role == 'admin':
                user_obj.is_staff = True
                user_obj.is_superuser = True
            elif role == 'staff':
                user_obj.is_staff = True
                user_obj.is_superuser = False
            else:  # customer
                user_obj.is_staff = False
                user_obj.is_superuser = False
            
            # Update password if provided
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            if password1 and password2 and password1 == password2:
                user_obj.set_password(password1)
            
            user_obj.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='user',
                description=f'Updated user: {user_obj.get_full_name()}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'User "{user_obj.get_full_name()}" updated successfully!')
            return redirect('users:user_list')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'user_obj': user_obj,
        'order_count': order_count,
        'total_spent': total_spent,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'users/edit_user.html', context)

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete user"""
    if request.method == 'POST':
        try:
            user_obj = get_object_or_404(User, id=user_id)
            user_name = user_obj.get_full_name() or user_obj.username
            
            # Prevent deleting yourself
            if user_obj == request.user:
                messages.error(request, 'You cannot delete your own account!')
                return redirect('users:user_list')
            
            user_obj.delete()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                activity_type='user',
                description=f'Deleted user: {user_name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'User "{user_name}" deleted successfully!')
            
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('users:user_list')


#### User mmanagement ended

#############################################################################


@require_POST
@login_required
def update_order_status_view(request, order_number):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        order = get_object_or_404(Order, order_number=order_number)
        
        order.status = data.get('status', order.status)
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Order status updated',
            'status': order.get_status_display()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    
 #######################################################################
def sales_reports(request):
    # Get date parameters with proper validation
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    start_date = None
    end_date = None
    
    # Validate and parse dates
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Invalid start date format. Use YYYY-MM-DD.')
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Invalid end date format. Use YYYY-MM-DD.')
    
    # Set default dates if not provided
    if not start_date:
        start_date = datetime.now().date() - datetime.timedelta(days=30)  # Last 30 days
    
    if not end_date:
        end_date = datetime.now().date()
    
    # Ensure end_date is not before start_date
    if end_date < start_date:
        end_date = start_date
    
    # Your existing sales report logic here
    orders = Order.objects.filter(created_at__date__range=[start_date, end_date])
    
    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'orders': orders,
        # ... other context data
    }
    
    return render(request, 'store/sales_reports.html', context)


# store/views.py - Add these views
@login_required
def order_history_view(request):
    """Main order history page"""
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Get user's orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Apply filters
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Get status counts for filter
    status_counts = {
        'all': Order.objects.filter(user=request.user).count(),
        'pending': Order.objects.filter(user=request.user, status='pending').count(),
        'paid': Order.objects.filter(user=request.user, status='paid').count(),
        'delivered': Order.objects.filter(user=request.user, status='delivered').count(),
        'cancelled': Order.objects.filter(user=request.user, status='cancelled').count(),
    }
    
    # Format orders for template
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'date': order.formatted_date,
            'time': order.formatted_time,
            'total': order.total_amount,
            'status': order.display_status,
            'payment_status': order.display_payment_status,
            'item_count': order.items.count(),
            'items_list': order.items_list,
            'can_cancel': order.status in ['pending', 'paid'],
            'can_reorder': order.status in ['delivered', 'cancelled'],
        })
    
    return render(request, 'store/order_history.html', {
        'orders': orders_data,
        'status_counts': status_counts,
        'current_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_orders': status_counts['all'],
        'total_spent': sum(order.total_amount for order in orders),
    })

@login_required
def order_detail_history_view(request, order_number):
    """Order detail view for history"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Get order items with product details
    order_items = []
    for item in order.items.all():
        order_items.append({
            'id': item.id,
            'product_id': item.product.id,
            'name': item.product.name,
            'image': item.product.image_url,
            'quantity': item.quantity,
            'price': item.price,
            'subtotal': item.subtotal,
            'category': item.product.category.name,
        })
    
    # Get payment details if exists
    payment = None
    try:
        payment = PaymentRecord.objects.get(order=order)
    except PaymentRecord.DoesNotExist:
        pass
    
    return render(request, 'store/order_detail_history.html', {
        'order': order,
        'order_items': order_items,
        'payment': payment,
        'timeline': get_order_timeline(order),
    })


@require_POST
@login_required
def cancel_order_view(request, order_number):
    """Cancel an order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Check if order can be cancelled
    if order.status not in ['pending', 'paid']:
        return JsonResponse({
            'success': False,
            'message': f'Order cannot be cancelled in {order.get_status_display()} status'
        })
    
    # Update order status
    order.status = 'cancelled'
    order.save()
    
    # If payment was made, initiate refund
    try:
        payment = PaymentRecord.objects.get(order=order)
        if payment.is_successful:
            # Mark for refund (in real app, call Paystack refund API)
            payment.payment_status = 'refunded'
            payment.save()
    except PaymentRecord.DoesNotExist:
        pass
    
    messages.success(request, f'Order #{order_number} has been cancelled.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully',
            'status': order.get_status_display()
        })
    else:
        return redirect('order_detail_history', order_number=order_number)
    

@require_POST
@login_required
def reorder_view(request, order_number):
    """Reorder all items from a previous order"""
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        # Get user's cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Add all items from order to cart
        added_items = []
        skipped_items = []
        
        for order_item in order.items.all():
            # Check if product is still available
            if order_item.product.is_active and order_item.product.stock > 0:
                # Check if already in cart
                cart_item, item_created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=order_item.product,
                    defaults={'quantity': order_item.quantity}
                )
                
                if not item_created:
                    # Add to existing quantity
                    cart_item.quantity += order_item.quantity
                    cart_item.save()
                
                added_items.append(order_item.product.name)
            else:
                skipped_items.append(order_item.product.name)
        
        # Prepare messages
        messages_list = []
        if added_items:
            messages_list.append(f"Added {len(added_items)} items to cart")
        
        if skipped_items:
            messages_list.append(f"{len(skipped_items)} items unavailable")
        
        return JsonResponse({
            'success': True,
            'message': ' | '.join(messages_list),
            'added_count': len(added_items),
            'skipped_count': len(skipped_items),
            'cart_url': reverse('cart_view')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })

def get_order_timeline(order):
    """Get order timeline events"""
    timeline = []
    
    # Order placed
    timeline.append({
        'event': 'Order Placed',
        'date': order.created_at,
        'description': 'Your order has been received',
        'icon': 'fas fa-shopping-cart',
        'color': 'primary',
        'completed': True
    })
    
    # Payment processed
    if order.payment_status == 'completed':
        payment = PaymentRecord.objects.filter(order=order).first()
        if payment and payment.paid_at:
            timeline.append({
                'event': 'Payment Confirmed',
                'date': payment.paid_at,
                'description': f'Payment of ₦{order.total_amount:,.2f} confirmed',
                'icon': 'fas fa-credit-card',
                'color': 'success',
                'completed': True
            })
    
    # Status-based events
    status_events = {
        'paid': {'event': 'Order Processing', 'description': 'Preparing your order for shipment'},
        'shipped': {'event': 'Shipped', 'description': 'Your order is on the way'},
        'delivered': {'event': 'Delivered', 'description': 'Order delivered successfully'},
        'cancelled': {'event': 'Cancelled', 'description': 'Order has been cancelled'}
    }
    
    if order.status in status_events:
        event_data = status_events[order.status]
        timeline.append({
            'event': event_data['event'],
            'date': order.updated_at,
            'description': event_data['description'],
            'icon': 'fas fa-box',
            'color': 'info' if order.status != 'cancelled' else 'danger',
            'completed': True
        })
    
    # Sort by date
    timeline.sort(key=lambda x: x['date'])
    return timeline


@login_required
def test_paystack_view(request):
    """Test Paystack connection"""
    from paystackapi.transaction import Transaction
    
    try:
        # Test with a small amount (100 kobo = ₦1)
        response = Transaction.initialize(
            amount=100,  # 100 kobo = ₦1
            email=request.user.email,
            reference=f"TEST_{uuid.uuid4().hex[:8]}",
            callback_url=request.build_absolute_uri(reverse('product_list'))
        )
        
        return JsonResponse({
            'success': response['status'],
            'message': response.get('message', ''),
            'data': response.get('data', {})
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    

# Create a logging utility
from .models import ActivityLog

def log_activity(user, activity_type, description, **kwargs):
    """Log admin activity"""
    try:
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            metadata=kwargs,
            ip_address=user.last_login_ip if hasattr(user, 'last_login_ip') else None
        )
    except Exception as e:
        print(f"Failed to log activity: {e}")