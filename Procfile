release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn hansriess.wsgi --log-file -
