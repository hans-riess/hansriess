# academic/signals.py

import subprocess
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Profile, Education, Experience, Grant, Talk, Service, Course, Reference

# List of all models that should trigger a CV update.
CV_MODELS = [
    Profile, Education, Experience, Grant, Talk, Service, Course, 
    Reference
]

# @receiver([post_save, post_delete], sender=CV_MODELS)
# def trigger_cv_generation(sender, instance, **kwargs):
#     """
#     Calls the management command to regenerate the CV PDF in the background.
    
#     This function is triggered whenever an instance of one of the CV_MODELS
#     is saved or deleted.
#     """
#     print(f"Signal received from {sender.__name__}. Triggering CV generation.")
    
#     # We use Popen to run the command in a non-blocking way.
#     # This prevents the user from having to wait for the PDF to compile
#     # during a request-response cycle in the admin panel.
#     subprocess.Popen(['python', 'manage.py', 'generate_cv'])