from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML, Field, Fieldset
import re
from django.utils import timezone
from .models import (
    User, Student, Parent
)
from store.models import FeePayment, Payment, Attendance

 
# ==================== CUSTOM WIDGETS ====================

class DatePickerWidget(forms.DateInput):
    input_type = 'date'
    
    def __init__(self, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({'class': 'form-control datepicker'})
        super().__init__(**kwargs)


class PhoneNumberWidget(PhoneNumberPrefixWidget):
    """
    Safe wrapper for PhoneNumberPrefixWidget that supplies default widgets
    and default attrs if not provided. This avoids MultiWidget.__init__
    being called without the required `widgets` argument.
    """
    def __init__(self, widgets=None, attrs=None, *args, **kwargs):
        # Ensure attrs exists and contains the form-control class
        if attrs is None:
            attrs = {'class': 'form-control phone-input'}
        else:
            attrs = dict(attrs)  # copy to avoid mutating caller dict
            existing = attrs.get('class', '')
            classes = (existing + ' form-control phone-input').strip()
            attrs['class'] = classes

        # If widgets not supplied, build defaults like SplitPhoneNumberField does
        if widgets is None:
            # Lazy import to avoid circular import at module import time
            from phonenumber_field.formfields import PrefixChoiceField
            from django.forms import CharField as DjangoCharField

            prefix_widget = PrefixChoiceField().widget
            number_widget = DjangoCharField().widget
            widgets = (prefix_widget, number_widget)

        # Call base MultiWidget constructor correctly (widgets first)
        super().__init__(widgets, attrs=attrs)





class MultipleStudentSelectWidget(forms.SelectMultiple):
    template_name = 'widgets/multiple_student_select.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({
            'class': 'form-control select2-multiple',
            'data-placeholder': 'Search and select students...'
        })
        super().__init__(*args, **kwargs)


class PriceInput(forms.NumberInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({
            'class': 'form-control price-input',
            'step': '0.01',
            'min': '0'
        })
        super().__init__(*args, **kwargs)


# ==================== AUTHENTICATION FORMS ====================

class BrillsPayUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number',
            'pattern': '[0-9]{11}',
            'title': 'Please enter a valid 11-digit phone number'
        })
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'first_name', 'last_name', 'role', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'autocomplete': 'username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'brillspay-form'
        
        # Customize password help text
        self.fields['password1'].help_text = """
            <ul class="password-help">
                <li>At least 8 characters</li>
                <li>Contains uppercase letter</li>
                <li>Contains lowercase letter</li>
                <li>Contains number</li>
                <li>Contains special character (!@#$%^&*)</li>
            </ul>
        """
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control password-strength',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        # Nigerian phone number validation
        if not re.match(r'^0[7-9][0-1]\d{8}$', phone):
            raise ValidationError("Please enter a valid Nigerian phone number (e.g., 08012345678)")
        
        # Check if phone number already exists
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("This phone number is already registered.")
        
        return phone
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match.")
        
        # Password strength validation
        if password1:
            if len(password1) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Z]', password1):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password1):
                raise ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'[0-9]', password1):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*]', password1):
                raise ValidationError("Password must contain at least one special character (!@#$%^&*).")
        
        return password2


