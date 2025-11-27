from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from PIL import Image
from exams.models import Class, Subject




class User(AbstractUser):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]

    GENDER = (
        ('female', 'Female'),
        ('male', 'Male')
    )
    
    # Personal Information
    surname = models.CharField(max_length=150, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    other_name = models.CharField(max_length=150, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    date_joined = models.DateTimeField(auto_now=True)
    gender = models.CharField(max_length=10, choices=GENDER, null=True, blank=True)
    age = models.PositiveIntegerField(default=8)
    date_of_birth = models.CharField(max_length=20, blank=True, null=True)
    student_class = models.ForeignKey(
        Class, on_delete=models.CASCADE, null=True, blank=True, to_field="name", related_name="student_class"
    )

    # Contact Information
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Parent/Guardian Information (for students)
    parent_name = models.CharField(max_length=150, blank=True, null=True)
    parent_email = models.EmailField(blank=True, null=True)
    parent_phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Parent relationship (for parent users)
    children = models.ManyToManyField('self', symmetrical=False, blank=True, 
                                     limit_choices_to={'role': 'student'})
    
    # Approval system
    approved = models.BooleanField(default=False)

    # Profile picture
    profile_picture = models.ImageField(
        upload_to="profiles/",
        default="profiles/default_profile.png",
        null=True,
        blank=True
    )

    # Teachers/Admin specific fields
    qualification = models.CharField(max_length=200, blank=True, null=True)
    subject_assigned = models.ForeignKey(
        Subject, on_delete=models.CASCADE, null=True, blank=True
    )
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    next_of_kin = models.CharField(max_length=150, blank=True, null=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True, null=True)

    # Exam Access Control
    can_take_exam = models.BooleanField(default=False)

    # Registration number
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated Student Registration Number"
    )

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
            self.registration_number = User.create_unique_reg_no()
            
        # Set username to email if not set
        if not self.username and self.email:
            self.username = self.email

        super().save(*args, **kwargs)

        # Resize profile picture AFTER saving
        if self.profile_picture and hasattr(self.profile_picture, 'path'):
            try:
                img = Image.open(self.profile_picture.path)
                if img.height > 200 or img.width > 200:
                    output_size = (200, 200)
                    img.thumbnail(output_size)
                    img.save(self.profile_picture.path, optimize=True, quality=85)
            except (FileNotFoundError, ValueError):
                # Handle case where file doesn't exist yet
                pass

    def is_teacher(self):
        return self.role == "teacher"

    def is_student(self):
        return self.role == "student"
    
    def is_parent(self):
        return self.role == "parent"

    def can_approve(self):
        return self.role in ["superadmin", "admin"]

    def get_full_name(self):
        name_parts = [self.first_name or '', self.surname or '', self.other_name or '']
        return ' '.join(filter(None, name_parts)).strip() or self.username

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"


class Parent(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='parent_profile')
    address = models.TextField()
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    occupation = models.CharField(max_length=150, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def number_of_wards(self):
        return self.user.children.count()
    
    def __str__(self):
        return f"Parent of {self.user.first_name} {self.user.surname}"

# class User(AbstractUser):
#     ROLE_CHOICES = [
#         ('superadmin', 'Super Admin'),
#         ('admin', 'Admin'),
#         ('teacher', 'Teacher'),
#         ('student', 'Student'),
#     ]
#     GENDER = (
#         ('female', 'Female'),
#         ('male', 'Male')
#         )
  

#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)
#     other_name = models.CharField(max_length=100, blank=True, null=True)
#     date_joined = models.DateTimeField(auto_now=True)
#     gender = models.CharField(max_length=10, choices=GENDER, null=True, blank=True)
#     age = models.PositiveIntegerField(default=8)
#     date_of_birth = models.CharField(max_length=20, blank=True, null=True)
#     student_class = models.ForeignKey(Class, on_delete=models.CASCADE, null=True, to_field='name', related_name='student_class')
#     address = models.TextField(blank=True, null=True)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     approved = models.BooleanField(default=False)  # SuperAdmin must approve Admins
#     can_take_exam = models.BooleanField(default=False)  # permission to take exams
#     parent_email = models.EmailField(blank=True, null=True)
#     profile_picture = models.ImageField(upload_to='profiles/', default='profiles/default_profile.png', null=True, blank=True)
#        # NEW FIELDS for teachers/admins
#     qualification = models.CharField(max_length=200, blank=True, null=True)
#     subject_assigned = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
#     years_of_experience = models.PositiveIntegerField(blank=True, null=True)
#     next_of_kin = models.CharField(max_length=150, blank=True, null=True)
#     next_of_kin_phone = models.CharField(max_length=15, blank=True, null=True)
#     registration_number = models.CharField(max_length=50, unique=True, blank=True, null=True)

    
#     def can_approve(self):
#         """Only SuperAdmins and Admins can approve users"""
#         return self.role in ['superadmin', 'admin']
    
#     def generate_registration_number():
#         year = timezone.now().year

#         # Count existing users for that year
#         count = User.objects.filter(registration_number__startswith=f"TBS/{year}/").count() + 1

#         return f"TBS/{year}/{count:04d}" 

    
#     def __str__(self):
       
#         return f"{self.username} ({self.role}) {self.user.get_full_name()} ({self.registration_number})"


#     def save(self, *args, **kwargs):
#             # Generate registration number if missing
#         if not self.registration_number:
#             self.registration_number = self.generate_registration_number()

#         super().save(*args, **kwargs)

#         if self.profile_picture:
#             try:
#                 img = Image.open(self.profile_picture.path)
#                 # Resize logic
#                 max_size = (50, 50) 
#                 img.thumbnail(max_size)

#                 # Optimize and save
#                 img.save(self.profile_picture.path, optimize=True, quality=85)
#             except Exception:
#                 pass

       
class Notification(models.Model):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_sent_notifications"
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="status_changes")
    changed_at = models.DateTimeField(default=timezone.now)
