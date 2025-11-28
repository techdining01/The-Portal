# backup/management/commands/create_backup.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from backup.models import DatabaseBackup
import os
import json
import datetime
from django.core import serializers

User = get_user_model()

class Command(BaseCommand):
    help = 'Create database backups'
    
    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, default='full', 
                          choices=['full', 'transactions', 'users', 'products'],
                          help='Type of backup to create')
    
    def handle(self, *args, **options):
        backup_type = options['type']
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = f"{backup_type}_backup_{timestamp}.json"
        file_path = os.path.join(backup_dir, filename)
        
        # Get data based on backup type
        if backup_type == 'full':
            from store.models import Product, Order, Transaction
            from accounts.models import User
            data = {
                'users': serializers.serialize('json', User.objects.all()),
                'products': serializers.serialize('json', Product.objects.all()),
                'orders': serializers.serialize('json', Order.objects.all()),
                'transactions': serializers.serialize('json', Transaction.objects.all()),
            }
        elif backup_type == 'transactions':
            from store.models import Transaction, Order
            data = {
                'transactions': serializers.serialize('json', Transaction.objects.all()),
                'orders': serializers.serialize('json', Order.objects.all()),
            }
        elif backup_type == 'users':
            data = {
                'users': serializers.serialize('json', User.objects.all()),
            }
        elif backup_type == 'products':
            from store.models import Product
            data = {
                'products': serializers.serialize('json', Product.objects.all()),
            }
        
        # Save backup file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create backup record
        backup = DatabaseBackup.objects.create(
            backup_type=backup_type,
            file_path=file_path,
            file_size=file_size,
            created_by=User.objects.filter(is_superuser=True).first(),
            notes=f"Automated {backup_type} backup"
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {backup_type} backup: {filename} ({file_size} bytes)')
        )