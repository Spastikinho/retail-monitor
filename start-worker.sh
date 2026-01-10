#!/bin/bash
set -e

cd src

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings

echo "Starting Celery Worker..."
echo "DATABASE_URL is set: ${DATABASE_URL:+yes}"
echo "CELERY_BROKER_URL is set: ${CELERY_BROKER_URL:+yes}"

# Wait for database to be ready
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
"

echo "Starting Celery Worker..."
# Start celery worker
exec celery -A config worker --loglevel=info --concurrency=2
