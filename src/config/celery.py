"""
Celery configuration for Retail Monitor project.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('retail_monitor')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


# Celery Beat Schedule
# These are defaults; the actual schedule is managed via django-celery-beat
# in the database, allowing dynamic changes through Django Admin.
app.conf.beat_schedule = {
    # Monthly price scraping - runs on the 1st of each month at 6:00 AM Moscow
    'monthly-price-scrape': {
        'task': 'apps.scraping.tasks.scheduled_monthly_scrape',
        'schedule': crontab(hour=6, minute=0, day_of_month=1),
        'options': {'queue': 'scraping'},
    },
    # Monthly review scraping - runs on the 1st of each month at 7:00 AM Moscow
    'monthly-review-scrape': {
        'task': 'apps.scraping.tasks.scrape_all_reviews',
        'schedule': crontab(hour=7, minute=0, day_of_month=1),
        'options': {'queue': 'scraping'},
    },
    # Update session statistics - runs every hour
    'update-session-stats-hourly': {
        'task': 'apps.scraping.tasks.cleanup_stale_sessions',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    # Monthly review analysis - runs on the 2nd of each month at 6:00 AM
    # (after review scraping completes on the 1st)
    'monthly-review-analysis': {
        'task': 'apps.analytics.tasks.generate_all_analyses',
        'schedule': crontab(hour=6, minute=0, day_of_month=2),
        'options': {'queue': 'analytics'},
    },
    # Process unprocessed reviews for topic extraction - daily
    'daily-topic-extraction': {
        'task': 'apps.analytics.tasks.process_unprocessed_reviews',
        'schedule': crontab(hour=3, minute=0),  # 3:00 AM daily
        'options': {'queue': 'analytics'},
    },
    # Deliver pending alerts - every 5 minutes
    'deliver-pending-alerts': {
        'task': 'apps.alerts.tasks.deliver_pending_alerts',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'alerts'},
    },
    # Cleanup old alert events - weekly
    'cleanup-old-alerts': {
        'task': 'apps.alerts.tasks.cleanup_old_events',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Sunday 4:00 AM
        'options': {'queue': 'alerts'},
    },
}

# Task routing
app.conf.task_routes = {
    'apps.scraping.tasks.*': {'queue': 'scraping'},
    'apps.analytics.tasks.*': {'queue': 'analytics'},
    'apps.alerts.tasks.*': {'queue': 'alerts'},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