class ParentRegistrationForm(BrillsPayUserCreationForm):
    student_ids = forms.ModelMultipleChoiceField(
        queryset=Student.objects.all(),
        widget=MultipleStudentSelectWidget,
        required=True,
        label="Select Your Children"
    )
    relationship = forms.ChoiceField(
        choices=[
            ('father', 'Father'),
            ('mother', 'Mother'),
            ('guardian', 'Guardian'),
            ('other', 'Other')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    occupation = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Occupation (optional)'
        })
    )
    
    class Meta(BrillsPayUserCreationForm.Meta):
        fields = BrillsPayUserCreationForm.Meta.fields + (
            'student_ids', 'relationship', 'occupation'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = 'parent'
        self.fields['role'].widget = forms.HiddenInput()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'parent'
        
        if commit:
            user.save()
            # Create parent profile
            parent = Parent.objects.create(
                user=user,
                occupation=self.cleaned_data.get('occupation', ''),
                relationship=self.cleaned_data.get('relationship', 'guardian')
            )
            # Link selected students
            parent.students.set(self.cleaned_data['student_ids'])
            parent.save()
        
        return user


class StudentRegistrationForm(BrillsPayUserCreationForm):
    admission_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admission Number'
        })
    )
    date_of_birth = forms.DateField(
        widget=DatePickerWidget,
        required=True
    )
    current_class = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., JSS 1A'
        })
    )
    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta(BrillsPayUserCreationForm.Meta):
        fields = BrillsPayUserCreationForm.Meta.fields + (
            'admission_number', 'date_of_birth', 'current_class', 'gender'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = 'student'
        self.fields['role'].widget = forms.HiddenInput()
    
    def clean_admission_number(self):
        admission_number = self.cleaned_data['admission_number']
        if Student.objects.filter(admission_number=admission_number).exists():
            raise ValidationError("This admission number is already registered.")
        return admission_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        
        if commit:
            user.save()
            # Create student profile
            Student.objects.create(
                user=user,
                admission_number=self.cleaned_data['admission_number'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                date_of_birth=self.cleaned_data['date_of_birth'],
                current_class=self.cleaned_data['current_class'],
                gender=self.cleaned_data['gender']
            )
        
        return user


class BrillsPayLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email, Username or Admission Number',
            'autocomplete': 'username'
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
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'brillspay-login-form'
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username/email/admission number
            user = None
            
            # Check if input is admission number
            if Student.objects.filter(admission_number=username).exists():
                student = Student.objects.get(admission_number=username)
                user = student.user
            
            # If not admission number, try username/email
            if not user:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    try:
                        user = User.objects.get(email=username)
                    except User.DoesNotExist:
                        pass
            
            if user:
                self.user_cache = authenticate(
                    request=self.request,
                    username=user.username,
                    password=password
                )
                
                if self.user_cache is None:
                    raise ValidationError(
                        "Please enter a correct username/email/admission number and password."
                    )
                elif not self.user_cache.is_active:
                    raise ValidationError("This account is inactive.")
            else:
                raise ValidationError(
                    "Please enter a correct username/email/admission number and password."
                )
        
        return self.cleaned_data


class BrillsPayPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email address',
            'autocomplete': 'email'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'


class BrillsPaySetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'autocomplete': 'new-password'
        }),
        help_text="Your password must contain at least 8 characters with uppercase, lowercase, number, and special character."
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'


# ==================== USER PROFILE FORMS ====================

class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': '[0-9]{11}'
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_picture', 
                 'address', 'city', 'state', 'country', 'postal_code']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-6'),
                Column('phone', css_class='col-md-6'),
            ),
            'profile_picture',
            'address',
            Row(
                Column('city', css_class='col-md-4'),
                Column('state', css_class='col-md-4'),
                Column('postal_code', css_class='col-md-4'),
            ),
            'country',
            Submit('submit', 'Update Profile', css_class='btn-primary w-100')
        )


class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['occupation', 'employer', 'income_range', 'relationship', 'is_primary']
        widgets = {
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'employer': forms.TextInput(attrs={'class': 'form-control'}),
            'income_range': forms.Select(attrs={'class': 'form-control'}),
            'relationship': forms.Select(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StudentProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(widget=DatePickerWidget)
    
    class Meta:
        model = Student
        fields = ['date_of_birth', 'gender', 'student_class', 'section', 
                 'roll_number', 'academic_year', 'emergency_contact', 
                 'emergency_phone', 'notes']
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'current_class': forms.TextInput(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ==================== ATTENDANCE & SCHOOL MANAGEMENT FORMS ====================

class AttendanceForm(forms.ModelForm):
    date = forms.DateField(
        widget=DatePickerWidget,
        initial=lambda: timezone.now().date() if 'timezone' in locals() else None
    )
    
    class Meta:
        model = Attendance
        fields = ['student', 'date', 'status', 'check_in', 'check_out', 'notes']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'check_in': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'check_out': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BulkAttendanceForm(forms.Form):
    date = forms.DateField(
        widget=DatePickerWidget,
        label="Attendance Date"
    )
    class_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., JSS 1A'
        }),
        label="Class"
    )
    attendance_data = forms.CharField(
        widget=forms.HiddenInput()
    )


