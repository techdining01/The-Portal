# forms.py
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, 
    UserChangeForm, 
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    PasswordChangeForm
)
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import re
from .models import (
    UserProfile, StudentParentRelationship, 
    Class, Subject, Department
)
from django.utils import timezone
from datetime import date

# ============================================================================
# REGISTRATION FORMS
# ============================================================================

class UserRegistrationForm(UserCreationForm):
    """Base registration form with common fields"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        }),
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Please enter a valid email address.'
        }
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number (optional)',
            'autocomplete': 'tel'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'
            )
        ]
    )
    
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'You must accept the terms and conditions.'}
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'autocomplete': 'username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
        
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
        
        # Add help text
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = [
            'Your password must contain at least 8 characters.',
            'Your password can\'t be too similar to your other personal information.',
            'Your password can\'t be a commonly used password.',
            'Your password can\'t be entirely numeric.',
        ]
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email address already exists.'))
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError(_('This username is already taken. Please choose another.'))
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure email and username are not the same
        email = cleaned_data.get('email', '')
        username = cleaned_data.get('username', '')
        
        if email and username and email.lower() == username.lower():
            self.add_error('username', 'Username cannot be the same as email address.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
        
        return user

class StudentRegistrationForm(UserRegistrationForm):
    """Student registration form with additional fields"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]
    
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Select your class'
        }),
        empty_label="Select Class"
    )
    
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'max': timezone.now().date().isoformat()
        }),
        help_text="Format: YYYY-MM-DD"
    )
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    parent_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parent/Guardian email (optional)'
        }),
        help_text="If parent already has an account, enter their email to link"
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Home address (optional)'
        })
    )
    
    emergency_contact = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact number'
        })
    )
    
    medical_info = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any medical conditions or allergies (optional)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set role-specific validation
        self.fields['date_of_birth'].widget.attrs['max'] = timezone.now().date().isoformat()
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + [
            'student_class', 'date_of_birth', 'gender', 'parent_email',
            'address', 'emergency_contact', 'medical_info'
        ]
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = timezone.now().date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 4:
                raise ValidationError('Student must be at least 4 years old.')
            elif age > 25:
                raise ValidationError('Student age seems incorrect. Please verify.')
        
        return dob
    
    def clean_parent_email(self):
        email = self.cleaned_data.get('parent_email')
        if email:
            # Check if parent exists and has parent role
            try:
                parent = User.objects.get(email=email)
                if not hasattr(parent, 'userprofile') or parent.userprofile.role != 'parent':
                    raise ValidationError(
                        'The email provided belongs to a user who is not registered as a parent.'
                    )
            except User.DoesNotExist:
                # Parent doesn't exist yet - we'll create invitation later
                pass
        
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role='student',
                phone_number=self.cleaned_data.get('phone_number', ''),
                gender=self.cleaned_data['gender'],
                date_of_birth=self.cleaned_data['date_of_birth'],
                student_class=self.cleaned_data['student_class'],
                address=self.cleaned_data.get('address', ''),
                emergency_contact=self.cleaned_data.get('emergency_contact', ''),
            )
            
            # Handle parent linking
            parent_email = self.cleaned_data.get('parent_email')
            if parent_email:
                try:
                    parent_user = User.objects.get(email=parent_email)
                    StudentParentRelationship.objects.create(
                        student=user,
                        parent=parent_user,
                        relationship='parent',
                        is_primary=True,
                        verified=False  # Needs admin verification
                    )
                except User.DoesNotExist:
                    # Create invitation or log for admin follow-up
                    pass
            
            # Add to Student group
            student_group, created = Group.objects.get_or_create(name='Students')
            user.groups.add(student_group)
        
        return user

