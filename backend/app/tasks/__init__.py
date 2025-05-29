"""Celery tasks for background processing."""

from .ai_tasks import *
from .email_tasks import *
from .file_tasks import *
from .notification_tasks import *
from .calendar_tasks import *

__all__ = [
    # AI tasks
    "analyze_tender_task",
    "generate_quote_suggestions_task",
    "optimize_pricing_task",
    
    # Email tasks
    "send_email_task",
    "send_template_email_task",
    "send_quote_notification_task",
    "send_tender_notification_task",
    "send_welcome_email_task",
    
    # File tasks
    "process_file_upload_task",
    "generate_pdf_task",
    "cleanup_temp_files",
    "extract_pdf_text_task",
    
    # Notification tasks
    "send_notification_task",
    "cleanup_expired_notifications",
    "send_deadline_reminders_task",
    
    # Calendar tasks
    "schedule_event_task",
    "send_deadline_reminders",
    "schedule_tender_reminder_task",
]
