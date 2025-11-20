from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from .models import Item, Cart, CartItem, Order, OrderItem
import secrets
import requests
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from .forms import ItemForm
from django.views.decorators.http import require_POST



def shop_home(request):
    items = Item.objects.filter(is_active=True)
    return render(request, "shop/home.html", {"items": items})

def product_detail(request, slug):
    item = get_object_or_404(Item, slug=slug)
    return render(request, "shop/detail.html", {"item": item})



def get_or_create_cart(request):
    # If user is logged in → attach user cart
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Use session for guest cart
        if not request.session.session_key:
            request.session.create()  # create session if missing

        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)

    return cart


def add_to_cart(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    cart = get_or_create_cart(request)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        item=item
    )

    cart_item.qty 
    cart_item.save()

    return redirect("shop:cart")


def cart_page(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("item")
    return render(request, "shop/cart.html", {"cart": cart, "items": items})


def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    print(item)
    item.delete()
    return redirect("shop:cart")


@require_POST
def update_cart_ajax(request):
    cart = get_or_create_cart(request)
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("qty"))

    cart_item = get_object_or_404(CartItem, cart=cart, item_id=item_id)
    cart_item.qty = qty
    cart_item.save()

    return JsonResponse({
        "success": True,
        "item_total": float(cart_item.line_total()),
        "cart_total": float(cart.total())
    })


def checkout(request):
    cart = get_or_create_cart(request)

    if cart.items.count() == 0:
        return redirect("shop:cart")
    
    line_totals = [ci.line_total() for ci in cart.items.all()]
    total_amount = cart.total()

    return render(request, "shop/checkout.html", {
        "cart": cart,
        "items": cart.items.all(),
        "total": total_amount,
        "line_totals": line_totals,
        "PAYSTACK_PUBLIC_KEY": settings.PAYSTACK_PUBLIC_KEY,
    })


def clear_cart(request):
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    return redirect("cart")


# Quantity Adjustment Views -----------------------------


def increase_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.quantity += 1
    item.save()
    return redirect("shop:cart")

def decrease_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
    return redirect("shop:cart")


@require_POST
def update_cart_ajax(request):
    cart = Cart(request)
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")

    item = get_object_or_404(Item, id=item_id)

    if action == "increase":
        cart.add(item, quantity=1)

    elif action == "decrease":
        cart.add(item, quantity=-1)

        # Auto-remove if quantity becomes 0
        if cart.get_quantity(item_id) <= 0:
            cart.remove(item)

    # Build response
    items = []
    removed_ids = []

    for item in cart:
        items.append({
            "item_id": item["item"].id,
            "quantity": item["quantity"],
            "total_price": f"{item['total_price']:.2f}",
        })

    # Check for removed items
    if action == "decrease" and cart.get_quantity(item_id) <= 0:
        removed_ids.append(int(item_id))

    return JsonResponse({
        "status": "success",
        "items": items,
        "total_price": f"{cart.get_total_price():.2f}",
        "total_items": len(cart),
        "removed_ids": removed_ids,
    })



@require_POST
def remove_from_cart_ajax(request):
    cart = Cart(request)
    item_id = request.POST.get("item_id")
    item = get_object_or_404(Item, id=item_id)

    cart.remove(item)

    # Rebuild updated items
    items = []
    for item in cart:
        items.append({
            "item_id": item["item"].id,
            "quantity": item["quantity"],
            "total_price": f"{item['total_price']:.2f}",
        })

    return JsonResponse({
        "status": "removed",
        "items": items,
        "removed_ids": [int(item_id)],
        "total_price": f"{cart.get_total_price():.2f}",
        "total_items": len(cart),
    })


def get_total_price(self):
    return sum(item["total_price"] for item in self.cart.values())


def get_quantity(self, item_id):
    item_id = str(item_id)
    return self.cart[item_id]["quantity"] if item_id in self.cart else 0


def initiate_checkout(request):
    cart = get_or_create_cart(request.session)
    if not cart:
        return redirect('shop:index')
    total = 0
    from .models import Item as ItemModel, Order, OrderItem
    for id_str, qty in cart.items():
        obj = ItemModel.objects.get(pk=int(id_str))
        total += obj.price * qty
    reference = secrets.token_hex(10)
    order = Order.objects.create(user=request.user if request.user.is_authenticated else None,
                                 reference=reference, amount=total, status='pending')
    for id_str, qty in cart.items():
        obj = ItemModel.objects.get(pk=int(id_str))
        OrderItem.objects.create(order=order, item=obj, quantity=qty, unit_price=obj.price)
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    callback = request.build_absolute_uri(reverse('shop:verify', args=[reference]))
    data = {'email': request.user.email if request.user.is_authenticated else '', 'amount': total*100, 'reference': reference, 'callback_url': callback}
    resp = requests.post('https://api.paystack.co/transaction/initialize', json=data, headers=headers, timeout=30)
    if resp.status_code != 200:
        return HttpResponseBadRequest('Payment initialization failed')
    payload = resp.json()
    request.session['cart'] = {}
    request.session.modified = True
    return redirect(payload['data']['authorization_url'])

def verify_payment(request, reference):
    import requests
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    resp = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers, timeout=30)
    data = resp.json()
    order = get_object_or_404(Order, reference=reference)
    if data.get('status') and data['data']['status'] == 'success':
        order.status = 'paid'
        order.save()
        return render(request, 'shop/success.html', {'order': order})
    order.status = 'failed'
    order.save()
    return render(request, 'shop/failed.html', {'order': order})


@require_POST
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


def is_admin(user):
    return user.is_staff or user.is_superuser


# --- Admin Item List ---
@login_required
@user_passes_test(is_admin)
def admin_items(request):
    items = Item.objects.all().order_by("-created_at")
    return render(request, "shop/admin/items.html", {"items": items})


# --- Create Item ---
@login_required
@user_passes_test(is_admin)
def admin_add_item(request):
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Item added successfully.")
            return redirect("shop:admin_items")
    else:
        form = ItemForm()

    return render(request, "shop/admin/item_form.html", {"form": form, "title": "Add Item"})


# --- Edit Item ---
@login_required
@user_passes_test(is_admin)
def admin_edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect("shop:admin_items")

    else:
        form = ItemForm(instance=item)

    return render(request, "shop/admin/item_form.html", {"form": form, "title": "Edit Item"})


# --- Delete Item ---
@login_required
@user_passes_test(is_admin)
def admin_delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    item.delete()
    messages.warning(request, "Item deleted.")
    return redirect("shop:admin_items")


# --- Increase Stock ---
@login_required
@user_passes_test(is_admin)
def admin_increase_stock(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    item.stock += 1
    item.save()
    messages.success(request, "Stock increased.")
    return redirect("shop:admin_items")


# --- Decrease Stock ---
@login_required
@user_passes_test(is_admin)
def admin_decrease_stock(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if item.stock > 0:
        item.stock -= 1
        item.save()
        messages.info(request, "Stock decreased.")
    else:
        messages.error(request, "Stock cannot go below 0.")
    return redirect("shop:admin_items")



