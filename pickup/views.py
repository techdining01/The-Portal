import hmac, hashlib, json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from .models import PickupAuthorization
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

User = get_user_model()

# ---------- PICKUP VIEWS (AJAX friendly) ----------
def create_pickup_view(request):
    """
    POST (AJAX): { student_reg, bearer_name, bearer_phone, optionally signature (file) }
    Returns JSON with code and verify_url,
    """
    if request.method != "POST":
        return JsonResponse({"error":"POST only"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"error":"Authentication required"}, status=403)

    student_reg = request.POST.get("student_reg")
    bearer_name = request.POST.get("bearer_name")
    bearer_phone = request.POST.get("bearer_phone")

    if not (student_reg and bearer_name and bearer_phone):
        return JsonResponse({"error":"Missing fields"}, status=400)

    try:
        student = User.objects.get(registration_number=student_reg, role="student")
    except User.DoesNotExist:
        return JsonResponse({"error":"Student not found"}, status=404)

    pick = PickupAuthorization(parent=request.user, student=student, bearer_name=bearer_name, bearer_phone=bearer_phone)
    # signature image (optional)
    if request.FILES.get("signature"):
        pick.signature_image = request.FILES.get("signature")
    pick.save()
    verify_url = request.build_absolute_uri(reverse("shop:pickup_verify", args=[pick.code]))
    return JsonResponse({"ok": True, "code": pick.code, "verify_url": verify_url})

def pickup_verify_view(request, code):
    """
    GET -> show pickup record
    POST (AJAX) -> admin verifies (must be can_approve)
    """
    obj = get_object_or_404(PickupAuthorization, code=code)
    if request.method == "POST":
        if not request.user.is_authenticated or not getattr(request.user, "can_approve", lambda: False)():
            return JsonResponse({"error":"Permission denied"}, status=403)
        obj.verified_at = timezone.now()
        obj.verified_by = request.user
        obj.save()
        return JsonResponse({"ok": True, "verified_at": obj.verified_at.isoformat()})
    # GET: return html partial or data
    data = {
        "parent": obj.parent.get_full_name() or obj.parent.username,
        "student": str(obj.student),
        "bearer_name": obj.bearer_name,
        "bearer_phone": obj.bearer_phone,
        "code": obj.code,
        "verified": bool(obj.verified_at),
        "expires_at": obj.expires_at.isoformat() if obj.expires_at else None
    }
    return JsonResponse(data)


# def parent_dashboard(request):
#     students = User.objects.filter(role='student')  
#     active_pickups = PickupAuthorization.objects.filter(
#         parent=request.user, 
#         expires_at__gte=timezone.now()
#     ).order_by('-created_at')

#     user = request.user
#     if user.role  == 'parent':
#         # Parent dashboard
#         children = user.children.all()
#         recent_orders = user.order_set.order_by('-created_at')[:5]
       
#     context = { 
#         'children': children,
#         'recent_orders': recent_orders,
#         'students': students,
#         'active_pickups': active_pickups,
#         'verified_pickups': active_pickups.filter(verified_at__isnull=False),
#         'pending_pickups': active_pickups.filter(verified_at__isnull=True),
#     }
#     return render(request, 'pickup/parent_dashboard.html', context)



User = get_user_model()

@login_required
def parent_dashboard(request):
    """Mobile-first parent dashboard with pickup management"""
    # Get students associated with this parent
    # Adjust this query based on your user relationships
    students = User.objects.filter(
        role='student', 
        # Add your relationship logic here, for example:
        # parent=request.user or family=request.user.family
    )
    
    # Get active pickups for this parent
    active_pickups = PickupAuthorization.objects.filter(
        parent=request.user,
        expires_at__gte=timezone.now()
    ).order_by('-created_at')
    
    context = {
        'students': students,
        'active_pickups': active_pickups,
        'verified_pickups': active_pickups.filter(verified_at__isnull=False),
        'pending_pickups': active_pickups.filter(verified_at__isnull=True),
    }
    return render(request, 'pickup/parent_dashboard.html', context)


