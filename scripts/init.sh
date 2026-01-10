#!/bin/bash
# Initialize the application after first deployment

set -e

echo "Running migrations..."
python src/manage.py migrate

echo "Setting up initial data..."
python src/manage.py setup_initial_data

echo "Creating superuser if not exists..."
python src/manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created: admin / admin')
else:
    print('Superuser already exists')
EOF

echo "Collecting static files..."
python src/manage.py collectstatic --noinput

echo "Done!"
