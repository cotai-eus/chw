"""Email sending tasks for background execution."""

import logging
from typing import List, Dict, Any, Optional

from app.celery_app import celery_app
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.email_tasks.send_email_task")
def send_email_task(
    self,
    to_emails: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send an email in the background.
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
        attachments: Optional list of file paths to attach
        cc_emails: Optional list of CC recipients
        bcc_emails: Optional list of BCC recipients
        
    Returns:
        Result of email sending
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Preparing email", "progress": 10}
        )
        
        async def _send():
            self.update_state(
                state="PROGRESS",
                meta={"status": "Sending email", "progress": 50}
            )
            
            success = await email_service.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                html_body=html_body,
                attachments=attachments,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"status": "Email sent", "progress": 100}
            )
            
            return {"success": success, "recipients": to_emails}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Email sending task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="app.tasks.email_tasks.send_template_email_task")
def send_template_email_task(
    self,
    to_emails: List[str],
    template_name: str,
    context: Dict[str, Any],
    subject: str,
    attachments: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send a template-based email in the background.
    
    Args:
        to_emails: List of recipient email addresses
        template_name: Name of the template file
        context: Context variables for template rendering
        subject: Email subject
        attachments: Optional list of file paths to attach
        cc_emails: Optional list of CC recipients
        bcc_emails: Optional list of BCC recipients
        
    Returns:
        Result of email sending
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Rendering template", "progress": 20}
        )
        
        async def _send():
            self.update_state(
                state="PROGRESS",
                meta={"status": "Sending template email", "progress": 60}
            )
            
            success = await email_service.send_template_email(
                to_emails=to_emails,
                template_name=template_name,
                context=context,
                subject=subject,
                attachments=attachments,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"status": "Template email sent", "progress": 100}
            )
            
            return {"success": success, "template": template_name, "recipients": to_emails}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Template email task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(name="app.tasks.email_tasks.send_quote_notification_task")
def send_quote_notification_task(
    quote_data: Dict[str, Any],
    recipient_email: str,
    attachment_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send quote notification email.
    
    Args:
        quote_data: Quote information
        recipient_email: Recipient email address
        attachment_path: Optional path to quote PDF
        
    Returns:
        Result of email sending
    """
    try:
        async def _send():
            success = await email_service.send_quote_notification(
                quote_data=quote_data,
                recipient_email=recipient_email,
                attachment_path=attachment_path
            )
            return {"success": success, "recipient": recipient_email}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Quote notification task failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.email_tasks.send_tender_notification_task")
def send_tender_notification_task(
    tender_data: Dict[str, Any],
    recipient_emails: List[str]
) -> Dict[str, Any]:
    """
    Send tender notification email to suppliers.
    
    Args:
        tender_data: Tender information
        recipient_emails: List of supplier email addresses
        
    Returns:
        Result of email sending
    """
    try:
        async def _send():
            success = await email_service.send_tender_notification(
                tender_data=tender_data,
                recipient_emails=recipient_emails
            )
            return {"success": success, "recipients": recipient_emails}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Tender notification task failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.email_tasks.send_welcome_email_task")
def send_welcome_email_task(
    user_data: Dict[str, Any],
    temp_password: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send welcome email to new user.
    
    Args:
        user_data: User information
        temp_password: Temporary password if applicable
        
    Returns:
        Result of email sending
    """
    try:
        async def _send():
            success = await email_service.send_welcome_email(
                user_data=user_data,
                temp_password=temp_password
            )
            return {"success": success, "user_email": user_data.get("email")}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Welcome email task failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.email_tasks.send_password_reset_task")
def send_password_reset_task(
    email: str,
    reset_token: str,
    user_name: str
) -> Dict[str, Any]:
    """
    Send password reset email.
    
    Args:
        email: User email address
        reset_token: Password reset token
        user_name: User's full name
        
    Returns:
        Result of email sending
    """
    try:
        async def _send():
            success = await email_service.send_password_reset(
                email=email,
                reset_token=reset_token,
                user_name=user_name
            )
            return {"success": success, "email": email}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Password reset email task failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.email_tasks.send_bulk_emails")
def send_bulk_emails(
    email_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Send multiple emails in bulk.
    
    Args:
        email_list: List of email configurations
        
    Returns:
        Bulk sending results
    """
    try:
        results = []
        total = len(email_list)
        
        for i, email_config in enumerate(email_list):
            try:
                # Send individual email
                task = send_email_task.delay(**email_config)
                result = task.get(timeout=60)  # 1 minute timeout per email
                
                results.append({
                    "index": i,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Failed to send bulk email {i}: {str(e)}")
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "total_emails": total,
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Bulk email sending failed: {str(e)}")
        raise
