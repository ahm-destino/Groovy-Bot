from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Create Celery app
celery_app = Celery(
    'grooovy',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Lagos',
    enable_utc=True,
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    'cleanup-expired-bookings': {
        'task': 'app.tasks.bookings.cleanup_expired_bookings_task',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'process-location-reveals': {
        'task': 'app.tasks.reveals.process_location_reveals_task',
        'schedule': crontab(minute=0),  # Every hour
    },
    'send-event-reminders-24h': {
        'task': 'app.tasks.reminders.send_24h_reminders_task',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'send-event-reminders-1h': {
        'task': 'app.tasks.reminders.send_1h_reminders_task',
        'schedule': crontab(minute=0),  # Every hour
    },
}