class ParentRegistrationForm(UserRegistrationForm):
    """Parent registration form"""
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
    ]
    
    occupation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Occupation (optional)'
        })
    )
    
    marital_status = forms.ChoiceField(
        choices=MARITAL_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Residential address'
        })
    )
    
    emergency_contact_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact person'
        })
    )
    
    emergency_contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact phone'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Please enter a valid phone number.'
            )
        ]
    )
    
    student_registration_numbers = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student registration numbers (comma separated)'
        }),
        help_text="Enter registration numbers of your children separated by commas"
    )
    
    receive_sms = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Receive SMS notifications"
    )
    
    receive_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Receive email notifications"
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + [
            'occupation', 'marital_status', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'student_registration_numbers', 'receive_sms', 'receive_email'
        ]
    
    def clean_student_registration_numbers(self):
        data = self.cleaned_data.get('student_registration_numbers', '')
        if not data:
            return []
        
        reg_numbers = [rn.strip() for rn in data.split(',') if rn.strip()]
        students = []
        
        for reg_num in reg_numbers:
            try:
                profile = UserProfile.objects.get(
                    registration_number=reg_num,
                    role='student'
                )
                students.append(profile.user)
            except UserProfile.DoesNotExist:
                raise ValidationError(
                    _('Student with registration number "%(reg_num)s" not found.'),
                    params={'reg_num': reg_num},
                    code='student_not_found'
                )
        
        return students
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role='parent',
                phone_number=self.cleaned_data.get('phone_number', ''),
                occupation=self.cleaned_data.get('occupation', ''),
                address=self.cleaned_data['address'],
                emergency_contact=self.cleaned_data.get('emergency_contact_phone', ''),
            )
            
            # Link students if provided
            students = self.cleaned_data.get('student_registration_numbers', [])
            for student in students:
                StudentParentRelationship.objects.get_or_create(
                    student=student,
                    parent=user,
                    defaults={
                        'relationship': 'parent',
                        'is_primary': True,
                        'verified': False  # Needs verification
                    }
                )
            
            # Add to Parents group
            parent_group, created = Group.objects.get_or_create(name='Parents')
            user.groups.add(parent_group)
        
        return user

class TeacherRegistrationForm(UserRegistrationForm):
    """Teacher registration form"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]
    
    QUALIFICATION_CHOICES = [
        ('bachelors', "Bachelor's Degree"),
        ('masters', "Master's Degree"),
        ('phd', 'PhD'),
        ('diploma', 'Diploma'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'max': timezone.now().date().isoformat()
        })
    )
    
    qualification = forms.ChoiceField(
        choices=QUALIFICATION_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    qualification_details = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., B.Sc. Computer Science'
        })
    )
    
    subject_specialization = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'height: 150px;'
        }),
        help_text="Hold Ctrl/Cmd to select multiple subjects"
    )
    
    years_of_experience = forms.IntegerField(
        min_value=0,
        max_value=50,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Years of teaching experience'
        })
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Department"
    )
    
    address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Residential address'
        })
    )
    
    emergency_contact = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact number'
        })
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + [
            'gender', 'date_of_birth', 'qualification', 'qualification_details',
            'subject_specialization', 'years_of_experience', 'department',
            'address', 'emergency_contact'
        ]
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = timezone.now().date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 21:
                raise ValidationError('Teacher must be at least 21 years old.')
        
        return dob
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role='teacher',
                phone_number=self.cleaned_data.get('phone_number', ''),
                gender=self.cleaned_data['gender'],
                date_of_birth=self.cleaned_data['date_of_birth'],
                qualification=self.cleaned_data['qualification'],
                years_of_experience=self.cleaned_data['years_of_experience'],
                address=self.cleaned_data['address'],
                emergency_contact=self.cleaned_data['emergency_contact'],
            )
            
            # Save subject specialization (many-to-many)
            if self.cleaned_data.get('subject_specialization'):
                profile.subject_specialization.set(self.cleaned_data['subject_specialization'])
            
            # Add to Teachers group
            teacher_group, created = Group.objects.get_or_create(name='Teachers')
            user.groups.add(teacher_group)
        
        return user

class AdminRegistrationForm(UserRegistrationForm):
    """Administrator registration form (superusers only)"""
    
    ADMIN_ROLE_CHOICES = [
        ('admin', 'School Administrator'),
        ('superadmin', 'System Administrator'),
    ]
    
    role = forms.ChoiceField(
        choices=ADMIN_ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_staff = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    is_superuser = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Grants full access to all features"
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number'
        })
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Assigned department (optional)"
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + [
            'role', 'is_staff', 'is_superuser', 'phone_number', 'department'
        ]
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set admin permissions
        user.is_staff = self.cleaned_data.get('is_staff', True)
        user.is_superuser = self.cleaned_data.get('is_superuser', False)
        
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                phone_number=self.cleaned_data['phone_number'],
            )
            
            # Add to appropriate admin group
            if self.cleaned_data['role'] == 'admin':
                group_name = 'Administrators'
            else:
                group_name = 'Super Administrators'
            
            admin_group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(admin_group)
        
        return user

# ============================================================================
# AUTHENTICATION FORMS
# ============================================================================

class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with enhanced styling"""
    
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autocomplete': 'username',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Remember me"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make error messages more user-friendly
        self.error_messages.update({
            'invalid_login': _(
                "Please enter a correct username/email and password. "
                "Note that both fields may be case-sensitive."
            ),
            'inactive': _("This account is inactive."),
        })
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Allow login with either username or email
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                username = user.username
            except User.DoesNotExist:
                pass
        
        return username

