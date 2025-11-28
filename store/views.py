
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Product, Cart, CartItem, Order, OrderItem, Transaction
from .paystack import Paystack
import json

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
            student = get_object_or_404(request.user.children, id=student_id)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            student=student,
            defaults={'quantity': 1}
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        messages.success(request, 'Product added to cart successfully!')
        return redirect('cart')
    
    return redirect('product_list')

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    children = request.user.children.all() if hasattr(request.user, 'children') else []
    return render(request, 'store/cart.html', {'cart': cart, 'children': children})

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            item.quantity = quantity
            item.save()
            messages.success(request, 'Cart updated successfully!')
        else:
            item.delete()
            messages.success(request, 'Item removed from cart!')
    
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('cart')

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if cart.items.count() == 0:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')
    
    children = request.user.children.all() if hasattr(request.user, 'children') else []
    
    if request.method == 'POST':
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_amount
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                student=cart_item.student
            )
        
        # Initialize Paystack payment
        paystack = Paystack()
        result = paystack.initialize_transaction(
            email=request.user.email,
            amount=int(order.total_amount * 100),  # Convert to kobo
            reference=order.order_number,
            callback_url=request.build_absolute_uri('/payment/verify/')
        )
        
        if result['status']:
            # Clear cart
            cart.items.all().delete()
            
            # Create transaction record
            Transaction.objects.create(
                order=order,
                paystack_reference=result['data']['reference'],
                amount=order.total_amount
            )
            
            return redirect(result['data']['authorization_url'])
        else:
            messages.error(request, 'Payment initialization failed. Please try again.')
            return redirect('checkout')
    
    return render(request, 'store/checkout.html', {'cart': cart, 'children': children})

@login_required
def payment_verify(request):
    reference = request.GET.get('reference')
    
    if reference:
        transaction = get_object_or_404(Transaction, paystack_reference=reference)
        paystack = Paystack()
        result = paystack.verify_transaction(reference)
        
        if result['status'] and result['data']['status'] == 'success':
            transaction.payment_status = 'success'
            transaction.paid_at = result['data']['paid_at']
            transaction.gateway_response = json.dumps(result['data'])
            transaction.save()
            
            # Update order status
            transaction.order.status = 'paid'
            transaction.order.payment_verified = True
            transaction.order.save()
            
            messages.success(request, 'Payment completed successfully!')
            return redirect('order_success', order_id=transaction.order.id)
        else:
            messages.error(request, 'Payment verification failed!')
            return redirect('order_failed')
    
    return redirect('cart')

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})

@csrf_exempt
@require_POST
def paystack_webhook(request):
    """
    Paystack webhook for payment verification
    """
    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'charge.success':
            data = payload.get('data')
            reference = data.get('reference')
            
            try:
                transaction = Transaction.objects.get(paystack_reference=reference)
                transaction.payment_status = 'success'
                transaction.paid_at = data.get('paid_at')
                transaction.gateway_response = json.dumps(data)
                transaction.save()
                
                # Update order status
                transaction.order.status = 'paid'
                transaction.order.payment_verified = True
                transaction.order.save()
                
                return JsonResponse({'status': 'success'})
            except Transaction.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Transaction not found'}, status=404)
        
        return JsonResponse({'status': 'ignored'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)