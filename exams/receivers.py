# from django.dispatch import receiver
# # from payments.signals import payment_successful
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from .models import ActionLog  

# User = get_user_model()

# @receiver(payment_successful)
# def handle_payment_success(sender, student_id, invoice_id, payment_id, gateway, amount, raw_response, **kwargs):
  
#     try:
#         user = User.objects.filter(pk=student_id).first()
#     except Exception:
#         user = None

#     # Create an action log entry 
#     try:
#         if user:
#             ActionLog.objects.create(
#                 user=user,
#                 action_type='approved',  # you can define a new type 'payment'
#                 description=f'Payment received for invoice {invoice_id} (payment {payment_id}) via {gateway}',
#                 model_name='Invoice',
#                 object_id=str(invoice_id),
#                 details={'payment_id': payment_id, 'amount': amount}
#             )
#     except Exception as e:
#         print("ActionLog creation failed:", e)

#     # OPTIONAL: Unlock CBT for the user — example only
#     # Uncomment and adapt to your model if you have a flag or permission to toggle.
#     #
#     # if user and hasattr(user, 'can_take_exam'):
#     #     user.can_take_exam = True
#     #     user.save(update_fields=['can_take_exam'])
#     #
#     # Or toggle 'approved' (if your business logic uses approved to allow exams):
#     # if user and hasattr(user, 'approved'):
#     #     user.approved = True
#     #     user.save(update_fields=['approved'])

#     # You can also send an email/SMS receipt here.
