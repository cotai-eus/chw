"""
Utility modules initialization.
"""
from .email_templates import (
    EmailTemplateManager,
    get_welcome_email_context,
    get_password_reset_context,
    get_tender_notification_context,
    get_quote_notification_context,
    get_reminder_email_context
)
from .file_processing import (
    FileProcessor,
    FileValidator,
    file_processor
)
from .datetime_utils import (
    DateTimeUtils,
    WorkingHoursUtils
)
from .helpers import (
    ValidationUtils,
    StringUtils,
    HashUtils,
    DataUtils,
    FormatUtils,
    IDGenerator
)

__all__ = [
    # Email templates
    "EmailTemplateManager",
    "get_welcome_email_context",
    "get_password_reset_context",
    "get_tender_notification_context",
    "get_quote_notification_context",
    "get_reminder_email_context",
    
    # File processing
    "FileProcessor",
    "FileValidator",
    "file_processor",
    
    # DateTime utilities
    "DateTimeUtils",
    "WorkingHoursUtils",
    
    # General helpers
    "ValidationUtils",
    "StringUtils",
    "HashUtils",
    "DataUtils",
    "FormatUtils",
    "IDGenerator"
]
