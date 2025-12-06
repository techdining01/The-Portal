import requests
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from .models import Payment, Order, FeePayment

logger = logging.getLogger(__name__)

class PaystackAPI:
    """Paystack API integration for BrillsPay"""
    
    def __init__(self, secret_key=None):
        self.secret_key = secret_key or settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
    
    def initialize_transaction(self, email, amount, reference, metadata=None, callback_url=None):
        """
        Initialize a Paystack transaction
        
        Args:
            email: Customer email
            amount: Amount in Naira (will be converted to kobo)
            reference: Unique transaction reference
            metadata: Additional data to store with transaction
            callback_url: Callback URL for payment verification
            
        Returns:
            Dictionary with transaction data or error
        """
        try:
            # Convert amount to kobo (Paystack uses kobo for NGN)
            amount_kobo = int(float(amount) * 100)
            
            payload = {
                'email': email,
                'amount': amount_kobo,
                'reference': reference,
                'callback_url': callback_url or settings.PAYSTACK_CALLBACK_URL,
                'metadata': metadata or {}
            }
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'authorization_url': data['data']['authorization_url'],
                    'access_code': data['data']['access_code'],
                    'reference': data['data']['reference']
                }
            else:
                logger.error(f"Paystack initialization failed: {data.get('message', 'Unknown error')}")
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to initialize payment')
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request error: {str(e)}")
            return {
                'success': False,
                'message': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Paystack initialization error: {str(e)}")
            return {
                'success': False,
                'message': f"Payment initialization failed: {str(e)}"
            }
    
    def verify_transaction(self, reference):
        """
        Verify a Paystack transaction
        
        Args:
            reference: Transaction reference to verify
            
        Returns:
            Dictionary with verification data
        """
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') and data['data']['status'] == 'success':
                # Convert amount from kobo to Naira
                amount_ngn = Decimal(data['data']['amount']) / Decimal('100')
                
                return {
                    'success': True,
                    'verified': True,
                    'amount': amount_ngn,
                    'currency': data['data']['currency'],
                    'transaction_date': data['data']['transaction_date'],
                    'gateway_response': data['data']['gateway_response'],
                    'channel': data['data']['channel'],
                    'paid_at': data['data']['paid_at'],
                    'metadata': data['data'].get('metadata', {}),
                    'customer': data['data'].get('customer', {}),
                    'authorization': data['data'].get('authorization', {}),
                    'raw_response': data
                }
            else:
                return {
                    'success': False,
                    'verified': False,
                    'message': data.get('message', 'Transaction verification failed'),
                    'gateway_response': data['data'].get('gateway_response', ''),
                    'raw_response': data
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification request error: {str(e)}")
            return {
                'success': False,
                'verified': False,
                'message': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {
                'success': False,
                'verified': False,
                'message': f"Verification failed: {str(e)}"
            }
    
    def create_transfer_recipient(self, name, account_number, bank_code, description=None):
        """
        Create a transfer recipient for disbursements
        
        Args:
            name: Recipient name
            account_number: Bank account number
            bank_code: Bank code from Paystack's bank list
            description: Optional description
            
        Returns:
            Dictionary with recipient data
        """
        try:
            payload = {
                'type': 'nuban',
                'name': name,
                'account_number': account_number,
                'bank_code': bank_code,
                'currency': 'NGN',
                'description': description or f"Recipient for {name}"
            }
            
            response = requests.post(
                f"{self.base_url}/transferrecipient",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'recipient_code': data['data']['recipient_code'],
                    'details': data['data']['details']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to create recipient')
                }
                
        except Exception as e:
            logger.error(f"Paystack create recipient error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to create recipient: {str(e)}"
            }
    
    def initiate_transfer(self, recipient_code, amount, reason, reference=None):
        """
        Initiate a transfer to a recipient
        
        Args:
            recipient_code: Recipient code from create_transfer_recipient
            amount: Amount in Naira
            reason: Transfer reason
            reference: Optional custom reference
            
        Returns:
            Dictionary with transfer data
        """
        try:
            # Convert amount to kobo
            amount_kobo = int(float(amount) * 100)
            
            payload = {
                'source': 'balance',
                'amount': amount_kobo,
                'recipient': recipient_code,
                'reason': reason,
                'reference': reference or f"TRF-{timezone.now().timestamp()}"
            }
            
            response = requests.post(
                f"{self.base_url}/transfer",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'transfer_code': data['data']['transfer_code'],
                    'reference': data['data']['reference'],
                    'status': data['data']['status']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to initiate transfer')
                }
                
        except Exception as e:
            logger.error(f"Paystack transfer initiation error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to initiate transfer: {str(e)}"
            }
    
    def verify_transfer(self, reference):
        """
        Verify a transfer status
        
        Args:
            reference: Transfer reference
            
        Returns:
            Dictionary with transfer status
        """
        try:
            response = requests.get(
                f"{self.base_url}/transfer/verify/{reference}",
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'status': data['data']['status'],
                'amount': Decimal(data['data']['amount']) / Decimal('100'),
                'recipient': data['data']['recipient'],
                'reason': data['data']['reason']
            }
                
        except Exception as e:
            logger.error(f"Paystack transfer verification error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to verify transfer: {str(e)}"
            }
    
    def list_transactions(self, per_page=50, page=1, **kwargs):
        """
        List Paystack transactions
        
        Args:
            per_page: Items per page (max 100)
            page: Page number
            **kwargs: Additional filters (customer, status, etc.)
            
        Returns:
            List of transactions
        """
        try:
            params = {
                'perPage': min(per_page, 100),
                'page': page,
                **kwargs
            }
            
            response = requests.get(
                f"{self.base_url}/transaction",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'transactions': data['data'],
                    'meta': data.get('meta', {})
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to fetch transactions')
                }
                
        except Exception as e:
            logger.error(f"Paystack list transactions error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to fetch transactions: {str(e)}"
            }
    
    def create_subscription(self, customer_email, plan_code, start_date=None, authorization_code=None):
        """
        Create a subscription plan
        
        Args:
            customer_email: Customer email
            plan_code: Paystack plan code
            start_date: Subscription start date (defaults to now)
            authorization_code: Customer authorization code
            
        Returns:
            Subscription data
        """
        try:
            payload = {
                'customer': customer_email,
                'plan': plan_code,
                'start_date': start_date or timezone.now().isoformat()
            }
            
            if authorization_code:
                payload['authorization'] = authorization_code
            
            response = requests.post(
                f"{self.base_url}/subscription",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'subscription_code': data['data']['subscription_code'],
                    'email_token': data['data']['email_token'],
                    'status': data['data']['status']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to create subscription')
                }
                
        except Exception as e:
            logger.error(f"Paystack create subscription error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to create subscription: {str(e)}"
            }
    
    def list_banks(self, country='nigeria'):
        """
        Get list of banks
        
        Args:
            country: Country code (default: nigeria)
            
        Returns:
            List of banks
        """
        try:
            response = requests.get(
                f"{self.base_url}/bank",
                headers=self.headers,
                params={'country': country},
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'banks': data['data']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to fetch banks')
                }
                
        except Exception as e:
            logger.error(f"Paystack list banks error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to fetch banks: {str(e)}"
            }
    
    def resolve_account_number(self, account_number, bank_code):
        """
        Resolve account number to account name
        
        Args:
            account_number: Bank account number
            bank_code: Paystack bank code
            
        Returns:
            Account name and details
        """
        try:
            response = requests.get(
                f"{self.base_url}/bank/resolve",
                headers=self.headers,
                params={
                    'account_number': account_number,
                    'bank_code': bank_code
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'account_name': data['data']['account_name'],
                    'account_number': data['data']['account_number']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to resolve account')
                }
                
        except Exception as e:
            logger.error(f"Paystack resolve account error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to resolve account: {str(e)}"
            }
    
    def create_plan(self, name, amount, interval, description=None):
        """
        Create a subscription plan
        
        Args:
            name: Plan name
            amount: Amount in Naira per interval
            interval: Interval (daily, weekly, monthly, annually)
            description: Plan description
            
        Returns:
            Plan data
        """
        try:
            # Convert amount to kobo
            amount_kobo = int(float(amount) * 100)
            
            payload = {
                'name': name,
                'amount': amount_kobo,
                'interval': interval,
                'description': description or name
            }
            
            response = requests.post(
                f"{self.base_url}/plan",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'plan_code': data['data']['plan_code'],
                    'plan_id': data['data']['id']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to create plan')
                }
                
        except Exception as e:
            logger.error(f"Paystack create plan error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to create plan: {str(e)}"
            }
    
    def charge_authorization(self, authorization_code, email, amount, reference=None):
        """
        Charge a previously authorized card
        
        Args:
            authorization_code: Customer authorization code
            email: Customer email
            amount: Amount in Naira
            reference: Transaction reference
            
        Returns:
            Transaction data
        """
        try:
            # Convert amount to kobo
            amount_kobo = int(float(amount) * 100)
            
            payload = {
                'authorization_code': authorization_code,
                'email': email,
                'amount': amount_kobo,
                'reference': reference or f"CHG-{timezone.now().timestamp()}"
            }
            
            response = requests.post(
                f"{self.base_url}/transaction/charge_authorization",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') and data['data']['status'] == 'success':
                return {
                    'success': True,
                    'reference': data['data']['reference'],
                    'amount': Decimal(data['data']['amount']) / Decimal('100'),
                    'status': data['data']['status']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Charge authorization failed'),
                    'gateway_response': data['data'].get('gateway_response', '')
                }
                
        except Exception as e:
            logger.error(f"Paystack charge authorization error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to charge authorization: {str(e)}"
            }
    
    def check_balance(self):
        """
        Check Paystack account balance
        
        Returns:
            Account balance
        """
        try:
            response = requests.get(
                f"{self.base_url}/balance",
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return {
                    'success': True,
                    'balance': data['data'][0]['balance'],
                    'currency': data['data'][0]['currency']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to check balance')
                }
                
        except Exception as e:
            logger.error(f"Paystack check balance error: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to check balance: {str(e)}"
            }


# ==================== PAYSTACK HELPER FUNCTIONS ====================

class PaystackHelper:
    """Helper functions for Paystack integration"""
    
    @staticmethod
    def generate_reference(prefix='PY'):
        """Generate unique Paystack reference"""
        import uuid
        import time
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}-{timestamp}-{unique_id}"
    
    @staticmethod
    def validate_webhook_signature(payload, signature):
        """
        Validate Paystack webhook signature
        
        Args:
            payload: Request body
            signature: X-Paystack-Signature header
            
        Returns:
            Boolean indicating if signature is valid
        """
        import hmac
        import hashlib
        
        secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
        computed_signature = hmac.new(secret, payload, hashlib.sha512).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
    
    @staticmethod
    def parse_webhook_payload(payload):
        """
        Parse Paystack webhook payload
        
        Args:
            payload: Webhook JSON payload
            
        Returns:
            Parsed event and data
        """
        try:
            import json
            data = json.loads(payload)
            
            event = data.get('event', '')
            payment_data = data.get('data', {})
            
            # Common events
            if event == 'charge.success':
                return {
                    'event': 'payment_success',
                    'reference': payment_data.get('reference'),
                    'amount': Decimal(payment_data.get('amount', 0)) / Decimal('100'),
                    'status': payment_data.get('status'),
                    'metadata': payment_data.get('metadata', {})
                }
            elif event == 'charge.failed':
                return {
                    'event': 'payment_failed',
                    'reference': payment_data.get('reference'),
                    'message': payment_data.get('gateway_response', 'Payment failed'),
                    'metadata': payment_data.get('metadata', {})
                }
            elif event == 'transfer.success':
                return {
                    'event': 'transfer_success',
                    'reference': payment_data.get('reference'),
                    'amount': Decimal(payment_data.get('amount', 0)) / Decimal('100'),
                    'recipient': payment_data.get('recipient', {})
                }
            elif event == 'transfer.failed':
                return {
                    'event': 'transfer_failed',
                    'reference': payment_data.get('reference'),
                    'reason': payment_data.get('reason', 'Transfer failed'),
                    'recipient': payment_data.get('recipient', {})
                }
            elif event == 'subscription.create':
                return {
                    'event': 'subscription_created',
                    'subscription_code': payment_data.get('subscription_code'),
                    'customer': payment_data.get('customer', {})
                }
            elif event == 'subscription.disable':
                return {
                    'event': 'subscription_disabled',
                    'subscription_code': payment_data.get('subscription_code'),
                    'customer': payment_data.get('customer', {})
                }
            else:
                return {
                    'event': event,
                    'data': payment_data
                }
                
        except Exception as e:
            logger.error(f"Error parsing webhook payload: {str(e)}")
            return None
    
    @staticmethod
    def create_order_metadata(order):
        """
        Create metadata for order payment
        
        Args:
            order: Order object
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'order_id': order.id,
            'order_number': order.order_number,
            'user_id': order.user.id,
            'user_email': order.user.email,
            'user_name': order.user.get_full_name(),
            'custom_fields': [
                {
                    'display_name': 'Order Type',
                    'variable_name': 'order_type',
                    'value': 'product_purchase'
                }
            ]
        }
        
        if order.student:
            metadata['student_id'] = order.student.id
            metadata['student_name'] = order.student.get_full_name()
            metadata['student_admission'] = order.student.admission_number
            metadata['custom_fields'].append({
                'display_name': 'Student',
                'variable_name': 'student',
                'value': order.student.get_full_name()
            })
        
        return metadata
    
    @staticmethod
    def create_fee_payment_metadata(fee_payment):
        """
        Create metadata for fee payment
        
        Args:
            fee_payment: FeePayment object
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'fee_payment_id': fee_payment.id,
            'student_id': fee_payment.student.id,
            'student_name': fee_payment.student.get_full_name(),
            'student_admission': fee_payment.student.admission_number,
            'fee_structure': fee_payment.fee_structure.name,
            'academic_year': fee_payment.fee_structure.academic_year,
            'term': fee_payment.fee_structure.get_term_display(),
            'custom_fields': [
                {
                    'display_name': 'Payment Type',
                    'variable_name': 'payment_type',
                    'value': 'school_fee'
                },
                {
                    'display_name': 'Student Class',
                    'variable_name': 'student_class',
                    'value': fee_payment.student.current_class
                }
            ]
        }
        
        if fee_payment.student.user:
            metadata['parent_id'] = fee_payment.student.user.id
            metadata['parent_email'] = fee_payment.student.user.email
            metadata['parent_name'] = fee_payment.student.user.get_full_name()
        
        return metadata


# ==================== PAYSTACK INTEGRATION SERVICE ====================

class PaystackService:
    """Service layer for Paystack operations"""
    
    def __init__(self):
        self.api = PaystackAPI()
        self.helper = PaystackHelper()
    
    def process_order_payment(self, order, request):
        """
        Process order payment through Paystack
        
        Args:
            order: Order object
            request: HTTP request object
            
        Returns:
            Dictionary with payment initialization result
        """
        try:
            # Generate unique reference
            reference = self.helper.generate_reference('ORD')
            
            # Create metadata
            metadata = self.helper.create_order_metadata(order)
            
            # Build callback URL
            callback_url = request.build_absolute_uri(
                f'/store/payment/verify/{reference}/'
            )
            
            # Initialize payment
            result = self.api.initialize_transaction(
                email=order.user.email,
                amount=order.total_amount,
                reference=reference,
                metadata=metadata,
                callback_url=callback_url
            )
            
            if result['success']:
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    reference=reference,
                    amount=order.total_amount,
                    payment_method='paystack',
                    payer_email=order.user.email,
                    payer_name=order.user.get_full_name(),
                    payer_phone=order.user.phone,
                    paystack_reference=result['reference'],
                    paystack_access_code=result['access_code'],
                    gateway_response={'initialization': result}
                )
                
                logger.info(f"Payment initialized for order {order.id}: {reference}")
                
                return {
                    'success': True,
                    'payment': payment,
                    'authorization_url': result['authorization_url'],
                    'reference': reference
                }
            else:
                logger.error(f"Failed to initialize payment for order {order.id}: {result.get('message')}")
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to initialize payment')
                }
                
        except Exception as e:
            logger.error(f"Error processing order payment: {str(e)}")
            return {
                'success': False,
                'message': f"Payment processing error: {str(e)}"
            }
    
    def process_fee_payment(self, fee_payment, request):
        """
        Process fee payment through Paystack
        
        Args:
            fee_payment: FeePayment object
            request: HTTP request object
            
        Returns:
            Dictionary with payment initialization result
        """
        try:
            # Get user from fee payment
            user = fee_payment.student.user or request.user
            
            # Generate unique reference
            reference = self.helper.generate_reference('FEE')
            
            # Create metadata
            metadata = self.helper.create_fee_payment_metadata(fee_payment)
            
            # Build callback URL
            callback_url = request.build_absolute_uri(
                f'/store/fees/pay/verify/{reference}/'
            )
            
            # Initialize payment
            result = self.api.initialize_transaction(
                email=user.email,
                amount=fee_payment.amount_paid,
                reference=reference,
                metadata=metadata,
                callback_url=callback_url
            )
            
            if result['success']:
                # Create payment record
                payment = Payment.objects.create(
                    fee_payment=fee_payment,
                    reference=reference,
                    amount=fee_payment.amount_paid,
                    payment_method='paystack',
                    payer_email=user.email,
                    payer_name=user.get_full_name(),
                    payer_phone=user.phone,
                    paystack_reference=result['reference'],
                    paystack_access_code=result['access_code'],
                    gateway_response={'initialization': result}
                )
                
                logger.info(f"Fee payment initialized for student {fee_payment.student.id}: {reference}")
                
                return {
                    'success': True,
                    'payment': payment,
                    'authorization_url': result['authorization_url'],
                    'reference': reference
                }
            else:
                logger.error(f"Failed to initialize fee payment: {result.get('message')}")
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to initialize payment')
                }
                
        except Exception as e:
            logger.error(f"Error processing fee payment: {str(e)}")
            return {
                'success': False,
                'message': f"Payment processing error: {str(e)}"
            }
    
    def verify_and_complete_payment(self, reference):
        """
        Verify and complete a payment
        
        Args:
            reference: Payment reference
            
        Returns:
            Dictionary with verification result
        """
        try:
            # Get payment record
            payment = Payment.objects.filter(reference=reference).first()
            if not payment:
                return {
                    'success': False,
                    'message': 'Payment record not found'
                }
            
            # Verify with Paystack
            verification = self.api.verify_transaction(reference)
            
            if not verification['success']:
                return {
                    'success': False,
                    'message': verification.get('message', 'Verification failed'),
                    'payment': payment
                }
            
            if verification['verified']:
                # Update payment record
                payment.status = 'completed'
                payment.verified_at = timezone.now()
                payment.verification_response = verification
                payment.transaction_id = verification.get('channel', '')
                payment.save()
                
                # Process based on payment type
                if payment.order:
                    self._complete_order_payment(payment)
                elif payment.fee_payment:
                    self._complete_fee_payment(payment)
                
                logger.info(f"Payment completed successfully: {reference}")
                
                return {
                    'success': True,
                    'verified': True,
                    'payment': payment,
                    'message': 'Payment verified successfully'
                }
            else:
                # Payment failed
                payment.status = 'failed'
                payment.save()
                
                logger.warning(f"Payment verification failed: {reference}")
                
                return {
                    'success': False,
                    'verified': False,
                    'payment': payment,
                    'message': verification.get('message', 'Payment verification failed')
                }
                
        except Exception as e:
            logger.error(f"Error verifying payment {reference}: {str(e)}")
            return {
                'success': False,
                'message': f"Verification error: {str(e)}"
            }
    
    def _complete_order_payment(self, payment):
        """Complete order payment processing"""
        try:
            order = payment.order
            
            # Update order status
            order.payment_status = 'completed'
            order.payment_reference = payment.reference
            order.payment_date = payment.verified_at
            order.status = 'processing'  # Move to processing after payment
            order.save()
            
            # Update student's total spent
            if order.student:
                order.student.update_spending()
            
            # Log transaction
            from .models import Transaction
            Transaction.objects.create(
                user=order.user,
                student=order.student,
                transaction_id=payment.reference,
                transaction_type='payment',
                amount=payment.amount,
                payment=payment,
                order=order,
                status='completed',
                description=f"Order payment: {order.order_number}"
            )
            
            logger.info(f"Order payment completed: {order.id}")
            
        except Exception as e:
            logger.error(f"Error completing order payment: {str(e)}")
            raise
    
    def _complete_fee_payment(self, payment):
        """Complete fee payment processing"""
        try:
            fee_payment = payment.fee_payment
            
            # Update fee payment
            fee_payment.mark_as_paid(payment.reference)
            fee_payment.issue_receipt(payment.fee_payment.student.user)
            
            # Update student's outstanding balance
            student = fee_payment.student
            student.outstanding_balance -= fee_payment.amount_paid
            if student.outstanding_balance < 0:
                student.outstanding_balance = Decimal('0.00')
            student.save()
            
            # Log transaction
            from .models import Transaction
            Transaction.objects.create(
                user=student.user,
                student=student,
                transaction_id=payment.reference,
                transaction_type='fee_payment',
                amount=payment.amount,
                payment=payment,
                status='completed',
                description=f"Fee payment: {fee_payment.fee_structure.name}"
            )
            
            logger.info(f"Fee payment completed: {fee_payment.id}")
            
        except Exception as e:
            logger.error(f"Error completing fee payment: {str(e)}")
            raise
    
    def process_refund(self, payment, reason='', amount=None):
        """
        Process refund for a payment
        
        Args:
            payment: Payment object
            reason: Refund reason
            amount: Refund amount (defaults to full amount)
            
        Returns:
            Dictionary with refund result
        """
        try:
            # Check if payment can be refunded
            if payment.status != 'completed':
                return {
                    'success': False,
                    'message': 'Only completed payments can be refunded'
                }
            
            # For Paystack, we would need recipient details
            # This is a simplified version - in production, you'd need:
            # 1. Create transfer recipient
            # 2. Initiate transfer
            
            # For now, just mark as refunded
            refund_amount = amount or payment.amount
            
            payment.status = 'refunded'
            payment.save()
            
            # Create refund record
            from .models import Refund
            refund = Refund.objects.create(
                payment=payment,
                amount=refund_amount,
                reason=reason,
                status='processed',
                processed_at=timezone.now(),
                refund_reference=f"REF-{timezone.now().timestamp()}",
                refund_method='paystack_transfer'
            )
            
            logger.info(f"Refund processed: {refund.id} for payment {payment.id}")
            
            return {
                'success': True,
                'refund': refund,
                'message': 'Refund processed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            return {
                'success': False,
                'message': f"Refund error: {str(e)}"
            }
    
    def handle_webhook(self, request):
        """
        Handle Paystack webhook
        
        Args:
            request: HTTP request with webhook payload
            
        Returns:
            Dictionary with webhook handling result
        """
        try:
            # Get payload and signature
            payload = request.body
            signature = request.headers.get('X-Paystack-Signature', '')
            
            # Validate signature
            if not self.helper.validate_webhook_signature(payload, signature):
                logger.warning(f"Invalid webhook signature: {signature}")
                return {
                    'success': False,
                    'message': 'Invalid signature'
                }
            
            # Parse payload
            event_data = self.helper.parse_webhook_payload(payload)
            if not event_data:
                return {
                    'success': False,
                    'message': 'Failed to parse webhook payload'
                }
            
            # Handle different events
            event_type = event_data['event']
            reference = event_data.get('reference')
            
            if event_type == 'payment_success':
                # Verify and complete payment
                result = self.verify_and_complete_payment(reference)
                
                if result['success']:
                    logger.info(f"Webhook: Payment success for {reference}")
                else:
                    logger.warning(f"Webhook: Payment verification failed for {reference}")
                
                return result
                
            elif event_type == 'payment_failed':
                # Update payment status
                payment = Payment.objects.filter(reference=reference).first()
                if payment:
                    payment.status = 'failed'
                    payment.save()
                    logger.info(f"Webhook: Payment failed for {reference}")
                
                return {
                    'success': True,
                    'message': 'Payment failure recorded'
                }
                
            elif event_type == 'transfer_success':
                logger.info(f"Webhook: Transfer success for {reference}")
                return {
                    'success': True,
                    'message': 'Transfer success recorded'
                }
                
            elif event_type == 'transfer_failed':
                logger.warning(f"Webhook: Transfer failed for {reference}")
                return {
                    'success': True,
                    'message': 'Transfer failure recorded'
                }
                
            else:
                logger.info(f"Webhook: Unhandled event {event_type} for {reference}")
                return {
                    'success': True,
                    'message': f'Event {event_type} received'
                }
                
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return {
                'success': False,
                'message': f"Webhook error: {str(e)}"
            }


# ==================== SINGLETON INSTANCE ====================

paystack_service = PaystackService()

# Export main functions
initialize_payment = paystack_service.process_order_payment
initialize_fee_payment = paystack_service.process_fee_payment
verify_payment = paystack_service.verify_and_complete_payment
handle_webhook = paystack_service.handle_webhook
process_refund = paystack_service.process_refund

# Export API classes
__all__ = [
    'PaystackAPI',
    'PaystackHelper',
    'PaystackService',
    'paystack_service',
    'initialize_payment',
    'initialize_fee_payment',
    'verify_payment',
    'handle_webhook',
    'process_refund'
]