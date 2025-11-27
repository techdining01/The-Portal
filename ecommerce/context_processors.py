from django.conf import settings
from .models import Cart

def paystack_keys(request):
    return {
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
    }

def cart_count(request):
    """Add cart item count to all templates"""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user, is_active=True)
            cart_count = cart.items.count()
        except Cart.DoesNotExist:
            cart_count = 0
    else:
        cart_count = 0
    
    return {'cart_count': cart_count}


def site_settings(request):
    """Add site settings to template context"""
    from django.conf import settings
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'THE BRILLS SCHOOL'),
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', 'supportthebrills@gmail.com'),
        'SUPPORT_PHONE': getattr(settings, 'SUPPORT_PHONE', ''),
    }

