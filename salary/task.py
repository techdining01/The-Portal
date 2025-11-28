from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import TeacherSalary
from store.paystack import Paystack

@shared_task
def process_bulk_salary_payments(salary_ids):
    """
    Process multiple salary payments in background
    """
    salaries = TeacherSalary.objects.filter(id__in=salary_ids, payment_status='pending')
    
    for salary in salaries:
        try:
            # Process individual salary payment
            process_single_salary_payment.delay(salary.id)
        except Exception as e:
            # Log error and continue with next salary
            print(f"Error processing salary {salary.id}: {str(e)}")
            continue

@shared_task
def process_single_salary_payment(salary_id):
    """
    Process single salary payment
    """
    salary = TeacherSalary.objects.get(id=salary_id)
    
    # Initialize Paystack transfer (this would be adapted for transfers)
    paystack = Paystack()
    
    # For demonstration - in reality you'd use transfer API
    result = paystack.initialize_transaction(
        email=salary.teacher.email,
        amount=int(salary.net_salary * 100),
        reference=f"SALARY_{salary.id}",
        callback_url=f"{settings.SITE_URL}/salary/payment/verify/"
    )
    
    if result['status']:
        salary.payment_status = 'processing'
        salary.paystack_reference = result['data']['reference']
        salary.save()
        
        # Send notification email
        send_salary_processing_email.delay(salary.id)

@shared_task
def send_salary_processing_email(salary_id):
    """
    Send email notification for salary processing
    """
    salary = TeacherSalary.objects.get(id=salary_id)
    
    subject = f"Salary Payment Processing - {salary.payment_period}"
    message = f"""
    Dear {salary.teacher.get_full_name()},
    
    Your salary for {salary.payment_period} is being processed.
    Amount: ₦{salary.net_salary}
    Reference: {salary.paystack_reference}
    
    You will receive a confirmation once the payment is completed.
    
    Best regards,
    BrillsPay Administration
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [salary.teacher.email],
        fail_silently=False,
    )

@shared_task
def generate_monthly_salary_reports():
    """
    Generate monthly salary reports automatically
    """
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get last month
    today = timezone.now()
    first_day_last_month = today.replace(day=1) - timedelta(days=1)
    first_day_last_month = first_day_last_month.replace(day=1)
    last_day_last_month = today.replace(day=1) - timedelta(days=1)
    
    # Generate report data
    paid_salaries = TeacherSalary.objects.filter(
        payment_status='paid',
        paid_at__gte=first_day_last_month,
        paid_at__lte=last_day_last_month
    )
    
    total_paid = sum(salary.net_salary for salary in paid_salaries)
    total_teachers = paid_salaries.count()
    
    # Send report to admin
    subject = f"Monthly Salary Report - {first_day_last_month.strftime('%B %Y')}"
    message = f"""
    Monthly Salary Report for {first_day_last_month.strftime('%B %Y')}
    
    Total Teachers Paid: {total_teachers}
    Total Amount Paid: ₦{total_paid:,.2f}
    
    Breakdown:
    {''.join([f"- {s.teacher.get_full_name()}: ₦{s.net_salary:,.2f}\n" for s in paid_salaries])}
    
    Generated on: {today.strftime('%Y-%m-%d %H:%M')}
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        ['admin@brillspay.edu'],  # Admin email
        fail_silently=False,
    )