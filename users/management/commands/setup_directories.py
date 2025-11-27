# ecommerce/management/commands/setup_directories.py
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Create all required directories for the application'

    def handle(self, *args, **options):
        # Directories to create
        directories = [
            settings.LOGS_DIR,
            settings.MEDIA_ROOT,
            settings.BACKUP_ROOT,
            settings.STATIC_ROOT,
        ]
        
        # Media subdirectories
        media_subdirs = [
            'profiles',
            'signatures',
            'products', 
            'payment_proofs',
            'backups',
        ]
        
        # Backup subdirectories
        backup_subdirs = [
            'database',
            'transactions',
            'audit',
        ]
        
        # Static subdirectories
        static_subdirs = [
            'css',
            'js', 
            'images',
            'vendor/bootstrap',
            'vendor/fontawesome',
            'vendor/jquery',
        ]
        
        # Create main directories
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Created directory: {directory}')
            )
        
        # Create media subdirectories
        for subdir in media_subdirs:
            path = settings.MEDIA_ROOT / subdir
            path.mkdir(parents=True, exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Created directory: {path}')
            )
        
        # Create backup subdirectories
        for subdir in backup_subdirs:
            path = settings.BACKUP_ROOT / subdir
            path.mkdir(parents=True, exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Created directory: {path}')
            )
        
        # Create static subdirectories (in STATICFILES_DIRS[0])
        static_base = settings.STATICFILES_DIRS[0]
        for subdir in static_subdirs:
            path = static_base / subdir
            path.mkdir(parents=True, exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Created directory: {path}')
            )
        
        # Create empty log files
        log_files = ['django.log', 'payments.log', 'webhooks.log', 'backups.log']
        for log_file in log_files:
            log_path = settings.LOGS_DIR / log_file
            if not log_path.exists():
                with open(log_path, 'w') as f:
                    f.write('')
                self.stdout.write(
                    self.style.SUCCESS(f'Created log file: {log_path}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('All directories created successfully!')
        )