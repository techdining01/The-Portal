from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Seed all sample data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding all sample data...')
        
        # Run all seed commands in order
        commands = [
            'createsuperadmin',
            'seed_users',
            'seed_store', 
            'seed_orders',
            'seed_salary_data',
            'seed_classes_subjects',
        ]
        
        for command in commands:
            self.stdout.write(f'Running {command}...')
            try:
                call_command(command)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error in {command}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('All seed data completed!'))
