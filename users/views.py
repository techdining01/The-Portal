from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Notification
from django.urls import reverse
from .forms import TeacherAdminForm, EditUserRegistrationForm, EditTeacherAdminForm, UserRegistrationForm, loginForm, UserProfileForm, ParentForm, LinkStudentForm
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST   
from exams.models import ActionLog  
from pickup.models import PickupAuthorization
import json


User = get_user_model()


@login_required
def profile(request):
    """User profile view"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    # Calculate total spent (you might want to implement this properly)
    total_spent = sum(order.total_amount for order in request.user.order_set.filter(status='paid'))
    
    context = {
        'form': form,
        'total_spent': total_spent,
    }
    return render(request, 'users/profile.html', context)


def signup_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.save() 
            user_id = user.id
            role = user.role
            if role in ['admin', 'teacher']:
                messages.success(request, f'{user.role.title()} account created successfully. Awaiting approval.')
                url = reverse('users:teacheradminprofile', kwargs={'user_id': user_id})
                return redirect(url)
            elif role == 'parent':
                messages.success(request, f'{user.role.title()} account created successfully. Awaiting approval.')
                url = reverse('users:parent_profile', kwargs={'user_id': user_id})
                return redirect(url)
            else:
                messages.success(request, "Registration successful. Please wait for approval.")
            return redirect("users:dashboard")
    else:
        form = UserRegistrationForm()
    return render(request, 'users/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = loginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user.approved == True:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name} 👋")
                return redirect('users:dashboard')
            else:
                messages.info(request, 'Ensure you have been approval by Admin')
        messages.error(request, "Invalid username or password.")
    else:
        form = loginForm()
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('users:login')



def teacheradminprofile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = TeacherAdminForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = user
            profile.save()
            if request.user.is_authenticated:
                messages.success(request, f'{user.role.title()} profile updated successfully. wait for approval')
                return redirect('users:dashboard')
            messages.success(request, f'{user.role.title()} profile created successfully. wait for approval')
            return redirect('users:login')
    else:
        form = TeacherAdminForm()


    context = {'form': form, 'user': user}

    return render(request, "users/teacheradminprofile.html", context )


def parentprofile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = ParentForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = user
            profile.save()
            if request.user.is_authenticated:
                messages.success(request, f'{user.role.title()} profile updated successfully. wait for approval')
                return redirect('users:dashboard')
            messages.success(request, f'{user.role.title()} profile created successfully. wait for approval')
            return redirect('users:login')
    else:
        form = ParentForm()


    context = {'form': form, 'user': user}

    return render(request, "users/parentprofile.html", context )


@login_required
def view_profile(request):
    """Read-only profile page for Student, Teacher, Admin."""
    return render(request, "users/view_profile.html", {"user": request.user})



@login_required
def edit_user(request, user_id):
    """Allow Student, Teacher, or Admin to update their profile."""

    user = get_object_or_404(User, id=user_id)

    # Pick form by role
    form_class = EditUserRegistrationForm if user.role == "student" else EditTeacherAdminForm

    if request.method == "POST":
        old_data = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
        form = form_class(request.POST, request.FILES, instance=user)
        if form.is_valid():
            updated_user = form.save()
            new_data = {
                "username": updated_user.username,
                "email": updated_user.email,
                "role": updated_user.role,
            }
            # Log the edit
            ActionLog.objects.create(
                user=request.user,
                action_type="Edit User",
                model_name="User",
                object_id=str(updated_user.id),
                details={"old": old_data, "new": new_data, "target": updated_user.username},
            )
            messages.success(request, "Profile updated successfully!")

                # Redirect back to dashboard
            if request.user.is_authenticated == "student":
                return redirect("exams:student_dashboard")
            elif request.user.is_authenticated == "teacher":
                return redirect("exams:teacher_dashboard")
            else:
                return redirect("exams:admin_dashboard")
    else:
        form = form_class(instance=user)


    return render(request, "users/edit_profile.html", {"form": form, "user": user})

            

def create_user(request):
    return redirect('users:signup')



def is_admin_or_superadmin(user):
    return user.role in ["admin", "superadmin"]


@login_required
@user_passes_test(is_admin_or_superadmin)
def user_approval_list(request):
    users = User.objects.exclude(role="superadmin")  # Exclude superadmins
    return render(request, "users/user_approval_list.html", {"users": users})


@login_required
@user_passes_test(is_admin_or_superadmin)
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = True
    user.save()
    messages.success(request, f"{user.username} has been approved ✅.")
    return redirect("users:user_approval_list")


@login_required
@user_passes_test(is_admin_or_superadmin)
def reject_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = False
    user.delete()
    messages.warning(request, f"{user.username} has been rejected ❌.")
    return redirect("users:user_approval_list")





########## VERSION 2 ################################################

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import (
    StudentRegistrationForm, ParentRegistrationForm,
    TeacherRegistrationForm, AdminRegistrationForm
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_GET
import csv
from django.http import HttpResponse
from .models import UserProfile, ParentProfile, StudentParentRelationship, Class


def register_view(request):
    """Main registration view with role selection"""
    if request.method == 'POST':
        role = request.POST.get('role', 'student')
        
        if role == 'student':
            form = StudentRegistrationForm(request.POST)
        elif role == 'parent':
            form = ParentRegistrationForm(request.POST)
        elif role == 'teacher':
            form = TeacherRegistrationForm(request.POST)
        else:
            form = None
        
        if form and form.is_valid():
            user = form.save()
            
            # No Auto-login after registration
            
            if user.approved == True:
                login(request, user)
                messages.success(
                    request,
                    f'Account created successfully! Welcome, {user.get_full_name()}!'
                )
                
                # Redirect based on role
                if role == 'student':
                    return redirect('users:student_dashboard')
                elif role == 'parent':
                    return redirect('users:parent_dashboard')
                elif role == 'teacher':
                    return redirect('users:teacher_dashboard')
            else:
                messages.success(
                    request,
                    f'Admin account created successfully for {user.get_full_name()}!'
                )
                return redirect('users:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = None
    
    context = {
        'form': form,
        'classes': Class.objects.all(),
    }
    
    return render(request, 'registration/register.html', context)

def register_student_view(request):
    """Direct student registration"""
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.is_approved == True:
                login(request, user)
                messages.success(request, 'Student account created successfully!')
                return redirect('users:student_dashboard')
    else:
        form = StudentRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Student Registration',
        'classes': Class.objects.all(),
    }
    
    return render(request, 'registration/simple_register.html', context)

def register_parent_view(request):
    """Direct parent registration"""
    if request.method == 'POST':
        form = ParentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Parent account created successfully!')
            return redirect('users:parent_dashboard')
    else:
        form = ParentRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Parent Registration',
    }
    
    return render(request, 'registration/simple_register.html', context)

def register_teacher_view(request):
    """Direct teacher registration"""
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Teacher account created successfully!')
            return redirect('users:teacher_dashboard')
    else:
        form = TeacherRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Teacher Registration',
    }
    
    return render(request, 'registration/simple_register.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def register_admin_view(request):
    """Admin registration (superuser only)"""
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Admin account created for {user.get_full_name()}')
            return redirect('users:user_list')
    else:
        form = AdminRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Admin Registration',
    }
    
    return render(request, 'registration/simple_register.html', context)


def is_admin_user(user):
    """Check if user is admin or superuser"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin_user)
