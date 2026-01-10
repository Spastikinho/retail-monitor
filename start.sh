#!/bin/bash
cd src
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Create or update admin user if credentials are set
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Setting up admin user..."
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
user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True})
user.set_password(password)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()
if created:
    print(f'Created admin user: {username}')
else:
    print(f'Updated password for admin user: {username}')
"
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --worker-class gthread --log-file -
