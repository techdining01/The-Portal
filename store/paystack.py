import requests
from django.conf import settings

class Paystack:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
    
    def _make_request(self, method, endpoint, data=None):
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            else:
                response = requests.post(url, headers=headers, json=data)
            
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'status': False, 'message': str(e)}
    
    def initialize_transaction(self, email, amount, reference, callback_url=None):
        data = {
            'email': email,
            'amount': amount,
            'reference': reference,
            'callback_url': callback_url
        }
        return self._make_request('POST', '/transaction/initialize', data)
    
    def verify_transaction(self, reference):
        return self._make_request('GET', f'/transaction/verify/{reference}')
    
    def create_customer(self, email, first_name=None, last_name=None, phone=None):
        data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone
        }
        return self._make_request('POST', '/customer', data)