@login_required
@require_POST
def create_pickup_view(request):
    """Create pickup authorization - FIXED with proper user handling"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=403)
    
    student_reg = request.POST.get("student_reg")
    bearer_name = request.POST.get("bearer_name")
    bearer_phone = request.POST.get("bearer_phone")

    if not (student_reg and bearer_name and bearer_phone):
        return JsonResponse({"error": "Missing fields"}, status=400)

    try:
        student = User.objects.get(registration_number=student_reg, role="student")
    except User.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)

    # Create pickup with logged-in user as parent
    pick = PickupAuthorization(
        parent=request.user, 
        student=student, 
        bearer_name=bearer_name, 
        bearer_phone=bearer_phone
    )
    
    # signature image (optional)
    if request.FILES.get("signature"):
        pick.signature_image = request.FILES.get("signature")
    
    pick.save()
    verify_url = request.build_absolute_uri(reverse("pickup:pickup_verify", args=[pick.code]))
    
    return JsonResponse({
        "ok": True, 
        "code": pick.code, 
        "verify_url": verify_url,
        "expires_at": pick.expires_at.isoformat()
    })




# # ---------- PAYSTACK WEBHOOK with HMAC verification ----------
# @csrf_exempt
# def paystack_webhook(request):
#     """
#     Handle Paystack webhooks. Verify signature using HMAC SHA512.
#     Paystack sends header 'x-paystack-signature' (confirm with Paystack docs).
#     """
#     payload = request.body
#     signature = request.headers.get("x-paystack-signature") or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
#     # verify signature
#     expected_sig = None
#     if signature and settings.PAYSTACK_SECRET_KEY:
#         computed = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
#         expected_sig = computed
#         if not hmac.compare_digest(computed, signature):
#             # signature mismatch
#             return HttpResponseForbidden("Invalid signature")
#     # parse payload
#     try:
#         data = json.loads(payload.decode("utf-8"))
#     except Exception:
#         data = {"raw": payload.decode("utf-8", errors="ignore")}

#     # backup raw payload
#     reference = data.get("data", {}).get("reference") or data.get("reference")
#     tb = TransactionBackup.objects.create(paystack_reference=reference, raw_payload=data)
#     # handle charge.success event
#     event = data.get("event")
#     if event == "charge.success" or data.get("data", {}).get("status") == "success":
#         ref = data.get("data", {}).get("reference")
#         order = Order.objects.filter(reference=ref).first()
#         if order:
#             order.status = "paid"
#             order.paid_at = timezone.now()
#             order.paystack_payment_ref = data.get("data", {}).get("reference")
#             order.save()
#             tb.order = order
#             tb.verified = True
#             tb.save()
#             # create Receipt record + StudentPurchase records
#             html = render_to_string("shop/receipt_partial.html", {"order": order})
#             receipt = Receipt.objects.create(order=order, html_snapshot=html)
#             # create StudentPurchase entries
#             for it in order.order_items.all():
#                 if it.student:
#                     StudentPurchase.objects.create(order_item=it, student=it.student)
#     return JsonResponse({"status":"ok"})

# # ---------- RECEIPT VIEW (shareable & PDF) ----------
# def receipt_view(request, slug):
#     order = get_object_or_404(Order, receipt_slug=slug)
#     # Anyone with link can view (shareable)
#     html = render_to_string("shop/receipt_full.html", {"order": order, "ui_name": "BrillsPay", "request": request})
#     # Save snapshot if no Receipt exists
#     if not hasattr(order, "receipt"):
#         Receipt.objects.create(order=order, html_snapshot=html)
#     if request.GET.get("pdf") == "1":
#         # Use WeasyPrint if available to generate a PDF; fallback to HTML
#         try:
#             from weasyprint import HTML
#             pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
#             response = HttpResponse(pdf, content_type='application/pdf')
#             response['Content-Disposition'] = f'attachment; filename=receipt-{order.reference}.pdf'
#             return response
#         except Exception:
#             return HttpResponse(html)
#     return HttpResponse(html)

# # ---------- PURCHASE HISTORY ----------
# def parent_purchase_history(request):
#     """Parent or admin can view all orders placed by the parent"""
#     if not request.user.is_authenticated:
#         return redirect(settings.LOGIN_URL)
#     orders = Order.objects.filter(parent=request.user).order_by("-created_at")
#     return render(request, "shop/purchase_history_parent.html", {"orders": orders, "ui_name":"BrillsPay"})

# def student_purchase_history(request, student_reg):
#     """View purchases for a student by registration number (admin or parent)"""
#     # Allow parent or admin only
#     if not request.user.is_authenticated:
#         return redirect(settings.LOGIN_URL)
#     try:
#         student = User.objects.get(registration_number=student_reg, role="student")
#     except User.DoesNotExist:
#         return HttpResponse("Student not found", status=404)
#     # parent check: allow if request.user is parent of student (parent_email or next_of_kin etc) OR admin
#     is_admin = getattr(request.user, "can_approve", lambda: False)()
#     if not is_admin:
#         # here we allow any logged parent with parent_email matching user's email OR if user is the parent_name
#         if not (request.user.email and request.user.email == student.parent_email):
#             return HttpResponseForbidden("Not allowed")
#     purchases = StudentPurchase.objects.filter(student=student).select_related("order_item__product", "order_item__order").order_by("-created_at")
#     return render(request, "shop/purchase_history_student.html", {"student": student, "purchases": purchases})


