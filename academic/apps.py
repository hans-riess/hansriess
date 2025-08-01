# academic/apps.py

from django.apps import AppConfig

class AcademicConfig(AppConfig):
    """
    Configuration for the 'academic' app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academic'

    def ready(self):
        """
        This method is called when Django starts.
        We import our signals here to ensure they are registered.
        """
        import academic.signals