from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("teacher-admin-profile/<int:user_id>/", views.teacheradminprofile, name="teacheradminprofile"),
    path("parent-profile/<int:user_id>/", views.parentprofile, name="parent_profile"),
    # path("profile/", views.view_profile, name="view_profile"),
    # path("edit-user/", views.edit_user, name="edit_profile"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("broadcast/send/", views.send_broadcast, name="send_broadcast"),
    path("notification/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),

    #user management
    path("approvals/", views.user_approval_list, name="user_approval_list"),
    path("approve/<int:user_id>/", views.approve_user, name="approve_user"),
    path("reject/<int:user_id>/", views.reject_user, name="reject_user"),
    path("pending/<int:user_id>/", views.pending_user, name="pending_user"),
    path('create/user', views.create_user, name='create_user'),
    # path("update-status/<int:user_id>/", views.update_user_status, name="update_user_status"),
    path("edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("manage/", views.manage_users, name="manage_users"),
    path("manage/load/", views.load_users, name="load_users"),  # AJAX
    path("manage/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    

    # Profile and dashboard
    path('profile/', views.profile, name='profile'),
    
    ]


from django.urls import path
from . import views

app_name = 'users'

urlpatterns += [
    # User management
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    path('users/<int:user_id>/reset-password/', views.user_reset_password_view, name='user_reset_password'),
    path('users/<int:user_id>/json/', views.user_detail_json_view, name='user_detail_json'),
    
    # Bulk actions
    path('users/bulk-action/', views.bulk_action_view, name='bulk_action'),
    path('users/export/', views.user_export_view, name='user_export'),
]


urlpatterns += [
    # Registration URLs
    path('register/', views.register_view, name='register'),
    path('register/student/', views.register_student_view, name='register_student'),
    path('register/parent/', views.register_parent_view, name='register_parent'),
    path('register/teacher/', views.register_teacher_view, name='register_teacher'),
    path('register/admin/', views.register_admin_view, name='register_admin'),
    
    # Login/Logout URLs (Django built-in or custom)
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Dashboard URLs
    path('student/dashboard/', views.student_dashboard_view, name='student_dashboard'),
    path('parent/dashboard/', views.parent_dashboard_view, name='parent_dashboard'),
    path('teacher/dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
]