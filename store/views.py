
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from .models import Product, Cart, CartItem, Order, OrderItem, Transaction, Product
import json, datetime, requests
from users.models import User
from django.utils import timezone
import secrets
from django.conf import settings
from .utils.payment import store_payment
from .utils.cart_utils import (
    get_cart_items, get_cart_total, get_cart_items_count,
    add_to_cart, update_cart_quantity, remove_from_cart, clear_cart
)



def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'store/product_list.html', {'products': products})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, 'store/product_detail.html', {'product': product})


@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        student_id = request.POST.get('student')
        student = None
        if student_id:
            try:
                student = request.user.children.get(id=student_id)
            except User.DoesNotExist:
                messages.warning(request, 'Selected student not found.')
        
        # Check if item already exists in cart
        existing_item = CartItem.objects.filter(
            cart=cart, 
            product=product,
            student=student
        ).first()
        
        if existing_item:
            # Update existing item quantity
            quantity = int(request.POST.get('quantity', 1))
            existing_item.quantity += quantity
            existing_item.save()
            messages.success(request, f'Updated quantity for {product.name}!')
        else:
            # Create new cart item
            quantity = int(request.POST.get('quantity', 1))
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                student=student
            )
            messages.success(request, f'{product.name} added to cart successfully!')
        
        return redirect('store:cart_view')
    
    return redirect('product_list')


# @login_required
# def update_cart_item(request, item_id):
#     if request.method == 'POST':
#         item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
#         quantity = int(request.POST.get('quantity', 1))
        
#         if quantity > 0:
#             item.quantity = quantity
#             item.save()
#             messages.success(request, 'Cart updated successfully!')
#         else:
#             item.delete()
#             messages.success(request, 'Item removed from cart!')
    
#     return redirect('store:cart_view')


# @login_required
# def cart_view(request):
#     cart, created = Cart.objects.get_or_create(user=request.user)
#     children = request.user.children.all() if hasattr(request.user, 'children') else []
#     return render(request, 'store/cart.html', {'cart': cart, 'children': children})


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('store:cart_view')


##--------------------------------------------------------------------------
   
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



###############-----------------------------------------------------------######################



def cart_view(request):
    """Mobile-first cart page"""
    cart_items = get_cart_items(request)
    cart_total = get_cart_total(request)
    cart_items_count = get_cart_items_count(request)
    
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_items_count': cart_items_count,
    }
    return render(request, 'store/cart.html', context)

@require_POST
def add_to_cart_view(request, product_id):
    """AJAX view to add product to cart"""
    try:
        quantity = int(request.POST.get('quantity', 1))
        result = add_to_cart(request, product_id, quantity)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'cart_items_count': result['cart_items_count'],
                'message': 'Product added to cart successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    

@require_POST
def update_cart_view(request):
    """AJAX view to update cart quantities"""
    try:
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        
        if action == 'increase':
            cart_items = get_cart_items(request)
            cart_item = cart_items.get(product_id=product_id)
            result = update_cart_quantity(
                request, 
                product_id, 
                cart_item.quantity + 1
            )
            
        elif action == 'decrease':
            cart_items = get_cart_items(request)
            cart_item = cart_items.get(product_id=product_id)
            result = update_cart_quantity(
                request, 
                product_id, 
                cart_item.quantity - 1
            )
            
        elif action == 'remove':
            result = remove_from_cart(request, product_id)
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action'
            }, status=400)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'quantity': result.get('cart_item', {}).quantity if 'cart_item' in result else 0,
                'item_total': result.get('cart_item', {}).total_price if 'cart_item' in result else 0,
                'cart_total': get_cart_total(request),
                'cart_items_count': get_cart_items_count(request),
                'action': result.get('action', 'updated')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_POST
def clear_cart_view(request):
    """AJAX view to clear cart"""
    try:
        result = clear_cart(request)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': 'Cart cleared successfully',
                'cart_items_count': result['cart_items_count']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    

@login_required
def checkout_view(request):
    """Mobile-first checkout page with payment"""
    cart_items = get_cart_items(request)
    cart_total = get_cart_total(request)
    
    if not cart_items:
        messages.warning(request, "Your cart is empty")
        return redirect('store:product_list')
    
    context = {
        'cart_items': cart_items,
        'total_amount': cart_total,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'store/checkout.html', context)


# store/views.py
@login_required
@require_POST
def initialize_payment_view(request):
    """Initialize Paystack payment for store purchase - FIXED"""
    try:
        # Get cart data in the format needed for payment
        cart_items_dict = {}
        cart_items = get_cart_items(request)
        for item in cart_items:
            cart_items_dict[str(item.product.id)] = item.quantity
        
        total_amount = get_cart_total(request)
        
        if not cart_items_dict or total_amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Cart is empty'
            }, status=400)
        
        # Get student selection
        student_id = request.POST.get('student_id')
        
        # Initialize payment
        result = store_payment.initialize_store_payment(
            request=request,
            cart_items=cart_items_dict,
            total_amount=total_amount,
            student_id=student_id
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    

@login_required
@require_GET
def verify_payment_view(request):
    """Verify payment after redirect from Paystack"""
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, "Payment reference missing")
        return redirect('store:checkout')
    
    # Verify payment
    result = store_payment.verify_store_payment(request, reference)
    
    if result['success']:
        messages.success(
            request, 
            f"Payment successful! Order #{result['order_number']} has been created."
        )
        return redirect('store:order_detail', order_id=result['order_id'])
    else:
        messages.error(request, result['error'])
        return redirect('store:checkout')


@csrf_exempt
@require_POST
def payment_webhook_view(request):
    """Paystack webhook for store payments"""
    try:
        # In production, validate webhook signature here
        payload = json.loads(request.body)
        
        # Process webhook
        store_payment.handle_store_webhook(payload)
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return JsonResponse({'status': 'error'}, status=400)

@login_required
def order_list_view(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_list.html', {'orders': orders})

@login_required
def order_detail_view(request, order_id):
    """Order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})