def user_list_view(request):
    """User management list view with filtering and pagination"""
    
    # Get all users with profiles
    users = User.objects.select_related('userprofile').prefetch_related('userprofile__student_parent_relationships').all()
    
    # Apply filters
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    if role_filter:
        users = users.filter(userprofile__role=role_filter)
    
    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
        elif status_filter == 'suspended':
            users = users.filter(userprofile__suspended=True)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(userprofile__phone_number__icontains=search_query)
        )
    
    # Order by date joined (newest first)
    users = users.order_by('-date_joined')
    
    # Get statistics
    total_students = User.objects.filter(userprofile__role='student').count()
    total_parents = User.objects.filter(userprofile__role='parent').count()
    total_teachers = User.objects.filter(userprofile__role='teacher').count()
    total_active_users = User.objects.filter(is_active=True).count()
    
    # Get parent users for dropdown
    parent_users = User.objects.filter(userprofile__role='parent')
    
    # Pagination
    paginator = Paginator(users, 25)  # 25 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'total_students': total_students,
        'total_parents': total_parents,
        'total_teachers': total_teachers,
        'total_active_users': total_active_users,
        'parent_users': parent_users,
    }
    
    return render(request, 'store/admin/user_list.html', context)

@login_required
@user_passes_test(is_admin_user)
def user_create_view(request):
    """Create new user"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Set additional fields
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            
            # Create user profile
            user_profile = UserProfile.objects.create(
                user=user,
                role=request.POST.get('role', 'student'),
                phone_number=request.POST.get('phone', '')
            )
            
            # Handle student-specific fields
            if user_profile.role == 'student':
                user_profile.grade_level = request.POST.get('grade_level', '')
                user_profile.save()
                
                # Link parent if provided
                parent_id = request.POST.get('parent')
                if parent_id:
                    try:
                        parent_user = User.objects.get(id=parent_id)
                        StudentParentRelationship.objects.create(
                            student=user,
                            parent=parent_user,
                            relationship='parent'
                        )
                    except User.DoesNotExist:
                        pass
            
            messages.success(request, f'User {user.username} created successfully.')
            
            # Send welcome email if requested
            if request.POST.get('send_welcome'):
                send_welcome_email(user, form.cleaned_data.get('password1'))
            
            return redirect('admin:user_list')
    else:
        form = UserCreationForm()
    
    return render(request, 'store/admin/user_create.html', {'form': form})

@login_required
@user_passes_test(is_admin_user)
def user_edit_view(request, user_id):
    """Edit existing user"""
    user = get_object_or_404(User, id=user_id)
    user_profile = getattr(user, 'userprofile', None)
    
    if request.method == 'POST':
        # Update user fields
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.is_active = 'is_active' in request.POST
        
        if request.POST.get('password'):
            user.set_password(request.POST.get('password'))
        
        user.save()
        
        # Update user profile
        if user_profile:
            user_profile.role = request.POST.get('role', user_profile.role)
            user_profile.phone_number = request.POST.get('phone', user_profile.phone_number)
            user_profile.save()
        
        messages.success(request, f'User {user.username} updated successfully.')
        return redirect('admin:user_list')
    
    context = {
        'user': user,
        'user_profile': user_profile,
    }
    
    return render(request, 'store/admin/user_edit.html', context)

@login_required
@user_passes_test(is_admin_user)
@require_POST
def user_delete_view(request, user_id):
    """Delete user (AJAX endpoint)"""
    if request.user.id == user_id:
        return JsonResponse({
            'success': False,
            'error': 'You cannot delete your own account'
        })
    
    try:
        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'User {username} deleted successfully.'
        })
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        })

@login_required
@user_passes_test(is_admin_user)
@require_POST
def user_reset_password_view(request, user_id):
    """Send password reset email"""
    try:
        user = User.objects.get(id=user_id)
        # Generate reset token and send email
        # Implementation depends on your email setup
        
        return JsonResponse({
            'success': True,
            'message': 'Password reset email sent.'
        })
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        })

@login_required
@user_passes_test(is_admin_user)
@require_POST
def bulk_action_view(request):
    """Handle bulk actions"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    data = request.POST or json.loads(request.body)
    action = data.get('action')
    user_ids = data.get('user_ids', [])
    
    if not action or not user_ids:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    users = User.objects.filter(id__in=user_ids)
    
    if action == 'activate':
        users.update(is_active=True)
        message = 'Users activated successfully'
    elif action == 'deactivate':
        users.update(is_active=False)
        message = 'Users deactivated successfully'
    elif action == 'delete':
        # Don't allow deleting own account
        users = users.exclude(id=request.user.id)
        count = users.count()
        users.delete()
        message = f'{count} user(s) deleted successfully'
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    return JsonResponse({'success': True, 'message': message})

