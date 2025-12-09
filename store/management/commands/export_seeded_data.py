# management/commands/export_seeded_data.py
import json
from django.core.management.base import BaseCommand
from django.core import serializers
from django.apps import apps

class Command(BaseCommand):
    help = 'Export seeded data for backup'
    
    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='seed_data.json', help='Output file name')
    
    def handle(self, *args, **options):
        # Models to export (in dependency order)
        models = [
            'users.User',
            'exams.Class',
            'users.Student',
            'users.Parent',
            'users.Teacher',
            'users.Staff',
            'users.StudentParent',
            'store.Category',
            'store.Product',
            'store.Cart',
            'store.CartItem',
            'store.Order',
            'store.OrderItem',
            'store.Payment',
            'store.Transaction',
            'store.FeeStructure',
            'store.FeePayment',
            'store.Supplier',
            'store.Inventory',
            'store.PurchaseOrder',
        ]
        
        all_data = []
        
        for model_path in models:
            app_label, model_name = model_path.split('.')
            model = apps.get_model(app_label, model_name)
            
            data = serializers.serialize('json', model.objects.all())
            data_list = json.loads(data)
            
            if data_list:
                all_data.extend(data_list)
                self.stdout.write(f'Exported {len(data_list)} {model_name} records')
        
        # Save to file
        with open(options['output'], 'w') as f:
            json.dump(all_data, f, indent=2)
        
        self.stdout.write(self.style.SUCCESS(f'Data exported to {options["output"]}'))