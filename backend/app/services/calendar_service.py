"""Calendar service for managing events and scheduling."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_

from app.core.config import settings

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for calendar and scheduling functionality."""
    
    def __init__(self):
        self.default_timezone = settings.DEFAULT_TIMEZONE
    
    async def create_event(
        self,
        db: AsyncSession,
        event_data: Dict[str, Any],
        user_id: UUID,
        company_id: UUID
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.
        
        Args:
            db: Database session
            event_data: Event information
            user_id: ID of the user creating the event
            company_id: ID of the company
            
        Returns:
            Created event information
        """
        try:
            # Validate event data
            self._validate_event_data(event_data)
            
            # Check for conflicts
            conflicts = await self._check_conflicts(
                db, event_data, user_id, company_id
            )
            
            if conflicts:
                logger.warning(f"Event conflicts detected for user {user_id}")
                return {
                    "error": "Schedule conflict detected",
                    "conflicts": conflicts
                }
            
            # Create event (this would interact with a calendar model)
            event = {
                "id": str(UUID()),
                "title": event_data["title"],
                "description": event_data.get("description", ""),
                "start_time": event_data["start_time"],
                "end_time": event_data["end_time"],
                "location": event_data.get("location", ""),
                "attendees": event_data.get("attendees", []),
                "reminder_minutes": event_data.get("reminder_minutes", 15),
                "user_id": str(user_id),
                "company_id": str(company_id),
                "created_at": datetime.utcnow()
            }
            
            logger.info(f"Event created: {event['id']}")
            return event
            
        except Exception as e:
            logger.error(f"Failed to create event: {str(e)}")
            return {"error": str(e)}
    
    async def get_events(
        self,
        db: AsyncSession,
        user_id: UUID,
        company_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events for a user within a date range.
        
        Args:
            db: Database session
            user_id: User ID
            company_id: Company ID
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of events
        """
        try:
            # Default to current month if no dates provided
            if not start_date:
                start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if not end_date:
                # Last day of current month
                next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
                end_date = next_month - timedelta(days=1)
            
            # This would query from a calendar events table
            # For now, return mock data
            events = [
                {
                    "id": "event-1",
                    "title": "Tender Review Meeting",
                    "description": "Review submitted tenders for Q1 projects",
                    "start_time": start_date + timedelta(days=3, hours=10),
                    "end_time": start_date + timedelta(days=3, hours=11),
                    "location": "Conference Room A",
                    "attendees": ["user1@example.com", "user2@example.com"],
                    "type": "meeting"
                },
                {
                    "id": "event-2",
                    "title": "Supplier Presentation",
                    "description": "ABC Corp product presentation",
                    "start_time": start_date + timedelta(days=7, hours=14),
                    "end_time": start_date + timedelta(days=7, hours=15, minutes=30),
                    "location": "Virtual Meeting",
                    "attendees": ["supplier@abc.com"],
                    "type": "presentation"
                }
            ]
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get events: {str(e)}")
            return []
    
    async def schedule_tender_deadline_reminder(
        self,
        db: AsyncSession,
        tender_data: Dict[str, Any],
        user_id: UUID,
        company_id: UUID,
        reminder_days: int = 3
    ) -> Dict[str, Any]:
        """
        Schedule a reminder for tender deadline.
        
        Args:
            db: Database session
            tender_data: Tender information
            user_id: User ID
            company_id: Company ID
            reminder_days: Days before deadline to remind
            
        Returns:
            Scheduled reminder information
        """
        try:
            deadline = tender_data.get("deadline")
            if not deadline:
                return {"error": "No deadline specified"}
            
            # Calculate reminder time
            reminder_time = deadline - timedelta(days=reminder_days)
            
            if reminder_time <= datetime.utcnow():
                return {"error": "Reminder time is in the past"}
            
            # Create reminder event
            event_data = {
                "title": f"Tender Deadline Reminder: {tender_data.get('title')}",
                "description": f"Tender '{tender_data.get('title')}' deadline is in {reminder_days} days",
                "start_time": reminder_time,
                "end_time": reminder_time + timedelta(minutes=30),
                "reminder_minutes": 60,
                "type": "reminder"
            }
            
            reminder = await self.create_event(db, event_data, user_id, company_id)
            
            logger.info(f"Tender deadline reminder scheduled for {reminder_time}")
            return reminder
            
        except Exception as e:
            logger.error(f"Failed to schedule tender reminder: {str(e)}")
            return {"error": str(e)}
    
    async def schedule_quote_followup(
        self,
        db: AsyncSession,
        quote_data: Dict[str, Any],
        user_id: UUID,
        company_id: UUID,
        followup_days: int = 7
    ) -> Dict[str, Any]:
        """
        Schedule a follow-up for a submitted quote.
        
        Args:
            db: Database session
            quote_data: Quote information
            user_id: User ID
            company_id: Company ID
            followup_days: Days after submission to follow up
            
        Returns:
            Scheduled follow-up information
        """
        try:
            submitted_at = quote_data.get("submitted_at", datetime.utcnow())
            
            # Calculate follow-up time
            followup_time = submitted_at + timedelta(days=followup_days)
            
            # Create follow-up event
            event_data = {
                "title": f"Quote Follow-up: {quote_data.get('quote_number')}",
                "description": f"Follow up on quote {quote_data.get('quote_number')} for tender '{quote_data.get('tender_title')}'",
                "start_time": followup_time,
                "end_time": followup_time + timedelta(minutes=30),
                "reminder_minutes": 30,
                "type": "followup"
            }
            
            followup = await self.create_event(db, event_data, user_id, company_id)
            
            logger.info(f"Quote follow-up scheduled for {followup_time}")
            return followup
            
        except Exception as e:
            logger.error(f"Failed to schedule quote follow-up: {str(e)}")
            return {"error": str(e)}
    
    async def get_upcoming_deadlines(
        self,
        db: AsyncSession,
        user_id: UUID,
        company_id: UUID,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming tender deadlines and important dates.
        
        Args:
            db: Database session
            user_id: User ID
            company_id: Company ID
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming deadlines
        """
        try:
            end_date = datetime.utcnow() + timedelta(days=days_ahead)
            
            # This would query from tender and other relevant tables
            # For now, return mock data
            deadlines = [
                {
                    "id": "tender-1",
                    "title": "IT Infrastructure Tender",
                    "type": "tender_deadline",
                    "deadline": datetime.utcnow() + timedelta(days=5),
                    "priority": "high",
                    "description": "Submit quotes for IT infrastructure upgrade"
                },
                {
                    "id": "quote-1",
                    "title": "Follow-up on Security System Quote",
                    "type": "quote_followup",
                    "deadline": datetime.utcnow() + timedelta(days=2),
                    "priority": "medium",
                    "description": "Follow up on submitted security system quote"
                }
            ]
            
            # Sort by deadline
            deadlines.sort(key=lambda x: x["deadline"])
            
            return deadlines
            
        except Exception as e:
            logger.error(f"Failed to get upcoming deadlines: {str(e)}")
            return []
    
    async def _check_conflicts(
        self,
        db: AsyncSession,
        event_data: Dict[str, Any],
        user_id: UUID,
        company_id: UUID
    ) -> List[Dict[str, Any]]:
        """Check for scheduling conflicts."""
        try:
            start_time = event_data["start_time"]
            end_time = event_data["end_time"]
            
            # This would query existing events for conflicts
            # For now, return empty list (no conflicts)
            return []
            
        except Exception as e:
            logger.error(f"Failed to check conflicts: {str(e)}")
            return []
    
    def _validate_event_data(self, event_data: Dict[str, Any]):
        """Validate event data."""
        required_fields = ["title", "start_time", "end_time"]
        
        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Missing required field: {field}")
        
        start_time = event_data["start_time"]
        end_time = event_data["end_time"]
        
        if end_time <= start_time:
            raise ValueError("End time must be after start time")
        
        if start_time < datetime.utcnow():
            raise ValueError("Start time cannot be in the past")


# Global instance
calendar_service = CalendarService()
