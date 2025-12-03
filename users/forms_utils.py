# forms_utils.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import secrets
import string

User = get_user_model()

def generate_random_password(length=12):
    """Generate a random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_welcome_email(user, password=None):
    """Send welcome email to new user"""
    context = {
        'user': user,
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_URL,
        'password': password,
    }
    
    subject = f'Welcome to {settings.SITE_NAME}'
    html_message = render_to_string('emails/welcome_email.html', context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True,
    )

def send_password_reset_email(user, reset_url):
    """Send password reset email"""
    context = {
        'user': user,
        'reset_url': reset_url,
        'site_name': settings.SITE_NAME,
    }
    
    subject = f'Password Reset Request - {settings.SITE_NAME}'
    html_message = render_to_string('emails/password_reset.html', context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True,
    )

def get_form_errors(form):
    """Get form errors in a clean format"""
    errors = {}
    for field, error_list in form.errors.items():
        if field == '__all__':
            errors['non_field_errors'] = error_list
        else:
            errors[field] = error_list
    return errors

def create_user_from_csv_row(row, default_role='student'):
    """Create user from CSV row data"""
    try:
        username = row.get('username') or row.get('email').split('@')[0]
        email = row.get('email')
        first_name = row.get('first_name', '')
        last_name = row.get('last_name', '')
        role = row.get('role', default_role)
        phone = row.get('phone', '')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=generate_random_password(),
            first_name=first_name,
            last_name=last_name,
        )
        
        # Create profile
        from .models import UserProfile
        profile = UserProfile.objects.create(
            user=user,
            role=role,
            phone_number=phone,
        )
        
        # Set role-specific fields
        if role == 'student' and 'student_class' in row:
            from .models import Class
            try:
                profile.student_class = Class.objects.get(name=row['student_class'])
            except Class.DoesNotExist:
                pass
        
        profile.save()
        
        return user, True
    except Exception as e:
        return str(e), False