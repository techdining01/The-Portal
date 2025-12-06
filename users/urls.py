from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    
    # Authentication
    # path('signup/', views.signup_view, name='signup'),
    # path('login/', views.login_view, name='login'),
    # path('logout/', views.logout_view, name='logout'),
    # # path("teacher-admin-profile/<int:user_id>/", views.teacheradminprofile, name="teacheradminprofile"),
    # path("parent-profile/<int:user_id>/", views.parentprofile, name="parent_profile"),
    # # path("profile/", views.view_profile, name="view_profile"),
    # # path("edit-user/", views.edit_user, name="edit_profile"),
    # path("dashboard/", views.dashboard_redirect, name="dashboard"),
    # path("broadcast/send/", views.send_broadcast, name="send_broadcast"),
    # path("notification/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),

    # #user management
    # path("approvals/", views.user_approval_list, name="user_approval_list"),
    # path("approve/<int:user_id>/", views.approve_user, name="approve_user"),
    # path("reject/<int:user_id>/", views.reject_user, name="reject_user"),
    # path("pending/<int:user_id>/", views.pending_user, name="pending_user"),
    # path('create/user', views.create_user, name='create_user'),
    # # path("update-status/<int:user_id>/", views.update_user_status, name="update_user_status"),
    # path("edit/<int:user_id>/", views.edit_user, name="edit_user"),
    # path("manage/", views.manage_users, name="manage_users"),
    # path("manage/load/", views.load_users, name="load_users"),  # AJAX
    # path("manage/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    

    # # Profile and dashboard
    # path('profile/', views.profile, name='profile'),
    
    ]


from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'store'

urlpatterns = [
   
    # ==================== AUTHENTICATION ====================
    path('login/', auth_views.LoginView.as_view(
        template_name='store/auth/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='store:landing'), name='logout'),
    path('register/parent/', views.ParentRegistrationView.as_view(), name='register_parent'),
    path('register/student/', views.StudentRegistrationView.as_view(), name='register_student'),
      
    # ==================== AJAX ENDPOINTS ====================
    path('ajax/students/', views.ajax_student_list, name='ajax_student_list'),
    
    # ==================== USER PROFILE ====================
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # ==================== PASSWORD RESET ====================
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='store/auth/password_reset.html',
             email_template_name='store/auth/password_reset_email.html',
             subject_template_name='store/auth/password_reset_subject.txt',
             success_url=reverse_lazy('store:password_reset_done')
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='store/auth/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='store/auth/password_reset_confirm.html',
             success_url=reverse_lazy('store:password_reset_complete')
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='store/auth/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]

# Error handlers
handler404 = 'store.views.handler404'
handler500 = 'store.views.handler500'
handler403 = 'store.views.handler403'
handler400 = 'store.views.handler400'