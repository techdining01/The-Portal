from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import TeacherSalary, SalaryPayment
from store.paystack import Paystack
import json

def is_admin(user):
    return user.role in ['admin', 'superadmin']

@login_required
@user_passes_test(is_admin)
def salary_dashboard(request):
    pending_salaries = TeacherSalary.objects.filter(payment_status='pending')
    paid_salaries = TeacherSalary.objects.filter(payment_status='paid')
    
    context = {
        'pending_salaries': pending_salaries,
        'paid_salaries': paid_salaries,
        'total_pending': sum(salary.net_salary for salary in pending_salaries),
        'total_paid': sum(salary.net_salary for salary in paid_salaries),
    }
    return render(request, 'salary/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def process_salary_payment(request, salary_id):
    salary = get_object_or_404(TeacherSalary, id=salary_id)
    
    if request.method == 'POST':
        # Initialize Paystack transfer
        paystack = Paystack()
        
        # Note: Paystack transfers require additional configuration
        # This is a simplified version
        result = paystack.initialize_transaction(
            email=salary.teacher.email,
            amount=int(salary.net_salary * 100),
            reference=f"SALARY_{salary.id}",
            callback_url=request.build_absolute_uri('/salary/payment/verify/')
        )
        
        if result['status']:
            salary.payment_status = 'processing'
            salary.paystack_reference = result['data']['reference']
            salary.save()
            
            # Create payment record
            SalaryPayment.objects.create(
                teacher_salary=salary,
                paystack_reference=result['data']['reference'],
                amount=salary.net_salary
            )
            
            return JsonResponse({
                'status': 'success',
                'authorization_url': result['data']['authorization_url']
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Payment initialization failed'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@require_POST
def salary_webhook(request):
    """
    Webhook for salary payment verification
    """
    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'transfer.success':
            data = payload.get('data')
            reference = data.get('reference')
            
            try:
                payment = SalaryPayment.objects.get(paystack_reference=reference)
                payment.payment_status = 'paid'
                payment.paid_at = data.get('createdAt')
                payment.gateway_response = json.dumps(data)
                payment.save()
                
                # Update teacher salary record
                payment.teacher_salary.payment_status = 'paid'
                payment.teacher_salary.paid_at = data.get('createdAt')
                payment.teacher_salary.save()
                
                return JsonResponse({'status': 'success'})
            except SalaryPayment.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)
        
        return JsonResponse({'status': 'ignored'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)