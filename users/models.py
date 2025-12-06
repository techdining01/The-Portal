############### VERSION 2 ###################################

import secrets
from django.utils.crypto import get_random_string
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
import uuid
import random
import string
from decimal import Decimal
from django.db import models
from django.utils import timezone
from PIL import Image


# ==================== CUSTOM USER MANAGER ====================

class UserManager(BaseUserManager):
    """Custom user manager for handling user creation"""
    
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)


# ==================== USER MODEL ====================

class User(AbstractUser):
    """Custom User model for BrillsPay system"""
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent/Guardian'),
        ('teacher', 'Teacher'),
        ('staff', 'Staff'),
        ('admin', 'Administrator'),
        ('superadmin', 'Super Administrator'),
    ]
    
    # Remove default fields we don't need
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(_('phone number'), max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_approved = models.BooleanField(default=False)

    # Profile fields
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    address = models.TextField(_('address'), blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Nigeria')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # School-related fields
    student = models.OneToOneField(
        'Student', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='user_account'
    )
    parent = models.OneToOneField(
        'Parent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account'
    )
    teacher = models.OneToOneField(
        'Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account'
    )
    staff = models.OneToOneField(
        'Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account'
    )
    
    # Additional fields
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True)
    date_verified = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def get_full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_parent(self):
        return self.role == 'parent'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_staff_member(self):
        return self.role == 'staff'
    
    @property
    def is_administrator(self):
        return self.role in ['admin', 'superadmin']
    
    def save(self, *args, **kwargs):
        # Ensure email is lowercase
        self.email = self.email.lower()

        #Resize profile picture
        if self.profile_picture and hasattr(self.profile_picture, 'path'):
            try:
                img = Image.open(self.profile_picture.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.profile_picture.path, optimize=True, quality=85)
            except (FileNotFoundError, ValueError):
                pass
    
        super().save(*args, **kwargs)


# ==================== STUDENT MODEL ====================

class Student(models.Model):
    """Student model for school students"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    # Student identification
    admission_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Admission Number'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Academic information
    student_class = models.ForeignKey('exams.Class', on_delete=models.CASCADE, related_name='student_class')
    section = models.CharField(max_length=50, blank=True)  # e.g., "A", "B"
    roll_number = models.IntegerField(null=True, blank=True)
    academic_year = models.CharField(max_length=20, default='2025/2026')
    enrollment_date = models.DateField(auto_now_add=True)
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated Student Registration Number"
    )

    # Parent/Guardian relationship
    parents = models.ManyToManyField(
        'Parent',
        related_name='children',
        blank=True
    )
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    
    # Financial information (for BrillsPay)
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    outstanding_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['student_class', 'roll_number', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.admission_number}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_age(self):
        """Calculate student's age"""
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age
    
    @staticmethod
    def generate_unique_reg_no():
        """
        Generates a unique registration number in format:
        TBS/2025/AB93K  (crypto-safe, collision-free)
        """
        year = timezone.now().year
        random_part = get_random_string(length=5).upper()
        return f"TBS/{year}/{random_part}"
    
    @classmethod
    def create_unique_reg_no(cls):
        """
        Ensures the generated number is always unique.
        """
        reg_no = cls.generate_unique_reg_no()
        while cls.objects.filter(registration_number=reg_no).exists():
            reg_no = cls.generate_unique_reg_no()
        return reg_no

    def save(self, *args, **kwargs):
        # Generate unique registration number for students only
        if self.role == "student" and not self.registration_number:
            self.registration_number =User.create_unique_reg_no()
            
        # Set username to email if not set
        if not self.username and self.email:
            self.username = self.email

        super().save(*args, **kwargs)
    
    @property
    def class_level(self):
        """Extract class level from current_class (e.g., 'JSS 1' from 'JSS 1A')"""
        parts = self.student_class.split()
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return self.student_class
    
    def update_spending(self):
        """Update total spent based on completed orders"""
        from django.db.models import Sum
        # import Order locally to avoid circular imports at module import time
        from store.models import Order
        total = Order.objects.filter(
            student=self,
            payment_status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        self.total_spent = total
        self.save(update_fields=['total_spent'])

    def get_unpaid_fees(self):
        """Get all unpaid fee structures for this student"""
        from django.db.models import Sum
        # import fee models locally to avoid circular imports
        from store.models import FeeStructure, FeePayment

        unpaid_fees = []
        fee_structures = FeeStructure.objects.filter(
            class_level=self.class_level,
            is_active=True
        )
        for fee in fee_structures:
            paid_amount = FeePayment.objects.filter(
                student=self,
                fee_structure=fee
            ).aggregate(total=Sum('amount_paid'))['total'] or 0

            if paid_amount < fee.amount:
                unpaid_fees.append({
                    'fee': fee,
                    'paid': paid_amount,
                    'balance': fee.amount - paid_amount
                })

        return unpaid_fees

# ==================== PARENT/GUARDIAN MODEL ====================

class Parent(models.Model):
    """Parent/Guardian model"""
    
    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    ]
    
    INCOME_RANGE_CHOICES = [
        ('low', 'Low Income'),
        ('middle', 'Middle Income'),
        ('high', 'High Income'),
    ]
    
    # Link to User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    
    # Personal information
    phone = models.CharField(max_length=15, unique=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=100, blank=True)
    income_range = models.CharField(
        max_length=20,
        choices=INCOME_RANGE_CHOICES,
        blank=True
    )
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        default='guardian'
    )
    
    # Students (already linked via Student model's parents field)
    students = models.ManyToManyField(
        Student,
        through='StudentParent',
        related_name='parent_guardians'
    )
    
    # Address (can be different from User address)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Nigeria')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Financial preferences
    preferred_payment_method = models.CharField(
        max_length=50,
        default='paystack',
        choices=[
            ('paystack', 'Paystack'),
            ('bank_transfer', 'Bank Transfer'),
            ('cash', 'Cash'),
            ('card', 'Debit/Credit Card'),
        ]
    )
    
    # Status
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Parent/Guardian'
        verbose_name_plural = 'Parents/Guardians'
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_relationship_display()})"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def email(self):
        return self.user.email
    
    def get_student_names(self):
        """Get comma-separated list of student names"""
        return ", ".join([str(student) for student in self.students.all()])
    
    def total_spent(self):

        """Calculate total spent across all linked students"""

        from django.db.models import Sum
        from store.models import Order
        total = Order.objects.filter(
            user=self.user, payment_status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        return total

    def last_purchase(self):
        """Get last purchase date"""
        from store.models import Order
        last_order = Order.objects.filter(user=self.user).order_by('-created_at').first()
        return last_order.created_at if last_order else None


class StudentParent(models.Model):
    """Through model for Student-Parent relationship with additional info"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    is_primary_guardian = models.BooleanField(default=False)
    can_pickup = models.BooleanField(default=True)
    pickup_code = models.CharField(max_length=10, blank=True)
    
    class Meta:
        unique_together = ['student', 'parent']
        verbose_name = 'Student-Parent Relationship'
        verbose_name_plural = 'Student-Parent Relationships'
    
    def __str__(self):
        return f"{self.parent} - {self.student}"
    
    def generate_pickup_code(self):
        """Generate a unique pickup code"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.pickup_code = code
        self.save()
        return code


# ==================== TEACHER MODEL ====================

class Teacher(models.Model):
    """Teacher model"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    staff_id = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=100)
    class_teacher_of = models.CharField(max_length=50, blank=True)  # e.g., "JSS 1A"
    qualification = models.CharField(max_length=200, blank=True)
    years_of_experience = models.IntegerField(default=0)
    joining_date = models.DateField(default=timezone.now)
    
    # Contact information
    phone = models.CharField(max_length=15)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.subject}"


# ==================== STAFF MODEL ====================

class Staff(models.Model):
    """Non-teaching staff model"""
    
    DEPARTMENT_CHOICES = [
        ('administration', 'Administration'),
        ('accounts', 'Accounts'),
        ('library', 'Library'),
        ('laboratory', 'Laboratory'),
        ('maintenance', 'Maintenance'),
        ('security', 'Security'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    staff_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    position = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200, blank=True)
    joining_date = models.DateField(default=timezone.now)
    
    # Contact information
    phone = models.CharField(max_length=15)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'
        ordering = ['department', 'user__last_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"




# class UserProfile(models.Model):
#     ROLE_CHOICES = [
#         ('student', 'Student'),
#         ('parent', 'Parent'),
#         ('teacher', 'Teacher'),
#         ('admin', 'Administrator'),
#         ('superadmin', 'SuperAdministrator'),
#     ]

#     GENDER = (
#         ('female', 'Female'),
#         ('male', 'Male')
#     )
    
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
#     # Personal info
#     surname = models.CharField(max_length=50)
#     other_name = models.CharField(max_length=50, blank=True, null=True)
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
#     phone_number = models.CharField(max_length=20, blank=True, null=True)
#     last_login_ip = models.GenericIPAddressField(null=True, blank=True)
#     is_approved = models.BooleanField(default=False)
#     profile_picture = models.ImageField(
#         upload_to='profile_pictures/',
#         blank=True,
#         null=True,
#         default='profile_pictures/default.png'
#     )
    
#     # Student specific fields
#     registration_number = models.CharField(
#         max_length=20,
#         unique=True,
#         blank=True,
#         null=True,
#         help_text="Auto-generated Student Registration Number"
#     )
#     date_joined_profile = models.DateTimeField(auto_now=True)
#     gender = models.CharField(max_length=10, choices=GENDER, null=True, blank=True)
#     age = models.PositiveIntegerField(default=8)
#     date_of_birth = models.CharField(max_length=20, blank=True, null=True)
    
#     # STUDENT CLASS FIELD - INCLUDED
#     student_class = models.ForeignKey(
#         Class, 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True, 
#         related_name="students"
#     )
    
#     parent_email = models.EmailField(blank=True, null=True)
#     department = models.TextField(blank=True, null=True)
#     qualifications = models.CharField(max_length=60, null=True, blank=True)
#     enrollment_date = models.DateTimeField(auto_now_add=True)

#     # Parent specific fields
#     occupation = models.CharField(max_length=100, blank=True, null=True)
#     emergency_contact = models.CharField(max_length=20, blank=True, null=True)
#     address = models.TextField(blank=True, null=True)
    
#     # Teacher specific fields
#     subject_assigned = models.CharField(max_length=100, blank=True, null=True)
#     qualification = models.CharField(max_length=200, blank=True, null=True)
#     years_of_experience = models.PositiveIntegerField(blank=True, null=True)
#     next_of_kin = models.CharField(max_length=150, blank=True, null=True)
#     next_of_kin_phone = models.CharField(max_length=15, blank=True, null=True)
#     hire_date = models.DateTimeField(auto_now_add=True)

#     # Exam Access Control
#     can_take_exam = models.BooleanField(default=False)
    
#     # Common fields
#     bio = models.TextField(blank=True)
#     suspended = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     @staticmethod
#     def generate_unique_reg_no():
#         """
#         Generates a unique registration number in format:
#         TBS/2025/AB93K  (crypto-safe, collision-free)
#         """
#         year = timezone.now().year
#         random_part = get_random_string(length=5).upper()
#         return f"TBS/{year}/{random_part}"
    
    

#     @classmethod
#     def create_unique_reg_no(cls):
#         """
#         Ensures the generated number is always unique.
#         """
#         reg_no = cls.generate_unique_reg_no()
#         while cls.objects.filter(registration_number=reg_no).exists():
#             reg_no = cls.generate_unique_reg_no()
#         return reg_no

#     def save(self, *args, **kwargs):
#         # Generate unique registration number for students only
#         if self.role == "student" and not self.registration_number:
#             self.registration_number =User.create_unique_reg_no()
            
#         # Set username to email if not set
#         if not self.username and self.email:
#             self.username = self.email

#         super().save(*args, **kwargs)

      
#         # Resize profile picture
#         if self.profile_picture and hasattr(self.profile_picture, 'path'):
#             try:
#                 img = Image.open(self.profile_picture.path)
#                 if img.height > 300 or img.width > 300:
#                     output_size = (300, 300)
#                     img.thumbnail(output_size)
#                     img.save(self.profile_picture.path, optimize=True, quality=85)
#             except (FileNotFoundError, ValueError):
#                 pass

#     def is_teacher(self):
#         return self.role == "teacher"

#     def is_student(self):
#         return self.role == "student"
    
#     def is_parent(self):
#         return self.role == "parent"

#     def can_approve(self):
#         return self.role in ["superadmin", "admin"]

#     def get_full_name(self):
#         name_parts = [
#             self.user.first_name or '',
#             self.surname or '',
#             self.other_name or ''
#         ]
#         return ' '.join(filter(None, name_parts)).strip() or self.user.username
    
#     @property
#     def is_active(self):
#         return self.user.is_active
    
#     def __str__(self):
#         return f"{self.get_full_name()} - {self.get_role_display()}"

       
class Notification(models.Model):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    sender = models.ForeignKey(
       User, on_delete=models.CASCADE, related_name="Userprofile_sent_notifications"
    )
    recipient = models.ForeignKey(
       User, on_delete=models.CASCADE, related_name="received_notifications"
    )
    message = models.TextField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_broadcast = models.BooleanField(default=False)  # optional flag
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
 
    def get_target_display(self):
        return f"To {self.recipient} from {self.sender}: {self.message[:30]}"

    def __str__(self):
        return f"To {self.recipient} from {self.sender}: {self.message[:30]}"


class UserStatusLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="status_changes")
    changed_at = models.DateTimeField(default=timezone.now)


