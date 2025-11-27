import json
import hashlib
import logging
from django.utils import timezone
from django.db import transaction
from .models import TransactionBackup, AuditLog, PaymentBackup, Payment, Order, Cart, CartItem

logger = logging.getLogger('backup_service')

class BackupService:
    def __init__(self):
        self.encryption_key = None  # You can implement encryption here
    
    def create_checksum(self, data):
        """Create SHA256 checksum for data integrity"""
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def backup_payment(self, payment, backup_type='status_change', reason=None, user=None):
        """Create comprehensive payment backup"""
        try:
            with transaction.atomic():
                # Get complete payment data
                payment_data = self.serialize_payment(payment)
                order_data = self.serialize_order(payment.order)
                
                # Create checksum
                combined_data = {**payment_data, 'order': order_data}
                checksum = self.create_checksum(combined_data)
                
                # Create payment backup
                payment_backup = PaymentBackup.objects.create(
                    payment=payment,
                    backup_type=backup_type,
                    payment_data=payment_data,
                    order_data=order_data,
                    gateway_response=payment.gateway_response,
                    checksum=checksum,
                    reason=reason,
                    created_by=user
                )
                
                # Also create general transaction backup
                self.backup_transaction(
                    transaction_type='payment',
                    original_id=str(payment.id),
                    data=combined_data,
                    reason=f"Payment backup: {backup_type}",
                    user=user
                )
                
                logger.info(f"Payment backup created: {payment.reference} - {backup_type}")
                return payment_backup
                
        except Exception as e:
            logger.error(f"Payment backup failed: {str(e)}")
            raise
    
    def backup_order(self, order, reason=None, user=None):
        """Create comprehensive order backup"""
        try:
            order_data = self.serialize_order(order)
            order_items_data = [
                self.serialize_order_item(item) for item in order.items.all()
            ]
            
            combined_data = {
                'order': order_data,
                'items': order_items_data,
                'payment': self.serialize_payment(order.payment) if hasattr(order, 'payment') else None
            }
            
            return self.backup_transaction(
                transaction_type='order',
                original_id=str(order.id),
                data=combined_data,
                reason=reason,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Order backup failed: {str(e)}")
            raise
    
    def backup_cart(self, cart, reason=None, user=None):
        """Create cart backup (useful for abandoned carts)"""
        try:
            cart_data = self.serialize_cart(cart)
            cart_items_data = [
                self.serialize_cart_item(item) for item in cart.items.all()
            ]
            
            combined_data = {
                'cart': cart_data,
                'items': cart_items_data
            }
            
            return self.backup_transaction(
                transaction_type='cart',
                original_id=str(cart.id),
                data=combined_data,
                reason=reason,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Cart backup failed: {str(e)}")
            raise
    
    def backup_transaction(self, transaction_type, original_id, data, reason=None, user=None):
        """Generic transaction backup method"""
        try:
            # Generate unique reference
            import uuid
            reference_number = f"BKUP_{uuid.uuid4().hex[:12].upper()}"
            
            # Create checksum
            checksum = self.create_checksum(data)
            
            # Get original record timestamps if available
            original_created = data.get('created_at', timezone.now())
            original_updated = data.get('updated_at', timezone.now())
            
            backup = TransactionBackup.objects.create(
                transaction_type=transaction_type,
                original_id=original_id,
                reference_number=reference_number,
                data_snapshot=data,
                backup_reason=reason,
                backed_up_by=user,
                original_created_at=original_created,
                original_updated_at=original_updated,
                checksum=checksum
            )
            
            logger.info(f"Transaction backup created: {reference_number}")
            return backup
            
        except Exception as e:
            logger.error(f"Transaction backup failed: {str(e)}")
            raise
    
    def serialize_payment(self, payment):
        """Serialize payment object to JSON-serializable dict"""
        return {
            'id': payment.id,
            'reference': payment.reference,
            'paystack_reference': payment.paystack_reference,
            'amount': str(payment.amount),
            'status': payment.status,
            'payment_method': payment.payment_method,
            'payment_gateway': payment.payment_gateway,
            'verified': payment.verified,
            'webhook_received': payment.webhook_received,
            'verification_attempts': payment.verification_attempts,
            'gateway_response': payment.gateway_response,
            'transfer_proof': str(payment.transfer_proof) if payment.transfer_proof else None,
            'transfer_date': payment.transfer_date.isoformat() if payment.transfer_date else None,
            'transfer_reference': payment.transfer_reference,
            'created_at': payment.payment_date.isoformat(),
            'updated_at': payment.updated_at.isoformat(),
        }
    
    def serialize_order(self, order):
        """Serialize order object"""
        return {
            'id': order.id,
            'order_number': order.order_number,
            'user_id': order.user.id,
            'user_email': order.user.email,
            'total_amount': str(order.total_amount),
            'status': order.status,
            'payment_method': order.payment_method,
            'payment_reference': order.payment_reference,
            'billing_address': order.billing_address,
            'billing_phone': order.billing_phone,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'paid_at': order.paid_at.isoformat() if order.paid_at else None,
        }
    
    def serialize_order_item(self, item):
        """Serialize order item"""
        return {
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': str(item.price),
            'student_id': item.student.id,
            'student_name': item.student.get_full_name(),
        }
    
    def serialize_cart(self, cart):
        """Serialize cart"""
        return {
            'id': cart.id,
            'user_id': cart.user.id,
            'user_email': cart.user.email,
            'total_amount': str(cart.total_amount),
            'item_count': cart.item_count,
            'is_active': cart.is_active,
            'created_at': cart.created_at.isoformat(),
            'updated_at': cart.updated_at.isoformat(),
        }
    
    def serialize_cart_item(self, item):
        """Serialize cart item"""
        return {
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'student_id': item.student.id,
            'student_name': item.student.get_full_name(),
            'added_at': item.added_at.isoformat(),
        }
    
    def restore_backup(self, backup, user):
        """Restore a backup (creates new records)"""
        try:
            if not backup.verify_integrity():
                raise ValueError("Backup integrity check failed")
            
            data = backup.data_snapshot
            
            if backup.transaction_type == 'payment':
                return self.restore_payment(data, user)
            elif backup.transaction_type == 'order':
                return self.restore_order(data, user)
            elif backup.transaction_type == 'cart':
                return self.restore_cart(data, user)
            else:
                raise ValueError(f"Unsupported transaction type: {backup.transaction_type}")
                
        except Exception as e:
            logger.error(f"Backup restoration failed: {str(e)}")
            raise
    
    def restore_payment(self, data, user):
        """Restore payment from backup"""
        # This would create a new payment record based on backup data
        # Implementation depends on your business logic
        pass
    
    def restore_order(self, data, user):
        """Restore order from backup"""
        # This would create a new order record based on backup data
        pass
    
    def restore_cart(self, data, user):
        """Restore cart from backup"""
        # This would create a new cart record based on backup data
        pass

class AuditService:
    """Service for creating audit logs"""
    
    def log_action(self, action_type, table_name, record_id, user=None, 
                   old_values=None, new_values=None, description=None, 
                   reference=None, request=None):
        """Create an audit log entry"""
        try:
            # Get user IP and agent from request
            user_ip = None
            user_agent = None
            if request:
                user_ip = self.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            # Determine changed fields
            changed_fields = None
            if old_values and new_values:
                changed_fields = list(set(old_values.keys()) | set(new_values.keys()))
            
            audit_log = AuditLog.objects.create(
                action_type=action_type,
                table_name=table_name,
                record_id=record_id,
                user=user,
                user_ip=user_ip,
                user_agent=user_agent,
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                description=description,
                reference=reference
            )
            
            logger.info(f"Audit log created: {action_type} on {table_name}.{record_id}")
            return audit_log
            
        except Exception as e:
            logger.error(f"Audit logging failed: {str(e)}")
            # Don't raise exception - audit failure shouldn't break main functionality
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# Global instances
backup_service = BackupService()
audit_service = AuditService()