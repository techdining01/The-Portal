from django.apps import AppConfig

class CoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cores'

    # def ready(self):
    #     from django.db.models.signals import post_migrate
    #     from .tasks import start_scheduler
    #     post_migrate.connect(lambda **kwargs: start_scheduler(), sender=self)