from django.contrib.auth.forms import PasswordChangeForm as BasePasswordChangeForm

class PasswordChangeForm(BasePasswordChangeForm):
    """Custom password change form with better styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Customize widget attributes
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Current password',
            'autocomplete': 'current-password'
        })
        
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control password-strength',
            'placeholder': 'New password',
            'autocomplete': 'new-password'
        })
        
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
        
        # Update help text
        self.fields['new_password1'].help_text = """
            <div class="password-requirements">
                <small>Your password must contain:</small>
                <ul class="small text-muted mt-2 mb-0">
                    <li>At least 8 characters</li>
                    <li>At least one uppercase letter</li>
                    <li>At least one lowercase letter</li>
                    <li>At least one number</li>
                    <li>At least one special character (!@#$%^&*)</li>
                </ul>
            </div>
        """
        
        # Add FormHelper for crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'password-change-form'
        self.helper.layout = Layout(
            Fieldset(
                'Change Password',
                'old_password',
                'new_password1',
                HTML('<div class="password-strength-meter mb-3">'
                     '<small>Password strength: <span id="strengthText">None</span></small>'
                     '<div class="progress" style="height: 4px;">'
                     '<div class="progress-bar" id="strengthBar" style="width: 0%"></div>'
                     '</div>'
                     '</div>'),
                'new_password2',
                css_class='mb-4'
            ),
            Submit('submit', 'Change Password', css_class='btn-primary w-100')
        )
    
    def clean_new_password2(self):
        """Additional password validation"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        
        # Additional password strength validation
        if password1:
            if len(password1) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Z]', password1):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password1):
                raise ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'[0-9]', password1):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*]', password1):
                raise ValidationError("Password must contain at least one special character (!@#$%^&*).")
        
        return password2


class PasswordResetRequestForm(forms.Form):
    """Password reset request form"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email address',
            'autocomplete': 'email'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'password-reset-form'
        self.helper.layout = Layout(
            Fieldset(
                'Reset Password',
                HTML('<p class="text-muted mb-3">'
                     'Enter your email address and we will send you instructions to reset your password.'
                     '</p>'),
                'email',
                css_class='mb-4'
            ),
            Submit('submit', 'Send Reset Instructions', css_class='btn-primary w-100')
        )


class SetNewPasswordForm(SetPasswordForm):
    """Set new password form"""
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control password-strength',
            'placeholder': 'New password',
            'autocomplete': 'new-password'
        }),
        help_text="Your password must contain at least 8 characters with uppercase, lowercase, number, and special character."
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'set-password-form'
        self.helper.layout = Layout(
            Fieldset(
                'Set New Password',
                HTML('<p class="text-muted mb-3">'
                     'Please enter your new password twice to verify you typed it correctly.'
                     '</p>'),
                'new_password1',
                HTML('<div class="password-strength-meter mb-3">'
                     '<small>Password strength: <span id="strengthText">None</span></small>'
                     '<div class="progress" style="height: 4px;">'
                     '<div class="progress-bar" id="strengthBar" style="width: 0%"></div>'
                     '</div>'
                     '</div>'),
                'new_password2',
                css_class='mb-4'
            ),
            Submit('submit', 'Set New Password', css_class='btn-primary w-100')
        )
    
    def clean_new_password2(self):
        """Additional password validation"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        
        # Additional password strength validation
        if password1:
            if len(password1) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Z]', password1):
                raise ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password1):
                raise ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'[0-9]', password1):
                raise ValidationError("Password must contain at least one number.")
            if not re.search(r'[!@#$%^&*]', password1):
                raise ValidationError("Password must contain at least one special character (!@#$%^&*).")
        
        return password2
    


# ==================== REPORT & ANALYTICS FORMS ====================

