import requests
from django.conf import settings

def verify_reference(reference):
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    resp = requests.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data  # inspect data['data']['status'] == 'success'
