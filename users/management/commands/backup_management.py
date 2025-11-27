from django.core.management.base import BaseCommand
from django.utils import timezone
from ecommerce.models import TransactionBackup
import logging
from ecommerce.backup_manager import backup_manager, scheduled_backup_service


logger = logging.getLogger('management_commands')

class Command(BaseCommand):
    help = 'Manage database backups and transactions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['create', 'cleanup', 'verify', 'export'],
            help='Backup action to perform'
        )
        parser.add_argument(
            '--backup-id',
            type=int,
            help='Specific backup ID for verification'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days for export (default: 7)'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'create':
            self.create_backup()
        elif action == 'cleanup':
            self.cleanup_backups()
        elif action == 'verify':
            self.verify_backup(options['backup_id'])
        elif action == 'export':
            self.export_transactions(options['days'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify a valid action: create, cleanup, verify, export')
            )
    
    def create_backup(self):
        """Create a manual backup"""
        self.stdout.write('Creating manual backup...')
        
        try:
            # Create database backup
            db_backup_path = backup_manager.create_database_backup()
            
            if db_backup_path:
                self.stdout.write(
                    self.style.SUCCESS(f'Database backup created: {db_backup_path}')
                )
            
            # Perform scheduled backup
            scheduled_backup_service.perform_scheduled_backup()
            
            self.stdout.write(
                self.style.SUCCESS('Manual backup completed successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Backup creation failed: {str(e)}')
            )
    
    def cleanup_backups(self):
        """Clean up old backups"""
        self.stdout.write('Cleaning up old backups...')
        
        try:
            backup_manager.cleanup_old_backups()
            self.stdout.write(
                self.style.SUCCESS('Backup cleanup completed')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Backup cleanup failed: {str(e)}')
            )
    
    def verify_backup(self, backup_id):
        """Verify specific backup integrity"""
        if not backup_id:
            self.stdout.write(
                self.style.ERROR('Please provide a backup ID with --backup-id')
            )
            return
        
        self.stdout.write(f'Verifying backup ID: {backup_id}')
        
        try:
            success, message = backup_manager.verify_backup_integrity(backup_id)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Backup verified: {message}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Backup verification failed: {message}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Verification failed: {str(e)}')
            )
    
    def export_transactions(self, days):
        """Export transactions for specified days"""
        self.stdout.write(f'Exporting transactions for last {days} days...')
        
        try:
            end_date = timezone.now()
            start_date = end_date - timezone.timedelta(days=days)
            
            export_path = backup_manager.export_transaction_data(start_date, end_date)
            
            if export_path:
                self.stdout.write(
                    self.style.SUCCESS(f'Transactions exported: {export_path}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Transaction export failed')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Export failed: {str(e)}')
            )



            