from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Parent
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, Class, Subject, Parent
import os


class loginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))

    widget = {
        'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
    }

    
class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'age', 'address', 'date_of_birth',
                  'role', 'gender', 'student_class', 'phone_number', 'profile_picture', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'student_class': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }


class EditUserRegistrationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'age', 'address', 'date_of_birth',
                  'parent_name','role', 'gender', 'student_class', 'profile_picture', 'password']        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', "place_holder": "first_name"}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'student_class': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }


class TeacherAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['subject_assigned', 'qualification', 
                  'next_of_kin', 'next_of_kin_phone', 'years_of_experience']
        exclude = ['password']
        widgets = {
            'subject_assigned': forms.Select(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
 
    def clean_experience_years(self):
        experience_years = self.cleaned_data.get('experience_years')
        if experience_years is not None and experience_years < 0:
            raise forms.ValidationError("Experience years cannot be negative.")
        return experience_years
    

class EditTeacherAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [ 'username', 'first_name', 'last_name', 'email', 'age', 'address', 'date_of_birth',
                  'role', 'gender', 'student_class', 'profile_picture', 'subject_assigned', 'qualification', 
                  'next_of_kin', 'next_of_kin_phone', 'years_of_experience', 'password']

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'student_class': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'subject_assigned': forms.Select(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'password':forms.TextInput(attrs={'class': 'form-control'}),
        }
 
    def clean_experience_years(self):
        experience_years = self.cleaned_data.get('experience_years')
        if experience_years is not None and experience_years < 0:
            raise forms.ValidationError("Experience years cannot be negative.")
        return experience_years
    
class ParentForm(forms.ModelForm):

    model = User
    # For linking existing students
    student_registration_numbers = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter student registration numbers separated by commas'
        }),
        help_text="Optional: Link to existing students by their registration numbers"
    )
    class Meta:
        model = Parent
        fields = ['address', 'signature', 
                  'occupation', 'emergency_contact', 'student_registration_numbers']
       
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'signature': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ParentRegistrationForm(UserRegistrationForm):
    occupation = forms.CharField(max_length=150, required=False)
    emergency_contact = forms.CharField(max_length=15, required=False)
    gender = forms.ChoiceField(choices=User.GENDER, required=True)
    
    # For linking existing students
    student_registration_numbers = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter student registration numbers separated by commas'
        }),
        help_text="Optional: Link to existing students by their registration numbers"
    )
    
    def clean_student_registration_numbers(self):
        data = self.cleaned_data.get('student_registration_numbers', '')
        if data:
            reg_numbers = [rn.strip() for rn in data.split(',') if rn.strip()]
            # Verify all students exist
            students = User.objects.filter(
                registration_number__in=reg_numbers,
                role='student'
            )
            found_numbers = set(students.values_list('registration_number', flat=True))
            not_found = set(reg_numbers) - found_numbers
            if not_found:
                raise ValidationError(
                    f"Students not found with registration numbers: {', '.join(not_found)}"
                )
        return data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'parent'
        
        if commit:
            user.save()
            
            # Link students if provided
            reg_numbers = self.cleaned_data.get('student_registration_numbers', '')
            if reg_numbers:
                reg_list = [rn.strip() for rn in reg_numbers.split(',') if rn.strip()]
                students = User.objects.filter(
                    registration_number__in=reg_list,
                    role='student'
                )
                user.children.add(*students)
            
            # Create Parent profile
            Parent.objects.get_or_create(
                user=user,
                defaults={
                    'occupation': self.cleaned_data.get('occupation', ''),
                    'emergency_contact': self.cleaned_data.get('emergency_contact', ''),
                    'address': self.cleaned_data.get('address', '')
                }
            )
        
        return user

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email address'
    }))
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your first name'
    }))
    surname = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your surname'
    }))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'surname', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.surname = self.cleaned_data['surname']
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'surname', 'other_name', 'phone_number', 'address', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'other_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class LinkStudentForm(forms.Form):
    registration_number = forms.CharField(
        max_length=20,
        required=True,
        help_text="Enter the student's registration number"
    )
    relationship = forms.ChoiceField(
        choices=[
            ('parent', 'Parent'),
            ('guardian', 'Guardian'),
            ('sibling', 'Sibling'),
            ('other', 'Other')
        ],
        initial='parent'
    )
    verification_code = forms.CharField(
        max_length=10,
        required=False,
        help_text="Optional: If provided by school administration"
    )
    
    def clean_registration_number(self):
        reg_number = self.cleaned_data.get('registration_number')
        try:
            student = User.objects.get(
                registration_number=reg_number,
                role='student'
            )
            return reg_number
        except User.DoesNotExist:
            raise ValidationError("No student found with this registration number.")
        




