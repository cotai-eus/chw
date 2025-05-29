"""Celery configuration and task management."""

import os
from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "tender_management",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.ai_tasks",
        "app.tasks.email_tasks", 
        "app.tasks.file_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.calendar_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DEFAULT_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    # Task routing
    task_routes={
        "app.tasks.ai_tasks.*": {"queue": "ai_processing"},
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.file_tasks.*": {"queue": "file_processing"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.calendar_tasks.*": {"queue": "calendar"},
    },
    # Periodic tasks
    beat_schedule={
        "cleanup-temp-files": {
            "task": "app.tasks.file_tasks.cleanup_temp_files",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-expired-notifications": {
            "task": "app.tasks.notification_tasks.cleanup_expired_notifications",
            "schedule": 21600.0,  # Every 6 hours
        },
        "send-deadline-reminders": {
            "task": "app.tasks.calendar_tasks.send_deadline_reminders",
            "schedule": 86400.0,  # Daily
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
