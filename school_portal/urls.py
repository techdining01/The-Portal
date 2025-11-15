from django.urls import path
from . import views

app_name = 'school_portal'

urlpatterns = [
    # path('', views.school_portal, name='home'),
    path("", views.school_portal, name="landing"),
    # path('home/', views.landing_page, name='landing_page'),
]
