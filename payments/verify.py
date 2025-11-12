import requests, os


def verify_reference(reference):
    headers = {"Authorization": " Bearer os.getenv(PAYSTACK_SECRET_KEY)"}
    resp = requests.get(f" os.getenv(PAYSTACK_BASE_URL)/transaction/verify/{reference}", headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data  # inspect data['data']['status'] == 'success'
