# signals kept for future extension; current webhook directly updates user
from django.dispatch import Signal


payment_successful = Signal()