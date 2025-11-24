from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Product, Cart, CartItem

def get_user_cart(request):
    """Create or fetch cart for logged-in/anonymous user."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(parent=request.user)
    else:
        session_id = request.session.session_key or request.session.create()
        cart, _ = Cart.objects.get_or_create(session_id=request.session.session_key)

    return cart


def get_cart_data(request):
    cart = get_user_cart(request)
    items = cart.items.select_related("product")

    data = {
        "items": [
            {
                "id": item.id,
                "product": item.product.name,
                "price": float(item.price),
                "qty": item.quantity,
                "subtotal": float(item.subtotal())
            }
            for item in items
        ],
        "total": float(cart.total_amount()),
    }
    return JsonResponse(data)


def add_to_cart(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    product_id = request.POST.get("product_id")
    qty = int(request.POST.get("qty", 1))

    product = Product.objects.get(id=product_id)
    cart = get_user_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"price": product.price}
    )

    if not created:
        cart_item.quantity += qty
    cart_item.save()

    return JsonResponse({"success": True})


def update_cart(request):
    product_id = request.POST.get("product_id")
    qty = int(request.POST.get("qty", 1))

    cart = get_user_cart(request)

    try:
        item = cart.items.get(product_id=product_id)
        item.quantity = qty
        item.save()
    except CartItem.DoesNotExist:
        return JsonResponse({"error": "item not found"}, status=404)

    return JsonResponse({"success": True})


def remove_from_cart(request):
    product_id = request.POST.get("product_id")
    cart = get_user_cart(request)

    cart.items.filter(product_id=product_id).delete()

    return JsonResponse({"success": True})


def clear_cart(request):
    cart = get_user_cart(request)
    cart.items.all().delete()
    return JsonResponse({"success": True})


def checkout_page(request):
    cart = get_user_cart(request)
    total = float(cart.total_amount())
    return render(request, "shop/checkout.html", {"total": total})
