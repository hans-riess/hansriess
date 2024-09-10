import os

if os.getenv('DJANGO_ENV') == 'production':
    from .settings_production import *
else:
    from .settings_local import *