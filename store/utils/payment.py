# store/payment_utils.py
import requests
import json
import secrets
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from ..models import Order, OrderItem, Product

class StorePayment:
    """
    Paystack payment handler specifically for school store
    """
    
    def __init__(self):
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
    
    def initialize_store_payment(self, request, cart_items, total_amount, student_id=None):
        """
        Initialize payment for store purchase
        """
        try:
            # Convert Decimal to float for JSON serialization
            if isinstance(total_amount, Decimal):
                total_amount = float(total_amount)
            
            # Convert amount to kobo
            amount_in_kobo = int(total_amount * 100)
            
            # Generate reference
            reference = f"STORE_{secrets.token_hex(8).upper()}"
            
            # Prepare metadata - ensure all values are JSON serializable
            metadata = {
                'user_id': request.user.id,
                'username': request.user.username,
                'student_id': student_id,
                'cart_items': json.dumps(cart_items),
                'purpose': 'school_store_purchase',
                'total_amount': float(total_amount)  # Convert to float
            }
            
            url = f"{self.base_url}/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'email': request.user.email,
                'amount': amount_in_kobo,
                'reference': reference,
                'callback_url': f"{settings.PAYMENT_SUCCESS_URL}?reference={reference}",
                'metadata': metadata
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response_data.get('status'):
                # Store payment data in session - convert Decimals to floats
                request.session['pending_payment'] = {
                    'reference': reference,
                    'amount': float(total_amount),  # Convert to float
                    'cart_items': cart_items,
                    'student_id': student_id
                }
                request.session.modified = True
                
                return {
                    'success': True,
                    'authorization_url': response_data['data']['authorization_url'],
                    'reference': reference
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('message', 'Payment initialization failed')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_store_payment(self, request, reference):
        """
        Verify store payment and create order
        """
        try:
            url = f"{self.base_url}/transaction/verify/{reference}"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
            }
            
            response = requests.get(url, headers=headers)
            response_data = response.json()
            
            if response_data.get('status') and response_data['data']['status'] == 'success':
                return self._create_store_order(request, response_data['data'])
            else:
                return {
                    'success': False,
                    'error': 'Payment verification failed',
                    'payment_data': response_data.get('data', {})
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_store_order(self, request, payment_data):
        """
        Create order after successful payment
        """
        try:
            pending_payment = request.session.get('pending_payment')
            if not pending_payment:
                return {
                    'success': False,
                    'error': 'Payment data not found'
                }
            
            # Get cart items from pending payment
            cart_items = pending_payment['cart_items']
            
            # Create order - amount is already float from session
            order = Order.objects.create(
                user=request.user,
                total_amount=pending_payment['amount'],
                payment_reference=payment_data['reference'],
                payment_method='paystack',
                payment_status='completed',
                status='processing',
                student_id=pending_payment.get('student_id')
            )
            
            # Create order items and update stock
            order_items = []
            for product_id, quantity in cart_items.items():
                try:
                    product = Product.objects.get(id=product_id)
                    
                    # Check stock availability
                    if product.stock < quantity:
                        return {
                            'success': False,
                            'error': f'Insufficient stock for {product.name}'
                        }
                    
                    # Create order item
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.price
                    )
                    order_items.append(order_item)
                    
                    # Update product stock
                    product.stock -= quantity
                    product.save()
                    
                except Product.DoesNotExist:
                    continue
            
            # Clear session data
            request.session['cart'] = {}
            if 'pending_payment' in request.session:
                del request.session['pending_payment']
            request.session.modified = True
            
            return {
                'success': True,
                'order_id': order.id,
                'order_number': str(order.id).zfill(6),
                'total_amount': pending_payment['amount'],
                'items_count': len(order_items)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error creating order: {str(e)}'
            }

# Create global instance
store_payment = StorePayment()