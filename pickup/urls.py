from django.urls import path
from . import views

app_name = "pickup"

urlpatterns = [
path("pickup/generate/", views.create_pickup_view, name="pickup_generate"),
path("pickup/verify/<str:code>/", views.pickup_verify_view, name="pickup_verify"),
]