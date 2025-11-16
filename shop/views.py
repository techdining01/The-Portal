from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from .models import Item, Cart, CartItem, Order
import secrets
import requests
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone



def shop_home(request):
    items = Item.objects.filter(active=True)
    return render(request, "shop/home.html", {"items": items})

def product_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    return render(request, "shop/detail.html", {"item": item})

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart

def add_to_cart(request):
    # expects POST: item_id, qty
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("qty", 1))
    item = get_object_or_404(Item, id=item_id)
    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not created:
        cart_item.qty += qty
    cart_item.save()
    return JsonResponse({"ok": True, "cart_total": float(cart.total())})

def cart_view(request):
    cart = get_or_create_cart(request)
    return render(request, "shop/cart.html", {"cart": cart})


def update_cart_item(request):
    # POST item_id, qty
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("qty", 1))
    cart = get_or_create_cart(request)
    ci = cart.items.filter(item_id=item_id).first()
    if not ci:
        return JsonResponse({"error":"no item"}, status=400)
    if qty <= 0:
        ci.delete()
    else:
        ci.qty = qty
        ci.save()
    return JsonResponse({"ok":True, "cart_total": float(cart.total())})


def initiate_checkout(request):
    cart = get_or_create_cart(request)
    if cart.items.count() == 0:
        return redirect("shop:home")
    # create order
    reference = secrets.token_hex(12)
    amount = cart.total()
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        reference=reference,
        amount=amount,
        status='pending'
    )
    # add order items
    for ci in cart.items.all():
        order.order_items.create(item=ci.item, qty=ci.qty, price=ci.item.price)
    # init paystack
    paystack_secret = settings.PAYSTACK_SECRET_KEY
    headers = {"Authorization": f"Bearer {paystack_secret}"}
    callback = request.build_absolute_uri(f"/shop/paystack/verify/{reference}/")
    data = {
        "email": request.user.email if request.user.is_authenticated else request.POST.get("email"),
        "amount": int(amount * 100),
        "reference": reference,
        "callback_url": callback,
    }
    resp = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers, timeout=30)
    resp.raise_for_status()
    j = resp.json()
    # redirect to authorization_url
    return redirect(j["data"]["authorization_url"])

@csrf_exempt
def paystack_webhook(request):
    import hmac, hashlib, json
    signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE") or request.headers.get("x-paystack-signature")
    secret = settings.PAYSTACK_SECRET_KEY.encode()
    computed = hmac.new(secret, request.body, hashlib.sha512).hexdigest()
    if not signature or not hmac.compare_digest(computed, signature):
        return HttpResponse(status=403)
    payload = json.loads(request.body)
    event = payload.get("event")
    if event in ("charge.success", "payment.success"):
        data = payload.get("data", {})
        reference = data.get("reference")
        order = Order.objects.filter(reference=reference).first()
        if order and order.status != "success":
            order.status = "success"
            order.paid_at = timezone.now()
            order.save()
            # optional: clear cart for user/session
            if order.user:
                Cart.objects.filter(user=order.user).delete()
            else:
                # remove session cart by matching session?
                pass
    return HttpResponse(status=200)


# @login_required
# def student_fees(request):
#     # all fee items for the student's class or school
#     fees = Fee.objects.filter(is_active=True)
#     payments = Payment.objects.filter(user=request.user, status='success')
#     paid_amount = sum(p.amount for p in payments)
#     total_fees = sum(f.amount for f in fees)
#     return render(request, "students/fees.html", {
#         "fees": fees, "paid_amount": paid_amount, "balance": total_fees - paid_amount
#     })
