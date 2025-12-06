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
    Product, Category, Order, Cart, CartItem,
    Payment, FeeStructure, FeePayment, Inventory,
    Supplier, PurchaseOrder, Attendance
)
 
from .models import PaymentRecord
from users.models import User, Student, Parent
from django.db.models import Q, Sum
from django.db import models
import datetime
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




# ==================== PRODUCT & STORE FORMS ====================

class ProductForm(forms.ModelForm):
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=PriceInput
    )
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=PriceInput
    )
    low_stock_threshold = forms.IntegerField(
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'cost_price',
                 'stock_quantity', 'low_stock_threshold', 'sku', 'barcode',
                 'image', 'image_2', 'image_3', 'image_4', 'size', 'color',
                 'material', 'weight', 'dimensions', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'image_2': forms.FileInput(attrs={'class': 'form-control'}),
            'image_3': forms.FileInput(attrs={'class': 'form-control'}),
            'image_4': forms.FileInput(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'weight': forms.TextInput(attrs={'class': 'form-control'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'description', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...',
            'autocomplete': 'off'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('name', 'Name (A-Z)'),
            ('-name', 'Name (Z-A)'),
            ('price', 'Price (Low to High)'),
            ('-price', 'Price (High to Low)'),
            ('created_at', 'Newest First'),
            ('-created_at', 'Oldest First'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise ValidationError("Minimum price cannot be greater than maximum price.")
        
        return cleaned_data


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control quantity-input',
            'min': '1',
            'max': '99'
        })
    )
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),  # Will be populated in view
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, user=None, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Populate students based on user role
            if user.role == 'parent':
                # Get parent's students
                try:
                    parent = Parent.objects.get(user=user)
                    self.fields['student'].queryset = parent.students.all()
                except Parent.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
            elif user.role == 'student':
                # Student can only buy for themselves
                try:
                    student = Student.objects.get(user=user)
                    self.fields['student'].queryset = Student.objects.filter(id=student.id)
                    self.fields['student'].initial = student
                    self.fields['student'].widget = forms.HiddenInput()
                except Student.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
        
        if product:
            # Set max quantity based on stock
            if product.stock_quantity:
                self.fields['quantity'].widget.attrs['max'] = min(99, product.stock_quantity)


class CartItemUpdateForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=99,
        widget=forms.NumberInput(attrs={
            'class': 'form-control cart-quantity',
            'min': '1',
            'max': '99'
        })
    )
    
    class Meta:
        model = CartItem
        fields = ['quantity']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.product:
            self.fields['quantity'].widget.attrs['max'] = min(
                99, 
                self.instance.product.stock_quantity
            )
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.instance and self.instance.product:
            if quantity > self.instance.product.stock_quantity:
                raise ValidationError(
                    f"Only {self.instance.product.stock_quantity} items available in stock."
                )
        return quantity


# ==================== ORDER & PAYMENT FORMS ====================

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Shipping address (if different from profile)'
        })
    )
    delivery_date = forms.DateField(
        required=False,
        widget=DatePickerWidget,
        label="Preferred Delivery Date"
    )
    delivery_time = forms.ChoiceField(
        required=False,
        choices=[
            ('morning', 'Morning (8am - 12pm)'),
            ('afternoon', 'Afternoon (12pm - 4pm)'),
            ('evening', 'Evening (4pm - 7pm)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='paystack'
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes or instructions'
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I agree to the terms and conditions"
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.address:
            self.fields['shipping_address'].initial = user.address
    
    def clean_delivery_date(self):
        from django.utils import timezone
        delivery_date = self.cleaned_data.get('delivery_date')
        if delivery_date and delivery_date < timezone.now().date():
            raise ValidationError("Delivery date cannot be in the past.")
        return delivery_date


class PaystackPaymentForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email for payment receipt'
        })
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.HiddenInput()
    )
    reference = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        if order:
            self.fields['amount'].initial = order.total_amount
            self.fields['email'].initial = order.user.email


