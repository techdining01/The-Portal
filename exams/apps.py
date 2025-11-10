from django.apps import AppConfig


class ExamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exams'

    def ready(self):
        try:
            import exams.receivers
        except Exception as e:
            print('Failed to import exams.receivers', e)
            
