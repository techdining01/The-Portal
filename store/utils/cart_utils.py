# store/utils.py
from ..models import Cart, CartItem, Product
from django.contrib.sessions.models import Session
from decimal import Decimal
import json


def get_cart_total(request):
    """Calculate total amount in cart - returns float for JSON compatibility"""
    try:
        cart_items = get_cart_items(request)
        total = sum(item.total_price for item in cart_items)
        # Convert Decimal to float for JSON serialization
        return float(total) if isinstance(total, Decimal) else total
    except Exception as e:
        print(f"Error calculating cart total: {e}")
        return 0

def get_cart_summary(request):
    """Get complete cart summary with JSON-serializable data"""
    try:
        cart_items = get_cart_items(request)
        cart_total = get_cart_total(request)
        items_count = get_cart_items_count(request)
        
        # Convert cart items to JSON-serializable format
        serializable_items = []
        for item in cart_items:
            serializable_items.append({
                'id': item.id,
                'product_id': item.product.id,
                'quantity': item.quantity,
                'product_name': item.product.name,
                'product_price': float(item.product.price),  # Convert Decimal to float
                'total_price': float(item.total_price),      # Convert Decimal to float
                'product_image': item.product.image.url if item.product.image else None
            })
        
        return {
            'success': True,
            'cart_items': serializable_items,
            'total_amount': cart_total,
            'items_count': items_count
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_or_create_cart(request):
    """Get or create cart for user (authenticated or anonymous)"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # For anonymous users, use session key
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            user=None
        )
    return cart

def get_cart_items(request):
    """Get cart items for current user/session with product details"""
    try:
        cart = get_or_create_cart(request)
        return CartItem.objects.filter(cart=cart).select_related('product')
    except Exception as e:
        print(f"Error getting cart items: {e}")
        return CartItem.objects.none()

def get_cart_items_count(request):
    """Get total number of items in cart"""
    try:
        cart_items = get_cart_items(request)
        return sum(item.quantity for item in cart_items)
    except Exception as e:
        print(f"Error counting cart items: {e}")
        return 0

def add_to_cart(request, product_id, quantity=1):
    """Add product to cart"""
    try:
        cart = get_or_create_cart(request)
        product = Product.objects.get(id=product_id)
        
        # Check stock availability
        if product.stock < quantity:
            return {
                'success': False,
                'error': f'Only {product.stock} items available in stock'
            }
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Check if new quantity exceeds stock
            if cart_item.quantity + quantity > product.stock:
                return {
                    'success': False,
                    'error': f'Cannot add more than {product.stock} items'
                }
            cart_item.quantity += quantity
            cart_item.save()
        
        return {
            'success': True,
            'cart_item': cart_item,
            'cart_items_count': get_cart_items_count(request)
        }
        
    except Product.DoesNotExist:
        return {
            'success': False,
            'error': 'Product not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def update_cart_quantity(request, product_id, quantity):
    """Update product quantity in cart"""
    try:
        cart = get_or_create_cart(request)
        
        if quantity <= 0:
            # Remove item if quantity is 0 or less
            CartItem.objects.filter(cart=cart, product_id=product_id).delete()
            return {
                'success': True,
                'action': 'removed'
            }
        
        # Check stock availability
        product = Product.objects.get(id=product_id)
        if quantity > product.stock:
            return {
                'success': False,
                'error': f'Only {product.stock} items available in stock'
            }
        
        cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
        cart_item.quantity = quantity
        cart_item.save()
        
        return {
            'success': True,
            'cart_item': cart_item,
            'action': 'updated'
        }
        
    except CartItem.DoesNotExist:
        return {
            'success': False,
            'error': 'Item not found in cart'
        }
    except Product.DoesNotExist:
        return {
            'success': False,
            'error': 'Product not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def remove_from_cart(request, product_id):
    """Remove product from cart"""
    try:
        cart = get_or_create_cart(request)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        
        return {
            'success': True,
            'cart_items_count': get_cart_items_count(request)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def clear_cart(request):
    """Clear all items from cart"""
    try:
        cart = get_or_create_cart(request)
        CartItem.objects.filter(cart=cart).delete()
        
        return {
            'success': True,
            'cart_items_count': 0
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

