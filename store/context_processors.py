def cart_context(request):
    cart = request.session.get('cart', {})
    cart_total = 0
    cart_items_count = 0
    
    from .models import Product
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            cart_total += product.price * quantity
            cart_items_count += quantity
        except Product.DoesNotExist:
            continue
    
    return {
        'cart_total': cart_total,
        'cart_items_count': cart_items_count,
    }