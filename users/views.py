from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F, DecimalField
from django.db.models.functions import TruncMonth, TruncYear, TruncDay
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import update_session_auth_hash
from .forms import *
from .models import *
from django.contrib import messages
from django.http import JsonResponse
from .forms import PasswordChangeForm



##================== REGISTRATION VIEWS ====================


# users/views.py
from django.views.generic import TemplateView, CreateView, View
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from users.models import User, Student, Parent, Teacher, Staff, StudentParent
from users.forms import ParentRegistrationForm, StudentRegistrationForm
from exams.models import Class

User = get_user_model()

class RegisterView(TemplateView):
    """Main registration page with both parent and student forms"""
    template_name = 'users/registration/register.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add forms to context
        context['parent_form'] = ParentRegistrationForm()
        context['student_form'] = StudentRegistrationForm()
        
        # Get school name from settings
        from django.conf import settings
        context['SCHOOL_NAME'] = getattr(settings, 'SCHOOL_NAME', 'My School')
        
        return context
    
    def post(self, request, *args, **kwargs):
        user_type = request.POST.get('user_type', 'parent')
        
        if user_type == 'parent':
            form = ParentRegistrationForm(request.POST)
            success_url = reverse_lazy('users:login')
        else:
            form = StudentRegistrationForm(request.POST)
            success_url = reverse_lazy('users:login')
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    
                    if user_type == 'parent':
                        # Additional parent setup
                        self.setup_parent_account(user, form.cleaned_data)
                        messages.success(request, 'Parent account created successfully! Please login.')
                    else:
                        # Additional student setup
                        self.setup_student_account(user, form.cleaned_data)
                        messages.success(request, 'Student account created successfully! Please login.')
                
                return redirect(success_url)
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
                return self.render_to_response(self.get_context_data(form=form))
        else:
            messages.error(request, 'Please correct the errors below.')
            return self.render_to_response(self.get_context_data(form=form))
    
    def setup_parent_account(self, user, cleaned_data):
        """Setup parent account with linked students"""
        # Create parent profile
        parent = Parent.objects.create(
            user=user,
            phone=cleaned_data.get('phone', ''),
            relationship=cleaned_data.get('relationship', 'guardian'),
            occupation=cleaned_data.get('occupation', ''),
            address=cleaned_data.get('address', ''),
            is_primary=True
        )
        
        # Link selected students
        student_ids = cleaned_data.get('student_ids', [])
        if student_ids:
            students = Student.objects.filter(id__in=student_ids)
            parent.students.set(students)
            
            # Create StudentParent relationships
            for student in students:
                StudentParent.objects.create(
                    student=student,
                    parent=parent,
                    is_primary_guardian=True,
                    can_pickup=True
                )
    
    def setup_student_account(self, user, cleaned_data):
        """Setup student account"""
        # Get or create student record
        admission_number = cleaned_data.get('admission_number')
        
        if admission_number:
            try:
                student = Student.objects.get(admission_number=admission_number)
                student.user_account = user
                student.save()
            except Student.DoesNotExist:
                # Create new student record if not found
                student = Student.objects.create(
                    admission_number=admission_number,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    date_of_birth=cleaned_data.get('date_of_birth'),
                    gender=cleaned_data.get('gender', 'M'),
                    student_class=cleaned_data.get('student_class'),
                    user_account=user
                )

    
# users/api_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from users.models import Student
from exams.models import Class

@require_GET
def student_search_api(request):
    """API endpoint for searching students"""
    query = request.GET.get('q', '')
    
    students = Student.objects.filter(is_active=True)
    
    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(admission_number__icontains=query)
        )
    
    # Limit results
    students = students[:20]
    
    data = {
        'students': [
            {
                'id': student.id,
                'name': student.get_full_name(),
                'admission_no': student.admission_number,
                'class_name': str(student.student_class) if student.student_class else '',
                'class_id': student.student_class.id if student.student_class else None,
                'has_account': bool(student.user_account)
            }
            for student in students
        ]
    }
    
    return JsonResponse(data)

@require_GET
def class_list_api(request):
    """API endpoint for getting class list"""
    classes = Class.objects.filter(is_active=True)
    
    data = {
        'classes': [
            {
                'id': cls.id,
                'name': cls.name,
                'level': cls.grade_level,
            }
            for cls in classes
        ]
    }
    
    return JsonResponse(data)

##================== PROFILE VIEWS ====================

@login_required
def profile_view(request):
    """User profile view"""
    context = {}
    
    if request.user.role == 'parent':
        try:
            parent = request.user.parent_profile
            context['parent'] = parent
            context['students'] = parent.students.all()
        except Parent.DoesNotExist:
            pass
    
    elif request.user.role == 'student':
        try:
            student = request.user.student
            context['student'] = student
            context['parents'] = student.parents.all()
        except Student.DoesNotExist:
            pass
    
    elif request.user.role == 'teacher':
        try:
            teacher = request.user.teacher_profile
            context['teacher'] = teacher
        except Teacher.DoesNotExist:
            pass
    
    elif request.user.role == 'staff':
        try:
            staff = request.user.staff_profile
            context['staff'] = staff
        except Staff.DoesNotExist:
            pass
    
    return render(request, 'users/profile/view.html', context)


@login_required
def profile_edit(request):
    """Edit user profile"""
    user = request.user
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('users:profile_view')
    else:
        user_form = UserProfileForm(instance=user)
    
    context = {'user_form': user_form}
    return render(request, 'users/profile/edit.html', context)


@login_required
def change_password(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:profile_view')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {'form': form}
    return render(request, 'users/profile/change_password.html', context)

 
# ==================== REGISTRATION VIEWS ====================

class ParentRegistrationView(CreateView):
    """Parent registration view"""
    form_class = ParentRegistrationForm
    template_name = 'users/auth/register_parent.html'
    success_url = reverse_lazy('users:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Registration successful! Please login to continue.'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Parent Registration'
        return context


class StudentRegistrationView(CreateView):
    """Student registration view"""
    form_class = StudentRegistrationForm
    template_name = 'users/auth/register_student.html'
    success_url = reverse_lazy('users:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Registration successful! Please login to continue.'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Student Registration'
        return context


# ==================== API & AJAX VIEWS ====================

@login_required
def ajax_student_list(request):
    """AJAX endpoint for student search"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    query = request.GET.get('q', '')
    user = request.user
    
    students = Student.objects.none()
    
    if user.role == 'parent':
        try:
            parent = user.parent_profile
            students = parent.students.filter(
                Q(admission_number__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )[:10]
        except Parent.DoesNotExist:
            pass
    
    elif user.role == 'admin' or user.role == 'staff':
        students = Student.objects.filter(
            Q(admission_number__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )[:10]
    
    data = [{
        'id': s.id,
        'text': f'{s.get_full_name()} - {s.admission_number} ({s.student_class})'
    } for s in students]
    
    return JsonResponse({'results': data})