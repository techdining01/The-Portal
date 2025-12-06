from django.core.management.base import BaseCommand
from exams.models import Class, Subject

class Command(BaseCommand):
    help = 'Seed Nigerian classes and subjects'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Nigerian classes and subjects...')
        
        try:
            # Clear existing data first to avoid conflicts
            self.clear_existing_data()
            
            classes = self.create_classes()
            self.create_subjects(classes)
            
            self.stdout.write(
                self.style.SUCCESS('Successfully seeded classes and subjects!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error in seed_classes_subjects: {e}')
            )
        finally:
            self.stdout.write('All seed data completed!')

    def clear_existing_data(self):
        """Clear existing data to avoid unique constraint errors"""
        self.stdout.write('Clearing existing data...')
        Subject.objects.all().delete()
        Class.objects.all().delete()

    def create_classes(self):
        """Create Nigerian school classes with level and order fields"""
        classes_data = [
            # Kindergarten - order 1-2
            {'name': 'Kindergarten 1', 'grade_level': 'kindergarten', 'order': 1},
            {'name': 'Kindergarten 2', 'grade_level': 'kindergarten', 'order': 2},
            
            # Nursery - order 3-5
            {'name': 'Nursery 1', 'grade_level': 'nursery', 'order': 3},
            {'name': 'Nursery 2', 'grade_level': 'nursery', 'order': 4},
            {'name': 'Nursery 3', 'grade_level': 'nursery', 'order': 5},
            
            # Primary - order 6-11
            {'name': 'Primary 1', 'grade_level': 'primary', 'order': 6},
            {'name': 'Primary 2', 'grade_level': 'primary', 'order': 7},
            {'name': 'Primary 3', 'grade_level': 'primary', 'order': 8},
            {'name': 'Primary 4', 'grade_level': 'primary', 'order': 9},
            {'name': 'Primary 5', 'grade_level': 'primary', 'order': 10},
            {'name': 'Primary 6', 'grade_level': 'primary', 'order': 11},
            
            # Junior Secondary - order 12-14
            {'name': 'JSS 1', 'grade_level': 'junior_secondary', 'order': 12},
            {'name': 'JSS 2', 'grade_level': 'junior_secondary', 'order': 13},
            {'name': 'JSS 3', 'grade_level': 'junior_secondary', 'order': 14},
            
            # Senior Secondary - order 15-17
            {'name': 'SSS 1', 'grade_level': 'senior_secondary', 'order': 15},
            {'name': 'SSS 2', 'grade_level': 'senior_secondary', 'order': 16},
            {'name': 'SSS 3', 'grade_level': 'senior_secondary', 'order': 17},
        ]
        
        classes = []
        for class_data in classes_data:
            class_obj = Class.objects.create(**class_data)
            classes.append(class_obj)
            self.stdout.write(f'Created class: {class_obj.name} ({class_obj.grade_level}) - Order: {class_obj.order}')
        
        return classes

    def create_subjects(self, classes):
        """Create subjects for each class level"""
        subjects_data = {
            # Kindergarten Subjects
            'Kindergarten 1': [
                'Number Work', 'Letter Work', 'Social Habits',
                'Health Habits', 'Science', 'Creative Arts',
                'Physical Development', 'Music', 'Rhymes'
            ],
            'Kindergarten 2': [
                'Number Work', 'Letter Work', 'Social Habits',
                'Health Habits', 'Science', 'Creative Arts',
                'Physical Development', 'Music', 'Rhymes'
            ],
            
            # Nursery Subjects
            'Nursery 1': [
                'Number Work', 'Letter Work', 'Social Habits',
                'Health Habits', 'Science', 'Creative Arts',
                'Physical Development', 'Music', 'Rhymes',
                'Colouring', 'Story Time'
            ],
            'Nursery 2': [
                'Number Work', 'Letter Work', 'Social Habits',
                'Health Habits', 'Science', 'Creative Arts',
                'Physical Development', 'Music', 'Rhymes',
                'Colouring', 'Story Time'
            ],
            'Nursery 3': [
                'Number Work', 'Letter Work', 'Social Habits',
                'Health Habits', 'Science', 'Creative Arts',
                'Physical Development', 'Music', 'Rhymes',
                'Colouring', 'Story Time', 'Pre-Writing'
            ],
            
            # Primary School Subjects
            'Primary 1': [
                'English Studies', 'Mathematics', 'Basic Science', 
                'Social Studies', 'Verbal Reasoning', 'Quantitative Reasoning', 
                'Christian Religious Studies', 'Yoruba', 'French', 
                'Computer Studies', 'Creative Arts', 'Physical Education'
            ],
            'Primary 2': [
                'English Studies', 'Mathematics', 'Basic Science', 
                'Social Studies', 'Verbal Reasoning', 'Quantitative Reasoning', 
                'Christian Religious Studies', 'Yoruba', 'French', 
                'Computer Studies', 'Creative Arts', 'Physical Education'
            ],
            'Primary 3': [
                'English Studies', 'Mathematics', 'Basic Science', 
                'Social Studies', 'Verbal Reasoning', 'Quantitative Reasoning', 
                'Christian Religious Studies', 'Yoruba', 'French', 
                'Computer Studies', 'Creative Arts', 'Physical Education'
            ],
            'Primary 4': [
                'English Studies', 'Mathematics', 'Basic Science', 
                'Social Studies', 'Verbal Reasoning', 'Quantitative Reasoning', 
                'Christian Religious Studies', 'Yoruba', 'French', 
                'Computer Studies', 'Creative Arts', 'Physical Education'
            ],
            'Primary 5': [
                'English Studies', 'Mathematics', 'Basic Science', 
                'Social Studies', 'Verbal Reasoning', 'Quantitative Reasoning', 
                'Christian Religious Studies', 'Yoruba', 'French', 
                'Computer Studies', 'Creative Arts', 'Physical Education'
            ],
            'Primary 6': [
                'English Studies', 'Mathematics', 'Basic Science', 
                'Social Studies', 'Verbal Reasoning', 'Quantitative Reasoning', 
                'Christian Religious Studies', 'Yoruba', 'French', 
                'Computer Studies', 'Creative Arts', 'Physical Education'
            ],
            
            # Junior Secondary Subjects
            'JSS 1': [
                'English Language', 'Mathematics', 'Basic Science', 
                'Basic Technology', 'Business Studies', 'Social Studies', 
                'French', 'Christian Religious Studies', 'Yoruba', 
                'Computer Studies', 'Creative Arts', 'Physical Education',
                'Agricultural Science', 'Home Economics'
            ],
            'JSS 2': [
                'English Language', 'Mathematics', 'Basic Science', 
                'Basic Technology', 'Business Studies', 'Social Studies', 
                'French', 'Christian Religious Studies', 'Yoruba', 
                'Computer Studies', 'Creative Arts', 'Physical Education',
                'Agricultural Science', 'Home Economics'
            ],
            'JSS 3': [
                'English Language', 'Mathematics', 'Basic Science', 
                'Basic Technology', 'Business Studies', 'Social Studies', 
                'French', 'Christian Religious Studies', 'Yoruba', 
                'Computer Studies', 'Creative Arts', 'Physical Education',
                'Agricultural Science', 'Home Economics'
            ],
            
            # Senior Secondary Subjects
            'SSS 1': [
                'English Language', 'Mathematics', 'Biology', 'Physics', 'Chemistry',
                'Economics', 'Geography', 'Government', 'Literature in English',
                'Financial Accounting', 'Commerce', 'French', 'Yoruba',
                'Christian Religious Studies', 'Agricultural Science', 
                'Further Mathematics', 'Physical Education'
            ],
            'SSS 2': [
                'English Language', 'Mathematics', 'Biology', 'Physics', 'Chemistry',
                'Economics', 'Geography', 'Government', 'Literature in English',
                'Financial Accounting', 'Commerce', 'French', 'Yoruba',
                'Christian Religious Studies', 'Agricultural Science', 
                'Further Mathematics', 'Physical Education'
            ],
            'SSS 3': [
                'English Language', 'Mathematics', 'Biology', 'Physics', 'Chemistry',
                'Economics', 'Geography', 'Government', 'Literature in English',
                'Financial Accounting', 'Commerce', 'French', 'Yoruba',
                'Christian Religious Studies', 'Agricultural Science', 
                'Further Mathematics', 'Physical Education'
            ],
        }
        defauult = {'core': 'Core Subject'}
        subject_count = 0
        for class_obj in classes:
            class_name = class_obj.name
            if class_name in subjects_data:
                for subject_name in subjects_data[class_name]:
                    subject = Subject.objects.create(
                        name=subject_name,
                        school_class=class_obj,
                        category=defauult['core']
                        )
                    subject_count += 1
                    self.stdout.write(f'Created subject: {subject_name} for {class_name}')
        
        self.stdout.write(f'Created {subject_count} subjects across all classes')