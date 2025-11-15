import os
from django.apps import AppConfig

class CoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cores'

    # def ready(self):
    #     from django.conf import settings
    #     from cores.tasks import start_scheduler

    #     if settings.DEBUG:
    #         # Prevent double scheduler during auto-reload
    #         if os.environ.get("RUN_MAIN") != "true":
    #             return

    #     start_scheduler()
