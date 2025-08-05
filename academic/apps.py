# academic/apps.py

from django.apps import AppConfig

class AcademicConfig(AppConfig):
    """
    Configuration for the 'academic' app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academic'