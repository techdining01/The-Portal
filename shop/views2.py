# import uuid, json, hmac, hashlib, requests
# from decimal import Decimal
# from django.shortcuts import render, get_object_or_404, redirect
# from django.conf import settings
# from django.utils import timezone
# from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
# from django.db import transaction
# from .models import Product, Order, OrderItem, Payment
# from django.views.decorators.csrf import csrf_exempt
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.urls import reverse

# CART_SESSION_ID = 'shop_cart'

# # ---------- cart helpers (session-based) ----------
# def _get_cart(request):
#     return request.session.get(CART_SESSION_ID, {})

# def _save_cart(request, cart):
#     request.session[CART_SESSION_ID] = cart
#     request.session.modified = True

# def product_list(request):
#     products = Product.objects.filter(active=True).order_by('name')
#     return render(request, 'shop/product_list.html', {'products': products})

# def product_detail(request, pk):
#     product = get_object_or_404(Product, pk=pk, active=True)
#     return render(request, 'shop/product_detail.html', {'product': product})

# # AJAX add to cart
# def cart_add(request):
#     if request.method != 'POST':
#         return JsonResponse({'error':'POST only'}, status=405)
#     data = json.loads(request.body)
#     sku = data.get('sku')
#     qty = int(data.get('qty', 1))
#     product = get_object_or_404(Product, sku=sku, active=True)
#     cart = _get_cart(request)
#     item = cart.get(str(product.pk), {'qty':0, 'price': str(product.price), 'name': product.name, 'sku': product.sku})
#     item['qty'] = item.get('qty',0) + qty
#     cart[str(product.pk)] = item
#     _save_cart(request, cart)
#     return JsonResponse({'status':'ok', 'cart_count': sum(i['qty'] for i in cart.values())})

# def cart_update(request):
#     if request.method != 'POST':
#         return JsonResponse({'error':'POST only'}, status=405)
#     data = json.loads(request.body)
#     updates = data.get('updates', {})
#     cart = _get_cart(request)
#     for k, v in updates.items():
#         if k in cart:
#             cart[k]['qty'] = int(v)
#             if cart[k]['qty'] <= 0:
#                 del cart[k]
#     _save_cart(request, cart)
#     return JsonResponse({'status':'ok', 'cart_total': _cart_total(cart)})

# def cart_remove(request):
#     if request.method != 'POST':
#         return JsonResponse({'error':'POST only'}, status=405)
#     data = json.loads(request.body)
#     pk = data.get('pk')
#     cart = _get_cart(request)
#     if str(pk) in cart:
#         del cart[str(pk)]
#     _save_cart(request, cart)
#     return JsonResponse({'status':'ok', 'cart_total': _cart_total(cart)})

# def _cart_total(cart):
#     total = Decimal('0.00')
#     for item in cart.values():
#         total += Decimal(item['price']) * item['qty']
#     return str(total)

# def cart_view(request):
#     cart = _get_cart(request)
#     # attach current product images/details if possible
#     items = []
#     for pk, item in cart.items():
#         try:
#             prod = Product.objects.get(pk=int(pk))
#             items.append({'pk':pk, 'name': item['name'], 'price': item['price'], 'qty': item['qty'], 'image': prod.image.url if prod.image else None})
#         except Product.DoesNotExist:
#             continue
#     total = Decimal(_cart_total(cart))
#     return render(request, 'shop/cart.html', {'items': items, 'total': total})

# # ---------- checkout creates Order then redirect to initiate payment ----------
# @transaction.atomic
# def checkout(request):
#     cart = _get_cart(request)
#     if not cart:
#         messages.error(request, "Your cart is empty.")
#         return redirect('shop:product_list')
#     # For non-logged users ask for email at checkout
#     if request.method == 'POST':
#         email = request.POST.get('email') or (request.user.email if request.user.is_authenticated else None)
#         if not email:
#             messages.error(request, "Please provide an email.")
#             return redirect('shop:cart')
#         # create Order snapshot
#         reference = f"ORD-{uuid.uuid4().hex[:12]}"
#         total = Decimal(_cart_total(cart))
#         order = Order.objects.create(user=request.user if request.user.is_authenticated else None,
#                                      email=email,
#                                      total_amount=total,
#                                      reference=reference,
#                                      metadata={'cart': cart})
#         # create OrderItem snapshot
#         for pk, it in cart.items():
#             try:
#                 prod = Product.objects.get(pk=int(pk))
#                 OrderItem.objects.create(order=order,
#                                          product=prod,
#                                          name=prod.name,
#                                          unit_price=prod.price,
#                                          quantity=it['qty'])
#             except Product.DoesNotExist:
#                 continue
#         # clear cart
#         request.session.pop(CART_SESSION_ID, None)
#         return redirect('shop:initiate_payment', order_ref=order.reference)
#     else:
#         total = Decimal(_cart_total(cart))
#         return render(request, 'shop/checkout.html', {'total': total, 'cart': cart})

