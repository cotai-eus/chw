"""
Email template utilities for generating HTML emails.
"""
import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
from app.core.config import get_settings

settings = get_settings()


class EmailTemplateManager:
    """Manages email templates using Jinja2."""
    
    def __init__(self, templates_dir: str = "app/templates/email"):
        self.templates_dir = templates_dir
        
        # Create templates directory if it doesn't exist
        os.makedirs(templates_dir, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True
        )
        
        # Add custom filters
        self.env.filters['datetime_format'] = self.datetime_format
        self.env.filters['currency_format'] = self.currency_format
        self.env.filters['truncate_text'] = self.truncate_text
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            # Fallback to basic template if specific template fails
            return self.render_basic_template(template_name, context)
    
    def render_basic_template(self, template_type: str, context: Dict[str, Any]) -> str:
        """Render basic fallback template."""
        basic_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #007bff; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f8f9fa; }
                .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
                .button { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ title }}</h1>
                </div>
                <div class="content">
                    {{ content }}
                </div>
                <div class="footer">
                    <p>{{ company_name }} - {{ current_year }}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(basic_template)
        return template.render(**context)
    
    @staticmethod
    def datetime_format(value, format_string='%Y-%m-%d %H:%M'):
        """Format datetime for templates."""
        if value is None:
            return ''
        return value.strftime(format_string)
    
    @staticmethod
    def currency_format(value, currency='USD'):
        """Format currency for templates."""
        if value is None:
            return '0.00'
        return f"{value:,.2f} {currency}"
    
    @staticmethod
    def truncate_text(value, length=100, suffix='...'):
        """Truncate text for templates."""
        if value is None:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + suffix


# Email template contexts
def get_welcome_email_context(user_name: str, company_name: str) -> Dict[str, Any]:
    """Get context for welcome email."""
    return {
        "title": "Welcome to the Platform",
        "user_name": user_name,
        "company_name": company_name,
        "login_url": f"{settings.FRONTEND_URL}/login",
        "support_email": settings.SUPPORT_EMAIL,
        "current_year": 2024
    }


def get_password_reset_context(
    user_name: str,
    reset_token: str,
    company_name: str
) -> Dict[str, Any]:
    """Get context for password reset email."""
    return {
        "title": "Password Reset Request",
        "user_name": user_name,
        "company_name": company_name,
        "reset_url": f"{settings.FRONTEND_URL}/reset-password?token={reset_token}",
        "support_email": settings.SUPPORT_EMAIL,
        "current_year": 2024
    }


def get_tender_notification_context(
    user_name: str,
    tender_title: str,
    tender_id: str,
    action: str,
    company_name: str
) -> Dict[str, Any]:
    """Get context for tender notification email."""
    return {
        "title": f"Tender {action.title()}",
        "user_name": user_name,
        "tender_title": tender_title,
        "tender_id": tender_id,
        "action": action,
        "tender_url": f"{settings.FRONTEND_URL}/tenders/{tender_id}",
        "company_name": company_name,
        "support_email": settings.SUPPORT_EMAIL,
        "current_year": 2024
    }


def get_quote_notification_context(
    user_name: str,
    quote_id: str,
    tender_title: str,
    action: str,
    company_name: str
) -> Dict[str, Any]:
    """Get context for quote notification email."""
    return {
        "title": f"Quote {action.title()}",
        "user_name": user_name,
        "quote_id": quote_id,
        "tender_title": tender_title,
        "action": action,
        "quote_url": f"{settings.FRONTEND_URL}/quotes/{quote_id}",
        "company_name": company_name,
        "support_email": settings.SUPPORT_EMAIL,
        "current_year": 2024
    }


def get_reminder_email_context(
    user_name: str,
    reminder_type: str,
    item_title: str,
    due_date: str,
    company_name: str
) -> Dict[str, Any]:
    """Get context for reminder email."""
    return {
        "title": f"{reminder_type.title()} Reminder",
        "user_name": user_name,
        "reminder_type": reminder_type,
        "item_title": item_title,
        "due_date": due_date,
        "company_name": company_name,
        "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
        "support_email": settings.SUPPORT_EMAIL,
        "current_year": 2024
    }
