import uuid
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from .models import ShopItem, Order
from .cart import Cart


def checkout(request):
    cart = Cart(request)
    items = []
    total = 0

    for item_id, data in cart.cart.items():
        item = ShopItem.objects.get(id=item_id)
        qty = data["qty"]
        price = item.price * qty
        total += price

        items.append({
            "item": item,
            "qty": qty,
            "subtotal": price
        })

    reference = f"BRILLS-{uuid.uuid4().hex[:10]}"

    order = Order.objects.create(
        parent=request.user,
        reference=reference,
        amount=total,
        meta={"items": items}
    )

    return render(request, "shop/checkout.html", {
        "order": order,
        "total": total,
        "public_key": settings.PAYSTACK_PUBLIC_KEY
    })


def verify_payment(request, ref):
    url = f"https://api.paystack.co/transaction/verify/{ref}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    res = requests.get(url, headers=headers).json()

    if res["data"]["status"] == "success":
        order = Order.objects.get(reference=ref)
        order.status = "paid"
        order.save()

        # Unlock exam access automatically
        student = request.user
        student.can_take_exam = True
        student.save()

        return render(request, "shop/payment_success.html")

    return render(request, "shop/payment_failed.html")
