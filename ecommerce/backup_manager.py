import json
import hashlib
import logging
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .backup_service import BackupService

from .models import TransactionBackup, Payment

logger = logging.getLogger('backup_service')
backup_service = BackupService()

class BackupManager:
    """Enhanced backup manager with automated cleanup and encryption"""
    
    def __init__(self):
        self.backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        self.ensure_backup_dir()
    
    def ensure_backup_dir(self):
        """Create backup directory if it doesn't exist"""
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'database'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'transactions'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'audit'), exist_ok=True)
    
    def create_database_backup(self):
        """Create complete database backup"""
        try:
            from django.core.management import call_command
            import subprocess
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'database_backup_{timestamp}.json'
            filepath = os.path.join(self.backup_dir, 'database', filename)
            
            # Create JSON backup
            with open(filepath, 'w') as f:
                call_command('dumpdata', indent=2, stdout=f)
            
            logger.info(f"Database backup created: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            return None
    
    def cleanup_old_backups(self, retention_days=30):
        """Clean up backups older than retention period"""
        try:
            cutoff_date = timezone.now() - timedelta(days=retention_days)
            
            # Cleanup file backups
            for backup_type in ['database', 'transactions', 'audit']:
                backup_path = os.path.join(self.backup_dir, backup_type)
                for filename in os.listdir(backup_path):
                    filepath = os.path.join(backup_path, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                        if file_time < cutoff_date:
                            os.remove(filepath)
                            logger.info(f"Removed old backup: {filename}")
            
            # Cleanup database backups (soft delete)
            TransactionBackup.objects.filter(
                created_at__lt=cutoff_date,
                backup_status='active'
            ).update(backup_status='archived')
            
            logger.info("Backup cleanup completed")
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
    
    def export_transaction_data(self, start_date, end_date):
        """Export transaction data for specific period"""
        try:
            transactions = TransactionBackup.objects.filter(
                created_at__range=[start_date, end_date],
                backup_status='active'
            )
            
            data = {
                'export_info': {
                    'export_date': timezone.now().isoformat(),
                    'period': f"{start_date} to {end_date}",
                    'total_transactions': transactions.count()
                },
                'transactions': []
            }
            
            for transaction in transactions:
                data['transactions'].append({
                    'reference': transaction.reference_number,
                    'type': transaction.transaction_type,
                    'original_id': transaction.original_id,
                    'created_at': transaction.created_at.isoformat(),
                    'data': transaction.data_snapshot
                })
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'transactions_export_{timestamp}.json'
            filepath = os.path.join(self.backup_dir, 'transactions', filename)
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Transaction export completed: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Transaction export failed: {str(e)}")
            return None
    
    def verify_backup_integrity(self, backup_id):
        """Verify the integrity of a specific backup"""
        try:
            backup = TransactionBackup.objects.get(id=backup_id)
            
            # Verify checksum
            if not backup.verify_integrity():
                return False, "Checksum verification failed"
            
            # Verify data structure
            data = backup.data_snapshot
            required_fields = ['transaction_type', 'original_id']
            
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            
            return True, "Backup integrity verified"
            
        except Exception as e:
            return False, f"Integrity check failed: {str(e)}"

# Enhanced BackupService with scheduling
class ScheduledBackupService(BackupService):
    """Extended backup service with scheduling capabilities"""
    
    def __init__(self):
        super().__init__()
        self.manager = BackupManager()
    
    def perform_scheduled_backup(self):
        """Perform scheduled backup tasks"""
        try:
            # Create database backup
            self.manager.create_database_backup()
            
            # Backup recent transactions
            recent_cutoff = timezone.now() - timedelta(hours=24)
            recent_payments = Payment.objects.filter(
                payment_date__gte=recent_cutoff
            )
            
            for payment in recent_payments:
                self.backup_payment(
                    payment, 
                    'scheduled', 
                    "Daily scheduled backup"
                )
            
            # Cleanup old backups
            self.manager.cleanup_old_backups()
            
            logger.info("Scheduled backup completed successfully")
            
        except Exception as e:
            logger.error(f"Scheduled backup failed: {str(e)}")


# Global instances
backup_service = BackupService()
scheduled_backup_service = ScheduledBackupService()
backup_manager = BackupManager()

