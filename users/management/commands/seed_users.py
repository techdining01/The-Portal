from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Parent, Class
import random
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample users'

    def handle(self, *args, **options):
        self.stdout.write('Seeding user data...')
        
        # Create sample students
        students = self.create_students()
        
        # Create sample parents
        parents = self.create_parents(students)
        
        # Create sample teachers
        teachers = self.create_teachers()
        
        # Create admin users
        self.create_admins()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded user data!')
        )

    def create_students(self):
        # Get some classes to assign students to
        classes = Class.objects.all().order_by('order')[:6]
        
        students_data = [
            {
                'email': 'john.doe@student.brillspay.edu',
                'surname': 'Doe',
                'first_name': 'John',
                'other_name': 'Michael',
                'role': 'student',
                'gender': 'male',
                'age': 14,
                'date_of_birth': '2009-05-15',
                'phone_number': '08031112233',
                'address': '123 Main Street, Lagos',
                'student_class': classes[0] if classes else None
            },
            {
                'email': 'sarah.johnson@student.brillspay.edu',
                'surname': 'Johnson',
                'first_name': 'Sarah',
                'other_name': 'Grace',
                'role': 'student',
                'gender': 'female',
                'age': 15,
                'date_of_birth': '2008-08-22',
                'phone_number': '08032223344',
                'address': '456 Oak Avenue, Abuja',
                'student_class': classes[1] if classes else None
            },
            {
                'email': 'david.smith@student.brillspay.edu',
                'surname': 'Smith',
                'first_name': 'David',
                'other_name': 'James',
                'role': 'student',
                'gender': 'male',
                'age': 16,
                'date_of_birth': '2007-03-10',
                'phone_number': '08033334455',
                'address': '789 Pine Road, Port Harcourt',
                'student_class': classes[2] if classes else None
            },
            {
                'email': 'emily.brown@student.brillspay.edu',
                'surname': 'Brown',
                'first_name': 'Emily',
                'other_name': 'Rose',
                'role': 'student',
                'gender': 'female',
                'age': 17,
                'date_of_birth': '2006-11-30',
                'phone_number': '08034445566',
                'address': '321 Elm Street, Ibadan',
                'student_class': classes[3] if classes else None
            },
            {
                'email': 'michael.wilson@student.brillspay.edu',
                'surname': 'Wilson',
                'first_name': 'Michael',
                'other_name': 'Thomas',
                'role': 'student',
                'gender': 'male',
                'age': 18,
                'date_of_birth': '2005-07-18',
                'phone_number': '08035556677',
                'address': '654 Cedar Lane, Kano',
                'student_class': classes[4] if classes else None
            }
        ]

        students = []
        for student_data in students_data:
            user, created = User.objects.get_or_create(
                email=student_data['email'],
                defaults=student_data
            )
            if created:
                user.set_password('student123')  # Default password
                user.approved = True
                user.save()
                students.append(user)
                self.stdout.write(f'Created student: {user.get_full_name()}')

        return students

    def create_parents(self, students):
        parents_data = [
            {
                'email': 'robert.doe@parent.brillspay.edu',
                'surname': 'Doe',
                'first_name': 'Robert',
                'other_name': 'William',
                'role': 'parent',
                'gender': 'male',
                'age': 45,
                'phone_number': '08036667788',
                'address': '123 Main Street, Lagos',
                'occupation': 'Engineer',
                'emergency_contact': '08037778899'
            },
            {
                'email': 'linda.johnson@parent.brillspay.edu',
                'surname': 'Johnson',
                'first_name': 'Linda',
                'other_name': 'Marie',
                'role': 'parent',
                'gender': 'female',
                'age': 42,
                'phone_number': '08038889900',
                'address': '456 Oak Avenue, Abuja',
                'occupation': 'Doctor',
                'emergency_contact': '08039990011'
            }
        ]

        parents = []
        for i, parent_data in enumerate(parents_data):
            user, created = User.objects.get_or_create(
                email=parent_data['email'],
                defaults={
                    'surname': parent_data['surname'],
                    'first_name': parent_data['first_name'],
                    'other_name': parent_data['other_name'],
                    'role': parent_data['role'],
                    'gender': parent_data['gender'],
                    'age': parent_data['age'],
                    'phone_number': parent_data['phone_number'],
                    'address': parent_data['address']
                }
            )
            if created:
                user.set_password('parent123')  # Default password
                user.approved = True
                user.save()
                
                # Create parent profile
                parent_profile, _ = Parent.objects.get_or_create(
                    user=user,
                    defaults={
                        'address': parent_data['address'],
                        'occupation': parent_data['occupation'],
                        'emergency_contact': parent_data['emergency_contact']
                    }
                )
                
                # Assign children to parents
                if i == 0:  # First parent gets first two students
                    user.children.add(students[0], students[1])
                else:  # Second parent gets remaining students
                    user.children.add(students[2], students[3], students[4])
                
                parents.append(user)
                self.stdout.write(f'Created parent: {user.get_full_name()}')

        return parents

    def create_teachers(self):
        teachers_data = [
            {
                'email': 'james.anderson@teacher.brillspay.edu',
                'surname': 'Anderson',
                'first_name': 'James',
                'other_name': 'Robert',
                'role': 'teacher',
                'gender': 'male',
                'age': 35,
                'phone_number': '08031112299',
                'address': '234 Teacher Lane, Lagos',
                'qualification': 'M.Sc. Mathematics',
                'years_of_experience': 8,
                'next_of_kin': 'Mary Anderson',
                'next_of_kin_phone': '08032223399'
            },
            {
                'email': 'patricia.miller@teacher.brillspay.edu',
                'surname': 'Miller',
                'first_name': 'Patricia',
                'other_name': 'Ann',
                'role': 'teacher',
                'gender': 'female',
                'age': 32,
                'phone_number': '08033334499',
                'address': '567 Educator Road, Abuja',
                'qualification': 'B.Ed. English',
                'years_of_experience': 6,
                'next_of_kin': 'John Miller',
                'next_of_kin_phone': '08034445599'
            },
            {
                'email': 'richard.davis@teacher.brillspay.edu',
                'surname': 'Davis',
                'first_name': 'Richard',
                'other_name': 'Paul',
                'role': 'teacher',
                'gender': 'male',
                'age': 40,
                'phone_number': '08035556699',
                'address': '890 Professor Street, PH',
                'qualification': 'Ph.D. Physics',
                'years_of_experience': 12,
                'next_of_kin': 'Susan Davis',
                'next_of_kin_phone': '08036667799'
            }
        ]

        teachers = []
        for teacher_data in teachers_data:
            user, created = User.objects.get_or_create(
                email=teacher_data['email'],
                defaults={
                    'surname': teacher_data['surname'],
                    'first_name': teacher_data['first_name'],
                    'other_name': teacher_data['other_name'],
                    'role': teacher_data['role'],
                    'gender': teacher_data['gender'],
                    'age': teacher_data['age'],
                    'phone_number': teacher_data['phone_number'],
                    'address': teacher_data['address'],
                    'qualification': teacher_data['qualification'],
                    'years_of_experience': teacher_data['years_of_experience'],
                    'next_of_kin': teacher_data['next_of_kin'],
                    'next_of_kin_phone': teacher_data['next_of_kin_phone']
                }
            )
            if created:
                user.set_password('teacher123')  # Default password
                user.approved = True
                user.save()
                teachers.append(user)
                self.stdout.write(f'Created teacher: {user.get_full_name()}')

        return teachers

    def create_admins(self):
        admin_data = [
            {
                'email': 'admin@brillspay.edu',
                'surname': 'Admin',
                'first_name': 'System',
                'role': 'admin',
                'gender': 'male',
                'age': 30,
                'phone_number': '08030000001',
                'address': 'School Administrative Block'
            },
            {
                'email': 'superadmin@brillspay.edu',
                'surname': 'Super',
                'first_name': 'Admin',
                'role': 'superadmin',
                'gender': 'female',
                'age': 35,
                'phone_number': '08030000002',
                'address': 'School Administrative Block'
            }
        ]

        for admin in admin_data:
            user, created = User.objects.get_or_create(
                email=admin['email'],
                defaults=admin
            )
            if created:
                user.set_password('admin123')  # Default password
                user.approved = True
                user.save()
                self.stdout.write(f'Created admin: {user.get_full_name()}')