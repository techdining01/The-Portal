# core/context_processors.py
from django.conf import settings

def school_settings(request):
    """
    Inject school settings into templates.
    """
    return {
        'SCHOOL_NAME': getattr(settings, 'SCHOOL_NAME', ''),
        'SCHOOL_SLOGAN': getattr(settings, 'SCHOOL_SLOGAN', '')
    }
