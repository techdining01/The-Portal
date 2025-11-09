import hmac, hashlib, json
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import Invoice, Payment

@csrf_exempt
def paystack_webhook(request):
    # raw body (bytes)
    payload = request.body
    # header name can be lowercase in some environments
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE') or request.headers.get('x-paystack-signature')

    # compute HMAC SHA512
    secret = settings.PAYSTACK_SECRET_KEY.encode()
    computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()

    # Compare securely
    if not signature or not hmac.compare_digest(computed, signature):
        return HttpResponseForbidden("Invalid signature")

    data = json.loads(payload)
    event = data.get('event')
    # handle relevant events e.g. charge.success
    if event == 'charge.success' or event == 'payment.success':
        d = data.get('data', {})
        reference = d.get('reference')
        # idempotent: do nothing if payment exists
        if Payment.objects.filter(gateway_reference=reference).exists():
            return HttpResponse(status=200)
        invoice_id = d.get('metadata', {}).get('invoice_id')
        invoice = Invoice.objects.filter(pk=invoice_id).first()
        Payment.objects.create(
            invoice=invoice,
            gateway='paystack',
            gateway_reference=reference,
            amount=d.get('amount', 0),
            status=d.get('status', 'success'),
            raw_response=d
        )
        if invoice:
            invoice.paid = True
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=['paid', 'paid_at'])

    ###----------------Link CBT APP -------------------------------###
            # link to CBT: you can call internal function here to unlock features
            # to authorise student, bawo ni ki n se oo, ok i got it. @Exam time i will update 
            # their login page to login with thir receipt

    return HttpResponse(status=200)
