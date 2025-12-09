# management/commands/seed_all.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random
from datetime import datetime, timedelta
from exams.models import Class
import string
import os

# Import your models
from users.models import User, Student, Parent, Teacher, Staff, StudentParent
from store.models import (
    Category, Product, Cart, CartItem, Order, OrderItem,
    Payment, Transaction, Refund, FeeStructure, FeePayment,
    Inventory, Supplier, PurchaseOrder
)

UserModel = get_user_model()

class Command(BaseCommand):
    help = 'Seed comprehensive data for BrillsPay system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )
        
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of regular users to create'
        )
        
        parser.add_argument(
            '--students',
            type=int,
            default=200,
            help='Number of students to create'
        )
        
        parser.add_argument(
            '--products',
            type=int,
            default=100,
            help='Number of products to create'
        )
        
        parser.add_argument(
            '--orders',
            type=int,
            default=50,
            help='Number of orders to create'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('BrillsPay Comprehensive Seeding'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        if options['clear']:
            self.clear_data()
        
        # Step 1: Create superadmin and admin users
        self.create_superadmin()
        self.create_admin_users()
        
        # Step 2: Create school classes
        classes = self.create_school_classes()
        
        # Step 3: Create regular users
        users = self.create_regular_users(options['users'])
        
        # Step 4: Create students
        students = self.create_students(classes, options['students'])
        
        # Step 5: Create parents and link with students
        parents = self.create_parents(users[:len(users)//2], students)
        
        # Step 6: Create teachers
        teachers = self.create_teachers(users[len(users)// 2 : len(users)//4*3])
        
        # Step 7: Create staff
        staff = self.create_staff(users[users//4*3:])
        
        # Step 8: Create categories
        categories = self.create_categories()
        
        # Step 9: Create products
        products = self.create_products(categories, options['products'])
        
        # Step 10: Create fee structures
        fee_structures = self.create_fee_structures(classes)
        
        # Step 11: Create orders and payments
        self.create_orders_and_payments(users, students, products, options['orders'])
        
        # Step 12: Create fee payments
        self.create_fee_payments(students, fee_structures)
        
        # Step 13: Create inventory and suppliers
        self.create_inventory_and_suppliers(products)
        
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('Seeding completed successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Show summary
        self.show_summary()
    
    def clear_data(self):
        """Clear existing data"""
        self.stdout.write(self.style.WARNING('Clearing existing data...'))
        
        # Clear in reverse order to avoid foreign key constraints
        models_to_clear = [
            PurchaseOrder, Inventory, Supplier,
            FeePayment, FeeStructure,
            Refund, Transaction, Payment,
            OrderItem, Order,
            CartItem, Cart,
            StudentParent,
            Product, Category,
            Staff, Teacher, Parent, Student, User
        ]
        
        for model in models_to_clear:
            try:
                count = model.objects.count()
                model.objects.all().delete()
                self.stdout.write(f"  Cleared {count} {model._meta.verbose_name_plural}")
            except Exception as e:
                self.stdout.write(f"  Could not clear {model._meta.verbose_name}: {e}")
    
    def create_superadmin(self):
        """Create superadmin user"""
        self.stdout.write('\n' + self.style.SUCCESS('1. Creating Superadmin...'))
        
        superadmin_data = {
            'username': 'superadmin',
            'email': 'superadmin@brillspay.com',
            'first_name': 'Super',
            'last_name': 'Admin',
            'phone': '+2348000000001',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'is_verified': True,
            'is_approved': True,
        }
        
        user, created = UserModel.objects.get_or_create(
            username=superadmin_data['username'],
            defaults=superadmin_data
        )
        
        if created:
            user.set_password('superadmin123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created superadmin: {user.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⓘ Superadmin already exists: {user.email}'))
        
        return user
    
    def create_admin_users(self):
        """Create admin users"""
        self.stdout.write('\n' + self.style.SUCCESS('2. Creating Admin Users...'))
        
        admins = [
            {
                'username': 'admin_finance',
                'email': 'finance@brillspay.com',
                'first_name': 'Finance',
                'last_name': 'Admin',
                'phone': '+2348000000002',
                
            },
            {
                'username': 'admin_store',
                'email': 'store@brillspay.com',
                'first_name': 'Store',
                'last_name': 'Admin',
                'phone': '+2348000000003',
                
            },
            {
                'username': 'admin_school',
                'email': 'school@brillspay.com',
                'first_name': 'School',
                'last_name': 'Admin',
                'phone': '+2348000000004',
                
            },
        ]
        
        admin_users = []
        for admin_data in admins:
            user, created = UserModel.objects.get_or_create(
                username=admin_data['username'],
                defaults=admin_data
            )
            
            if created:
                user.set_password('admin123')
                user.is_staff = True
                user.is_active = True
                user.is_verified = True
                user.is_approved = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created admin: {user.email}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⓘ Admin already exists: {user.email}'))
            
            admin_users.append(user)
        
        return admin_users
    
    def create_school_classes(self):
        """Create school classes"""
        self.stdout.write('\n' + self.style.SUCCESS('3. Creating School Classes...'))
        
        grade_level = [
            # Nursery
            {'name': 'Nursery 1', 'grade_level': 'Nursery', 'section': 'A'},
            {'name': 'Nursery 2', 'grade_level': 'Nursery', 'section': 'A'},
            {'name': 'Nursery 3', 'grade_level': 'Nursery', 'section': 'A'},
            
            # Primary
            {'name': 'Primary 1', 'grade_level': 'Primary', 'section': 'A'},
            {'name': 'Primary 2', 'grade_level': 'Primary', 'section': 'A'},
            {'name': 'Primary 3', 'grade_level': 'Primary', 'section': 'A'},
            {'name': 'Primary 4', 'grade_level': 'Primary', 'section': 'A'},
            {'name': 'Primary 5', 'grade_level': 'Primary', 'section': 'A'},
            {'name': 'Primary 6', 'grade_level': 'Primary', 'section': 'A'},
            
            # Junior Secondary
            {'name': 'JSS 1', 'grade_level': 'Junior Secondary', 'section': 'A'},
            {'name': 'JSS 1', 'grade_level': 'Junior Secondary', 'section': 'B'},
            {'name': 'JSS 2', 'grade_level': 'Junior Secondary', 'section': 'A'},
            {'name': 'JSS 2', 'grade_level': 'Junior Secondary', 'section': 'B'},
            {'name': 'JSS 3', 'grade_level': 'Junior Secondary', 'section': 'A'},
            {'name': 'JSS 3', 'grade_level': 'Junior Secondary', 'section': 'B'},
            
            # Senior Secondary
            {'name': 'SSS 1', 'grade_level': 'Senior Secondary', 'section': 'A'},
            {'name': 'SSS 1', 'grade_level': 'Senior Secondary', 'section': 'B'},
            {'name': 'SSS 2', 'grade_level': 'Senior Secondary', 'section': 'A'},
            {'name': 'SSS 2', 'grade_level': 'Senior Secondary', 'section': 'B'},
            {'name': 'SSS 3', 'grade_level': 'Senior Secondary', 'section': 'A'},
            {'name': 'SSS 3', 'grade_level': 'Senior Secondary', 'section': 'B'},
        ]
        
        classes = []
        for class_data in grade_level:
            cls, created = Class.objects.get_or_create(
                name=class_data['name'],
                defaults={
                    'grade_level': class_data['grade_level'],
                    'academic_year': '2025/2026'
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Created class: {cls.name}')
            else:
                self.stdout.write(f'  ⓘ Class exists: {cls.name}')
            
            classes.append(cls)
        
        return classes
    
    def create_regular_users(self, count):
        """Create regular users (parents and students)"""
        self.stdout.write('\n' + self.style.SUCCESS(f'4. Creating {count} Regular Users...'))
        
        first_names = [
            'John', 'Mary', 'David', 'Sarah', 'Michael', 'Elizabeth', 'James', 'Patricia',
            'Robert', 'Jennifer', 'William', 'Linda', 'Richard', 'Barbara', 'Joseph', 'Susan',
            'Thomas', 'Jessica', 'Charles', 'Sarah', 'Christopher', 'Karen', 'Daniel', 'Nancy',
            'Matthew', 'Lisa', 'Anthony', 'Margaret', 'Donald', 'Sandra', 'Mark', 'Ashley',
            'Paul', 'Kimberly', 'Steven', 'Emily', 'Andrew', 'Donna', 'Kenneth', 'Michelle'
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
            'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
            'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
            'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores'
        ]
        
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'brillspay.com']
        
        users = []
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}.{last_name.lower()}{i}"
            email = f"{first_name.lower()}.{last_name.lower()}{i}@{random.choice(domains)}"
            phone = f"+23480{random.randint(10000000, 99999999)}"
            
            user_data = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'is_active': True,
                'is_verified': random.choice([True, False]),
                'is_approved': True,
            }
            
            try:
                user = UserModel.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password='password123',
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    phone=user_data['phone'],
                    is_active=user_data['is_active'],
                    is_verified=user_data['is_verified'],
                    is_approved=user_data['is_approved']
                )
                users.append(user)
                
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  Created {i + 1} users...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating user {username}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(users)} regular users'))
        return users
    
    def create_students(self, classes, count):
        """Create students"""
        self.stdout.write('\n' + self.style.SUCCESS(f'5. Creating {count} Students...'))
        
        first_names = [
            'Chiamaka', 'Chukwudi', 'Obinna', 'Ngozi', 'Emeka', 'Aisha', 'Fatima', 'Mohammed',
            'Blessing', 'Goodluck', 'Victoria', 'Samuel', 'Daniel', 'Joy', 'Peace', 'Faith',
            'David', 'Solomon', 'Ruth', 'Esther', 'John', 'Peter', 'Paul', 'James', 'Andrew',
            'Philip', 'Bartholomew', 'Matthew', 'Thomas', 'Simon', 'Judas', 'Mary', 'Martha',
            'Lazarus', 'Zacchaeus', 'Nicodemus', 'Joseph', 'Benjamin', 'Reuben', 'Simeon',
            'Levi', 'Judah', 'Dan', 'Naphtali', 'Gad', 'Asher', 'Issachar', 'Zebulun'
        ]
        
        last_names = [
            'Adebayo', 'Okafor', 'Chukwu', 'Nwankwo', 'Onyeka', 'Eze', 'Okoro', 'Adeyemi',
            'Akinwumi', 'Balogun', 'Bello', 'Dairo', 'Ezeife', 'Falana', 'Gbadamosi', 'Ibe',
            'Jaja', 'Kalu', 'Lamidi', 'Mbanefo', 'Nwachukwu', 'Obi', 'Okonkwo', 'Olanrewaju',
            'Onwuka', 'Opara', 'Oshodi', 'Oyekan', 'Salami', 'Talabi', 'Uchendu', 'Ude',
            'Ukaegbu', 'Umeh', 'Uzodinma', 'Wachuku', 'Yakubu', 'Yusuf', 'Zubairu'
        ]
        
        students = []
        for i in range(count):
            admission_number = f"STD/{datetime.now().year}/{i+1:05d}"
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            dob = datetime.now() - timedelta(days=random.randint(365*5, 365*18))
            gender = random.choice(['M', 'F'])
            student_class = random.choice(classes)
            
            student_data = {
                'admission_number': admission_number,
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': dob.date(),
                'gender': gender,
                'student_class': student_class,                
                'academic_year': '2025/2026',
                'emergency_contact': f"Emergency Contact {i+1}",
                'emergency_phone': f"+23470{random.randint(10000000, 99999999)}",
                'is_active': True,
            }
            
            try:
                student = Student.objects.create(**student_data)
                students.append(student)
                
                if (i + 1) % 20 == 0:
                    self.stdout.write(f'  Created {i + 1} students...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating student {admission_number}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(students)} students'))
        return students
    
    def create_parents(self, users, students):
        """Create parents and link with students"""
        self.stdout.write('\n' + self.style.SUCCESS('6. Creating Parents and Linking with Students...'))
        
        parent_users = [u for u in users ]
        
        parents = []
        for i, user in enumerate(parent_users):
            try:
                parent, created = Parent.objects.get_or_create(
                    user=user,
                    defaults={
                        'phone': user.phone,
                        'occupation': random.choice(['Teacher', 'Doctor', 'Engineer', 'Lawyer', 'Business', 'Civil Servant', 'Nurse']),
                        'employer': f"{random.choice(['Global', 'National', 'State', 'Local'])} {random.choice(['Company', 'Enterprise', 'Corporation', 'Limited'])}",
                        'income_range': random.choice(['low', 'middle', 'high']),
                        'relationship': random.choice(['father', 'mother', 'guardian']),
                        'address': f"{random.randint(1, 999)} {random.choice(['Main', 'Broad', 'High'])} Street, {random.choice(['Lagos', 'Abuja', 'Port Harcourt', 'Ibadan'])}",
                        'city': random.choice(['Lagos', 'Abuja', 'Port Harcourt', 'Ibadan', 'Kano']),
                        'state': random.choice(['Lagos', 'FCT', 'Rivers', 'Oyo', 'Kano']),
                        'preferred_payment_method': random.choice(['paystack', 'bank_transfer', 'cash', 'card']),
                        'is_primary': random.choice([True, False]),
                    }
                )
                
                # Link with 1-3 random students
                num_students = random.randint(1, 3)
                selected_students = random.sample(students, min(num_students, len(students)))
                
                for student in selected_students:
                    StudentParent.objects.get_or_create(
                        student=student,
                        parent=parent,
                        defaults={
                            'is_primary_guardian': random.choice([True, False]),
                            'can_pickup': random.choice([True, False]),
                        }
                    )
                
                parents.append(parent)
                
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  Created {i + 1} parents...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating parent for {user.username}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(parents)} parents'))
        return parents
    
    def create_teachers(self, users):
        """Create teachers"""
        self.stdout.write('\n' + self.style.SUCCESS('7. Creating Teachers...'))
        
        subjects = [
            'Mathematics', 'English Language', 'Physics', 'Chemistry', 'Biology',
            'Economics', 'Accounting', 'Commerce', 'Government', 'History',
            'Geography', 'Literature', 'French', 'Arabic', 'Yoruba', 'Igbo',
            'Hausa', 'Computer Science', 'Agricultural Science', 'Physical Education',
            'Music', 'Fine Arts', 'Home Economics', 'Technical Drawing'
        ]
        
        teachers = []
        for i, user in enumerate(users[:len(users)//2]):  # Use first half for teachers
            try:
                # Update user role to teacher
               
                user.save()
                
                teacher, created = Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        'staff_id': f"TCH/{datetime.now().year}/{i+1:03d}",
                        'subject': random.choice(subjects),
                        'class_teacher_of': random.choice(['JSS 1A', 'JSS 2B', 'SSS 1A', 'SSS 3B', '']),
                        'qualification': random.choice(['B.Sc', 'B.Ed', 'M.Sc', 'M.Ed', 'PhD']),
                        'years_of_experience': random.randint(1, 30),
                        'joining_date': datetime.now() - timedelta(days=random.randint(30, 3650)),
                        'phone': user.phone,
                        'emergency_contact': f"Emergency Contact {i+1}",
                        'emergency_phone': f"+23470{random.randint(10000000, 99999999)}",
                        'is_active': True,
                    }
                )
                
                teachers.append(teacher)
                
                if (i + 1) % 5 == 0:
                    self.stdout.write(f'  Created {i + 1} teachers...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating teacher for {user.username}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(teachers)} teachers'))
        return teachers
    
    def create_staff(self, users):
        """Create staff members"""
        self.stdout.write('\n' + self.style.SUCCESS('8. Creating Staff Members...'))
        
        staff_members = []
        for i, user in enumerate(users):  # Use remaining users for staff
            try:
                # Update user role to staff
               
                user.save()
                
                staff, created = Staff.objects.get_or_create(
                    user=user,
                    defaults={
                        'staff_id': f"STF/{datetime.now().year}/{i+1:03d}",
                        'department': random.choice(['administration', 'accounts', 'library', 'laboratory', 'maintenance', 'security']),
                        'position': random.choice(['Manager', 'Assistant', 'Officer', 'Clerk', 'Technician']),
                        'qualification': random.choice(['B.Sc', 'HND', 'OND', 'SSCE']),
                        'joining_date': datetime.now() - timedelta(days=random.randint(30, 3650)),
                        'phone': user.phone,
                        'is_active': True,
                    }
                )
                
                staff_members.append(staff)
                
                if (i + 1) % 5 == 0:
                    self.stdout.write(f'  Created {i + 1} staff...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating staff for {user.username}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(staff_members)} staff members'))
        return staff_members
    
    def create_categories(self):
        """Create product categories"""
        self.stdout.write('\n' + self.style.SUCCESS('9. Creating Product Categories...'))
        
        categories_data = [
            {
                'name': 'Textbooks',
                'slug': 'textbooks',
                'description': 'Educational textbooks for all levels',
                'is_active': True,
            },
            {
                'name': 'Stationery',
                'slug': 'stationery',
                'description': 'Writing materials and office supplies',
                'is_active': True,
            },
            {
                'name': 'School Uniforms',
                'slug': 'school-uniforms',
                'description': 'School uniforms and accessories',
                'is_active': True,
            },
            {
                'name': 'Electronics',
                'slug': 'electronics',
                'description': 'Electronic devices and accessories',
                'is_active': True,
            },
            {
                'name': 'Hostel Supplies',
                'slug': 'hostel-supplies',
                'description': 'Items for hostel accommodation',
                'is_active': True,
            },
            {
                'name': 'Sports Equipment',
                'slug': 'sports-equipment',
                'description': 'Sports gear and equipment',
                'is_active': True,
            },
            {
                'name': 'Food & Snacks',
                'slug': 'food-snacks',
                'description': 'Food items and snacks',
                'is_active': True,
            },
        ]
        
        categories = []
        for data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=data['slug'],
                defaults=data
            )
            categories.append(category)
            
            if created:
                self.stdout.write(f'  ✓ Created category: {category.name}')
        
        # Create some subcategories
        subcategories = [
            {'name': 'Mathematics Books', 'slug': 'math-books', 'parent': categories[0]},
            {'name': 'Science Books', 'slug': 'science-books', 'parent': categories[0]},
            {'name': 'Notebooks', 'slug': 'notebooks', 'parent': categories[1]},
            {'name': 'Pens & Pencils', 'slug': 'pens-pencils', 'parent': categories[1]},
        ]
        
        for data in subcategories:
            subcategory, created = Category.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'parent': data['parent'],
                    'description': f'{data["name"]} for students',
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Created subcategory: {subcategory.name}')
        
        return categories
    
    def create_products(self, categories, count):
        """Create products"""
        self.stdout.write('\n' + self.style.SUCCESS(f'10. Creating {count} Products...'))
        
        product_names = {
            'textbooks': [
                'Mathematics for JSS 1', 'English Language for SSS', 'Basic Science Textbook',
                'Nigerian History', 'Literature in English', 'Physics for Senior Secondary',
                'Chemistry Made Easy', 'Biology Textbook', 'Economics Principles',
                'Commerce Textbook', 'Government for SSS', 'Geography Textbook',
            ],
            'stationery': [
                'Student Notebook (80 pages)', 'Ballpoint Pen (Pack of 10)',
                'Mathematical Set', 'School Backpack', 'Scientific Calculator',
                'Geometry Box', 'Whiteboard Marker (Pack of 5)', 'Stapler',
                'Staple Pins (Box of 1000)', 'Glue Stick', 'Highlighter (Pack of 6)',
                'Pencil Case', 'Ruler (30cm)', 'Compass for Mathematics',
            ],
            'school-uniforms': [
                'School Shirt (White)', 'School Trousers (Black)',
                'School Skirt (Pleated)', 'School Blazer', 'School Tie',
                'School Socks (White)', 'School Shoes (Black)', 'PE Kit',
                'School Cap', 'School Belt', 'School Cardigan',
            ],
            'electronics': [
                'Student Tablet', 'Laptop for Students', 'Power Bank (10000mAh)',
                'USB Flash Drive 32GB', 'Headphones for Students',
                'Scientific Calculator (Advanced)', 'Digital Watch',
                'Portable Speaker', 'Phone Charger', 'Extension Socket',
            ],
            'hostel-supplies': [
                'Student Mattress', 'Bed Sheets Set', 'Student Pillow',
                'Mosquito Net', 'Laundry Basket', 'Bucket', 'Bath Towel',
                'Plastic Cup (Set of 6)', 'Plate Set', 'Cutlery Set',
                'Water Bottle', 'Lunch Box', 'Thermos Flask',
            ],
            'sports-equipment': [
                'Football', 'Basketball', 'Volleyball', 'Table Tennis Set',
                'Badminton Racket', 'Running Shoes', 'Sports Jersey',
                'Sports Shorts', 'Sports Socks', 'Swimming Goggles',
            ],
            'food-snacks': [
                'Packaged Biscuits', 'Fruit Juice (500ml)', 'Packaged Water',
                'Snack Bar', 'Chocolate Bar', 'Candy Pack', 'Nuts Mix',
                'Cereal Bar', 'Energy Drink', 'Milk Pack',
            ],
        }
        
        products = []
        for i in range(count):
            category = random.choice(categories)
            category_name = category.name.lower()
            
            if 'textbook' in category_name:
                name_list = product_names['textbooks']
            elif 'stationery' in category_name:
                name_list = product_names['stationery']
            elif 'uniform' in category_name:
                name_list = product_names['school-uniforms']
            elif 'electronic' in category_name:
                name_list = product_names['electronics']
            elif 'hostel' in category_name:
                name_list = product_names['hostel-supplies']
            elif 'sport' in category_name:
                name_list = product_names['sports-equipment']
            elif 'food' in category_name:
                name_list = product_names['food-snacks']
            else:
                name_list = product_names['stationery']  # Default
            
            name = random.choice(name_list)
            sku = f"SKU{datetime.now().year}{i+1:05d}"
            slug = f"{name.lower().replace(' ', '-').replace('(', '').replace(')', '')}-{i+1}"
            
            price = Decimal(random.randint(100, 50000))  # Between ₦100 and ₦50,000
            cost_price = price * Decimal(random.uniform(0.4, 0.7))
            stock = random.randint(0, 200)
            
            product_data = {
                'name': name,
                'slug': slug,
                'category': category,
                'description': f'High quality {name.lower()} for student use. Durable and reliable.',
                'price': price,
                'cost_price': cost_price,
                'stock_quantity': stock,
                'low_stock_threshold': 10,
                'sku': sku,
                'barcode': f'890123456789{i+1:03d}',
                'size': random.choice(['', 'Small', 'Medium', 'Large']),
                'color': random.choice(['', 'Red', 'Blue', 'Green', 'Black', 'White']),
                'material': random.choice(['', 'Plastic', 'Metal', 'Fabric', 'Paper', 'Rubber']),
                'weight': random.choice(['', '100g', '250g', '500g', '1kg']),
                'dimensions': random.choice(['', '10x15x5cm', '20x30x10cm', '30x40x15cm']),
                'is_active': random.choice([True, True, True, False]),  # 75% active
                'is_featured': random.choice([True, False]),
                'total_sold': random.randint(0, 100),
                'total_views': random.randint(0, 500),
                'meta_title': name,
                'meta_description': f'Buy {name} online at BrillsPay. Best quality for students.',
            }
            
            try:
                product = Product.objects.create(**product_data)
                products.append(product)
                
                if (i + 1) % 20 == 0:
                    self.stdout.write(f'  Created {i + 1} products...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating product {sku}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(products)} products'))
        return products
    
    def create_fee_structures(self, classes):
        """Create fee structures"""
        self.stdout.write('\n' + self.style.SUCCESS('11. Creating Fee Structures...'))
        
        fee_types = [
            'Tuition Fee', 'Development Levy', 'Examination Fee', 
            'Sports Fee', 'Laboratory Fee', 'Library Fee',
            'ICT Fee', 'Medical Fee', 'ID Card Fee', 'PTA Levy'
        ]
        
        fee_structures = []
        term_choices = ['first', 'second', 'third', 'annual']
        
        for term in term_choices:
            for cls in classes:
                for fee_type in fee_types[:3]:  # Create 3 fee types per class per term
                    fee_data = {
                        'name': f'{fee_type} - {cls.name}',
                        'description': f'{fee_type} for {cls.name} {term.title()} Term {datetime.now().year}/{datetime.now().year+1}',
                        'academic_year': f'{datetime.now().year}/{datetime.now().year+1}',
                        'student_class': cls,
                        'term': term,
                        'amount': Decimal(random.randint(5000, 50000)),
                        'due_date': datetime.now() + timedelta(days=random.randint(30, 180)),
                        'late_fee': Decimal(random.randint(1000, 5000)),
                        'late_fee_date': datetime.now() + timedelta(days=random.randint(180, 210)),
                        'tuition_fee': Decimal(random.randint(20000, 100000)) if fee_type == 'Tuition Fee' else Decimal('0.00'),
                        'development_levy': Decimal(random.randint(5000, 20000)) if fee_type == 'Development Levy' else Decimal('0.00'),
                        'exam_fee': Decimal(random.randint(3000, 15000)) if fee_type == 'Examination Fee' else Decimal('0.00'),
                        'sports_fee': Decimal(random.randint(2000, 10000)) if fee_type == 'Sports Fee' else Decimal('0.00'),
                        'other_charges': Decimal(random.randint(1000, 5000)),
                        'is_active': True,
                        'is_compulsory': random.choice([True, False]),
                    }
                    
                    try:
                        fee_structure = FeeStructure.objects.create(**fee_data)
                        fee_structures.append(fee_structure)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error creating fee structure: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(fee_structures)} fee structures'))
        return fee_structures
    
    def create_orders_and_payments(self, users, students, products, count):
        """Create orders and payments"""
        self.stdout.write('\n' + self.style.SUCCESS(f'12. Creating {count} Orders and Payments...'))
        
        # Get parent users
        parent_users = [u for u in users]
        
        for i in range(count):
            try:
                # Select random parent and student
                user = random.choice(parent_users)
                student = random.choice(students)
                
                # Create cart
                cart, created = Cart.objects.get_or_create(
                    user=user,
                    student=student,
                    defaults={'is_active': True}
                )
                
                # Add 1-5 random products to cart
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))
                
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    cart.add_item(product, quantity, student)
                
                # Create order from cart
                order = Order.objects.create(
                    user=user,
                    student=student,
                    status=random.choice(['pending', 'processing', 'shipped', 'delivered']),
                    payment_status=random.choice(['pending', 'completed', 'failed']),
                    payment_method=random.choice(['paystack', 'bank_transfer', 'cash', 'card']),
                    shipping_address=f"{random.randint(1, 999)} {random.choice(['Main', 'Broad', 'High'])} Street",
                    subtotal=cart.total_amount,
                    shipping_fee=Decimal(random.randint(500, 2000)),
                    discount_amount=Decimal(random.randint(0, 1000)),
                )
                order.calculate_totals()
                order.save()
                
                # Create order items
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price,
                        product_name=cart_item.product.name,
                        product_sku=cart_item.product.sku
                    )
                
                # Create payment if order is paid
                if order.payment_status == 'completed':
                    payment = Payment.objects.create(
                        order=order,
                        amount=order.total_amount,
                        payment_method=order.payment_method,
                        status='completed',
                        payer_email=user.email,
                        payer_phone=user.phone,
                        payer_name=user.get_full_name(),
                        reference=f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i+1}",
                        paystack_reference=f"PSK-{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}",
                        transaction_id=f"TXN-{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}",
                        verified_at=timezone.now(),
                    )
                    
                    # Create transaction
                    Transaction.objects.create(
                        user=user,
                        student=student,
                        payment=payment,
                        order=order,
                        transaction_id=payment.transaction_id,
                        transaction_type='payment',
                        amount=payment.amount,
                        status='completed',
                        description=f'Payment for order {order.order_number}',
                        reference=payment.reference,
                        completed_at=timezone.now(),
                    )
                
                # Clear cart after order
                cart.clear()
                cart.is_active = False
                cart.save()
                
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  Created {i + 1} orders...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating order {i+1}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {count} orders with payments'))
    
    def create_fee_payments(self, students, fee_structures):
        """Create fee payments"""
        self.stdout.write('\n' + self.style.SUCCESS('13. Creating Fee Payments...'))
        
        # Get admin user for verification
        admin_user = UserModel.objects.filter(role='admin').first()
        
        count = 0
        for student in students:
            # Get fee structures for student's class
            student_fees = fee_structures.filter(student_class=student.student_class)
            
            for fee in student_fees[:random.randint(0, 3)]:  # 0-3 fee payments per student
                try:
                    amount_paid = fee.amount
                    if random.choice([True, False]):  # Sometimes partial payment
                        amount_paid = fee.amount * Decimal(random.uniform(0.3, 0.9))
                    
                    fee_payment = FeePayment.objects.create(
                        student=student,
                        fee_structure=fee,
                        amount_paid=amount_paid,
                        payment_method=random.choice(['paystack', 'bank_transfer', 'cash', 'card']),
                        payment_reference=f"FEE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{count+1}",
                        is_verified=random.choice([True, False]),
                        verified_by=admin_user if random.choice([True, False]) else None,
                        verification_date=timezone.now() if random.choice([True, False]) else None,
                        receipt_issued=random.choice([True, False]),
                        receipt_issued_by=admin_user if random.choice([True, False]) else None,
                    )
                    
                    # Create payment record for fee payment
                    if random.choice([True, False]):  # 50% chance to create payment record
                        Payment.objects.create(
                            fee_payment=fee_payment,
                            amount=fee_payment.amount_paid,
                            payment_method=fee_payment.payment_method,
                            status='completed' if fee_payment.is_verified else 'pending',
                            payer_email=student.parents.first().user.email if student.parents.exists() else '',
                            payer_phone=student.parents.first().user.phone if student.parents.exists() else '',
                            payer_name=student.get_full_name(),
                            reference=fee_payment.payment_reference,
                            verified_at=fee_payment.verification_date,
                        )
                    
                    count += 1
                    
                    if count % 20 == 0:
                        self.stdout.write(f'  Created {count} fee payments...')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating fee payment: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {count} fee payments'))
    
    def create_inventory_and_suppliers(self, products):
        """Create inventory and suppliers"""
        self.stdout.write('\n' + self.style.SUCCESS('14. Creating Inventory and Suppliers...'))
        
        # Create suppliers
        suppliers_data = [
            {
                'name': 'Global Education Supplies',
                'contact_person': 'Mr. Adebayo Johnson',
                'phone': '+2348012345678',
                'email': 'supplies@globaledu.com',
                'address': '123 Business District, Lagos',
                'tax_id': 'TAX-001',
                'rating': Decimal('4.5'),
                'payment_terms': 'Net 30',
            },
            {
                'name': 'Scholar Books Limited',
                'contact_person': 'Mrs. Ngozi Okoro',
                'phone': '+2348098765432',
                'email': 'books@scholar.com',
                'address': '456 Academic Road, Abuja',
                'tax_id': 'TAX-002',
                'rating': Decimal('4.2'),
                'payment_terms': 'Net 45',
            },
            {
                'name': 'Uniforms Plus',
                'contact_person': 'Mr. Chukwudi Eze',
                'phone': '+2348055555555',
                'email': 'uniforms@uniformsplus.com',
                'address': '789 Fashion Street, Port Harcourt',
                'tax_id': 'TAX-003',
                'rating': Decimal('4.7'),
                'payment_terms': 'Net 15',
            },
        ]
        
        suppliers = []
        for data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            suppliers.append(supplier)
            
            if created:
                self.stdout.write(f'  ✓ Created supplier: {supplier.name}')
        
        # Create inventory for products
        inventory_count = 0
        for product in products:
            try:
                inventory, created = Inventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'current_stock': product.stock_quantity,
                        'minimum_stock': 10,
                        'maximum_stock': 1000,
                        'location': f'Shelf {random.randint(1, 50)}, Aisle {random.randint(1, 10)}',
                        'reorder_point': 20,
                        'last_restocked': timezone.now() - timedelta(days=random.randint(1, 90)),
                        'restock_quantity': random.randint(50, 200),
                        'is_low_stock': product.stock_quantity <= 10,
                        'needs_restock': product.stock_quantity <= 20,
                    }
                )
                
                if created:
                    inventory_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating inventory for {product.sku}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created inventory for {inventory_count} products'))
        
        # Create some purchase orders
        po_count = 0
        for supplier in suppliers:
            for i in range(random.randint(1, 3)):
                try:
                    po = PurchaseOrder.objects.create(
                        supplier=supplier,
                        items=f'Various school supplies from {supplier.name}',
                        total_amount=Decimal(random.randint(50000, 500000)),
                        status=random.choice(['draft', 'pending', 'approved', 'ordered', 'received']),
                        order_date=timezone.now().date() - timedelta(days=random.randint(1, 30)),
                        expected_delivery=timezone.now().date() + timedelta(days=random.randint(7, 30)),
                        notes=f'Purchase order #{i+1} for {supplier.name}',
                    )
                    
                    po_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating purchase order: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {po_count} purchase orders'))
    
    def show_summary(self):
        """Show seeding summary"""
        self.stdout.write('\n' + self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('SEEDING SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        summary_data = [
            ('Superadmin/Admins', UserModel.objects.filter(role__in=['superadmin', 'admin']).count()),
            ('Regular Users', UserModel.objects.filter(role__in=['student', 'parent']).count()),
            ('Students', Student.objects.count()),
            ('Parents', Parent.objects.count()),
            ('Teachers', Teacher.objects.count()),
            ('Staff', Staff.objects.count()),
            ('Categories', Category.objects.count()),
            ('Products', Product.objects.count()),
            ('Carts', Cart.objects.count()),
            ('Orders', Order.objects.count()),
            ('Payments', Payment.objects.count()),
            ('Transactions', Transaction.objects.count()),
            ('Fee Structures', FeeStructure.objects.count()),
            ('Fee Payments', FeePayment.objects.count()),
            ('Suppliers', Supplier.objects.count()),
            ('Inventory Items', Inventory.objects.count()),
            ('Purchase Orders', PurchaseOrder.objects.count()),
        ]
        
        for label, count in summary_data:
            self.stdout.write(f"  {label:25} : {count:>5}")
        
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Display login credentials
        self.stdout.write('\n' + self.style.SUCCESS('TEST CREDENTIALS:'))
        self.stdout.write(self.style.SUCCESS('-'*40))
        self.stdout.write(self.style.SUCCESS('Superadmin:'))
        self.stdout.write(self.style.SUCCESS('  Email: superadmin@brillspay.com'))
        self.stdout.write(self.style.SUCCESS('  Password: superadmin123'))
        self.stdout.write(self.style.SUCCESS('\nAdmin Users:'))
        
        for admin in UserModel.objects.filter(role='admin')[:3]:
            self.stdout.write(self.style.SUCCESS(f'  Email: {admin.email}'))
            self.stdout.write(self.style.SUCCESS(f'  Password: admin123'))
        
        self.stdout.write(self.style.SUCCESS('\nRegular Users:'))
        self.stdout.write(self.style.SUCCESS('  Email: (any parent/student email from list)'))
        self.stdout.write(self.style.SUCCESS('  Password: password123'))