# # ---------- initiate payment (server side) ----------
# def initiate_payment(request, order_ref):
#     order = get_object_or_404(Order, reference=order_ref)
#     # prepare Paystack initialize
#     paystack_secret = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
#     if not paystack_secret:
#         return HttpResponse("PAYSTACK_SECRET_KEY not configured", status=500)
#     headers = {'Authorization': f'Bearer {paystack_secret}', 'Content-Type': 'application/json'}
#     amount_kobo = int(order.total_amount * Decimal('100'))
#     callback = request.build_absolute_uri(reverse('shop:verify_payment', kwargs={'order_ref': order.reference}))
#     payload = {
#         "email": order.email,
#         "amount": amount_kobo,
#         "reference": order.reference,
#         "callback_url": callback,
#         "metadata": {"order_ref": order.reference}
#     }
#     resp = requests.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", json=payload, headers=headers, timeout=30)
#     resp.raise_for_status()
#     data = resp.json()
#     return redirect(data['data']['authorization_url'])

# # ---------- verify (redirect) ----------
# def verify_payment(request, order_ref):
#     order = get_object_or_404(Order, reference=order_ref)
#     # verify via Paystack verify endpoint
#     headers = {'Authorization': f'Bearer {getattr(settings, "PAYSTACK_SECRET_KEY", "")}'}
#     r = requests.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{order_ref}", headers=headers, timeout=30)
#     res = r.json()
#     if res.get('status') and res['data']['status'] == 'success':
#         # mark paid, create Payment object
#         order.status = 'paid'
#         order.paid_at = timezone.now()
#         order.save(update_fields=['status','paid_at'])
#         # record payment
#         Payment.objects.create(order=order, gateway='paystack', gateway_reference=order_ref, amount=res['data']['amount'], status='success', raw_response=res)
#         # Business logic post-pay: if the order contains a "school fee" product, unlock exam
#         # simplest approach: check product SKU prefix 'FEE-' or a boolean field in Product if it's fee
#         for item in order.items.all():
#             if item.product and item.product.sku.startswith('FEE-'):
#                 # unlock user (if exists)
#                 if order.user:
#                     order.user.can_take_exam = True
#                     order.user.save(update_fields=['can_take_exam'])
#         return render(request, 'shop/payment_success.html', {'order': order, 'data': res})
#     else:
#         order.status = 'failed'
#         order.save(update_fields=['status'])
#         return render(request, 'shop/payment_failed.html', {'order': order, 'data': res})

# # ---------- webhook (server-to-server) ----------
# @csrf_exempt
# def paystack_webhook(request):
#     payload = request.body
#     signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE') or request.headers.get('x-paystack-signature')
#     secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '').encode()
#     computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()
#     if not signature or not hmac.compare_digest(computed, signature):
#         return HttpResponseForbidden('Invalid signature')

#     event = json.loads(payload.decode())
#     if event.get('event') in ('charge.success','payment.success'):
#         data = event.get('data', {})
#         reference = data.get('reference')
#         try:
#             order = Order.objects.get(reference=reference)
#         except Order.DoesNotExist:
#             return HttpResponse(status=200)  # ignore unknown

#         # idempotent: check if Payment exists
#         if hasattr(order, 'payment'):
#             return HttpResponse(status=200)

#         amount = data.get('amount', 0)
#         Payment.objects.create(order=order, gateway='paystack', gateway_reference=reference, amount=amount, status=data.get('status','success'), raw_response=data)
#         order.status = 'paid'
#         order.paid_at = timezone.now()
#         order.save(update_fields=['status','paid_at'])

#         # business logic: unlock exam if fee item present
#         for it in order.items.all():
#             if it.product and it.product.sku.startswith('FEE-'):
#                 if order.user:
#                     order.user.can_take_exam = True
#                     order.user.save(update_fields=['can_take_exam'])

#     return HttpResponse(status=200)
