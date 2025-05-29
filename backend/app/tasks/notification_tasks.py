"""Notification tasks for background execution."""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.services.notification_service import notification_service
from app.db.session import get_async_db
from app.crud.crud_tender import crud_tender

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notification_tasks.send_notification_task")
def send_notification_task(
    user_id: str,
    company_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    data: Optional[Dict[str, Any]] = None,
    expires_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a notification to a user.
    
    Args:
        user_id: ID of the user to notify
        company_id: ID of the company
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        data: Additional data
        expires_at: Optional expiration time (ISO string)
        
    Returns:
        Notification creation result
    """
    try:
        async def _send():
            expires_datetime = None
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at)
            
            notification = await notification_service.create_notification(
                user_id=UUID(user_id),
                company_id=UUID(company_id),
                title=title,
                message=message,
                notification_type=notification_type,
                data=data,
                expires_at=expires_datetime
            )
            
            return notification
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Notification task failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notification_tasks.cleanup_expired_notifications")
def cleanup_expired_notifications() -> Dict[str, Any]:
    """
    Clean up expired notifications.
    
    Returns:
        Cleanup results
    """
    try:
        async def _cleanup():
            await notification_service.cleanup_expired_notifications()
            return {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_cleanup())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Notification cleanup failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notification_tasks.send_deadline_reminders_task")
def send_deadline_reminders_task() -> Dict[str, Any]:
    """
    Send deadline reminders for approaching tender deadlines.
    
    Returns:
        Reminder sending results
    """
    try:
        async def _send_reminders():
            async with get_async_db() as db:
                # Get tenders with approaching deadlines (3 days from now)
                reminder_date = datetime.utcnow() + timedelta(days=3)
                
                # This would query for tenders with deadlines approaching
                # For now, return placeholder data
                reminders_sent = 0
                
                # Example logic for sending reminders
                # tenders = await crud_tender.get_by_deadline_range(
                #     db, start_date=reminder_date, end_date=reminder_date + timedelta(hours=24)
                # )
                
                # for tender in tenders:
                #     # Send notification to relevant users
                #     notification_task = send_notification_task.delay(
                #         user_id=str(tender.created_by),
                #         company_id=str(tender.company_id),
                #         title="Tender Deadline Approaching",
                #         message=f"Tender '{tender.title}' deadline is in 3 days",
                #         notification_type="warning",
                #         data={"tender_id": str(tender.id), "action": "view_tender"}
                #     )
                #     reminders_sent += 1
                
                return {
                    "status": "completed",
                    "reminders_sent": reminders_sent,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send_reminders())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Deadline reminders task failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notification_tasks.send_bulk_notifications")
def send_bulk_notifications(
    notifications: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Send multiple notifications in bulk.
    
    Args:
        notifications: List of notification configurations
        
    Returns:
        Bulk sending results
    """
    try:
        results = []
        total = len(notifications)
        
        for i, notification_config in enumerate(notifications):
            try:
                # Send individual notification
                task = send_notification_task.delay(**notification_config)
                result = task.get(timeout=30)  # 30 second timeout per notification
                
                results.append({
                    "index": i,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Failed to send bulk notification {i}: {str(e)}")
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "total_notifications": total,
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Bulk notification sending failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notification_tasks.notify_tender_created")
def notify_tender_created(
    tender_data: Dict[str, Any],
    company_id: str,
    creator_id: str
) -> Dict[str, Any]:
    """
    Send notification when a tender is created.
    
    Args:
        tender_data: Tender information
        company_id: Company ID
        creator_id: ID of the user who created the tender
        
    Returns:
        Notification result
    """
    try:
        async def _notify():
            success = await notification_service.notify_tender_created(
                tender_data=tender_data,
                company_id=UUID(company_id),
                creator_id=UUID(creator_id)
            )
            return {"success": success, "tender_id": tender_data.get("id")}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_notify())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Tender creation notification failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notification_tasks.notify_quote_received")
def notify_quote_received(
    quote_data: Dict[str, Any],
    company_id: str,
    recipient_id: str
) -> Dict[str, Any]:
    """
    Send notification when a quote is received.
    
    Args:
        quote_data: Quote information
        company_id: Company ID
        recipient_id: ID of the user to notify
        
    Returns:
        Notification result
    """
    try:
        async def _notify():
            success = await notification_service.notify_quote_received(
                quote_data=quote_data,
                company_id=UUID(company_id),
                recipient_id=UUID(recipient_id)
            )
            return {"success": success, "quote_id": quote_data.get("id")}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_notify())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Quote received notification failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.notification_tasks.send_scheduled_notifications")
def send_scheduled_notifications() -> Dict[str, Any]:
    """
    Send scheduled notifications (daily digest, weekly reports, etc.).
    
    Returns:
        Scheduled notification results
    """
    try:
        # This would implement logic for sending scheduled notifications
        # like daily summaries, weekly reports, etc.
        
        notifications_sent = 0
        
        # Example: Daily digest notifications
        # users = await get_users_with_digest_enabled()
        # for user in users:
        #     digest_data = await generate_daily_digest(user.id)
        #     notification_task = send_notification_task.delay(
        #         user_id=str(user.id),
        #         company_id=str(user.company_id),
        #         title="Daily Digest",
        #         message="Your daily activity summary is ready",
        #         notification_type="info",
        #         data=digest_data
        #     )
        #     notifications_sent += 1
        
        return {
            "status": "completed",
            "notifications_sent": notifications_sent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Scheduled notifications task failed: {str(e)}")
        raise
