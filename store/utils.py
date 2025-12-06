import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Sum

def generate_order_number():
    """Generate unique order number"""
    from django.utils import timezone
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{timestamp}-{random_str}"

def generate_receipt_number():
    """Generate unique receipt number"""
    from django.utils import timezone
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=4))
    return f"REC-{timestamp}-{random_str}"

def generate_pickup_code():
    """Generate pickup code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def send_order_confirmation_email(order):
    """Send order confirmation email"""
    subject = f'Order Confirmation - {order.order_number}'
    html_message = render_to_string('store/emails/order_confirmation.html', {
        'order': order,
        'items': order.items.all(),
        'user': order.user
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        html_message=html_message,
        fail_silently=True
    )

def send_fee_receipt_email(fee_payment):
    """Send fee receipt email"""
    subject = f'Fee Payment Receipt - {fee_payment.receipt_number}'
    html_message = render_to_string('store/emails/fee_receipt.html', {
        'fee_payment': fee_payment,
        'student': fee_payment.student,
        'user': fee_payment.student.user
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[fee_payment.student.user.email],
        html_message=html_message,
        fail_silently=True
    )

def send_pickup_code_email(student_parent, code):
    """Send pickup code email to parent"""
    subject = f'Pickup Code for {student_parent.student.get_full_name()}'
    html_message = render_to_string('store/emails/pickup_code.html', {
        'student_parent': student_parent,
        'code': code,
        'student': student_parent.student
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student_parent.parent.user.email],
        html_message=html_message,
        fail_silently=True
    )

def format_currency(amount):
    """Format amount as Nigerian Naira"""
    return f"₦{amount:,.2f}"

def calculate_age(date_of_birth):
    """Calculate age from date of birth"""
    from django.utils import timezone
    today = timezone.now().date()
    age = today.year - date_of_birth.year
    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age

def get_student_unpaid_fees(student):
    """Get all unpaid fees for a student"""
    from .models import FeeStructure, FeePayment
    unpaid_fees = []
    
    fee_structures = FeeStructure.objects.filter(
        class_level=student.class_level,
        is_active=True
    )
    
    for fee in fee_structures:
        paid_amount = FeePayment.objects.filter(
            student=student,
            fee_structure=fee
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        if paid_amount < fee.amount:
            unpaid_fees.append({
                'fee': fee,
                'paid': paid_amount,
                'balance': fee.amount - paid_amount
            })
    
    return unpaid_fees

def check_exam_access(student):
    """Check if student has exam access"""
    from .models import FeePayment
    # Check if student has paid exam fees for current term
    exam_payments = FeePayment.objects.filter(
        student=student,
        fee_structure__exam_fee__gt=0,
        is_verified=True
    ).exists()
    
    return exam_payments

def generate_fee_breakdown(fee_structure):
    """Generate fee breakdown dictionary"""
    return {
        'tuition_fee': fee_structure.tuition_fee,
        'development_levy': fee_structure.development_levy,
        'exam_fee': fee_structure.exam_fee,
        'sports_fee': fee_structure.sports_fee,
        'other_charges': fee_structure.other_charges,
        'total': fee_structure.amount,
        'late_fee': fee_structure.late_fee if fee_structure.late_fee_applicable else 0,
        'total_with_late_fee': fee_structure.total_with_late_fee
    }