class SalesReportForm(forms.Form):
    start_date = forms.DateField(
        widget=DatePickerWidget,
        label="Start Date"
    )
    end_date = forms.DateField(
        widget=DatePickerWidget,
        label="End Date"
    )
    report_type = forms.ChoiceField(
        choices=[
            ('daily', 'Daily Sales'),
            ('weekly', 'Weekly Sales'),
            ('monthly', 'Monthly Sales'),
            ('yearly', 'Yearly Sales'),
            ('custom', 'Custom Range'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    group_by = forms.ChoiceField(
        required=False,
        choices=[
            ('category', 'Category'),
            ('product', 'Product'),
            ('student', 'Student'),
            ('class', 'Class'),
            ('payment_method', 'Payment Method'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data


class FeeCollectionReportForm(forms.Form):
    academic_year = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 2024/2025'
        })
    )
    term = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Terms'),
            ('first', 'First Term'),
            ('second', 'Second Term'),
            ('third', 'Third Term'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class_level = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., JSS 1, SSS 3'
        })
    )
    payment_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('paid', 'Paid'),
            ('partial', 'Partial'),
            ('unpaid', 'Unpaid'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ==================== CBT EXAM INTEGRATION FORMS ====================

class ExamAccessForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    exam_type = forms.ChoiceField(
        choices=[
            ('cbt', 'Computer Based Test'),
            ('practice', 'Practice Test'),
            ('mock', 'Mock Exam'),
            ('final', 'Final Exam'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    subject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    exam_date = forms.DateField(
        widget=DatePickerWidget
    )
    duration = forms.IntegerField(
        min_value=1,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Duration in minutes'
        })
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            if user.role == 'parent':
                try:
                    parent = Parent.objects.get(user=user)
                    self.fields['student'].queryset = parent.students.all()
                except Parent.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
            elif user.role == 'student':
                try:
                    student = Student.objects.get(user=user)
                    self.fields['student'].queryset = Student.objects.filter(id=student.id)
                    self.fields['student'].initial = student
                    self.fields['student'].widget = forms.HiddenInput()
                except Student.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()


class ExamPaymentVerificationForm(forms.Form):
    payment_reference = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter payment reference number'
        })
    )
    student_admission = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student admission number'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_reference = cleaned_data.get('payment_reference')
        student_admission = cleaned_data.get('student_admission')
        
        # Verify payment exists and is for the correct student
        try:
            payment = Payment.objects.get(
                reference=payment_reference,
                status='completed'
            )
            student = Student.objects.get(admission_number=student_admission)
            
            # Check if payment is for this student's fees
            fee_payment = FeePayment.objects.filter(
                student=student,
                payment_reference=payment_reference
            ).first()
            
            if not fee_payment:
                raise ValidationError(
                    "No fee payment found for this student with the given reference."
                )
            
            cleaned_data['payment'] = payment
            cleaned_data['student'] = student
            cleaned_data['fee_payment'] = fee_payment
            
        except Payment.DoesNotExist:
            raise ValidationError("Payment not found or not completed.")
        except Student.DoesNotExist:
            raise ValidationError("Student not found.")
        
        return cleaned_data


# ==================== UTILITY FORMS ====================

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email'
        })
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone number (optional)'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your message'
        })
    )
    message_type = forms.ChoiceField(
        choices=[
            ('general', 'General Inquiry'),
            ('payment', 'Payment Issue'),
            ('technical', 'Technical Support'),
            ('suggestion', 'Suggestion'),
            ('complaint', 'Complaint'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FeedbackForm(forms.Form):
    rating = forms.ChoiceField(
        choices=[
            (5, '★★★★★ Excellent'),
            (4, '★★★★ Very Good'),
            (3, '★★★ Good'),
            (2, '★★ Fair'),
            (1, '★ Poor'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Your feedback helps us improve...'
        })
    )
    anonymous = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Submit anonymously"
    )


# ==================== FORM UTILITIES ====================

class FormHelperMixin:
    """Mixin to add FormHelper to forms"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        if not hasattr(self.helper, 'layout'):
            self.helper.layout = Layout(*self.get_layout_fields())
    
    def get_layout_fields(self):
        """Get fields for layout - override in subclasses"""
        return [Field(field) for field in self.fields]


class DynamicStudentSelectForm(FormHelperMixin, forms.Form):
    """Form that dynamically loads students based on user"""
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control select2-dynamic'})
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            if user.role == 'parent':
                try:
                    parent = Parent.objects.get(user=user)
                    self.fields['student'].queryset = parent.students.all()
                except Parent.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
            elif user.role == 'student':
                try:
                    student = Student.objects.get(user=user)
                    self.fields['student'].queryset = Student.objects.filter(id=student.id)
                    self.fields['student'].initial = student
                except Student.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()


# ==================== FORM VALIDATORS ====================

def validate_nigerian_phone(value):
    """Validate Nigerian phone number"""
    pattern = r'^0[7-9][0-1]\d{8}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Enter a valid Nigerian phone number (e.g., 08012345678)'),
            code='invalid_phone'
        )


def validate_admission_number(value):
    """Validate admission number format"""
    # Example: BR/2024/001
    pattern = r'^[A-Z]{2,4}/\d{4}/\d{3,4}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Enter a valid admission number (e.g., BR/2024/001)'),
            code='invalid_admission'
        )


def validate_price(value):
    """Validate price is positive"""
    if value <= 0:
        raise ValidationError(
            _('Price must be greater than zero'),
            code='invalid_price'
        )


def validate_stock_quantity(value):
    """Validate stock quantity"""
    if value < 0:
        raise ValidationError(
            _('Stock quantity cannot be negative'),
            code='invalid_stock'
        )


# ==================== FORM FACTORIES ====================

def create_student_selector_form(user):
    """Factory function to create student selector form based on user role"""
    class StudentSelectorForm(forms.Form):
        student = forms.ModelChoiceField(
            queryset=Student.objects.none(),
            label="Select Student",
            widget=forms.Select(attrs={'class': 'form-control'})
        )
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if user.role == 'parent':
                try:
                    parent = Parent.objects.get(user=user)
                    self.fields['student'].queryset = parent.students.all()
                except Parent.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
            elif user.role == 'student':
                try:
                    student = Student.objects.get(user=user)
                    self.fields['student'].queryset = Student.objects.filter(id=student.id)
                    self.fields['student'].initial = student
                    self.fields['student'].widget = forms.HiddenInput()
                except Student.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
    
    return StudentSelectorForm


# Export forms for easy import
__all__ = [
    # Authentication
    'BrillsPayUserCreationForm',
    'ParentRegistrationForm',
    'StudentRegistrationForm',
    'BrillsPayLoginForm',
    'BrillsPayPasswordResetForm',
    'BrillsPaySetPasswordForm',
    
    # Profile
    'UserProfileForm',
    'ParentProfileForm',
    'StudentProfileForm',
    
    # # Store
    # 'ProductForm',
    # 'CategoryForm',
    # 'ProductSearchForm',
    # 'AddToCartForm',
    # 'CartItemUpdateForm',
    
    # # Orders & Payments
    # 'CheckoutForm',
    # 'PaystackPaymentForm',
    # 'OrderStatusUpdateForm',
    
    # # Fee Payments
    # 'FeePaymentForm',
    # 'BulkFeePaymentForm',
    
    # # Inventory
    # 'InventoryForm',
    # 'SupplierForm',
    # 'PurchaseOrderForm',
    
    # # Attendance
    # 'AttendanceForm',
    # 'BulkAttendanceForm',
    
    # # Reports
    # 'SalesReportForm',
    # 'FeeCollectionReportForm',
    
    # # CBT Integration
    # 'ExamAccessForm',
    # 'ExamPaymentVerificationForm',
    
    # Utilities
    'ContactForm',
    'FeedbackForm',
    'DynamicStudentSelectForm',
    
    # Validators
    'validate_nigerian_phone',
    'validate_admission_number',
    'validate_price',
    'validate_stock_quantity',
    
    # Factories
    'create_student_selector_form',
]