####################### VERSION 2 ###########################################



from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, StudentParentRelationship, Class

class UserRegistrationForm(UserCreationForm):
    """Form for user registration with role selection"""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
    ]
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'role-select'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError(_('This username is already taken.'))
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            # Create UserProfile
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                phone_number=self.cleaned_data.get('phone_number', '')
            )
            
            # Assign to appropriate group based on role
            group_name = self.cleaned_data['role'].capitalize() + 's'
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        
        return user

class StudentRegistrationForm(UserRegistrationForm):
    """Form for student registration with additional fields"""
    
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Select class'
        })
    )
    
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        })
    )
    
    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    parent_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parent email (optional)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = 'student'
        self.fields['role'].widget = forms.HiddenInput()  # Hide role field as it's always student
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + ['student_class', 'date_of_birth', 'gender', 'parent_email']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user_profile = UserProfile.objects.get(user=user)
        
        # Update student-specific fields
        user_profile.student_class = self.cleaned_data['student_class']
        user_profile.date_of_birth = self.cleaned_data['date_of_birth']
        user_profile.gender = self.cleaned_data['gender']
        
        if commit:
            user.save()
            user_profile.save()
            
            # Link parent if email provided
            parent_email = self.cleaned_data.get('parent_email')
            if parent_email:
                try:
                    parent_user = User.objects.get(email=parent_email)
                    StudentParentRelationship.objects.create(
                        student=user,
                        parent=parent_user,
                        relationship='parent',
                        is_primary=True
                    )
                except User.DoesNotExist:
                    # Parent doesn't exist yet, could create invitation
                    pass
        
        return user

class ParentRegistrationForm(UserRegistrationForm):
    """Form for parent registration"""
    
    occupation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Occupation (optional)'
        })
    )
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Address (optional)'
        }),
        required=False
    )
    
    student_registration_numbers = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student reg. numbers (comma separated)'
        }),
        help_text="Enter student registration numbers separated by commas"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = 'parent'
        self.fields['role'].widget = forms.HiddenInput()
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + ['occupation', 'address']
    
    def clean_student_registration_numbers(self):
        data = self.cleaned_data.get('student_registration_numbers', '')
        if data:
            reg_numbers = [rn.strip() for rn in data.split(',') if rn.strip()]
            
            # Check if all students exist
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
                        _('Student with registration number %(reg_num)s not found.'),
                        params={'reg_num': reg_num},
                        code='student_not_found'
                    )
            return students
        return []
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user_profile = UserProfile.objects.get(user=user)
        
        # Update parent-specific fields
        user_profile.occupation = self.cleaned_data.get('occupation', '')
        user_profile.address = self.cleaned_data.get('address', '')
        
        if commit:
            user.save()
            user_profile.save()
            
            # Link students if provided
            students = self.cleaned_data.get('student_registration_numbers', [])
            for student_user in students:
                StudentParentRelationship.objects.get_or_create(
                    student=student_user,
                    parent=user,
                    defaults={'relationship': 'parent', 'is_primary': True}
                )
        
        return user

class TeacherRegistrationForm(UserRegistrationForm):
    """Form for teacher registration"""
    
    subject = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject taught'
        })
    )
    
    qualification = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Qualifications (optional)'
        })
    )
    
    years_of_experience = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Years of experience'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = 'teacher'
        self.fields['role'].widget = forms.HiddenInput()
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + ['subject', 'qualification', 'years_of_experience']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user_profile = UserProfile.objects.get(user=user)
        
        # Update teacher-specific fields
        user_profile.subject = self.cleaned_data['subject']
        user_profile.qualification = self.cleaned_data.get('qualification', '')
        user_profile.years_of_experience = self.cleaned_data.get('years_of_experience', 0)
        
        if commit:
            user.save()
            user_profile.save()
        
        return user

