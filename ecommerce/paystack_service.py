import requests
import json
from django.conf import settings
from django.urls import reverse
from decimal import Decimal

class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_TEST_SECRET_KEY
        self.public_key = settings.PAYSTACK_TEST_PUBLIC_KEY
        self.base_url = 'https://api.paystack.co'
        
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(self, email, amount, reference, callback_url, metadata=None):
        """Initialize Paystack transaction"""
        amount_in_kobo = int(amount * 100)
        
        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'callback_url': callback_url,
            'metadata': metadata or {}
        }
        
        url = f"{self.base_url}/transaction/initialize"
        response = requests.post(url, headers=self.get_headers(), data=json.dumps(payload))
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Paystack API error: {response.text}")
    
    def verify_transaction(self, reference):
        """Verify Paystack transaction"""
        url = f"{self.base_url}/transaction/verify/{reference}"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Paystack verification error: {response.text}")
    
    def create_transfer_recipient(self, name, account_number, bank_code, description=None):
        """Create transfer recipient for refunds"""
        payload = {
            'type': 'nuban',
            'name': name,
            'account_number': account_number,
            'bank_code': bank_code,
            'currency': 'NGN',
            'description': description or f"Recipient for {name}"
        }
        
        url = f"{self.base_url}/transferrecipient"
        response = requests.post(url, headers=self.get_headers(), data=json.dumps(payload))
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Paystack recipient creation error: {response.text}")
    
    def initiate_transfer(self, amount, recipient, reason=None):
        """Initiate transfer for refunds"""
        amount_in_kobo = int(amount * 100)
        
        payload = {
            'source': 'balance',
            'amount': amount_in_kobo,
            'recipient': recipient,
            'reason': reason or 'Refund'
        }
        
        url = f"{self.base_url}/transfer"
        response = requests.post(url, headers=self.get_headers(), data=json.dumps(payload))
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Paystack transfer error: {response.text}")

class OPayService:
    """OPay Service (Similar structure to Paystack)"""
    def __init__(self):
        self.public_key = settings.OPAY_PUBLIC_KEY
        self.secret_key = settings.OPAY_SECRET_KEY
        self.base_url = 'https://api.opay.com'  # OPay API URL
        
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(self, email, amount, reference, callback_url, metadata=None):
        """Initialize OPay transaction"""
        # Similar implementation to Paystack
        # You'll need to check OPay API documentation
        pass
    
    def verify_transaction(self, reference):
        """Verify OPay transaction"""
        # Similar implementation to Paystack
        pass

# Utility functions
def generate_payment_reference():
    import uuid
    return f"REF_{uuid.uuid4().hex[:10].upper()}"

def format_amount_for_gateway(amount):
    """Convert decimal amount to kobo/cents"""
    return int(amount * 100)