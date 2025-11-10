from django.dispatch import Signal

# Sent after a successful payment is recorded.
# receiver will receive kwargs: student_id, invoice_id, payment_id, gateway, amount, raw_response
payment_successful = Signal("student_id", "invoice_id", "payment_id",
                     "gateway", "amount", "raw_response")