class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ==================== FEE PAYMENT FORMS ====================

class FeePaymentForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    amount_paid = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=PriceInput
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = FeePayment
        fields = ['student', 'fee_structure', 'amount_paid', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Filter students based on user role
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
    
    def clean_amount_paid(self):
        amount_paid = self.cleaned_data['amount_paid']
        fee_structure = self.cleaned_data.get('fee_structure')
        
        if fee_structure and amount_paid > fee_structure.amount:
            raise ValidationError(
                f"Amount paid (₦{amount_paid:,.2f}) cannot exceed fee amount (₦{fee_structure.amount:,.2f})"
            )
        
        return amount_paid


class BulkFeePaymentForm(forms.Form):
    student_ids = forms.ModelMultipleChoiceField(
        queryset=Student.objects.all(),
        widget=MultipleStudentSelectWidget,
        label="Select Students"
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student_ids'].queryset = Student.objects.filter(is_active=True)


# ==================== INVENTORY & SUPPLIER FORMS ====================

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['product', 'current_stock', 'minimum_stock', 
                 'maximum_stock', 'location', 'reorder_point']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'maximum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class SupplierForm(forms.ModelForm):
    phone = PhoneNumberField(
        widget=PhoneNumberWidget,
        required=True
    )
    
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 
                 'address', 'tax_id', 'rating', 'payment_terms']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '0.1'
            }),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'items', 'total_amount', 'status', 
                 'order_date', 'expected_delivery', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'items': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'total_amount': PriceInput,
            'status': forms.Select(attrs={'class': 'form-control'}),
            'order_date': DatePickerWidget,
            'expected_delivery': DatePickerWidget,
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ==================== PRODUCT & STORE FORMS ====================

class ProductForm(forms.ModelForm):
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=PriceInput
    )
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=PriceInput
    )
    low_stock_threshold = forms.IntegerField(
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'cost_price',
                 'stock_quantity', 'low_stock_threshold', 'sku', 'barcode',
                 'image', 'image_2', 'image_3', 'image_4', 'size', 'color',
                 'material', 'weight', 'dimensions', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'image_2': forms.FileInput(attrs={'class': 'form-control'}),
            'image_3': forms.FileInput(attrs={'class': 'form-control'}),
            'image_4': forms.FileInput(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'weight': forms.TextInput(attrs={'class': 'form-control'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'description', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...',
            'autocomplete': 'off'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('name', 'Name (A-Z)'),
            ('-name', 'Name (Z-A)'),
            ('price', 'Price (Low to High)'),
            ('-price', 'Price (High to Low)'),
            ('created_at', 'Newest First'),
            ('-created_at', 'Oldest First'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise ValidationError("Minimum price cannot be greater than maximum price.")
        
        return cleaned_data


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control quantity-input',
            'min': '1',
            'max': '99'
        })
    )
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),  # Will be populated in view
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, user=None, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Populate students based on user role
            if user.role == 'parent':
                # Get parent's students
                try:
                    parent = Parent.objects.get(user=user)
                    self.fields['student'].queryset = parent.students.all()
                except Parent.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
            elif user.role == 'student':
                # Student can only buy for themselves
                try:
                    student = Student.objects.get(user=user)
                    self.fields['student'].queryset = Student.objects.filter(id=student.id)
                    self.fields['student'].initial = student
                    self.fields['student'].widget = forms.HiddenInput()
                except Student.DoesNotExist:
                    self.fields['student'].queryset = Student.objects.none()
        
        if product:
            # Set max quantity based on stock
            if product.stock_quantity:
                self.fields['quantity'].widget.attrs['max'] = min(99, product.stock_quantity)


class CartItemUpdateForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=99,
        widget=forms.NumberInput(attrs={
            'class': 'form-control cart-quantity',
            'min': '1',
            'max': '99'
        })
    )
    
    class Meta:
        model = CartItem
        fields = ['quantity']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.product:
            self.fields['quantity'].widget.attrs['max'] = min(
                99, 
                self.instance.product.stock_quantity
            )
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.instance and self.instance.product:
            if quantity > self.instance.product.stock_quantity:
                raise ValidationError(
                    f"Only {self.instance.product.stock_quantity} items available in stock."
                )
        return quantity


