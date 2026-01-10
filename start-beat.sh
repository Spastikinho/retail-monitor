#!/bin/bash
set -e

cd src

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings

echo "Starting Celery Beat..."
echo "DATABASE_URL is set: ${DATABASE_URL:+yes}"
echo "CELERY_BROKER_URL is set: ${CELERY_BROKER_URL:+yes}"

# Wait for database to be ready and run a simple check
echo "Waiting for database..."
python -c "
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import connection
import time

for i in range(30):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        print('Database is ready!')
        break
    except Exception as e:
        print(f'Waiting for database... ({e})')
        time.sleep(2)
else:
    print('ERROR: Could not connect to database after 30 attempts')
    sys.exit(1)

# Check if django_celery_beat tables exist
try:
    with connection.cursor() as cursor:
        cursor.execute(\"SELECT COUNT(*) FROM django_celery_beat_periodictask\")
        count = cursor.fetchone()[0]
        print(f'django_celery_beat tables exist, {count} periodic tasks found')
except Exception as e:
    print(f'WARNING: django_celery_beat tables may not exist: {e}')
    print('Run migrations on the web service first')
"

echo "Starting Celery Beat scheduler..."
# Start celery beat
exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
