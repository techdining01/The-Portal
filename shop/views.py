import hmac, hashlib
import json, uuid, requests
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect, Http404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from .models import Product, Cart, CartItem, Order, OrderItem, TransactionBackup, Category, Receipt, StudentPurchase
from django.contrib.auth import get_user_model
from . import receipt
User = get_user_model()


# --- helpers ---
def get_cart_for_request(request):
    # Same helper as earlier; create or fetch cart
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(owner=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart

def cart_view(request):
    cart = get_cart_for_request(request)
    items = cart.items.select_related("product","student").all()
    total = sum([it.subtotal() for it in items])
    return render(request, "shop/cart_view.html", {"cart":cart, "items": items, "total": total, "ui_name":"BrillsPay"})


# POST add to cart (async)
@require_POST
def add_to_cart(request):
    """
    Expect JSON body:
    {
      "product_id": 12,
      "quantity": 2,
      "student_reg": "TBS/2025/ABC12"    # optional
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except:
        # Fallback to POST form data
        data = request.POST

    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1) or 1)
    student_reg = data.get("student_reg")

    if not product_id:
        return JsonResponse({"error": "product_id required"}, status=400)

    product = get_object_or_404(Product, pk=product_id)
    cart = get_cart_for_request(request)

    student_obj = None
    if student_reg:
        try:
            student_obj = User.objects.get(registration_number=student_reg, role="student")
        except User.DoesNotExist:
            student_obj = None

    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, student=student_obj,
        defaults={"quantity": quantity}
    )
    if not created:
        item.quantity = max(1, item.quantity + quantity)
        item.save()

    cart_item_count = cart.items.count()

    return JsonResponse({
        "success": True,
        "cart_id": cart.pk,
        "cart_item_count": cart_item_count,
        "item": {
            "id": item.pk,
            "product": product.name,
            "quantity": item.quantity,
            "student_reg": student_obj.registration_number if student_obj else None,
            "subtotal": str(item.subtotal())
        }
    })



# @require_POST
# def add_to_cart(request):
#     """
#     Expects JSON body: {"product_id": int, "quantity": int, "student_reg": str (optional)}
#     Returns JSON with cart_item_count and item details.
#     """
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#     except Exception:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)

#     product_id = data.get("product_id")
#     try:
#         quantity = max(1, int(data.get("quantity", 1)))
#     except Exception:
#         quantity = 1
#     student_reg = data.get("student_reg")

#     if not product_id:
#         return JsonResponse({"error": "product_id required"}, status=400)

#     from ..models import Product, Cart, CartItem

#     product = get_object_or_404(Product, pk=product_id)
#     # cart helper (same as earlier)
#     cart = get_cart_for_request(request)

#     student_obj = None
#     if student_reg:
#         try:
#             student_obj = User.objects.get(registration_number=student_reg, role="student")
#         except User.DoesNotExist:
#             student_obj = None

#     item, created = CartItem.objects.get_or_create(
#         cart=cart, product=product, student=student_obj,
#         defaults={"quantity": quantity}
#     )
#     if not created:
#         item.quantity = max(1, item.quantity + quantity)
#         item.save()

#     # return cart item count for UI
#     cart_count = cart.items.count()
#     return JsonResponse({
#         "success": True,
#         "cart_item_count": cart_count,
#         "item": {
#             "id": item.pk,
#             "product": product.name,
#             "quantity": item.quantity,
#             "student_reg": student_obj.registration_number if student_obj else None,
#             "subtotal": str(item.subtotal())
#         }
#     })



def cart_view(request):
    cart = get_cart_for_request(request)
    items = cart.items.select_related("product", "student").all()
    total = sum([it.subtotal() for it in items])
    return render(request, "shop/cart_view.html", {"cart": cart, "items": items,  "total": total, "ui_name":"BrillsPay"})

@require_POST
def cart_update_qty(request):
    # expects item_id and quantity in POST (async)
    item_id = request.POST.get("item_id")
    qty = int(request.POST.get("quantity", 1))
    item = get_object_or_404(CartItem, pk=item_id)
    if qty <= 0:
        item.delete()
        return JsonResponse({"ok": True, "action": "deleted"})
    item.quantity = qty
    item.save()
    return JsonResponse({"ok": True, "subtotal": float(item.subtotal()), "total": float(sum([i.subtotal() for i in item.cart.items.all()]))})

@require_POST
def cart_remove_item(request):
    item_id = request.POST.get("item_id")
    item = get_object_or_404(CartItem, pk=item_id)
    item.delete()
    return JsonResponse({"ok": True})

# product detail ajax
def product_detail_ajax(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "shop/partials/product_detail.html", {"product": product})

# --- pages ---
def product_list(request):
    products = Product.objects.filter(in_stock=True).order_by('-created_at')
    categories = Category.objects.all()
    return render(request, "shop/product_list.html", {"products": products, "categories": categories, "ui_name":"BrillsPay"})


@staff_member_required
def shop_dashboard(request):
    return render(request, "admin/shop_dashboard.html", {
        "total_products": Product.objects.count(),
        "active_products": Product.objects.filter(in_stock=True).count(),
        "categories": Category.objects.count(),
    })

####-------------------------------------------------------------------------
'''Paystack Inline popup on checkout with inline init'''

def checkout_inline_init(request):
    """
    Called by frontend to initialize an inline checkout.
    POST JSON: { "email": "...", "phone": "...", "name": "..." }
    Returns: { public_key, reference, amount, email, init_data }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = data.get("email") or (request.user.email if request.user.is_authenticated else None)
    phone = data.get("phone") or data.get("telephone") or ""
    if not email:
        return JsonResponse({"error": "email required"}, status=400)

    cart = get_cart_for_request(request)
    if cart.items.count() == 0:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    total = sum([it.subtotal() for it in cart.items.all()])
    order = Order.objects.create(
        cart=cart,
        parent=request.user if request.user.is_authenticated else None,
        email=email,
        phone=phone,
        total=total,
        status="pending"
    )

    # create order items
    for it in cart.items.all():
        OrderItem.objects.create(order=order, product=it.product, quantity=it.quantity, unit_price=it.product.price, student=it.student)

    # initialize with Paystack (server side)
    amount_kobo = int(total * 100)
    callback_url = request.build_absolute_uri(reverse("shop:paystack_verify_inline"))
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {"email": order.email, "amount": amount_kobo, "reference": order.reference, "callback_url": callback_url}
    r = requests.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", headers=headers, json=payload, timeout=20)
    try:
        resp = r.json()
    except Exception:
        resp = {"status": False, "message": "invalid response from paystack"}

    # backup the initialize payload
    TransactionBackup.objects.create(order=order, paystack_reference=order.reference, raw_payload=resp)

    if not resp.get("status"):
        order.status = "failed"
        order.save()
        return JsonResponse({"error": "Could not initialize transaction", "details": resp}, status=400)

    # send minimal data for frontend to use Paystack inline pop-up
    init_data = resp.get("data", {})
    return JsonResponse({
        "public_key": settings.PAYSTACK_PUBLIC_KEY,
        "reference": order.reference,
        "amount": amount_kobo,
        "email": order.email,
        "init": init_data
    })



def paystack_verify_inline(request):
    """
    After inline callback, Paystack returns `reference` param or we verify here.
    GET: ?reference=xxxx
    We'll call Paystack verify endpoint and update order, create Receipt PDF and StudentPurchase rows.
    """
    reference = request.GET.get("reference")
    if not reference:
        return JsonResponse({"error": "reference required"}, status=400)

    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    r = requests.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=headers, timeout=20)
    try:
        resp = r.json()
    except Exception:
        resp = {"status": False, "message": "invalid response from paystack"}

    # update backup
    tb = TransactionBackup.objects.filter(paystack_reference=reference).last()
    if tb:
        tb.raw_payload = resp
        tb.save()

    if resp.get("status") and resp.get("data", {}).get("status") == "success":
        order = Order.objects.filter(reference=reference).first()
        if not order:
            return JsonResponse({"error": "Order not found"}, status=404)
        order.status = "paid"
        order.paid_at = timezone.now()
        order.paystack_payment_ref = resp["data"].get("reference")
        order.save()
        if tb:
            tb.verified = True
            tb.order = order
            tb.save()

        # Create student purchases (one per order_item)
        for oi in order.order_items.all():
            StudentPurchase.objects.create(order_item=oi, student=oi.student if oi.student else order.parent, created_at=timezone.now())

        # Create Receipt record, generate PDF using ReportLab and attach
        receipt, _ = Receipt.objects.get_or_create(order=order)
        html_snapshot = render_to_string("shop/receipt.html", {"order": order, "request": request})
        receipt.html_snapshot = html_snapshot
        # generate PDF with ReportLab (helper below)
        pdf_file = receipt.generate_reportlab_receipt_pdf(order)
        if pdf_file:
            receipt.pdf_file.save(f"receipt-{order.reference}.pdf", pdf_file)
        receipt.save()

        # Clear cart (optionally)
        try:
            if order.cart:
                order.cart.items.all().delete()
        except Exception:
            pass

        # redirect to receipt page (shareable)
        return redirect(order.get_receipt_url())
    else:
        return HttpResponse("Payment not successful", status=400)



# shop/views.py
import hmac, hashlib

@csrf_exempt
def paystack_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE') or request.META.get('HTTP_X_PAYSTACK_SIG') or request.META.get('X-Paystack-Signature') or request.META.get('HTTP_X_PAYSTACK_SIGNATURE'.upper())

    # HMAC verify
    secret = settings.PAYSTACK_WEBHOOK_SECRET.encode() if hasattr(settings, "PAYSTACK_WEBHOOK_SECRET") else settings.PAYSTACK_SECRET_KEY.encode()
    computed = hmac.new(secret, payload, digestmod=hashlib.sha512).hexdigest()
    if not signature or not hmac.compare_digest(computed, signature):
        # signature mismatch
        return JsonResponse({"status": "signature_mismatch"}, status=400)

    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        data = {"raw": payload.decode("utf-8")}

    # store raw payload
    ref = data.get("data", {}).get("reference") or data.get("reference")
    tb = TransactionBackup.objects.create(paystack_reference=ref, raw_payload=data)

    # handle charge.success
    event = data.get("event") or ""
    if event == "charge.success" or data.get("event") == "charge.success":
        ref = data["data"]["reference"]
        order = Order.objects.filter(reference=ref).first()
        if order:
            order.status = "paid"
            order.paid_at = timezone.now()
            order.save()
            tb.order = order
            tb.verified = True
            tb.save()
            # generate receipt etc (similar to verify handler)
    return JsonResponse({"status": "ok"})

###-----------------------------------------------------------------------
'''Paystack Inline popup on checkout with inline view'''

@require_POST
def checkout_inline_view(request):
    """
    Starts Paystack transaction (server initializes transaction) and returns {authorization_url, reference, access_code}
    """
    cart = get_cart_for_request(request)
    if cart.items.count() == 0:
        return JsonResponse({"error":"Cart empty"}, status=400)
    email = request.POST.get("email") or (request.user.email if request.user.is_authenticated else None)
    phone = request.POST.get("phone")
    if not email:
        return JsonResponse({"error":"Email required"}, status=400)
    total = sum([it.subtotal() for it in cart.items.all()])
    order = Order.objects.create(cart=cart, parent=request.user if request.user.is_authenticated else None,
                                 email=email, phone=phone, total=total)
    order_items = []
    for it in cart.items.all():
        oi = OrderItem.objects.create(order=order, product=it.product, quantity=it.quantity, unit_price=it.product.price, student=it.student)
        order_items.append(oi)

    amount_kobo = int(order.total * 100)
    payload = {
        "email": order.email,
        "amount": amount_kobo,
        "reference": order.reference,
        "callback_url": request.build_absolute_uri(reverse("shop:paystack_callback"))  # optional
    }
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type":"application/json"}
    r = requests.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", headers=headers, json=payload)
    resp = r.json()
    TransactionBackup.objects.create(order=order, paystack_reference=order.reference, raw_payload=resp)
    if resp.get("status") and resp.get("data"):
        # Send authorization data to client
        return JsonResponse({"authorization": resp["data"], "order_reference": order.reference})
    else:
        order.status = "failed"
        order.save()
        return JsonResponse({"error":"Could not initialize payment"}, status=400)



# --- Checkout page that uses Paystack inline popup ---
@require_POST
def api_paystack_initialize(request):
    """
    Expects POST JSON: { order_id or cart total, email, phone }
    We'll create Order here and return the paystack authorization data for inline popup.
    """
    data = json.loads(request.body.decode('utf-8'))
    email = data.get("email")
    phone = data.get("phone")
    cart = get_cart_for_request(request)
    if cart.items.count() == 0:
        return JsonResponse({"error":"cart empty"}, status=400)
    total = cart.total()
    order = Order.objects.create(
        cart=cart,
        parent=request.user if request.user.is_authenticated else None,
        email=email,
        phone=phone,
        total=total
    )
    for it in cart.items.all():
        OrderItem.objects.create(order=order, product=it.product, quantity=it.quantity, unit_price=it.product.price, student=it.student)
    amount_kobo = int(total * 100)
    payload = {
        "email": order.email,
        "amount": amount_kobo,
        "reference": order.reference,
        "callback_url": request.build_absolute_uri(reverse('shop:paystack_callback'))
    }
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    r = requests.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", headers=headers, json=payload)
    resp = r.json()
    # backup raw response
    TransactionBackup.objects.create(order=order, paystack_reference=order.reference, raw_payload=resp)
    if resp.get("status") and resp.get("data"):
        # return data used by Paystack inline
        return JsonResponse({"authorization": resp["data"], "order_reference": order.reference})
    return JsonResponse({"error": "initialization failed", "raw": resp}, status=400)



@require_POST
def paystack_verify_inline(request):
    data = json.loads(request.body.decode('utf-8'))
    reference = data.get("reference")
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    r = requests.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=headers)
    resp = r.json()
    # find order by reference
    order = Order.objects.filter(reference=reference).first()
    TransactionBackup.objects.create(order=order, paystack_reference=reference, raw_payload=resp)
    if resp.get("status") and resp.get("data") and resp["data"].get("status") == "success":
        order.status="paid"
        order.paid_at = timezone.now()
        order.paystack_payment_ref = resp["data"].get("reference")
        order.save()
        # create Receipt and StudentPurchase entries
        Receipt.objects.get_or_create(order=order)
        for it in order.order_items.all():
            StudentPurchase.objects.create(student=it.student, order=order, product=it.product, quantity=it.quantity, unit_price=it.unit_price)
        receipt_url = request.build_absolute_uri(order.receipt.get_absolute_url() if hasattr(order, 'receipt') else reverse('shop:receipt', args=[order.receipt_slug]))
        return JsonResponse({"status":"success", "receipt_url": receipt_url})
    return JsonResponse({"status":"failed", "raw": resp})


@csrf_exempt
def paystack_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
    secret = settings.PAYSTACK_SECRET_KEY.encode()
    computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(computed, signature):
        return HttpResponse(status=400)  # signature mismatch

    data = json.loads(payload.decode('utf-8'))
    # store raw payload
    ref = data.get('data', {}).get('reference')
    tb = TransactionBackup.objects.create(paystack_reference=ref, raw_payload=data)
    if data.get('event') == 'charge.success':
        # mark order as paid
        order = Order.objects.filter(reference=ref).first()
        if order:
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save()
            tb.order = order
            tb.verified = True
            tb.save()
            Receipt.objects.get_or_create(order=order)
            # create StudentPurchase rows
            for it in order.order_items.all():
                StudentPurchase.objects.get_or_create(student=it.student, order=order, product=it.product, quantity=it.quantity, unit_price=it.unit_price)
    return JsonResponse({"status":"ok"})


###------------------------------------------------------------

def cart_summary(cart):
    items = cart.items.select_related('product','student').all()
    total = sum([item.product.price * item.quantity for item in items])
    return {"items": items, "total": total, "count": items.count()}



def checkout(request):
    cart_items = CartItem.objects.filter(session_key=request.session.session_key)

    total = sum(i.quantity * i.product.price for i in cart_items)

    context = {
        "cart_items": cart_items,
        "total": total,
        "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY
    }
    return render(request, "shop/checkout.html", context)

# --- async API endpoints (no Django forms) ---

# GET cart
def api_cart_view(request):
    cart = get_cart_for_request(request)
    items = []
    for it in cart.items.select_related('product','student').all():
        items.append({
            "id": it.id,
            "product_id": it.product.id,
            "product_name": it.product.name,
            "unit_price": str(it.product.price),
            "quantity": it.quantity,
            "student_reg": getattr(it.student, "registration_number", None),
            "subtotal": str(it.subtotal())
        })
    return JsonResponse({"items": items, "total": str(cart.total())})

# POST add to cart (async)
@require_POST
def api_cart_add(request):
    data = json.loads(request.body.decode('utf-8'))
    product_id = data.get("product_id")
    qty = int(data.get("quantity", 1))
    student_reg = data.get("student_reg")
    product = get_object_or_404(Product, pk=product_id)
    cart = get_cart_for_request(request)
    student_obj = None
    if student_reg:
        try:
            student_obj = User.objects.get(registration_number=student_reg, role="student")
        except User.DoesNotExist:
            student_obj = None
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, student=student_obj, defaults={"quantity": qty})
    if not created:
        item.quantity += qty
        item.save()
    return JsonResponse({"ok": True, "item_id": item.id})

# PATCH update quantity
@require_POST
def api_cart_update(request, item_id):
    data = json.loads(request.body.decode('utf-8'))
    qty = int(data.get("quantity", 1))
    cart = get_cart_for_request(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    if qty <= 0:
        item.delete()
        return JsonResponse({"ok": True, "deleted": True})
    item.quantity = qty
    item.save()
    return JsonResponse({"ok": True, "quantity": item.quantity, "subtotal": str(item.subtotal())})

# DELETE remove item
@require_POST
def api_cart_remove(request, item_id):
    cart = get_cart_for_request(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    return JsonResponse({"ok": True})



# Simplified admin dashboard
# create a simple admin view
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def management_dashboard(request):
    total_orders = Order.objects.count()
    total_paid = Order.objects.filter(status='paid').count()
    recent_txns = TransactionBackup.objects.order_by('-created_at')[:20]
    return render(request, 'shop/admin_dashboard.html', {"total_orders": total_orders, "total_paid": total_paid, "recent_txns": recent_txns})



# ---------- PAYSTACK WEBHOOK with HMAC verification ----------
@csrf_exempt
def paystack_webhook(request):
    """
    Handle Paystack webhooks. Verify signature using HMAC SHA512.
    Paystack sends header 'x-paystack-signature' (confirm with Paystack docs).
    """
    payload = request.body
    signature = request.headers.get("x-paystack-signature") or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
    # verify signature
    expected_sig = None
    if signature and settings.PAYSTACK_SECRET_KEY:
        computed = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
        expected_sig = computed
        if not hmac.compare_digest(computed, signature):
            # signature mismatch
            return HttpResponseForbidden("Invalid signature")
    # parse payload
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        data = {"raw": payload.decode("utf-8", errors="ignore")}

    # backup raw payload
    reference = data.get("data", {}).get("reference") or data.get("reference")
    tb = TransactionBackup.objects.create(paystack_reference=reference, raw_payload=data)
    # handle charge.success event
    event = data.get("event")
    if event == "charge.success" or data.get("data", {}).get("status") == "success":
        ref = data.get("data", {}).get("reference")
        order = Order.objects.filter(reference=ref).first()
        if order:
            order.status = "paid"
            order.paid_at = timezone.now()
            order.paystack_payment_ref = data.get("data", {}).get("reference")
            order.save()
            tb.order = order
            tb.verified = True
            tb.save()
            # create Receipt record + StudentPurchase records
            html = render_to_string("shop/receipt_partial.html", {"order": order})
            receipt = Receipt.objects.create(order=order, html_snapshot=html)
            # create StudentPurchase entries
            for it in order.order_items.all():
                if it.student:
                    StudentPurchase.objects.create(order_item=it, student=it.student)
    return JsonResponse({"status":"ok"})

# ---------- RECEIPT VIEW (shareable & PDF) ----------


# ---------- PURCHASE HISTORY ----------
def parent_purchase_history(request):
    """Parent or admin can view all orders placed by the parent"""
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL)
    orders = Order.objects.filter(parent=request.user).order_by("-created_at")
    return render(request, "shop/purchase_history_parent.html", {"orders": orders, "ui_name":"BrillsPay"})

def student_purchase_history(request, student_reg):
    """View purchases for a student by registration number (admin or parent)"""
    # Allow parent or admin only
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL)
    try:
        student = User.objects.get(registration_number=student_reg, role="student")
    except User.DoesNotExist:
        return HttpResponse("Student not found", status=404)
    # parent check: allow if request.user is parent of student (parent_email or next_of_kin etc) OR admin
    is_admin = getattr(request.user, "can_approve", lambda: False)()
    if not is_admin:
        # here we allow any logged parent with parent_email matching user's email OR if user is the parent_name
        if not (request.user.email and request.user.email == student.parent_email):
            return HttpResponseForbidden("Not allowed")
    purchases = StudentPurchase.objects.filter(student=student).select_related("order_item__product", "order_item__order").order_by("-created_at")
    return render(request, "shop/purchase_history_student.html", {"student": student, "purchases": purchases})








###---------------------------------------------------------------
'''
VERIFY THIS LATER IF NEEDED

'''

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'superadmin'])
def order_list(request):
    orders = Order.objects.select_related('user').prefetch_related('order_items').order_by('-created_at')
    return render(request, 'shop/order_list.html', {'orders': orders})


@login_required
def order_history(request):
    orders = Order.objects.filter(parent=request.user).order_by('-created_at')
    return render(request, "shop/order_history.html", {"orders": orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})


# @login_required
# def pickup_code_list(request):
#     codes = PickupAuthorization.objects.filter(generated_by=request.user).order_by('-created_at')
#     return render(request, 'shop/pickup_code_list.html', {'codes': codes})



