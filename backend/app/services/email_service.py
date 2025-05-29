"""Email service for sending notifications and documents."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import aiofiles
import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails with templates and attachments."""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        
        # Setup Jinja2 for email templates
        self.template_dir = Path("app/templates/email")
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email with optional HTML body and attachments.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            attachments: Optional list of file paths to attach
            cc_emails: Optional list of CC recipients
            bcc_emails: Optional list of BCC recipients
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = ', '.join(to_emails)
            
            if cc_emails:
                message['Cc'] = ', '.join(cc_emails)
            
            # Add text part
            text_part = MIMEText(body, 'plain', 'utf-8')
            message.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    await self._add_attachment(message, file_path)
            
            # Prepare recipient list
            recipients = to_emails.copy()
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)
            
            # Send email
            await self._send_message(message, recipients)
            
            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    async def send_template_email(
        self,
        to_emails: List[str],
        template_name: str,
        context: Dict[str, Any],
        subject: str,
        attachments: Optional[List[str]] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email using a Jinja2 template.
        
        Args:
            to_emails: List of recipient email addresses
            template_name: Name of the template file (without extension)
            context: Context variables for template rendering
            subject: Email subject
            attachments: Optional list of file paths to attach
            cc_emails: Optional list of CC recipients
            bcc_emails: Optional list of BCC recipients
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Render templates
            text_template = self.jinja_env.get_template(f"{template_name}.txt")
            text_body = text_template.render(**context)
            
            html_body = None
            try:
                html_template = self.jinja_env.get_template(f"{template_name}.html")
                html_body = html_template.render(**context)
            except:
                # HTML template is optional
                pass
            
            return await self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=text_body,
                html_body=html_body,
                attachments=attachments,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails
            )
            
        except Exception as e:
            logger.error(f"Failed to send template email: {str(e)}")
            return False
    
    async def send_quote_notification(
        self,
        quote_data: Dict[str, Any],
        recipient_email: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        """
        Send quote notification email.
        
        Args:
            quote_data: Quote information
            recipient_email: Recipient email address
            attachment_path: Optional path to quote PDF
            
        Returns:
            True if email was sent successfully
        """
        context = {
            'quote_number': quote_data.get('quote_number'),
            'company_name': quote_data.get('company_name'),
            'total_amount': quote_data.get('total_amount'),
            'tender_title': quote_data.get('tender_title'),
            'supplier_name': quote_data.get('supplier_name'),
            'valid_until': quote_data.get('valid_until'),
        }
        
        subject = f"New Quote #{quote_data.get('quote_number')} - {quote_data.get('tender_title')}"
        
        attachments = [attachment_path] if attachment_path else None
        
        return await self.send_template_email(
            to_emails=[recipient_email],
            template_name="quote_notification",
            context=context,
            subject=subject,
            attachments=attachments
        )
    
    async def send_tender_notification(
        self,
        tender_data: Dict[str, Any],
        recipient_emails: List[str]
    ) -> bool:
        """
        Send tender notification email to suppliers.
        
        Args:
            tender_data: Tender information
            recipient_emails: List of supplier email addresses
            
        Returns:
            True if email was sent successfully
        """
        context = {
            'tender_title': tender_data.get('title'),
            'company_name': tender_data.get('company_name'),
            'deadline': tender_data.get('deadline'),
            'description': tender_data.get('description'),
            'budget': tender_data.get('budget'),
        }
        
        subject = f"New Tender Opportunity: {tender_data.get('title')}"
        
        return await self.send_template_email(
            to_emails=recipient_emails,
            template_name="tender_notification",
            context=context,
            subject=subject
        )
    
    async def send_welcome_email(
        self,
        user_data: Dict[str, Any],
        temp_password: Optional[str] = None
    ) -> bool:
        """
        Send welcome email to new user.
        
        Args:
            user_data: User information
            temp_password: Temporary password if applicable
            
        Returns:
            True if email was sent successfully
        """
        context = {
            'user_name': user_data.get('full_name'),
            'email': user_data.get('email'),
            'company_name': user_data.get('company_name'),
            'temp_password': temp_password,
            'login_url': f"{settings.FRONTEND_URL}/login"
        }
        
        subject = f"Welcome to {settings.PROJECT_NAME}"
        
        return await self.send_template_email(
            to_emails=[user_data.get('email')],
            template_name="welcome",
            context=context,
            subject=subject
        )
    
    async def send_password_reset(
        self,
        email: str,
        reset_token: str,
        user_name: str
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            email: User email address
            reset_token: Password reset token
            user_name: User's full name
            
        Returns:
            True if email was sent successfully
        """
        context = {
            'user_name': user_name,
            'reset_url': f"{settings.FRONTEND_URL}/reset-password?token={reset_token}",
            'expiry_hours': 24
        }
        
        subject = f"Password Reset - {settings.PROJECT_NAME}"
        
        return await self.send_template_email(
            to_emails=[email],
            template_name="password_reset",
            context=context,
            subject=subject
        )
    
    async def _add_attachment(self, message: MIMEMultipart, file_path: str):
        """Add file attachment to email message."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.warning(f"Attachment file not found: {file_path}")
                return
            
            async with aiofiles.open(file_path, 'rb') as file:
                attachment_data = await file.read()
            
            attachment = MIMEApplication(attachment_data)
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=file_path_obj.name
            )
            message.attach(attachment)
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {str(e)}")
    
    async def _send_message(self, message: MIMEMultipart, recipients: List[str]):
        """Send the email message using aiosmtplib."""
        try:
            smtp_client = aiosmtplib.SMTP(
                hostname=self.smtp_server,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls
            )
            
            await smtp_client.connect()
            
            if self.smtp_username and self.smtp_password:
                await smtp_client.login(self.smtp_username, self.smtp_password)
            
            await smtp_client.send_message(
                message,
                sender=self.from_email,
                recipients=recipients
            )
            
            await smtp_client.quit()
            
        except Exception as e:
            logger.error(f"SMTP error: {str(e)}")
            raise


# Global instance
email_service = EmailService()