class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form"""
    
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        
        # Check if email exists in system
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise ValidationError(
                _("There is no user registered with the specified email address."),
                code='unknown_email'
            )
        
        return email

class CustomSetPasswordForm(SetPasswordForm):
    """Custom set password form"""
    
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        })
    )
    
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )

class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form"""
    
    old_password = forms.CharField(
        label=_("Old password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
            'autocomplete': 'current-password'
        })
    )
    
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        })
    )
    
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )

# ============================================================================
# PROFILE FORMS
# ============================================================================

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'profile_picture', 'gender', 'date_of_birth',
            'address', 'emergency_contact'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Address'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Pre-fill user fields
            self.fields['email'].initial = self.user.email
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
        
        # Make profile picture field optional
        self.fields['profile_picture'].required = False
        self.fields['profile_picture'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if self.user and User.objects.exclude(pk=self.user.pk).filter(email=email).exists():
            raise ValidationError(_('This email address is already in use.'))
        return email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user fields
        if self.user:
            self.user.email = self.cleaned_data['email']
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            
            if commit:
                self.user.save()
        
        if commit:
            profile.save()
        
        return profile

class StudentProfileForm(UserProfileForm):
    """Student-specific profile form"""
    
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    medical_info = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Medical information'
        })
    )
    
    class Meta(UserProfileForm.Meta):
        fields = UserProfileForm.Meta.fields + ['student_class', 'medical_info']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add student-specific fields
        if self.instance and self.instance.role == 'student':
            self.fields['medical_info'].initial = getattr(self.instance, 'medical_info', '')

