from django.urls import path
from . import views

app_name = 'school_portal'

urlpatterns = [
    path("", views.school_portal, name="landing_page"),
    path('about/', views.about, name='about'),
    
]