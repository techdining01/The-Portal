import os, uuid, json, requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Invoice

PAYSTACK_SECRET = settings.PAYSTACK_SECRET_KEY
PAYSTACK_BASE = settings.PAYSTACK_BASE_URL

@require_POST
def init_paystack(request):
    """
    Body JSON: {"invoice_id": 12}
    Returns JSON with authorization_url to redirect user to pay.
    """
    try:
        payload = json.loads(request.body)
        invoice_id = payload.get("invoice_id")
        invoice = Invoice.objects.get(pk=invoice_id)
    except Exception:
        return HttpResponseBadRequest("Invalid invoice")

    # create unique reference
    reference = f"school-{invoice.id}-{uuid.uuid4().hex[:8]}"
    invoice.reference = reference
    invoice.save(update_fields=['reference'])

    data = {
        "email": invoice.student.parent_email if hasattr(invoice.student, 'parent_email') else "no-reply@example.com",
        "amount": invoice.amount,   
        "reference": reference,
        "metadata": {
            "invoice_id": invoice.id,
            "student_id": invoice.student.id,
            "purpose": invoice.description
        }
    }
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET}",
        "Content-Type": "application/json"
    }

    resp = requests.post(f"{PAYSTACK_BASE}/transaction/initialize", json=data, headers=headers, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    # return authorization_url and access data to frontend
    return JsonResponse({
        "authorization_url": payload['data']['authorization_url'],
        "access": payload['data']
    })
