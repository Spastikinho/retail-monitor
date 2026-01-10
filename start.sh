#!/bin/bash
cd src
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Create or update admin user - always run
echo "Setting up admin user..."
python << 'PYTHON_SCRIPT'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('ADMIN_USERNAME', 'admin')
password = os.environ.get('ADMIN_PASSWORD', 'SIMpiter5')
email = os.environ.get('ADMIN_EMAIL', '')
print(f'Creating/updating user: {username}')
try:
    user = User.objects.filter(username=username).first()
    if user:
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        print(f'Updated password for: {username}')
    else:
        user = User.objects.create_superuser(username=username, email=email, password=password)
        print(f'Created admin user: {username}')
except Exception as e:
    print(f'Error setting up admin: {e}')
PYTHON_SCRIPT

# Setup initial data (retailers, etc.)
echo "Setting up initial data (retailers)..."
python manage.py setup_initial_data --verbosity=2 || echo "Initial data setup failed"

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --worker-class gthread --log-file -
