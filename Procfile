web: bash start.sh
worker: cd src && celery -A config worker --loglevel=info --concurrency=2
beat: cd src && celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
