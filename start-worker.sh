#!/bin/bash
cd src

# Wait for database to be ready
echo "Waiting for database..."
python -c "
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

# Start celery worker
exec celery -A config worker --loglevel=info --concurrency=2
