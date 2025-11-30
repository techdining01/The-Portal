import requests
import json
import secrets
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

class PaystackPayment:
    """
    A reusable Paystack payment class for handling payments, verification, and webhooks
    """
    
    def __init__(self):
        self.public_key = settings.PAYSTACK_TEST_PUBLIC_KEY 
        self.secret_key = settings.PAYSTACK_TEST_SECRET_KEY 
        self.base_url = settings.PAYSTACK_BASE_URL
        
    def initialize_payment(self, email, amount, callback_url=None, metadata=None, reference=None):
        """
        Initialize a Paystack payment
        
        Args:
            email (str): Customer email
            amount (float): Amount in Naira
            callback_url (str): Callback URL after payment
            metadata (dict): Additional data
            reference (str): Custom reference (optional)
            
        Returns:
            dict: Payment initialization response
        """
        try:
            # Convert amount to kobo (Paystack uses kobo)
            amount_in_kobo = int(amount * 100)
            
            # Generate reference if not provided
            if not reference:
                reference = self.generate_reference()
            
            url = f"{self.base_url}/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'email': email,
                'amount': amount_in_kobo,
                'reference': reference,
                'callback_url': callback_url or settings.PAYMENT_SUCCESS_URL,
                'metadata': metadata or {}
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response_data.get('status'):
                return {
                    'success': True,
                    'authorization_url': response_data['data']['authorization_url'],
                    'access_code': response_data['data']['access_code'],
                    'reference': reference
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('message', 'Payment initialization failed'),
                    'reference': reference
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'reference': reference
            }
    
    def verify_payment(self, reference):
        """
        Verify a Paystack payment
        
        Args:
            reference (str): Payment reference
            
        Returns:
            dict: Payment verification response
        """
        try:
            url = f"{self.base_url}/transaction/verify/{reference}"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
            }
            
            response = requests.get(url, headers=headers)
            response_data = response.json()
            
            if response_data.get('status') and response_data['data']['status'] == 'success':
                payment_data = response_data['data']
                return {
                    'success': True,
                    'verified': True,
                    'data': {
                        'reference': payment_data['reference'],
                        'amount': payment_data['amount'] / 100,  # Convert back to Naira
                        'currency': payment_data['currency'],
                        'channel': payment_data['channel'],
                        'paid_at': payment_data['paid_at'],
                        'customer': payment_data['customer'],
                        'metadata': payment_data.get('metadata', {})
                    }
                }
            else:
                return {
                    'success': True,
                    'verified': False,
                    'data': response_data.get('data', {})
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_transfer_recipient(self, name, account_number, bank_code, currency='NGN'):
        """
        Create a transfer recipient for payouts
        
        Args:
            name (str): Recipient name
            account_number (str): Bank account number
            bank_code (str): Bank code from Paystack
            currency (str): Currency code
            
        Returns:
            dict: Recipient creation response
        """
        try:
            url = f"{self.base_url}/transferrecipient"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'type': 'nuban',
                'name': name,
                'account_number': account_number,
                'bank_code': bank_code,
                'currency': currency
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response_data.get('status'):
                return {
                    'success': True,
                    'recipient_code': response_data['data']['recipient_code'],
                    'data': response_data['data']
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('message', 'Recipient creation failed')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def initiate_transfer(self, amount, recipient_code, reason=None, reference=None):
        """
        Initiate a transfer to a recipient
        
        Args:
            amount (float): Amount in Naira
            recipient_code (str): Recipient code from Paystack
            reason (str): Transfer reason
            reference (str): Custom reference
            
        Returns:
            dict: Transfer initiation response
        """
        try:
            amount_in_kobo = int(amount * 100)
            
            if not reference:
                reference = self.generate_reference()
                
            url = f"{self.base_url}/transfer"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'source': 'balance',
                'amount': amount_in_kobo,
                'recipient': recipient_code,
                'reference': reference,
                'reason': reason or 'Payment transfer'
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response_data.get('status'):
                return {
                    'success': True,
                    'transfer_code': response_data['data']['transfer_code'],
                    'reference': reference,
                    'data': response_data['data']
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('message', 'Transfer initiation failed')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_banks(self, country='nigeria'):
        """
        Get list of supported banks
        
        Args:
            country (str): Country code
            
        Returns:
            dict: List of banks
        """
        try:
            url = f"{self.base_url}/bank?country={country}"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
            }
            
            response = requests.get(url, headers=headers)
            response_data = response.json()
            
            if response_data.get('status'):
                return {
                    'success': True,
                    'banks': response_data['data']
                }
            else:
                return {
                    'success': False,
                    'error': response_data.get('message', 'Failed to fetch banks')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_reference(self):
        """Generate unique payment reference"""
        return f"PYMT_{secrets.token_hex(10).upper()}"
    
    def validate_webhook_signature(self, payload, signature):
        """
        Validate Paystack webhook signature
        
        Args:
            payload (bytes): Raw request body
            signature (str): X-Paystack-Signature header
            
        Returns:
            bool: True if signature is valid
        """
        import hashlib
        import hmac
        
        # For production, implement proper signature validation
        # This is a simplified version
        computed_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)


# Create a global instance for easy import
paystack = PaystackPayment()