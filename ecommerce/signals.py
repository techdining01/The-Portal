from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Payment, Order, Cart, AuditLog, TransactionBackup
from .backup_service import backup_service, audit_service

@receiver(pre_save, sender=Payment)
def backup_payment_before_change(sender, instance, **kwargs):
    """Backup payment before any changes"""
    if instance.pk:  # Only for existing instances
        try:
            old_payment = Payment.objects.get(pk=instance.pk)
            
            # Check if important fields are changing
            important_fields = ['status', 'amount', 'verified', 'gateway_response']
            changed_fields = {}
            
            for field in important_fields:
                old_value = getattr(old_payment, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changed_fields[field] = {'old': old_value, 'new': new_value}
            
            if changed_fields:
                # Create backup before change
                backup_service.backup_payment(
                    old_payment, 
                    backup_type='status_change',
                    reason=f"Pre-change backup: {', '.join(changed_fields.keys())}"
                )
                
        except Payment.DoesNotExist:
            pass

@receiver(post_save, sender=Payment)
def backup_payment_after_save(sender, instance, created, **kwargs):
    """Backup payment after save and create audit log"""
    try:
        if created:
            # Initial backup for new payment
            backup_service.backup_payment(
                instance,
                backup_type='initial',
                reason="Initial payment creation"
            )
            
            # Audit log
            audit_service.log_action(
                action_type='create',
                table_name='payment',
                record_id=str(instance.id),
                user=instance.order.user if hasattr(instance, 'order') else None,
                new_values=backup_service.serialize_payment(instance),
                description=f"Payment created: {instance.reference}",
                reference=instance.reference
            )
        else:
            # Audit log for updates
            audit_service.log_action(
                action_type='update',
                table_name='payment',
                record_id=str(instance.id),
                user=instance.order.user if hasattr(instance, 'order') else None,
                new_values=backup_service.serialize_payment(instance),
                description=f"Payment updated: {instance.reference}",
                reference=instance.reference
            )
            
    except Exception as e:
        # Log error but don't break the save operation
        import logging
        logger = logging.getLogger('signals')
        logger.error(f"Payment backup signal failed: {str(e)}")

@receiver(post_save, sender=Order)
def backup_order_after_save(sender, instance, created, **kwargs):
    """Backup order after save"""
    try:
        if created or instance.status_changed():
            backup_service.backup_order(
                instance,
                reason="Order created or status changed"
            )
    except Exception as e:
        import logging
        logger = logging.getLogger('signals')
        logger.error(f"Order backup signal failed: {str(e)}")

@receiver(post_save, sender=Cart)
def backup_cart_after_save(sender, instance, **kwargs):
    """Backup cart when deactivated (after checkout)"""
    try:
        if not instance.is_active:
            backup_service.backup_cart(
                instance,
                reason="Cart deactivated after checkout"
            )
    except Exception as e:
        import logging
        logger = logging.getLogger('signals')
        logger.error(f"Cart backup signal failed: {str(e)}")

# Webhook backup signal
def backup_webhook_processing(payment, webhook_data):
    """Backup payment when webhook is processed"""
    try:
        backup_service.backup_payment(
            payment,
            backup_type='webhook',
            reason=f"Webhook processing: {webhook_data.get('event', 'unknown')}",
            user=None  # System action
        )
        
        # Audit log
        audit_service.log_action(
            action_type='payment',
            table_name='payment',
            record_id=str(payment.id),
            user=None,
            new_values={'webhook_data': webhook_data},
            description=f"Webhook processed: {webhook_data.get('event', 'unknown')}",
            reference=payment.reference
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger('webhook')
        logger.error(f"Webhook backup failed: {str(e)}")