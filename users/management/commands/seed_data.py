import random
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from ecommerce.models import Category, Product
from exams.models import Class  # Assuming you have a Class model

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed database with sample products, students, and parents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()
        
        with transaction.atomic():
            self.create_categories()
            self.create_products()
            self.create_students_and_parents()
            
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded database with sample data!')
        )

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('Clearing existing data...')
        
        # Clear users (except superusers)
        User.objects.filter(is_superuser=False).delete()
        
        # Clear products and categories
        Product.objects.all().delete()
        Category.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('Existing data cleared!'))

    def create_categories(self):
        """Create product categories"""
        self.stdout.write('Creating categories...')
        
        categories_data = [
            {
                'name': 'School Fees',
                'description': 'Academic session and term fees'
            },
            {
                'name': 'Registration',
                'description': 'Admission and registration forms'
            },
            {
                'name': 'Uniforms',
                'description': 'School uniforms and accessories'
            },
            {
                'name': 'Textbooks',
                'description': 'Academic textbooks and workbooks'
            },
            {
                'name': 'Stationery',
                'description': 'Writing materials and supplies'
            },
            {
                'name': 'Extracurricular',
                'description': 'Sports and club activities'
            },
        ]
        
        categories = {}
        for data in categories_data:
            category, created = Category.objects.get_or_create(
                name=data['name'],
                defaults={'description': data['description']}
            )
            categories[data['name']] = category
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(categories)} categories'))
        return categories

    def create_products(self):
        """Create sample products"""
        self.stdout.write('Creating products...')
        
        # Get or create classes
        classes = self.get_or_create_classes()
        
        products_data = [
            # School Fees
            {
                'name': 'JSS 1 First Term School Fee',
                'description': 'Junior Secondary School 1 First Term complete school fee',
                'category': 'School Fees',
                'product_type': 'school_fee',
                'price': 25000.00,
                'applicable_class': classes['JSS 1'],
                'track_stock': False,
            },
            {
                'name': 'JSS 2 First Term School Fee',
                'description': 'Junior Secondary School 2 First Term complete school fee',
                'category': 'School Fees',
                'product_type': 'school_fee',
                'price': 26000.00,
                'applicable_class': classes['JSS 2'],
                'track_stock': False,
            },
            {
                'name': 'JSS 3 First Term School Fee',
                'description': 'Junior Secondary School 3 First Term complete school fee',
                'category': 'School Fees',
                'product_type': 'school_fee',
                'price': 27000.00,
                'applicable_class': classes['JSS 3'],
                'track_stock': False,
            },
            {
                'name': 'SSS 1 First Term School Fee',
                'description': 'Senior Secondary School 1 First Term complete school fee',
                'category': 'School Fees',
                'product_type': 'school_fee',
                'price': 28000.00,
                'applicable_class': classes['SSS 1'],
                'track_stock': False,
            },
            {
                'name': 'SSS 2 First Term School Fee',
                'description': 'Senior Secondary School 2 First Term complete school fee',
                'category': 'School Fees',
                'product_type': 'school_fee',
                'price': 29000.00,
                'applicable_class': classes['SSS 2'],
                'track_stock': False,
            },
            {
                'name': 'SSS 3 First Term School Fee',
                'description': 'Senior Secondary School 3 First Term complete school fee',
                'category': 'School Fees',
                'product_type': 'school_fee',
                'price': 30000.00,
                'applicable_class': classes['SSS 3'],
                'track_stock': False,
            },
            
            # Registration Forms
            {
                'name': 'Admission Form',
                'description': 'School admission application form',
                'category': 'Registration',
                'product_type': 'registration',
                'price': 5000.00,
                'track_stock': False,
            },
            {
                'name': 'Transfer Form',
                'description': 'Student transfer application form',
                'category': 'Registration',
                'product_type': 'registration',
                'price': 3000.00,
                'track_stock': False,
            },
            
            # Uniforms
            {
                'name': 'School Shirt',
                'description': 'White school shirt (all sizes)',
                'category': 'Uniforms',
                'product_type': 'uniform',
                'price': 2500.00,
                'stock_quantity': 50,
                'track_stock': True,
            },
            {
                'name': 'School Trouser',
                'description': 'Grey school trouser (all sizes)',
                'category': 'Uniforms',
                'product_type': 'uniform',
                'price': 3000.00,
                'stock_quantity': 45,
                'track_stock': True,
            },
            {
                'name': 'School Skirt',
                'description': 'Grey school skirt (all sizes)',
                'category': 'Uniforms',
                'product_type': 'uniform',
                'price': 2800.00,
                'stock_quantity': 40,
                'track_stock': True,
            },
            {
                'name': 'School Blouse',
                'description': 'White school blouse (all sizes)',
                'category': 'Uniforms',
                'product_type': 'uniform',
                'price': 2200.00,
                'stock_quantity': 35,
                'track_stock': True,
            },
            {
                'name': 'School Tie',
                'description': 'School neck tie',
                'category': 'Uniforms',
                'product_type': 'uniform',
                'price': 800.00,
                'stock_quantity': 60,
                'track_stock': True,
            },
            {
                'name': 'School Cardigan',
                'description': 'School cardigan sweater',
                'category': 'Uniforms',
                'product_type': 'uniform',
                'price': 4500.00,
                'stock_quantity': 30,
                'track_stock': True,
            },
            
            # Textbooks
            {
                'name': 'Mathematics JSS 1',
                'description': 'Mathematics textbook for JSS 1',
                'category': 'Textbooks',
                'product_type': 'textbook',
                'price': 1500.00,
                'stock_quantity': 25,
                'track_stock': True,
            },
            {
                'name': 'English Language JSS 1',
                'description': 'English Language textbook for JSS 1',
                'category': 'Textbooks',
                'product_type': 'textbook',
                'price': 1200.00,
                'stock_quantity': 30,
                'track_stock': True,
            },
            {
                'name': 'Basic Science JSS 1',
                'description': 'Basic Science textbook for JSS 1',
                'category': 'Textbooks',
                'product_type': 'textbook',
                'price': 1300.00,
                'stock_quantity': 20,
                'track_stock': True,
            },
            {
                'name': 'Mathematics SSS 1',
                'description': 'Mathematics textbook for SSS 1',
                'category': 'Textbooks',
                'product_type': 'textbook',
                'price': 1800.00,
                'stock_quantity': 22,
                'track_stock': True,
            },
            {
                'name': 'English Language SSS 1',
                'description': 'English Language textbook for SSS 1',
                'category': 'Textbooks',
                'product_type': 'textbook',
                'price': 1500.00,
                'stock_quantity': 28,
                'track_stock': True,
            },
            {
                'name': 'Physics SSS 1',
                'description': 'Physics textbook for SSS 1',
                'category': 'Textbooks',
                'product_type': 'textbook',
                'price': 2000.00,
                'stock_quantity': 18,
                'track_stock': True,
            },
            
            # Stationery
            {
                'name': 'Exercise Book (80 leaves)',
                'description': '80 leaves exercise book',
                'category': 'Stationery',
                'product_type': 'stationery',
                'price': 150.00,
                'stock_quantity': 200,
                'track_stock': True,
            },
            {
                'name': 'Mathematical Set',
                'description': 'Complete mathematical set',
                'category': 'Stationery',
                'product_type': 'stationery',
                'price': 800.00,
                'stock_quantity': 35,
                'track_stock': True,
            },
            {
                'name': 'School Bag',
                'description': 'Standard school backpack',
                'category': 'Stationery',
                'product_type': 'stationery',
                'price': 3500.00,
                'stock_quantity': 25,
                'track_stock': True,
            },
            {
                'name': 'Scientific Calculator',
                'description': 'Scientific calculator for senior students',
                'category': 'Stationery',
                'product_type': 'stationery',
                'price': 2500.00,
                'stock_quantity': 15,
                'track_stock': True,
            },
            
            # Extracurricular
            {
                'name': 'Sports Fee',
                'description': 'Annual sports and games fee',
                'category': 'Extracurricular',
                'product_type': 'other',
                'price': 2000.00,
                'track_stock': False,
            },
            {
                'name': 'Excursion Fee',
                'description': 'Educational trip and excursion fee',
                'category': 'Extracurricular',
                'product_type': 'other',
                'price': 5000.00,
                'track_stock': False,
            },
        ]
        
        categories = {cat.name: cat for cat in Category.objects.all()}
        
        products_created = 0
        for data in products_data:
            product, created = Product.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'category': categories[data['category']],
                    'product_type': data['product_type'],
                    'price': data['price'],
                    'stock_quantity': data.get('stock_quantity', 0),
                    'track_stock': data.get('track_stock', False),
                    'applicable_class': data.get('applicable_class'),
                    'is_available': True,
                }
            )
            if created:
                products_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {products_created} products'))

    def get_or_create_classes(self):
        """Get or create sample classes"""
        class_names = ['JSS 1', 'JSS 2', 'JSS 3', 'SSS 1', 'SSS 2', 'SSS 3']
        classes = {}
        
        for class_name in class_names:
            # Try to get existing class or create a simple representation
            # If you have a Class model, use it. Otherwise, we'll handle it.
            try:
                from exams.models import Class
                class_obj, created = Class.objects.get_or_create(
                    name=class_name,
                    defaults={'is_active': True}
                )
                classes[class_name] = class_obj
            except ImportError:
                # If Class model doesn't exist, set to None
                classes[class_name] = None
        
        return classes

    def create_students_and_parents(self):
        """Create sample students and parents"""
        self.stdout.write('Creating students and parents...')
        
        # Create parent users
        parents_data = [
            {
                'username': 'parent_adebayo',
                'email': 'adebayo.johnson@email.com',
                'first_name': 'Adebayo',
                'last_name': 'Johnson',
                'phone': '+2348012345001',
            },
            {
                'username': 'parent_chinedu',
                'email': 'chinedu.okoro@email.com',
                'first_name': 'Chinedu',
                'last_name': 'Okoro',
                'phone': '+2348012345002',
            },
            {
                'username': 'parent_funke',
                'email': 'funke.adeleke@email.com',
                'first_name': 'Funke',
                'last_name': 'Adeleke',
                'phone': '+2348012345003',
            },
            {
                'username': 'parent_emeka',
                'email': 'emeka.nwankwo@email.com',
                'first_name': 'Emeka',
                'last_name': 'Nwankwo',
                'phone': '+2348012345004',
            },
            {
                'username': 'parent_blessing',
                'email': 'blessing.ogun@email.com',
                'first_name': 'Blessing',
                'last_name': 'Ogun',
                'phone': '+2348012345005',
            },
        ]
        
        parents = {}
        for data in parents_data:
            parent, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': 'parent',
                    'is_active': True,
                }
            )
            if created:
                parent.set_password('password123')  # Default password
                parent.save()
                
                # Create user profile if your model has additional fields
                try:
                    from users.models import UserProfile
                    UserProfile.objects.get_or_create(
                        user=parent,
                        defaults={
                            'phone_number': data['phone'],
                            'address': 'Lagos, Nigeria',
                        }
                    )
                except ImportError:
                    pass
            
            parents[data['username']] = parent
        
        # Create student users
        students_data = [
            # Adebayo Johnson's children
            {
                'username': 'student_temi_johnson',
                'email': 'temi.johnson@student.school.com',
                'first_name': 'Temi',
                'last_name': 'Johnson',
                'parent': parents['parent_adebayo'],
                'class_level': 'JSS 1',
                'admission_number': 'STU001',
            },
            {
                'username': 'student_kunle_johnson',
                'email': 'kunle.johnson@student.school.com',
                'first_name': 'Kunle',
                'last_name': 'Johnson',
                'parent': parents['parent_adebayo'],
                'class_level': 'SSS 2',
                'admission_number': 'STU002',
            },
            
            # Chinedu Okoro's children
            {
                'username': 'student_amarachi_okoro',
                'email': 'amarachi.okoro@student.school.com',
                'first_name': 'Amarachi',
                'last_name': 'Okoro',
                'parent': parents['parent_chinedu'],
                'class_level': 'JSS 3',
                'admission_number': 'STU003',
            },
            
            # Funke Adeleke's children
            {
                'username': 'student_segun_adeleke',
                'email': 'segun.adeleke@student.school.com',
                'first_name': 'Segun',
                'last_name': 'Adeleke',
                'parent': parents['parent_funke'],
                'class_level': 'JSS 2',
                'admission_number': 'STU004',
            },
            {
                'username': 'student_bimpe_adeleke',
                'email': 'bimpe.adeleke@student.school.com',
                'first_name': 'Bimpe',
                'last_name': 'Adeleke',
                'parent': parents['parent_funke'],
                'class_level': 'SSS 1',
                'admission_number': 'STU005',
            },
            
            # Emeka Nwankwo's children
            {
                'username': 'student_chika_nwankwo',
                'email': 'chika.nwankwo@student.school.com',
                'first_name': 'Chika',
                'last_name': 'Nwankwo',
                'parent': parents['parent_emeka'],
                'class_level': 'SSS 3',
                'admission_number': 'STU006',
            },
            
            # Blessing Ogun's children
            {
                'username': 'student_david_ogun',
                'email': 'david.ogun@student.school.com',
                'first_name': 'David',
                'last_name': 'Ogun',
                'parent': parents['parent_blessing'],
                'class_level': 'JSS 1',
                'admission_number': 'STU007',
            },
            {
                'username': 'student_grace_ogun',
                'email': 'grace.ogun@student.school.com',
                'first_name': 'Grace',
                'last_name': 'Ogun',
                'parent': parents['parent_blessing'],
                'class_level': 'JSS 2',
                'admission_number': 'STU008',
            },
        ]
        
        students_created = 0
        for data in students_data:
            student, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': 'student',
                    'is_active': True,
                }
            )
            
            if created:
                student.set_password('password123')  # Default password
                student.save()
                students_created += 1
                
                # Create user profile with additional student information
                try:
                    from users.models import UserProfile
                    UserProfile.objects.get_or_create(
                        user=student,
                        defaults={
                            'parent': data['parent'],
                            'admission_number': data['admission_number'],
                            'class_level': data['class_level'],
                            'date_of_birth': datetime(2008 + random.randint(0, 6), random.randint(1, 12), random.randint(1, 28)),
                        }
                    )
                except ImportError:
                    # If UserProfile doesn't exist, just continue
                    pass
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(parents)} parents and {students_created} students'))