@login_required
@user_passes_test(is_admin_user)
def user_export_view(request):
    """Export users to CSV/Excel"""
    users = User.objects.select_related('userprofile').all()
    
    # Apply filters from request
    role_filter = request.GET.get('role')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    if role_filter:
        users = users.filter(userprofile__role=role_filter)
    
    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    export_format = request.GET.get('format', 'csv')
    
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Email', 'First Name', 'Last Name', 
            'Role', 'Phone', 'Status', 'Date Joined'
        ])
        
        for user in users:
            profile = getattr(user, 'userprofile', None)
            writer.writerow([
                user.username,
                user.email,
                user.first_name or '',
                user.last_name or '',
                profile.role if profile else '',
                profile.phone_number if profile else '',
                'Active' if user.is_active else 'Inactive',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    elif export_format == 'excel':
        # For Excel export, you might want to use a library like pandas or openpyxl
        # This is a simplified version
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="users.xlsx"'
        
        # Simplified - in production, use openpyxl or pandas
        import io
        import xlsxwriter
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Users')
        
        # Write headers
        headers = ['Username', 'Email', 'First Name', 'Last Name', 
                  'Role', 'Phone', 'Status', 'Date Joined']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, user in enumerate(users, start=1):
            profile = getattr(user, 'userprofile', None)
            data = [
                user.username,
                user.email,
                user.first_name or '',
                user.last_name or '',
                profile.role if profile else '',
                profile.phone_number if profile else '',
                'Active' if user.is_active else 'Inactive',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
            ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value)
        
        workbook.close()
        output.seek(0)
        response.write(output.read())
        
        return response
    
    else:
        return JsonResponse({'success': False, 'error': 'Invalid format'})

@login_required
@user_passes_test(is_admin_user)
def user_detail_json_view(request, user_id):
    """Return user details as JSON for AJAX requests"""
    try:
        user = User.objects.select_related('userprofile').get(id=user_id)
        profile = user.userprofile
        
        # Get parent info for students
        parent_info = None
        if profile.role == 'student':
            relationship = StudentParentRelationship.objects.filter(
                student=user
            ).first()
            if relationship:
                parent_info = {
                    'id': relationship.parent.id,
                    'name': relationship.parent.get_full_name(),
                    'email': relationship.parent.email
                }
        
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'is_active': user.is_active,
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'role': profile.role,
            'role_display': profile.get_role_display(),
            'phone': profile.phone_number,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
            'grade_level': getattr(profile, 'grade_level', ''),
            'registration_number': getattr(profile, 'registration_number', ''),
            'parent_name': parent_info['name'] if parent_info else None,
            'parent_id': parent_info['id'] if parent_info else None,
            'occupation': getattr(profile, 'occupation', ''),
            'emergency_contact': getattr(profile, 'emergency_contact', ''),
            'address': getattr(profile, 'address', ''),
        }
        
        return JsonResponse(data)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

# Helper function for sending welcome email
def send_welcome_email(user, password):
    """Send welcome email to new user"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f'Welcome to {settings.SITE_NAME}'
        message = f"""
        Hello {user.get_full_name() or user.username},
        
        Your account has been created successfully.
        
        Login details:
        Username: {user.username}
        Password: {password}
        
        You can login at: {settings.SITE_URL}/login/
        
        Please change your password after first login.
        
        Best regards,
        {settings.SITE_NAME} Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        
        return True
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return False


@login_required
def link_student_view(request):
    if request.method == 'POST':
        form = LinkStudentForm(request.POST)
        if form.is_valid():
            reg_number = form.cleaned_data['registration_number']
            try:
                student = User.objects.get(
                    registration_number=reg_number,
                    role='student'
                )
                
                # Check if student already has a parent linked
                if student.parents.filter(id=request.user.id).exists():
                    messages.warning(request, 'Student is already linked to your account.')
                else:
                    # Link student to parent
                    request.user.children.add(student)
                    messages.success(request, 
                        f'Successfully linked to student: {student.get_full_name()}')
                    
                    return redirect('profile')
                    
            except User.DoesNotExist:
                messages.error(request, 'Student not found.')
    else:
        form = LinkStudentForm()
    
    return render(request, 'registration/link_student.html', {'form': form})

@login_required
def unlink_student_view(request, student_id):
    if request.method == 'POST':
        try:
            student = User.objects.get(id=student_id, role='student')
            if student in request.user.children.all():
                request.user.children.remove(student)
                messages.success(request, 'Student unlinked successfully.')
            else:
                messages.error(request, 'Student not linked to your account.')
        except User.DoesNotExist:
            messages.error(request, 'Student not found.')
    
    return redirect('profile')

# Bulk linking view for admins
@user_passes_test(lambda u: u.is_admin)
def bulk_link_parent_student(request):
    if request.method == 'POST':
        parent_email = request.POST.get('parent_email')
        student_reg_numbers = request.POST.get('student_reg_numbers', '').split(',')
        
        try:
            parent = User.objects.get(email=parent_email, role='parent')
            students = User.objects.filter(
                registration_number__in=[rn.strip() for rn in student_reg_numbers],
                role='student'
            )
            
            for student in students:
                parent.children.add(student)
            
            messages.success(request, 
                f'Linked {students.count()} student(s) to parent {parent.email}')
                
        except User.DoesNotExist:
            messages.error(request, 'Parent not found.')
    
    return render(request, 'admin/bulk_link.html')


##########################################################################

@login_required
@user_passes_test(is_admin_or_superadmin)
def user_approval_list(request):
    users = User.objects.exclude(role="superadmin")  # Exclude superadmins
    return render(request, "users/user_approval_list.html", {"users": users})


@login_required
@user_passes_test(is_admin_or_superadmin)
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = True
    user.save()
    messages.success(request, f"{user.username} has been approved ✅.")
    return redirect("users:user_approval_list")


@login_required
@user_passes_test(is_admin_or_superadmin)
def reject_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = False
    user.delete()
    messages.warning(request, f"{user.username} has been rejected ❌.")
    return redirect("users:user_approval_list")


@login_required
@user_passes_test(is_admin_or_superadmin)
def pending_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = False
    user.save()
    messages.info(request, f"{user.username} is now pending ⏳.")
    return redirect("users:user_approval_list")


@login_required
def dashboard_redirect(request):
    if request.user.role == "superadmin":
        return redirect("exams:superadmin_dashboard")
    elif request.user.role == "admin":
        return redirect("exams:admin_dashboard")
    elif request.user.role == "teacher":
        return redirect("exams:teacher_dashboard")
    elif request.user.role == "student":
        return redirect("exams:student_dashboard")
    elif request.user.role == "parent":
        return redirect("pickup:parent_dashboard")
    else:
        messages.error(request, "Unknown role. Contact SuperAdmin.")
        return redirect("users:login")


@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    messages.success(request, "Notification marked as read ✅")
    return redirect("users:dashboard")


@login_required
def send_broadcast(request):
    if request.method == "POST":
        message = request.POST.get("message")
        sender = request.user

        # Decide recipients
        if sender.role == "admin":
            recipients = User.objects.filter(role__in=["teacher", "student"])
        elif sender.role == "teacher":
            recipients = User.objects.filter(role="student")
        else:
            messages.error(request, "You cannot send broadcasts.")
            return redirect("users:dashboard")

        # Create notifications
        for recipient in recipients:
            Notification.objects.create(
                sender=sender,
                recipient=recipient,
                message=message,
                role=recipient.role,
            )

        messages.success(request, "Broadcast sent successfully ✅")
    return redirect("users:dashboard")


from .models import User, UserStatusLog

def update_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    new_status = request.POST.get("status")  # "approve" / "reject" / "pending"

    if new_status not in ["approve", "reject", "pending"]:
        messages.error(request, "Invalid status")
        return redirect("users:manage_users")

    old_status = user.status  # assuming User model has a `status` field
    user.status = new_status
    user.save()

    # Log change
    UserStatusLog.objects.create(
        user=user,
        old_status=old_status,
        new_status=new_status,
        changed_by=request.user,
        changed_at=timezone.now()
    )

    messages.success(request, f"{user.username}'s status updated to {new_status}.")
    return redirect("users:manage_users")


@login_required
@user_passes_test(is_admin_or_superadmin)
def pending_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approved = False
    user.save()
    messages.info(request, f"{user.username} is now pending ⏳.")
    return redirect("users:user_approval_list")



def is_admin(user):
    return user.is_authenticated and (user.role in ['superadmin', 'admin'])


@login_required
@user_passes_test(is_admin)
def manage_users(request):
    """
    Renders main Manage Users page with AJAX support.
    """
    return render(request, "users/manage_users.html")


@login_required
@user_passes_test(is_admin)
def load_users(request):
    """
    Handles AJAX pagination and search
    """
    search = request.GET.get("search", "")
    page = request.GET.get("page", 1)

    users = User.objects.exclude(role="superadmin").order_by("-date_joined")

    if search:
        users = users.filter(username__icontains=search) | users.filter(first_name__icontains=search) | users.filter(last_name__icontains=search) | users.filter(email__icontains=search)

    page = Paginator(users, 10)  
    users_page = page.get_page(request.GET.get('page'))

    data = {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'student_class': str(u.student_class),
                "email": u.email,
                "role": u.role,
                "date_joined": u.date_joined.strftime("%d-%m-%Y %H:%M"),
            }
            for u in users_page
        ],
        "has_next": users_page.has_next(),
        "has_previous": users_page.has_previous(),
        "num_pages": page.num_pages,
        "current_page": users_page.number,
    }

    return JsonResponse(data)


