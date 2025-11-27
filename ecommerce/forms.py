from django import forms
from .models import Product, CartItem, Order, Payment, Category
from users.models import User

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'product_type', 'price',
            'sku', 'stock_quantity', 'low_stock_threshold', 'track_stock',
            'is_available', 'image', 'applicable_class'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StudentSelectionForm(forms.Form):
    search_type = forms.ChoiceField(
        choices=[('registration_number', 'Registration Number'), ('name', 'Name')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='registration_number'
    )
    registration_number = forms.CharField(
        required=False, 
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter registration number'})
    )
    student_name = forms.CharField(
        required=False, 
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter student name'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        search_type = cleaned_data.get('search_type')
        
        if search_type == 'registration_number' and not cleaned_data.get('registration_number'):
            raise forms.ValidationError("Please enter a registration number")
        elif search_type == 'name' and not cleaned_data.get('student_name'):
            raise forms.ValidationError("Please enter a student name")
        
        return cleaned_data
    
    def get_student(self):
        search_type = self.cleaned_data.get('search_type')
        
        if search_type == 'registration_number':
            try:
                return User.objects.get(
                    registration_number=self.cleaned_data['registration_number'],
                    role='student'
                )
            except User.DoesNotExist:
                raise forms.ValidationError("Student with this registration number not found")
        else:
            # Search by name
            name_parts = self.cleaned_data['student_name'].split()
            students = User.objects.filter(role='student')
            
            for student in students:
                full_name = student.get_full_name().lower()
                if all(part.lower() in full_name for part in name_parts):
                    return student
            
            raise forms.ValidationError("Student not found")

class AddToCartForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(role='student'),
        empty_label="Select Student",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = CartItem
        fields = ['quantity', 'student']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            })
        }
    
    def __init__(self, *args, **kwargs):
        parent_user = kwargs.pop('parent_user', None)
        super().__init__(*args, **kwargs)
        
        if parent_user and parent_user.is_parent():
            # Limit students to parent's children
            self.fields['student'].queryset = parent_user.children.all()

class CheckoutForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='paystack'
    )
    
    class Meta:
        model = Order
        fields = ['payment_method', 'billing_address', 'billing_phone']
        widgets = {
            'billing_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your complete billing address'
            }),
            'billing_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Pre-fill billing information
            self.fields['billing_address'].initial = user.address
            self.fields['billing_phone'].initial = user.phone_number

class ManualPaymentForm(forms.ModelForm):
    transfer_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    transfer_reference = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank transfer reference'})
    )
    transfer_proof = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Payment
        fields = ['transfer_date', 'transfer_reference', 'transfer_proof']

class StockUpdateForm(forms.Form):
    new_stock = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for stock update'})
    )