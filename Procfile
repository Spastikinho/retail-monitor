web: cd src && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread --log-file -
worker: cd src && celery -A config worker --loglevel=info --concurrency=2
beat: cd src && celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
release: cd src && python manage.py migrate --noinput && python manage.py collectstatic --noinput
