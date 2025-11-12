from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self):
        # import signals so they are registered
        try:
            import payments.signals  # noqa
        except Exception:
            pass
    
   