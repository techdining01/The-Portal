import os, json, uuid, hmac, hashlib, requests, random, string
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from .models import FeeItem, Payment
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

User = get_user_model()

PAYSTACK_BASE = os.getenv('PAYSTACK_BASE_URL')
PAYSTACK_SECRET = os.getenv('PAYSTACK_SECRET_KEY')


@require_POST
def init_paystack(request):
    """Initialize a Paystack transaction for a given user and payment type.
    Expects JSON body: {"user_id": <id>, "payment_type": "tuition", "amount": 50000}
    amount is in Naira (we convert to kobo for Paystack).
    Returns authorization_url for redirection.
    """
    try:
        payload = json.loads(request.body)
        user_id = payload['user_id']
        payment_type = payload['payment_type']
        amount_naira = float(payload['amount'])
    except Exception:
        return HttpResponseBadRequest('Invalid payload')

    user = get_object_or_404(User, pk=user_id)
    # create Payment record
    ref = f"pay-{user_id}-{uuid.uuid4().hex[:8]}"
    payment = Payment.objects.create(
        student=user,
        payment_type=payment_type,
        amount=amount_naira,
        reference=ref,
        status='pending'
    )

    # prepare paystack init
    data = {
        'email': getattr(user, 'parent_email', '') or getattr(user, 'email', ''),
        'amount': int(amount_naira * 100),  # kobo
        'reference': ref,
        'metadata': {'payment_id': payment.id, 'student_id': user_id, 'payment_type': payment_type}
    }
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET}', 'Content-Type': 'application/json'}
    resp = requests.post(f"{PAYSTACK_BASE}/transaction/initialize", json=data, headers=headers, timeout=30)
    resp.raise_for_status()
    j = resp.json()
    return JsonResponse({'authorization_url': j['data']['authorization_url'], 'data': j['data']})

@csrf_exempt
def paystack_webhook(request):
    # verify signature
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE') or request.headers.get('x-paystack-signature')
    secret = os.getenv('PAYSTACK_SECRET_KEY').encode()
    computed = hmac.new(secret, request.body, hashlib.sha512).hexdigest()
    if not signature or not hmac.compare_digest(computed, signature):
        return HttpResponseForbidden('Invalid signature')

    payload = json.loads(request.body)
    event = payload.get('event')
    if event in ('charge.success','payment.success'):
        d = payload.get('data',{})
        reference = d.get('reference')
        amt = d.get('amount',0) / 100.0
        # find payment by reference or metadata
        payment = None
        payment_id = d.get('metadata',{}).get('payment_id')
        if payment_id:
            try:
                payment = Payment.objects.get(pk=payment_id)
            except Payment.DoesNotExist:
                payment = None
        if not payment:
            payment = Payment.objects.filter(reference=reference).first()
        if payment and not payment.is_paid:
            payment.is_paid = True
            payment.verified = True
            payment.status = 'success'
            payment.paid_at = d.get('paid_at') or None
            payment.amount = amt
            payment.save()
            # update user access: only set can_take_exam True if payment succeeded
            user = payment.student
            user.can_take_exam = True
            user.save(update_fields=['can_take_exam'])
    return HttpResponse(status=200)

#@user_passes_test(lambda u: u.is_superuser or u.role in ['superadmin','admin'])
def payment_dashboard(request):
    # show classes and students with payments
    from exams.models import Class
    classes = Class.objects.prefetch_related('student_class__payments').all()
    return render(request, 'payments/dashboard.html', {'classes': classes})

@user_passes_test(lambda u: u.is_superuser or u.role in ['superadmin','admin'])
def toggle_exam_access(request, user_id):
    if request.method == 'POST':
        u = get_object_or_404(User, pk=user_id)
        u.can_take_exam = not u.can_take_exam
        u.save(update_fields=['can_take_exam'])
        return JsonResponse({'status':'ok','can_take_exam':u.can_take_exam})
    return HttpResponseBadRequest()



def pay_now_page(request):
    # optionally show payment types and start payment flow
    return render(request, 'payments/pay_now.html', {
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'paystack_mode': settings.PAYSTACK_MODE,
        'currency_symbol': '₦',
    })



def generate_reference():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))


def payment_page(request):
    fees = FeeItem.objects.all()
    if request.method == "POST":
        reg_number = request.POST.get("registration_number")
        selected_fees = request.POST.getlist("fees")

        try:
            student = User.objects.get(registration_number=reg_number)
        except User.DoesNotExist:
            return render(request, "payments/payment_page.html", {"fees": fees, "error": "Invalid registration number."})

        selected_fee_items = FeeItem.objects.filter(id__in=selected_fees)
        total = sum(item.amount for item in selected_fee_items)
        reference = generate_reference()

        payment = Payment.objects.create(student=student, total_amount=total, reference=reference)
        payment.fee_items.set(selected_fee_items)

        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        data = {
            "email": student.user.email,
            "amount": int(total * 100),  # in kobo
            "reference": reference,
            "callback_url": request.build_absolute_uri("/payments/verify/"),
        }
        response = requests.post(paystack_url, headers=headers, json=data)
        res_data = response.json()

        if res_data.get("status"):
            return redirect(res_data["data"]["authorization_url"])
        else:
            return render(request, "payments/payment_page.html", {"fees": fees, "error": "Error initializing payment."})

    return render(request, "payments/payment_page.html", {"fees": fees})


@csrf_exempt
def verify_payment(request):
    """
    Verifies Paystack payment via webhook or redirect callback
    """
    if request.method == "POST":
        payload = json.loads(request.body.decode("utf-8"))
        event = payload.get("event")

        if event == "charge.success":
            reference = payload["data"]["reference"]
            amount = payload["data"]["amount"] / 100  # convert from kobo
            email = payload["data"]["customer"]["email"]

            try:
                payment = Payment.objects.get(reference=reference)
                payment.verified = True
                payment.save()

                # Unlock exam access
                student = payment.student
                user = student.user
                user.can_take_exam = True
                user.save()

                print(f"[✅] Payment verified for {student.registration_number} ({email})")

            except ObjectDoesNotExist:
                print("[❌] Payment reference not found:", reference)

        return HttpResponse(status=200)

    # If callback redirect (Paystack redirects after success)
    reference = request.GET.get("reference")
    if reference:
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        url = f"https://api.paystack.co/transaction/verify/{reference}"

        response = requests.get(url, headers=headers)
        res_data = response.json()

        if res_data.get("status") and res_data["data"]["status"] == "success":
            payment = Payment.objects.get(reference=reference)
            payment.verified = True
            payment.save()

            student = payment.student
            user = student.user
            user.can_take_exam = True
            user.save()

            context = {
                "success": True,
                "student": student,
                "amount": payment.total_amount,
                "reference": reference,
                "timestamp": timezone.now(),
            }
            return render(request, "payments/verify_success.html", context)
        else:
            return render(request, "payments/verify_failed.html", {"reference": reference})

    return HttpResponse(status=400)