class ParentProfileForm(UserProfileForm):
    """Parent-specific profile form"""
    
    occupation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Occupation'
        })
    )
    
    marital_status = forms.ChoiceField(
        choices=ParentRegistrationForm.MARITAL_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    receive_sms = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    receive_email = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta(UserProfileForm.Meta):
        fields = UserProfileForm.Meta.fields + [
            'occupation', 'marital_status', 'receive_sms', 'receive_email'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add parent-specific fields
        if self.instance and self.instance.role == 'parent':
            self.fields['occupation'].initial = getattr(self.instance, 'occupation', '')
            self.fields['marital_status'].initial = getattr(self.instance, 'marital_status', '')
            self.fields['receive_sms'].initial = getattr(self.instance, 'receive_sms', True)
            self.fields['receive_email'].initial = getattr(self.instance, 'receive_email', True)

class TeacherProfileForm(UserProfileForm):
    """Teacher-specific profile form"""
    
    qualification = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Qualifications'
        })
    )
    
    years_of_experience = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    subject_specialization = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'height: 150px;'
        })
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta(UserProfileForm.Meta):
        fields = UserProfileForm.Meta.fields + [
            'qualification', 'years_of_experience', 
            'subject_specialization', 'department'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add teacher-specific fields
        if self.instance and self.instance.role == 'teacher':
            self.fields['qualification'].initial = getattr(self.instance, 'qualification', '')
            self.fields['years_of_experience'].initial = getattr(self.instance, 'years_of_experience', 0)
            
            if hasattr(self.instance, 'subject_specialization'):
                self.fields['subject_specialization'].initial = self.instance.subject_specialization.all()
            
            self.fields['department'].initial = getattr(self.instance, 'department', None)

# ============================================================================
# ADMIN MANAGEMENT FORMS
# ============================================================================

class AdminUserEditForm(UserChangeForm):
    """Admin form for editing users"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Active"
    )
    
    is_staff = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Staff status"
    )
    
    is_superuser = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Superuser status",
        help_text="Designates that this user has all permissions without explicitly assigning them."
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'height: 200px;'
        }),
        help_text="Hold Ctrl/Cmd to select multiple groups"
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'groups'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field
        self.fields.pop('password', None)
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

class AdminUserCreateForm(UserCreationForm):
    """Admin form for creating users"""
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
    ]
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    phone_number = forms.CharField(max_length=20, required=False)
    is_active = forms.BooleanField(initial=True, required=False)
    is_staff = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)
    
    # Student specific
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Parent specific
    occupation = forms.CharField(max_length=100, required=False)
    
    # Teacher specific
    qualification = forms.CharField(max_length=200, required=False)
    
    send_welcome_email = forms.BooleanField(
        required=False,
        initial=True,
        label="Send welcome email with login details"
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2', 'role', 'phone_number',
            'is_active', 'is_staff', 'is_superuser'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = self.cleaned_data.get('is_active', True)
        user.is_staff = self.cleaned_data.get('is_staff', False)
        user.is_superuser = self.cleaned_data.get('is_superuser', False)
        
        if commit:
            user.save()
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                phone_number=self.cleaned_data.get('phone_number', ''),
            )
            
            # Set role-specific fields
            role = self.cleaned_data['role']
            if role == 'student':
                profile.student_class = self.cleaned_data.get('student_class')
            elif role == 'parent':
                profile.occupation = self.cleaned_data.get('occupation', '')
            elif role == 'teacher':
                profile.qualification = self.cleaned_data.get('qualification', '')
            
            profile.save()
            
            # Add to appropriate group
            group_map = {
                'student': 'Students',
                'parent': 'Parents',
                'teacher': 'Teachers',
                'admin': 'Administrators',
            }
            
            if role in group_map:
                group, created = Group.objects.get_or_create(name=group_map[role])
                user.groups.add(group)
        
        return user

class BulkUserImportForm(forms.Form):
    """Form for bulk importing users from CSV"""
    
    IMPORT_TYPE_CHOICES = [
        ('csv', 'CSV File'),
        ('excel', 'Excel File'),
    ]
    
    import_type = forms.ChoiceField(
        choices=IMPORT_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        }),
        help_text="Upload CSV or Excel file with user data"
    )
    
    default_role = forms.ChoiceField(
        choices=AdminUserCreateForm.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Default role if not specified in file"
    )
    
    send_welcome_emails = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Send welcome emails to new users"
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Update existing users (matching by email)",
        help_text="If checked, existing users will be updated instead of skipping"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            valid_extensions = ['.csv', '.xlsx', '.xls']
            ext = file.name.lower().rsplit('.', 1)[-1]
            
            if f'.{ext}' not in valid_extensions:
                raise ValidationError(
                    _('Unsupported file format. Please upload CSV or Excel file.')
                )
            
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise ValidationError(_('File size must be less than 10MB.'))
        
        return file

class UserSearchFilterForm(forms.Form):
    """Form for searching and filtering users"""
    
    ROLE_CHOICES = [
        ('', 'All Roles'),
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
        ('superadmin', 'Super Administrator'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, username...'
        })
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Class"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            self.add_error('date_to', 'End date must be after start date.')
        
        return cleaned_data

class StudentParentLinkForm(forms.ModelForm):
    """Form for linking students to parents"""
    
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='student'),
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Select student'
        })
    )
    
    parent = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='parent'),
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Select parent'
        })
    )
    
    relationship = forms.ChoiceField(
        choices=StudentParentRelationship._meta.get_field('relationship').choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_primary = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Mark as primary parent/guardian"
    )
    
    verified = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Mark relationship as verified"
    )
    
    class Meta:
        model = StudentParentRelationship
        fields = ['student', 'parent', 'relationship', 'is_primary', 'verified']
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        parent = cleaned_data.get('parent')
        
        if student and parent:
            # Check if relationship already exists
            existing = StudentParentRelationship.objects.filter(
                student=student,
                parent=parent
            ).exists()
            
            if existing and not self.instance.pk:
                raise ValidationError(_('This relationship already exists.'))
            
            # If marking as primary, ensure only one primary per student
            if cleaned_data.get('is_primary'):
                StudentParentRelationship.objects.filter(
                    student=student,
                    is_primary=True
                ).exclude(pk=self.instance.pk if self.instance else None).update(is_primary=False)
        
        return cleaned_data

class BulkUserActionForm(forms.Form):
    """Form for bulk user actions"""
    
    ACTION_CHOICES = [
        ('activate', 'Activate Selected Users'),
        ('deactivate', 'Deactivate Selected Users'),
        ('delete', 'Delete Selected Users'),
        ('assign_group', 'Assign to Group'),
        ('remove_group', 'Remove from Group'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    user_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean_user_ids(self):
        data = self.cleaned_data.get('user_ids', '')
        if data:
            try:
                user_ids = [int(id.strip()) for id in data.split(',') if id.strip()]
                return user_ids
            except ValueError:
                raise ValidationError(_('Invalid user IDs format.'))
        return []
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        group = cleaned_data.get('group')
        
        if action in ['assign_group', 'remove_group'] and not group:
            self.add_error('group', 'Please select a group for this action.')
        
        return cleaned_data

# ============================================================================
# QUICK ACTION FORMS
# ============================================================================

class QuickUserEditForm(forms.ModelForm):
    """Quick edit form for user details"""
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Add phone number from profile
        if self.instance and hasattr(self.instance, 'userprofile'):
            self.fields['phone_number'].initial = self.instance.userprofile.phone_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Update phone number in profile
        if hasattr(user, 'userprofile'):
            user.userprofile.phone_number = self.cleaned_data.get('phone_number', '')
            if commit:
                user.userprofile.save()
        
        if commit:
            user.save()
        
        return user

class QuickPasswordResetForm(forms.Form):
    """Quick password reset form"""
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Send email notification to user"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("Passwords don't match"))
        
        # Password validation
        if password1:
            if len(password1) < 8:
                raise ValidationError(_("Password must be at least 8 characters long"))
            
            if password1.isdigit():
                raise ValidationError(_("Password cannot be entirely numeric"))
        
        return cleaned_data

# ============================================================================
# WIDGETS AND MIXINS
# ============================================================================

class BootstrapFormMixin:
    """Mixin to add Bootstrap classes to form fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form-control class to all fields except checkboxes and radios
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-select'
            else:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

class DateInputWidget(forms.DateInput):
    """Custom date input widget"""
    
    input_type = 'date'
    
    def __init__(self, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({
            'class': 'form-control'
        })
        super().__init__(**kwargs)

class Select2Widget(forms.Select):
    """Select2 widget for better select fields"""
    
    def __init__(self, attrs=None, choices=()):
        if attrs is None:
            attrs = {}
        attrs.update({
            'class': 'form-select select2',
            'data-placeholder': 'Select an option'
        })
        super().__init__(attrs, choices)

class ImagePreviewWidget(forms.ClearableFileInput):
    """Widget for image preview"""
    
    template_name = 'widgets/image_preview_widget.html'
    
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({'class': 'form-control'})
        super().__init__(attrs)

# ============================================================================
# FORM FACTORY
# ============================================================================

class FormFactory:
    """Factory to create appropriate forms based on user role"""
    
    @staticmethod
    def get_registration_form(role):
        """Get registration form based on role"""
        forms = {
            'student': StudentRegistrationForm,
            'parent': ParentRegistrationForm,
            'teacher': TeacherRegistrationForm,
            'admin': AdminRegistrationForm,
        }
        return forms.get(role, UserRegistrationForm)
    
    @staticmethod
    def get_profile_form(role):
        """Get profile form based on role"""
        forms = {
            'student': StudentProfileForm,
            'parent': ParentProfileForm,
            'teacher': TeacherProfileForm,
        }
        return forms.get(role, UserProfileForm)
    
    @staticmethod
    def get_edit_form(role):
        """Get edit form based on role (admin use)"""
        forms = {
            'student': AdminUserEditForm,
            'parent': AdminUserEditForm,
            'teacher': AdminUserEditForm,
            'admin': AdminUserEditForm,
        }
        return forms.get(role, AdminUserEditForm)

# ============================================================================
# CUSTOM VALIDATORS
# ============================================================================

def validate_phone_number(value):
    """Validate phone number"""
    pattern = r'^\+?1?\d{9,15}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Enter a valid phone number in the format: +999999999. Up to 15 digits allowed.')
        )

def validate_age_for_student(value):
    """Validate student age"""
    today = timezone.now().date()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    
    if age < 4:
        raise ValidationError(_('Student must be at least 4 years old.'))
    elif age > 25:
        raise ValidationError(_('Student age seems incorrect. Please verify.'))

def validate_age_for_teacher(value):
    """Validate teacher age"""
    today = timezone.now().date()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    
    if age < 21:
        raise ValidationError(_('Teacher must be at least 21 years old.'))