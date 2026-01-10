#!/bin/bash
cd src

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings

# Wait for database to be ready and run a simple check
echo "Waiting for database..."
python -c "
import os
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
"

# Start celery beat
exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
