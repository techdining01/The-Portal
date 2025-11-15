from django.urls import path
from . import views

app_name = 'cores'

urlpatterns = [
    path('backup/', views.backup_database, name='backup_database'),
    path('restore/', views.restore_database, name='restore_database'),
    path('session-expired/', views.session_expired, name='session_expired'),    
]