class AdminRegistrationForm(UserRegistrationForm):
    """Form for admin registration (only accessible by superusers)"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('superadmin', 'Super Administrator'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
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
        help_text="Give superuser privileges (full access)"
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + ['role', 'is_staff', 'is_superuser']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set admin permissions
        user.is_staff = self.cleaned_data.get('is_staff', True)
        user.is_superuser = self.cleaned_data.get('is_superuser', False)
        
        if commit:
            user.save()
            
            # Create UserProfile with admin role
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role']
            )
            
            # Add to appropriate group
            group_name = 'Administrators' if self.cleaned_data['role'] == 'admin' else 'Super Administrators'
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        
        return user

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'profile_picture', 'role',
            'grade_level', 'registration_number', 
            'occupation', 'emergency_contact', 'address',
            'subject', 'qualification', 'years_of_experience'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'grade_level': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make profile picture field more user-friendly
        self.fields['profile_picture'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })

class UserEditForm(UserChangeForm):
    """Form for editing user information (admin only)"""
    
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
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'height: 150px;'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'groups']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field from form
        self.fields.pop('password', None)
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

class StudentEditForm(UserEditForm):
    """Form for editing student information"""
    
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    parent = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='parent'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add student-specific fields
        if self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields['student_class'].initial = profile.student_class
                self.fields['date_of_birth'].initial = profile.date_of_birth
                self.fields['gender'].initial = profile.gender
                
                # Get current parent
                relationship = StudentParentRelationship.objects.filter(
                    student=self.instance,
                    is_primary=True
                ).first()
                if relationship:
                    self.fields['parent'].initial = relationship.parent
            except UserProfile.DoesNotExist:
                pass
    
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields + ['student_class', 'date_of_birth', 'gender', 'parent']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Update or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'student'
            profile.student_class = self.cleaned_data['student_class']
            profile.date_of_birth = self.cleaned_data['date_of_birth']
            profile.gender = self.cleaned_data['gender']
            profile.save()
            
            # Update parent relationship
            parent = self.cleaned_data.get('parent')
            if parent:
                # Remove existing primary relationship
                StudentParentRelationship.objects.filter(
                    student=user,
                    is_primary=True
                ).update(is_primary=False)
                
                # Create or update new relationship
                relationship, created = StudentParentRelationship.objects.get_or_create(
                    student=user,
                    parent=parent,
                    defaults={'relationship': 'parent', 'is_primary': True}
                )
                if not created:
                    relationship.is_primary = True
                    relationship.save()
        
        return user

class ParentEditForm(UserEditForm):
    """Form for editing parent information"""
    
    occupation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    
    emergency_contact = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    children = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(userprofile__role='student'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'style': 'height: 150px;'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add parent-specific fields
        if self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields['occupation'].initial = profile.occupation
                self.fields['address'].initial = profile.address
                self.fields['emergency_contact'].initial = profile.emergency_contact
                
                # Get current children
                children = User.objects.filter(
                    student_relationships__parent=self.instance
                )
                self.fields['children'].initial = children
            except UserProfile.DoesNotExist:
                pass
    
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields + ['occupation', 'address', 'emergency_contact', 'children']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Update or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'parent'
            profile.occupation = self.cleaned_data.get('occupation', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.emergency_contact = self.cleaned_data.get('emergency_contact', '')
            profile.save()
            
            # Update children relationships
            children = self.cleaned_data.get('children', [])
            
            # Remove existing relationships for children not in new list
            StudentParentRelationship.objects.filter(
                parent=user
            ).exclude(student__in=children).delete()
            
            # Add new relationships
            for child in children:
                StudentParentRelationship.objects.get_or_create(
                    student=child,
                    parent=user,
                    defaults={'relationship': 'parent', 'is_primary': True}
                )
        
        return user

class TeacherEditForm(UserEditForm):
    """Form for editing teacher information"""
    
    subject = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    qualification = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    years_of_experience = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add teacher-specific fields
        if self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields['subject'].initial = profile.subject
                self.fields['qualification'].initial = profile.qualification
                self.fields['years_of_experience'].initial = profile.years_of_experience
            except UserProfile.DoesNotExist:
                pass
    
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields + ['subject', 'qualification', 'years_of_experience']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Update or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'teacher'
            profile.subject = self.cleaned_data['subject']
            profile.qualification = self.cleaned_data.get('qualification', '')
            profile.years_of_experience = self.cleaned_data.get('years_of_experience', 0)
            profile.save()
        
        return user

class AdminEditForm(UserEditForm):
    """Form for editing admin information"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('superadmin', 'Super Administrator'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add admin-specific fields
        if self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields['role'].initial = profile.role
            except UserProfile.DoesNotExist:
                pass
    
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields + ['role']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Update or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.save()
            
            # Update groups
            group_name = 'Administrators' if self.cleaned_data['role'] == 'admin' else 'Super Administrators'
            user.groups.clear()
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        
        return user

