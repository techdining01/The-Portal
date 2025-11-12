
from django.shortcuts import render

def home(request):
    return render(request, 'school_portal/home.html')
