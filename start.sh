#!/bin/bash
cd src
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Create admin user if credentials are set and user doesn't exist
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Checking admin user..."
    python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('ADMIN_USERNAME')
password = os.environ.get('ADMIN_PASSWORD')
email = os.environ.get('ADMIN_EMAIL', '')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Created admin user: {username}')
else:
    print(f'Admin user {username} already exists')
"
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --worker-class gthread --log-file -
