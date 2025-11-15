
from django.shortcuts import render
from datetime import datetime


def school_portal(request):
    date = str
   
    return render(request, 'school_portal/landing_page.html', {'date': date})