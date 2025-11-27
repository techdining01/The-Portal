from celery import shared_task
from django.utils import timezone
import logging
from .backup_service import scheduled_backup_service, backup_manager

logger = logging.getLogger('celery_tasks')

@shared_task
def perform_daily_backup():
    """Perform daily automated backup"""
    try:
        logger.info("Starting daily backup task")
        
        # Perform scheduled backup
        scheduled_backup_service.perform_scheduled_backup()
        
        # Export today's transactions
        today = timezone.now().date()
        start_date = today
        end_date = today
        
        backup_manager.export_transaction_data(start_date, end_date)
        
        logger.info("Daily backup task completed successfully")
        return "Daily backup completed"
        
    except Exception as e:
        logger.error(f"Daily backup task failed: {str(e)}")
        return f"Backup failed: {str(e)}"

@shared_task
def cleanup_old_backups():
    """Clean up old backups"""
    try:
        logger.info("Starting backup cleanup task")
        
        backup_manager.cleanup_old_backups()
        
        logger.info("Backup cleanup task completed")
        return "Backup cleanup completed"
        
    except Exception as e:
        logger.error(f"Backup cleanup task failed: {str(e)}")
        return f"Cleanup failed: {str(e)}"

@shared_task
def verify_backup_integrity(backup_id):
    """Verify specific backup integrity"""
    try:
        success, message = backup_manager.verify_backup_integrity(backup_id)
        
        if success:
            logger.info(f"Backup integrity verified: {backup_id}")
        else:
            logger.warning(f"Backup integrity check failed: {backup_id} - {message}")
        
        return {
            'backup_id': backup_id,
            'success': success,
            'message': message
        }
        
    except Exception as e:
        logger.error(f"Backup integrity check failed: {str(e)}")
        return {
            'backup_id': backup_id,
            'success': False,
            'message': str(e)
        }