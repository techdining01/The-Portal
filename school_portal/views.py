
from django.shortcuts import render
from datetime import datetime


def school_portal(request):
     
    return render(request, 'school_portal/landing_page.html')