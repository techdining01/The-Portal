import json
import hmac
import hashlib
import logging
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from .models import Payment, Order, StockAlert
from .paystack_service import PaystackService

logger = logging.getLogger('payment_webhooks')

class WebhookHandler:
    def __init__(self):
        self.paystack_service = PaystackService()
    
    def verify_paystack_signature(self, payload, signature):
        """Verify Paystack webhook signature"""
        secret = settings.PAYSTACK_SECRET_KEY
        computed_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(computed_signature, signature)
    
    def handle_paystack_webhook(self, request):
        """Handle Paystack webhook"""
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        # Verify webhook signature
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            logger.error("Missing Paystack webhook signature")
            return JsonResponse({'error': 'Missing signature'}, status=400)
        
        if not self.verify_paystack_signature(request.body, signature):
            logger.error("Invalid Paystack webhook signature")
            return JsonResponse({'error': 'Invalid signature'}, status=400)
        
        try:
            payload = json.loads(request.body.decode('utf-8'))
            event = payload.get('event')
            data = payload.get('data')
            
            logger.info(f"Received Paystack webhook: {event}")
            
            if event == 'charge.success':
                return self.handle_charge_success(data, 'paystack')
            elif event == 'charge.failed':
                return self.handle_charge_failed(data, 'paystack')
            elif event == 'charge.abandoned':
                return self.handle_charge_abandoned(data, 'paystack')
            else:
                logger.info(f"Ignored Paystack event: {event}")
                return JsonResponse({'status': 'ignored', 'message': 'Event not handled'})
                
        except Exception as e:
            logger.error(f"Paystack webhook processing error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=200)
    
    def handle_charge_success(self, data, gateway):
        """Handle successful charge"""
        reference = data.get('reference')
        
        try:
            payment = Payment.objects.get(reference=reference, payment_gateway=gateway)
            
            # Skip if already processed
            if payment.verified:
                logger.info(f"Payment {reference} already processed")
                return JsonResponse({'status': 'success', 'message': 'Already processed'})
            
            # Additional verification with gateway API
            if gateway == 'paystack':
                verification = self.paystack_service.verify_transaction(reference)
                
                if verification['status'] and verification['data']['status'] == 'success':
                    # Mark as processing first
                    payment.mark_as_processing()
                    
                    # Update payment details
                    payment.mark_as_paid(
                        paystack_reference=data.get('reference'),
                        gateway_data=data
                    )
                    
                    # Send confirmation email
                    from .views import send_payment_confirmation_email
                    send_payment_confirmation_email(payment.order, payment)
                    
                    logger.info(f"Payment {reference} processed successfully via webhook")
                    return JsonResponse({'status': 'success', 'message': 'Payment processed'})
                else:
                    payment.mark_as_failed(gateway_data=data)
                    logger.warning(f"Payment {reference} verification failed")
                    return JsonResponse({'status': 'failed', 'message': 'Verification failed'})
            else:
                # Handle other gateways
                payment.mark_as_paid(gateway_data=data)
                return JsonResponse({'status': 'success', 'message': 'Payment processed'})
                
        except Payment.DoesNotExist:
            logger.error(f"Payment not found: {reference}")
            return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)
    
    def handle_charge_failed(self, data, gateway):
        """Handle failed charge"""
        reference = data.get('reference')
        
        try:
            payment = Payment.objects.get(reference=reference, payment_gateway=gateway)
            payment.status = 'failed'
            payment.gateway_response = data
            payment.webhook_processed_at = timezone.now()
            payment.save()
            
            logger.info(f"Payment {reference} marked as failed via webhook")
            return JsonResponse({'status': 'success', 'message': 'Payment marked as failed'})
        except Payment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)
    
    def handle_charge_abandoned(self, data, gateway):
        """Handle abandoned charge"""
        reference = data.get('reference')
        
        try:
            payment = Payment.objects.get(reference=reference, payment_gateway=gateway)
            payment.status = 'abandoned'
            payment.gateway_response = data
            payment.webhook_processed_at = timezone.now()
            payment.save()
            
            logger.info(f"Payment {reference} marked as abandoned via webhook")
            return JsonResponse({'status': 'success', 'message': 'Payment marked as abandoned'})
        except Payment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)

# Global webhook handler instance
webhook_handler = WebhookHandler()