import hmac
import hashlib
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import Invoice, Payment
from .signals import payment_successful
from django.contrib.auth import get_user_model



User = get_user_model()

@csrf_exempt
def paystack_webhook(request):
    """
    Verifies Paystack HMAC signature, records Payment + Invoice changes,
    emits payment_successful signal for other apps to listen to.
    """
    payload = request.body  # raw bytes
    # Paystack signs with x-paystack-signature header (HMAC SHA512)
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE') or request.headers.get('x-paystack-signature')
    secret = settings.PAYSTACK_SECRET_KEY.encode()

    computed = hmac.new(secret, payload, hashlib.sha512).hexdigest()

    if not signature or not hmac.compare_digest(computed, signature):
        return HttpResponseForbidden('Invalid signature')

    data = json.loads(payload)
    event = data.get('event')

    if event in ('charge.success', 'payment.success'):
        d = data.get('data', {})
        reference = d.get('reference')

        # idempotent: if Payment with this gateway_reference exists, ignore
        if Payment.objects.filter(gateway_reference=reference).exists():
            return HttpResponse(status=200)

        # Find invoice by reference or metadata
        invoice = None
        invoice_id = None
        # Prefer metadata invoice_id if present
        try:
            invoice_id = d.get('metadata', {}).get('invoice_id')
            if invoice_id:
                invoice = Invoice.objects.filter(pk=invoice_id).first()
        except Exception:
            invoice = None

        # Fallback: find invoice by stored reference
        if invoice is None:
            invoice = Invoice.objects.filter(reference=reference).first()

        # Create Payment record
        payment = Payment.objects.create(
            invoice=invoice,
            gateway='paystack',
            gateway_reference=reference,
            amount=d.get('amount', 0),
            status=d.get('status', 'success'),
            raw_response=d
        )

        # Mark invoice as paid
        if invoice:
            invoice.paid = True
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=['paid', 'paid_at'])

            # Emit signal for other apps (CBT) to listen
            try:
                payment_successful.send(
                    sender='payments.webhook',
                    student_id=invoice.student_id,
                    invoice_id=invoice.id,
                    payment_id=payment.id,
                    gateway='paystack',
                    amount=payment.amount,
                    raw_response=payment.raw_response
                )
            except Exception as e:
                # don't crash webhook on signal errors; log if you have logging
                print("Payment signal dispatch failed:", e)

         
            # Giving the user permission to take exams or set an 'fees_paid' flag.
    
            user = invoice.student  # this is a users.User instance
            if hasattr(user, 'approved'):
                user.approved = True
                user.save(update_fields=['approved'])

            '''
                Only paid students can take exams.on the exam checking side, ensure to check
                user.approved before allowing access. i will call payment app from exam app 
                invoking the signal payment_successful or invoice paid status 
                
            '''
            
            # Or, to create a simple Fee record in your exams app: 
            # i should have a payment template with search functionality student payment history and status
            from exams.models import ActionLog
            ActionLog.objects.create(user=user, action_type='payment', description=f'Invoice {invoice.id} paid')
           

        return HttpResponse(status=200)

    # For other events, just respond 200
    return HttpResponse(status=200)