class UserSearchForm(forms.Form):
    """Form for searching/filtering users"""
    
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
            'type': 'date',
            'placeholder': 'From date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'To date'
        })
    )
    
    class_ = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Class"
    )

class PasswordResetForm(forms.Form):
    """Form for resetting user password (admin)"""
    
    password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    send_email = forms.BooleanField(
        label="Send password reset email to user",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("Passwords don't match"))
        
        return cleaned_data

class UserImportForm(forms.Form):
    """Form for importing users from CSV/Excel"""
    
    IMPORT_TYPE_CHOICES = [
        ('csv', 'CSV File'),
        ('excel', 'Excel File'),
    ]
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
    ]
    
    import_type = forms.ChoiceField(
        choices=IMPORT_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    default_role = forms.ChoiceField(
        choices=ROLE_CHOICES,
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
        label="Update existing users (by email)"
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            valid_extensions = ['.csv', '.xlsx', '.xls']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(_('Unsupported file format. Please upload CSV or Excel file.'))
            
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise ValidationError(_('File size must be less than 10MB.'))
        
        return file

class StudentParentLinkForm(forms.ModelForm):
    """Form for linking students to parents"""
    
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='student'),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    parent = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='parent'),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    relationship = forms.ChoiceField(
        choices=StudentParentRelationship.RELATIONSHIP_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_primary = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Mark as primary parent/guardian"
    )
    
    class Meta:
        model = StudentParentRelationship
        fields = ['student', 'parent', 'relationship', 'is_primary']
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        parent = cleaned_data.get('parent')
        
        if student and parent:
            # Check if relationship already exists
            if StudentParentRelationship.objects.filter(
                student=student,
                parent=parent
            ).exists():
                raise ValidationError(_('This relationship already exists.'))
            
            # If marking as primary, unset primary for other relationships
            if cleaned_data.get('is_primary'):
                StudentParentRelationship.objects.filter(
                    student=student,
                    is_primary=True
                ).update(is_primary=False)
        
        return cleaned_data

class BulkUserCreationForm(forms.Form):
    """Form for creating multiple users at once"""
    
    user_data = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Enter user data in CSV format:\nusername,email,first_name,last_name,role,password'
        }),
        help_text="CSV format: username,email,first_name,last_name,role,password (optional)"
    )
    
    send_welcome_emails = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_user_data(self):
        data = self.cleaned_data.get('user_data')
        if not data:
            raise ValidationError(_('Please enter user data.'))
        
        lines = data.strip().split('\n')
        users = []
        
        for i, line in enumerate(lines, start=1):
            parts = [part.strip() for part in line.split(',')]
            
            if len(parts) < 4:
                raise ValidationError(
                    _('Line %(line)s: Expected at least 4 fields (username, email, first_name, last_name)'),
                    params={'line': i}
                )
            
            username, email, first_name, last_name = parts[:4]
            role = parts[4] if len(parts) > 4 else 'student'
            password = parts[5] if len(parts) > 5 else None
            
            # Validate username
            if User.objects.filter(username=username).exists():
                raise ValidationError(
                    _('Line %(line)s: Username "%(username)s" already exists'),
                    params={'line': i, 'username': username}
                )
            
            # Validate email
            if User.objects.filter(email=email).exists():
                raise ValidationError(
                    _('Line %(line)s: Email "%(email)s" already exists'),
                    params={'line': i, 'email': email}
                )
            
            # Validate role
            valid_roles = ['student', 'parent', 'teacher', 'admin']
            if role not in valid_roles:
                raise ValidationError(
                    _('Line %(line)s: Invalid role "%(role)s". Valid roles: %(valid_roles)s'),
                    params={'line': i, 'role': role, 'valid_roles': ', '.join(valid_roles)}
                )
            
            users.append({
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'password': password
            })
        
        return users

class UserActivationForm(forms.Form):
    """Form for activating/deactivating users"""
    
    action = forms.ChoiceField(
        choices=[
            ('activate', 'Activate Selected Users'),
            ('deactivate', 'Deactivate Selected Users'),
            ('delete', 'Delete Selected Users'),
        ],
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