from django.urls import path
from . import views

app_name = "pickup"

urlpatterns = [
    path("pickup/generate/", views.create_pickup_view, name="pickup_generate"),
    path("verify/<str:code>/", views.pickup_verify_view, name="pickup_verify"),
    
    path('parent-dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('create/', views.create_pickup_view, name='create_pickup'),
    path('verify/<str:code>/', views.pickup_verify_view, name='pickup_verify'),

]

