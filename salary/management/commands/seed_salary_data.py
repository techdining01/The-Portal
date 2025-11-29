from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from salary.models import SalaryStructure, TeacherSalary
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample salary data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding salary data...')
        
        teachers = User.objects.filter(role='teacher')
        
        if not teachers:
            self.stdout.write(self.style.ERROR('No teachers found! Run seed_users first.'))
            return

        # Create salary structures
        structures_data = [
            {
                'name': 'Entry Level Teacher',
                'base_salary': 85000.00,
                'allowances': 15000.00,
                'deductions': 5000.00,
                'frequency': 'monthly'
            },
            {
                'name': 'Experienced Teacher',
                'base_salary': 120000.00,
                'allowances': 25000.00,
                'deductions': 7500.00,
                'frequency': 'monthly'
            },
            {
                'name': 'Senior Teacher',
                'base_salary': 180000.00,
                'allowances': 35000.00,
                'deductions': 10000.00,
                'frequency': 'monthly'
            }
        ]

        structures = []
        for struct_data in structures_data:
            structure, created = SalaryStructure.objects.get_or_create(
                name=struct_data['name'],
                defaults=struct_data
            )
            if created:
                structures.append(structure)
                self.stdout.write(f'Created salary structure: {structure.name}')

        # Create teacher salaries
        payment_periods = ['January 2024', 'February 2024', 'March 2024']

        for i, teacher in enumerate(teachers):
            structure = structures[i % len(structures)]
            
            for j, period in enumerate(payment_periods):
                # Last period is pending, others are paid
                payment_status = 'pending' if j == len(payment_periods) - 1 else 'paid'
                paid_at = None if payment_status == 'pending' else datetime.now() - timedelta(days=30 * (len(payment_periods) - j - 1))

                salary, created = TeacherSalary.objects.get_or_create(
                    teacher=teacher,
                    payment_period=period,
                    defaults={
                        'salary_structure': structure,
                        'basic_salary': structure.base_salary,
                        'allowances': structure.allowances,
                        'deductions': structure.deductions,
                        'net_salary': structure.net_salary,
                        'payment_status': payment_status,
                        'paid_at': paid_at,
                        'paystack_reference': f"SAL_{teacher.id}_{period.replace(' ', '_')}" if payment_status == 'paid' else ''
                    }
                )
                
                if created:
                    self.stdout.write(f'Created salary for {teacher.get_full_name()} - {period}')

        self.stdout.write(self.style.SUCCESS('Successfully seeded salary data!'))