@require_POST
def update_user(request, user_id):
    """Edit user details via AJAX"""
    user = get_object_or_404(User, id=user_id)

    old_data = {
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }

    username = request.POST.get("username")
    email = request.POST.get("email")
    role = request.POST.get("role")

    if username:
        user.username = username
    if email:
        user.email = email
    if role in dict(User.ROLE_CHOICES):
        user.role = role

    user.save()

    # Log action
    ActionLog.objects.create(
        user=request.user,
        action_type="Edited user",
        model_name="User",
        object_id=user.id,
        details={
            "old": old_data,
            "new": {"username": user.username, "email": user.email, "role": user.role},
        },
    )

    return JsonResponse({
        "success": True,
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.get_role_display(),
    })


@require_POST
def delete_user(request, user_id):
    """Delete user via AJAX"""
    user = get_object_or_404(User, id=user_id)
    if user.role == "superadmin":
        return JsonResponse({"success": False, "message": "Cannot delete superadmin"})
    
    user_data = {"username": user.username, "email": user.email, "role": user.role}

    user.delete()

    # Log action
    ActionLog.objects.create(
        user=request.user,
        action_type="Deleted user",
        model_name="User",
        object_id=user_id,
        details=user_data,
    )

    return JsonResponse({"success": True, "id": user_id})
