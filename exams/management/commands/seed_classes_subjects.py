from django.core.management.base import BaseCommand
from exams.models import Class, Subject, ClassSubject

class Command(BaseCommand):
    help = 'Seed Nigerian educational classes and subjects from Kindergarten to SSS3'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Nigerian classes and subjects...')
        
        # Create classes
        classes = self.create_classes()
        
        # Create subjects
        subjects = self.create_subjects()
        
        # Assign subjects to classes
        self.assign_subjects_to_classes(classes, subjects)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded classes and subjects!')
        )

    def create_classes(self):
        classes_data = [
            # Kindergarten
            {'name': 'Kindergarten 1', 'level': 'kindergarten', 'order': 1, 'description': 'Early childhood education for 3-4 year olds'},
            {'name': 'Kindergarten 2', 'level': 'kindergarten', 'order': 2, 'description': 'Early childhood education for 4-5 year olds'},
            
            # Nursery
            {'name': 'Nursery 1', 'level': 'nursery', 'order': 3, 'description': 'Pre-primary education'},
            {'name': 'Nursery 2', 'level': 'nursery', 'order': 4, 'description': 'Pre-primary education'},
            
            # Primary School
            {'name': 'Primary 1', 'level': 'primary', 'order': 5, 'description': 'Elementary education year 1'},
            {'name': 'Primary 2', 'level': 'primary', 'order': 6, 'description': 'Elementary education year 2'},
            {'name': 'Primary 3', 'level': 'primary', 'order': 7, 'description': 'Elementary education year 3'},
            {'name': 'Primary 4', 'level': 'primary', 'order': 8, 'description': 'Elementary education year 4'},
            {'name': 'Primary 5', 'level': 'primary', 'order': 9, 'description': 'Elementary education year 5'},
            {'name': 'Primary 6', 'level': 'primary', 'order': 10, 'description': 'Elementary education year 6'},
            
            # Junior Secondary School (JSS)
            {'name': 'JSS 1', 'level': 'junior_secondary', 'order': 11, 'description': 'Junior Secondary School year 1'},
            {'name': 'JSS 2', 'level': 'junior_secondary', 'order': 12, 'description': 'Junior Secondary School year 2'},
            {'name': 'JSS 3', 'level': 'junior_secondary', 'order': 13, 'description': 'Junior Secondary School year 3'},
            
            # Senior Secondary School (SSS) - Science
            {'name': 'SSS 1', 'level': 'senior_secondary', 'arm': 'Science', 'order': 14, 'description': 'Senior Secondary School Science year 1'},
            {'name': 'SSS 2', 'level': 'senior_secondary', 'arm': 'Science', 'order': 15, 'description': 'Senior Secondary School Science year 2'},
            {'name': 'SSS 3', 'level': 'senior_secondary', 'arm': 'Science', 'order': 16, 'description': 'Senior Secondary School Science year 3'},
            
            # Senior Secondary School (SSS) - Arts
            {'name': 'SSS 1', 'level': 'senior_secondary', 'arm': 'Arts', 'order': 17, 'description': 'Senior Secondary School Arts year 1'},
            {'name': 'SSS 2', 'level': 'senior_secondary', 'arm': 'Arts', 'order': 18, 'description': 'Senior Secondary School Arts year 2'},
            {'name': 'SSS 3', 'level': 'senior_secondary', 'arm': 'Arts', 'order': 19, 'description': 'Senior Secondary School Arts year 3'},
            
            # Senior Secondary School (SSS) - Commercial
            {'name': 'SSS 1', 'level': 'senior_secondary', 'arm': 'Commercial', 'order': 20, 'description': 'Senior Secondary School Commercial year 1'},
            {'name': 'SSS 2', 'level': 'senior_secondary', 'arm': 'Commercial', 'order': 21, 'description': 'Senior Secondary School Commercial year 2'},
            {'name': 'SSS 3', 'level': 'senior_secondary', 'arm': 'Commercial', 'order': 22, 'description': 'Senior Secondary School Commercial year 3'},
        ]

        classes_dict = {}
        for class_data in classes_data:
            # Create unique name for classes with arms
            if class_data.get('arm'):
                unique_name = f"{class_data['name']} {class_data['arm']}"
            else:
                unique_name = class_data['name']
                
            class_obj, created = Class.objects.get_or_create(
                name=unique_name,
                defaults=class_data
            )
            if created:
                classes_dict[unique_name] = class_obj
                self.stdout.write(f'Created class: {unique_name}')

        return classes_dict

    def create_subjects(self):
        subjects_data = [
            # Core Subjects (All levels)
            {'name': 'English Language', 'code': 'ENG', 'category': 'core', 'description': 'English language and literature'},
            {'name': 'Mathematics', 'code': 'MATH', 'category': 'core', 'description': 'Mathematics and quantitative reasoning'},
            
            # Kindergarten & Nursery Subjects
            {'name': 'Number Work', 'code': 'NUM', 'category': 'core', 'description': 'Basic numeracy skills'},
            {'name': 'Letter Work', 'code': 'LET', 'category': 'core', 'description': 'Basic literacy and phonics'},
            {'name': 'Social Habits', 'code': 'SOC', 'category': 'core', 'description': 'Social skills and awareness'},
            {'name': 'Health Habits', 'code': 'HLT', 'category': 'core', 'description': 'Health and hygiene education'},
            {'name': 'Creative Arts', 'code': 'ART', 'category': 'core', 'description': 'Art and creative expression'},
            {'name': 'Physical Education', 'code': 'PE', 'category': 'core', 'description': 'Physical activities and games'},
            
            # Primary School Subjects
            {'name': 'Basic Science', 'code': 'BSC', 'category': 'core', 'description': 'Elementary science education'},
            {'name': 'Basic Technology', 'code': 'BST', 'category': 'core', 'description': 'Technology and computer basics'},
            {'name': 'Social Studies', 'code': 'SOS', 'category': 'core', 'description': 'Social sciences and citizenship'},
            {'name': 'Civic Education', 'code': 'CIV', 'category': 'core', 'description': 'Civics and government'},
            {'name': 'Christian Religious Studies', 'code': 'CRS', 'category': 'core', 'description': 'Christian religious education'},
            {'name': 'Islamic Religious Studies', 'code': 'IRS', 'category': 'core', 'description': 'Islamic religious education'},
            {'name': 'Home Economics', 'code': 'HEC', 'category': 'core', 'description': 'Home management and skills'},
            {'name': 'Agricultural Science', 'code': 'AGR', 'category': 'core', 'description': 'Agriculture and farming'},
            {'name': 'French', 'code': 'FRE', 'category': 'core', 'description': 'French language'},
            {'name': 'Yoruba', 'code': 'YOR', 'category': 'core', 'description': 'Yoruba language and culture'},
            {'name': 'Igbo', 'code': 'IGB', 'category': 'core', 'description': 'Igbo language and culture'},
            {'name': 'Hausa', 'code': 'HAU', 'category': 'core', 'description': 'Hausa language and culture'},
            
            # Junior Secondary Core Subjects
            {'name': 'Integrated Science', 'code': 'INTSCI', 'category': 'core', 'description': 'Integrated science curriculum'},
            {'name': 'Business Studies', 'code': 'BUS', 'category': 'core', 'description': 'Business and commerce basics'},
            {'name': 'Computer Studies', 'code': 'COMP', 'category': 'core', 'description': 'Computer science and IT'},
            
            # Senior Secondary Science Subjects
            {'name': 'Physics', 'code': 'PHY', 'category': 'core', 'description': 'Physics and physical sciences'},
            {'name': 'Chemistry', 'code': 'CHEM', 'category': 'core', 'description': 'Chemistry and chemical sciences'},
            {'name': 'Biology', 'code': 'BIO', 'category': 'core', 'description': 'Biology and life sciences'},
            {'name': 'Further Mathematics', 'code': 'FURMATH', 'category': 'elective', 'description': 'Advanced mathematics'},
            
            # Senior Secondary Arts Subjects
            {'name': 'Literature in English', 'code': 'LIT', 'category': 'core', 'description': 'English literature studies'},
            {'name': 'Government', 'code': 'GOV', 'category': 'core', 'description': 'Government and political science'},
            {'name': 'History', 'code': 'HIS', 'category': 'elective', 'description': 'Historical studies'},
            {'name': 'Geography', 'code': 'GEO', 'category': 'elective', 'description': 'Geography and environmental studies'},
            {'name': 'Economics', 'code': 'ECO', 'category': 'elective', 'description': 'Economics and economic theory'},
            
            # Senior Secondary Commercial Subjects
            {'name': 'Accounting', 'code': 'ACC', 'category': 'core', 'description': 'Accounting and bookkeeping'},
            {'name': 'Commerce', 'code': 'COM', 'category': 'core', 'description': 'Commerce and trade'},
            {'name': 'Office Practice', 'code': 'OFF', 'category': 'elective', 'description': 'Office administration and practice'},
            
            # Vocational Subjects
            {'name': 'Food and Nutrition', 'code': 'FNT', 'category': 'vocational', 'description': 'Food preparation and nutrition'},
            {'name': 'Technical Drawing', 'code': 'TDR', 'category': 'vocational', 'description': 'Technical and engineering drawing'},
            {'name': 'Music', 'code': 'MUS', 'category': 'vocational', 'description': 'Music theory and practice'},
            {'name': 'Fine Arts', 'code': 'FART', 'category': 'vocational', 'description': 'Fine arts and drawing'},
        ]

        subjects_dict = {}
        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                code=subject_data['code'],
                defaults=subject_data
            )
            if created:
                subjects_dict[subject_data['code']] = subject
                self.stdout.write(f'Created subject: {subject.name} ({subject.code})')

        return subjects_dict

    def assign_subjects_to_classes(self, classes, subjects):
        # Kindergarten subjects
        kindergarten_subjects = ['NUM', 'LET', 'SOC', 'HLT', 'ART', 'PE']
        for class_name in ['Kindergarten 1', 'Kindergarten 2']:
            self.assign_subjects_to_class(classes[class_name], kindergarten_subjects, subjects)

        # Nursery subjects (add English and Math basics)
        nursery_subjects = ['NUM', 'LET', 'SOC', 'HLT', 'ART', 'PE', 'ENG', 'MATH']
        for class_name in ['Nursery 1', 'Nursery 2']:
            self.assign_subjects_to_class(classes[class_name], nursery_subjects, subjects)

        # Primary 1-3 subjects
        primary_lower_subjects = ['ENG', 'MATH', 'NUM', 'LET', 'BSC', 'SOS', 'ART', 'PE', 'CRS', 'IRS']
        for i in range(1, 4):
            class_name = f'Primary {i}'
            self.assign_subjects_to_class(classes[class_name], primary_lower_subjects, subjects)

        # Primary 4-6 subjects (more advanced)
        primary_upper_subjects = ['ENG', 'MATH', 'BSC', 'BST', 'SOS', 'CIV', 'ART', 'PE', 'CRS', 'IRS', 'HEC', 'AGR', 'FRE']
        for i in range(4, 7):
            class_name = f'Primary {i}'
            self.assign_subjects_to_class(classes[class_name], primary_upper_subjects, subjects)

        # Junior Secondary (JSS) subjects
        jss_subjects = ['ENG', 'MATH', 'INTSCI', 'SOS', 'BUS', 'COMP', 'CRS', 'IRS', 'FRE', 'YOR', 'IGB', 'HAU', 'AGR', 'HEC', 'ART', 'PE']
        for i in range(1, 4):
            class_name = f'JSS {i}'
            self.assign_subjects_to_class(classes[class_name], jss_subjects, subjects)

        # Senior Secondary Science
        science_subjects = ['ENG', 'MATH', 'PHY', 'CHEM', 'BIO', 'GOV', 'CRS', 'IRS', 'FRE', 'YOR', 'IGB', 'HAU', 'AGR', 'COMP', 'PE']
        science_electives = ['FURMATH', 'GEO', 'ECO', 'TDR']
        
        for i in range(1, 4):
            class_name = f'SSS {i} Science'
            self.assign_subjects_to_class(classes[class_name], science_subjects, subjects, is_compulsory=True)
            self.assign_subjects_to_class(classes[class_name], science_electives, subjects, is_compulsory=False)

        # Senior Secondary Arts
        arts_subjects = ['ENG', 'MATH', 'LIT', 'GOV', 'HIS', 'CRS', 'IRS', 'FRE', 'YOR', 'IGB', 'HAU', 'COMP', 'PE']
        arts_electives = ['GEO', 'ECO', 'MUS', 'FART']
        
        for i in range(1, 4):
            class_name = f'SSS {i} Arts'
            self.assign_subjects_to_class(classes[class_name], arts_subjects, subjects, is_compulsory=True)
            self.assign_subjects_to_class(classes[class_name], arts_electives, subjects, is_compulsory=False)

        # Senior Secondary Commercial
        commercial_subjects = ['ENG', 'MATH', 'ACC', 'COM', 'ECO', 'GOV', 'CRS', 'IRS', 'FRE', 'YOR', 'IGB', 'HAU', 'COMP', 'PE']
        commercial_electives = ['OFF', 'BUS', 'GEO']
        
        for i in range(1, 4):
            class_name = f'SSS {i} Commercial'
            self.assign_subjects_to_class(classes[class_name], commercial_subjects, subjects, is_compulsory=True)
            self.assign_subjects_to_class(classes[class_name], commercial_electives, subjects, is_compulsory=False)

    def assign_subjects_to_class(self, class_obj, subject_codes, subjects, is_compulsory=True):
        for subject_code in subject_codes:
            if subject_code in subjects:
                class_subject, created = ClassSubject.objects.get_or_create(
                    class_obj=class_obj,
                    subject=subjects[subject_code],
                    defaults={
                        'is_compulsory': is_compulsory,
                        'periods_per_week': 5 if is_compulsory else 3
                    }
                )
                if created:
                    self.stdout.write(f'  Assigned {subjects[subject_code].name} to {class_obj.name}')