# ==================== ORDER & PAYMENT FORMS ====================

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Shipping address (if different from profile)'
        })
    )
    delivery_date = forms.DateField(
        required=False,
        widget=DatePickerWidget,
        label="Preferred Delivery Date"
    )
    delivery_time = forms.ChoiceField(
        required=False,
        choices=[
            ('morning', 'Morning (8am - 12pm)'),
            ('afternoon', 'Afternoon (12pm - 4pm)'),
            ('evening', 'Evening (4pm - 7pm)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='paystack'
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes or instructions'
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I agree to the terms and conditions"
    )
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.address:
            self.fields['shipping_address'].initial = user.address
    
    def clean_delivery_date(self):
        from django.utils import timezone
        from users.models import Student, Parent
        delivery_date = self.cleaned_data.get('delivery_date')
        if delivery_date and delivery_date < timezone.now().date():
            raise ValidationError("Delivery date cannot be in the past.")
        return delivery_date


class PaystackPaymentForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email for payment receipt'
        })
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.HiddenInput()
    )
    reference = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        if order:
            self.fields['amount'].initial = order.total_amount
            self.fields['email'].initial = order.user.email


class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ==================== FEE PAYMENT FORMS ====================

class FeePaymentForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    amount_paid = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=PriceInput
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = FeePayment
        fields = ['student', 'fee_structure', 'amount_paid', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Filter students based on user role
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
    
    def clean_amount_paid(self):
        amount_paid = self.cleaned_data['amount_paid']
        fee_structure = self.cleaned_data.get('fee_structure')
        
        if fee_structure and amount_paid > fee_structure.amount:
            raise ValidationError(
                f"Amount paid (₦{amount_paid:,.2f}) cannot exceed fee amount (₦{fee_structure.amount:,.2f})"
            )
        
        return amount_paid


class BulkFeePaymentForm(forms.Form):
    student_ids = forms.ModelMultipleChoiceField(
        queryset=Student.objects.all(),
        widget=MultipleStudentSelectWidget,
        label="Select Students"
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student_ids'].queryset = Student.objects.filter(is_active=True)


# ==================== INVENTORY & SUPPLIER FORMS ====================

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['product', 'current_stock', 'minimum_stock', 
                 'maximum_stock', 'location', 'reorder_point']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'maximum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class SupplierForm(forms.ModelForm):
    phone = PhoneNumberField(
        widget=PhoneNumberWidget,
        required=True
    )
    
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 
                 'address', 'tax_id', 'rating', 'payment_terms']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '0.1'
            }),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'items', 'total_amount', 'status', 
                 'order_date', 'expected_delivery', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'items': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'total_amount': PriceInput,
            'status': forms.Select(attrs={'class': 'form-control'}),
            'order_date': DatePickerWidget,
            'expected_delivery': DatePickerWidget,
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
    grade_level = forms.CharField(
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


class FeeStructureForm(forms.ModelForm):
    """Fee structure form for admin"""
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=PriceInput
    )
    tuition_fee = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PriceInput,
        label="Tuition Fee"
    )
    development_levy = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PriceInput,
        label="Development Levy"
    )
    exam_fee = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PriceInput,
        label="Exam Fee"
    )
    sports_fee = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PriceInput,
        label="Sports Fee"
    )
    other_charges = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PriceInput,
        label="Other Charges"
    )
    late_fee = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=PriceInput,
        label="Late Fee"
    )
    
    class Meta:
        model = FeeStructure
        fields = [
            'name', 'description', 'academic_year', 'student_class', 'term',
            'amount', 'due_date', 'late_fee', 'late_fee_date',
            'tuition_fee', 'development_levy', 'exam_fee', 
            'sports_fee', 'other_charges', 'is_active', 'is_compulsory', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., JSS 1 First Term Fees'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Fee structure description'
            }),
            'academic_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2024/2025'
            }),
            'student_class': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., JSS 1, SSS 3'
            }),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'due_date': DatePickerWidget,
            'late_fee_date': DatePickerWidget,
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_compulsory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional notes'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'fee-structure-form'
        
        # Set up layout with crispy forms
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='col-md-6'),
                    Column('academic_year', css_class='col-md-3'),
                    Column('term', css_class='col-md-3'),
                ),
                Row(
                    Column('student_class', css_class='col-md-6'),
                    Column('due_date', css_class='col-md-3'),
                    Column('late_fee_date', css_class='col-md-3'),
                ),
                'description',
                css_class='mb-4'
            ),
            
            Fieldset(
                'Fee Breakdown',
                HTML('<div class="alert alert-info">'
                     '<i class="fas fa-info-circle me-2"></i>'
                     'The total amount will be calculated automatically from the breakdown below.'
                     '</div>'),
                Row(
                    Column('tuition_fee', css_class='col-md-6'),
                    Column('development_levy', css_class='col-md-6'),
                ),
                Row(
                    Column('exam_fee', css_class='col-md-6'),
                    Column('sports_fee', css_class='col-md-6'),
                ),
                Row(
                    Column('other_charges', css_class='col-md-6'),
                    Column('late_fee', css_class='col-md-6'),
                ),
                Row(
                    Column('amount', css_class='col-md-6'),
                    Column(HTML('<div class="mt-4"><strong>Total:</strong> <span id="totalDisplay" class="h5 text-primary">₦0.00</span></div>'), 
                           css_class='col-md-6'),
                ),
                css_class='mb-4'
            ),
            
            Fieldset(
                'Additional Settings',
                Row(
                    Column('is_active', css_class='col-md-6'),
                    Column('is_compulsory', css_class='col-md-6'),
                ),
                'notes',
                css_class='mb-4'
            ),
            
            Submit('submit', 'Save Fee Structure', css_class='btn-primary w-100')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate dates
        due_date = cleaned_data.get('due_date')
        late_fee_date = cleaned_data.get('late_fee_date')
        
        if due_date and late_fee_date and late_fee_date <= due_date:
            raise ValidationError({
                'late_fee_date': 'Late fee date must be after the due date.'
            })
        
        # Calculate total from breakdown
        tuition_fee = cleaned_data.get('tuition_fee') or 0
        development_levy = cleaned_data.get('development_levy') or 0
        exam_fee = cleaned_data.get('exam_fee') or 0
        sports_fee = cleaned_data.get('sports_fee') or 0
        other_charges = cleaned_data.get('other_charges') or 0
        
        calculated_total = tuition_fee + development_levy + exam_fee + sports_fee + other_charges
        
        # Update amount if breakdown is provided
        if calculated_total > 0:
            cleaned_data['amount'] = calculated_total
        
        # Validate amount
        amount = cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError({
                'amount': 'Amount must be greater than zero.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Ensure breakdown matches total
        if instance.amount:
            # If any breakdown field is empty but amount is set, distribute
            if not instance.tuition_fee:
                instance.tuition_fee = instance.amount
        
        if commit:
            instance.save()
        
        return instance


class FeeStructureSearchForm(forms.Form):
    """Fee structure search form"""
    academic_year = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Academic Year'
        })
    )
    student_class = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Class Level'
        })
    )
    term = forms.ChoiceField(
        required=False,
        choices=[('', 'All Terms')] + FeeStructure.TERM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('active', 'Active Only'),
            ('inactive', 'Inactive Only'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

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
    
    # Store
    'ProductForm',
    'CategoryForm',
    'ProductSearchForm',
    'AddToCartForm',
    'CartItemUpdateForm',
    
    # Orders & Payments
    'CheckoutForm',
    'PaystackPaymentForm',
    'OrderStatusUpdateForm',
    
    # Fee Payments
    'FeePaymentForm',
    'BulkFeePaymentForm',
    
    # Inventory
    'InventoryForm',
    'SupplierForm',
    'PurchaseOrderForm',
    
    # Attendance
    'AttendanceForm',
    'BulkAttendanceForm',
    
    # Reports
    'SalesReportForm',
    'FeeCollectionReportForm',
    
    # CBT Integration
    'ExamAccessForm',
    'ExamPaymentVerificationForm',
    
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

class FeePaymentSearchForm(forms.Form):
    """Form for searching fee payments"""
    
    # Basic search
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by student, receipt, transaction...',
            'class': 'form-control',
        })
    )
    
    # Student filter
    student = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Student name or ID',
            'class': 'form-control',
        })
    )
    
    # Academic filters
    academic_year = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., 2024/2025',
            'class': 'form-control',
        })
    )
    
    student_class = forms.Select()
    
    term = forms.ChoiceField(
        required=False,
        choices=[('', 'All Terms')] + FeeStructure.TERM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Payment details
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('', 'All Methods')] + Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Payment.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Amount range
    min_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Min Amount',
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    max_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Max Amount',
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    # Date filters
    payment_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    
    payment_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    
    # Verification filter
    is_verified = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('verified', 'Verified Only'),
            ('unverified', 'Unverified Only'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    receipt_issued = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('issued', 'Receipt Issued'),
            ('not_issued', 'Receipt Not Issued'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Sort options
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('-payment_date', 'Newest Payments'),
            ('payment_date', 'Oldest Payments'),
            ('amount_paid', 'Amount Low-High'),
            ('-amount_paid', 'Amount High-Low'),
            ('student__last_name', 'Student A-Z'),
            ('-student__last_name', 'Student Z-A'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def search_queryset(self, queryset=None):
        """Apply search filters to queryset"""
        if queryset is None:
            queryset = FeePayment.objects.all()
        
        data = self.cleaned_data
        
        # Text search
        if data.get('search'):
            search_term = data['search']
            queryset = queryset.filter(
                Q(search_text__icontains=search_term) |
                Q(receipt_number__icontains=search_term) |
                Q(transaction_code__icontains=search_term) |
                Q(payment_reference__icontains=search_term) |
                Q(student__first_name__icontains=search_term) |
                Q(student__last_name__icontains=search_term) |
                Q(student__admission_number__icontains=search_term)
            )
        
        # Student filter
        if data.get('student'):
            student_term = data['student']
            queryset = queryset.filter(
                Q(student__first_name__icontains=student_term) |
                Q(student__last_name__icontains=student_term) |
                Q(student__admission_number__icontains=student_term)
            )
        
        # Academic filters via fee_structure
        if data.get('academic_year'):
            queryset = queryset.filter(fee_structure__academic_year__icontains=data['academic_year'])
        
        if data.get('grade_class'):
            queryset = queryset.filter(fee_structure__grade_class__icontains=data['grade_class'])
        
        if data.get('term'):
            queryset = queryset.filter(fee_structure__term=data['term'])
        
        # Payment details
        if data.get('payment_method'):
            queryset = queryset.filter(payment_method=data['payment_method'])
        
        if data.get('payment_status'):
            queryset = queryset.filter(payment_status=data['payment_status'])
        
        # Amount range
        if data.get('min_amount'):
            queryset = queryset.filter(amount_paid__gte=data['min_amount'])
        
        if data.get('max_amount'):
            queryset = queryset.filter(amount_paid__lte=data['max_amount'])
        
        # Date filters
        if data.get('payment_date_from'):
            queryset = queryset.filter(payment_date__date__gte=data['payment_date_from'])
        
        if data.get('payment_date_to'):
            queryset = queryset.filter(payment_date__date__lte=data['payment_date_to'])
        
        # Verification filter
        if data.get('is_verified') == 'verified':
            queryset = queryset.filter(is_verified=True)
        elif data.get('is_verified') == 'unverified':
            queryset = queryset.filter(is_verified=False)
        
        # Receipt filter
        if data.get('receipt_issued') == 'issued':
            queryset = queryset.filter(receipt_issued=True)
        elif data.get('receipt_issued') == 'not_issued':
            queryset = queryset.filter(receipt_issued=False)
        
        # Sorting
        if data.get('sort_by'):
            queryset = queryset.order_by(data['sort_by'])
        else:
            queryset = queryset.order_by('-payment_date')
        
        return queryset
    
    def get_summary_stats(self, queryset):
        """Get summary statistics for the filtered payments"""
        total_payments = queryset.count()
        total_amount = queryset.aggregate(models.Sum('amount_paid'))['amount_paid__sum'] or 0
        avg_amount = total_amount / total_payments if total_payments > 0 else 0
        
        # Count by status
        status_counts = {}
        for status_code, status_name in FeePayment.PAYMENT_STATUS_CHOICES:
            count = queryset.filter(payment_status=status_code).count()
            if count > 0:
                status_counts[status_name] = count
        
        # Count by payment method
        method_counts = {}
        for method_code, method_name in FeePayment.PAYMENT_METHOD_CHOICES:
            count = queryset.filter(payment_method=method_code).count()
            if count > 0:
                method_counts[method_name] = count
        
        return {
            'total_payments': total_payments,
            'total_amount': total_amount,
            'average_amount': avg_amount,
            'status_counts': status_counts,
            'method_counts': method_counts,
        }


class PaymentRecordSearchForm(forms.Form):
    """Simple search form for PaymentRecord"""
    
    # Search field
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by transaction ID, payer, amount...',
            'class': 'form-control',
        })
    )
    
    # Payment method filter
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('', 'All Methods')] + PaymentRecord.PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Status filter
    payment_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + PaymentRecord.PaymentStatus.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Amount range
    min_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Min Amount (₦)',
            'class': 'form-control',
            'min': '0.01',
            'step': '0.01'
        })
    )
    
    max_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Max Amount (₦)',
            'class': 'form-control',
            'min': '0.01',
            'step': '0.01'
        })
    )
    
    # Date range
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )
    
    def search_queryset(self):
        """Apply search filters to PaymentRecord queryset"""
        queryset = PaymentRecord.objects.all()
        
        if not hasattr(self, 'cleaned_data'):
            return queryset
        
        data = self.cleaned_data
        
        # Text search
        if data.get('search'):
            search_term = data['search']
            queryset = queryset.filter(
                Q(transaction_id__icontains=search_term) |
                Q(payer__username__icontains=search_term) |
                Q(payer__email__icontains=search_term) |
                Q(payer__first_name__icontains=search_term) |
                Q(payer__last_name__icontains=search_term) |
                Q(paystack_reference__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        # Payment method filter
        if data.get('payment_method'):
            queryset = queryset.filter(payment_method=data['payment_method'])
        
        # Status filter
        if data.get('payment_status'):
            queryset = queryset.filter(payment_status=data['payment_status'])
        
        # Amount range
        if data.get('min_amount'):
            queryset = queryset.filter(amount__gte=data['min_amount'])
        
        if data.get('max_amount'):
            queryset = queryset.filter(amount__lte=data['max_amount'])
        
        # Date range
        if data.get('start_date'):
            queryset = queryset.filter(payment_date__date__gte=data['start_date'])
        
        if data.get('end_date'):
            queryset = queryset.filter(payment_date__date__lte=data['end_date'])
        
        # Order by latest first
        queryset = queryset.order_by('-payment_date')
        
        return queryset
    
    def get_summary_stats(self, queryset):
        """Get summary statistics"""
        total_payments = queryset.count()
        total_amount = queryset.aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        successful_payments = queryset.filter(payment_status='successful').count()
        pending_payments = queryset.filter(payment_status='pending').count()
        
        return {
            'total_payments': total_payments,
            'total_amount': total_amount,
            'successful_payments': successful_payments,
            'pending_payments': pending_payments,
            'success_rate': (successful_payments / total_payments * 100) if total_payments > 0 else 0,
        }