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
    
    return render(request, 'store/profile/view.html', context)


@login_required
def profile_edit(request):
    """Edit user profile"""
    user = request.user
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('store:profile_view')
    else:
        user_form = UserProfileForm(instance=user)
    
    context = {'user_form': user_form}
    return render(request, 'store/profile/edit.html', context)


@login_required
def change_password(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('store:profile_view')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {'form': form}
    return render(request, 'store/profile/change_password.html', context)

 
# ==================== REGISTRATION VIEWS ====================

class ParentRegistrationView(CreateView):
    """Parent registration view"""
    form_class = ParentRegistrationForm
    template_name = 'store/auth/register_parent.html'
    success_url = reverse_lazy('store:login')
    
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
    template_name = 'store/auth/register_student.html'
    success_url = reverse_lazy('store:login')
    
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
        'text': f'{s.get_full_name()} - {s.admission_number} ({s.current_class})'
    } for s in students]
    
    return JsonResponse({'results': data})