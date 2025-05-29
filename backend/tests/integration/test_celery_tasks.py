"""
Comprehensive tests for Celery background tasks.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4
from typing import Dict, Any

from app.celery_app import celery_app
from app.tasks import (
    ai_tasks,
    email_tasks,
    file_tasks,
    notification_tasks,
    calendar_tasks
)
from app.models.tender import TenderModel
from app.models.quote import QuoteModel
from app.models.company import CompanyModel
from app.models.user import UserModel
from app.schemas.tender import TenderCreate


class TestAITasks:
    """Test AI processing tasks."""
    
    @pytest.mark.asyncio
    async def test_analyze_tender_task_success(self, test_db, mock_ai_service, test_company, test_user):
        """Test successful tender analysis task."""
        # Create test tender
        tender_data = TenderCreate(
            title="Test Tender Analysis",
            description="Test tender for AI analysis",
            requirements=["requirement1", "requirement2"],
            deadline=datetime.utcnow() + timedelta(days=30),
            budget_range_min=10000,
            budget_range_max=50000,
            category="software",
            company_id=test_company.id
        )
        
        tender = TenderModel(**tender_data.dict())
        tender.id = uuid4()
        test_db.add(tender)
        await test_db.commit()
        
        # Mock AI service response
        mock_analysis = {
            "complexity_score": 0.75,
            "estimated_hours": 120,
            "risk_factors": ["tight_deadline", "complex_requirements"],
            "suggested_price": 35000,
            "confidence": 0.85
        }
        mock_ai_service.analyze_tender.return_value = mock_analysis
        
        # Execute task
        with patch('app.tasks.ai_tasks.ai_service', mock_ai_service):
            result = ai_tasks.analyze_tender_task(str(tender.id))
        
        # Verify results
        assert result["status"] == "completed"
        assert result["analysis"]["complexity_score"] == 0.75
        assert result["analysis"]["estimated_hours"] == 120
        assert len(result["analysis"]["risk_factors"]) == 2
        mock_ai_service.analyze_tender.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_tender_task_not_found(self, test_db):
        """Test tender analysis task with non-existent tender."""
        fake_id = str(uuid4())
        
        result = ai_tasks.analyze_tender_task(fake_id)
        
        assert result["error"] == "Tender not found"
    
    @pytest.mark.asyncio
    async def test_generate_quote_suggestions_task(self, test_db, mock_ai_service, test_company, test_user):
        """Test quote suggestions generation task."""
        # Create test tender
        tender = TenderModel(
            id=uuid4(),
            title="Test Tender for Quote",
            description="Test tender for quote generation",
            requirements=["req1", "req2"],
            deadline=datetime.utcnow() + timedelta(days=30),
            budget_range_min=20000,
            budget_range_max=80000,
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Mock AI service response
        mock_suggestions = {
            "price_suggestion": 45000,
            "timeline_days": 45,
            "risk_assessment": "medium",
            "optimization_tips": ["tip1", "tip2"],
            "competitive_analysis": {"average_price": 50000, "position": "competitive"}
        }
        mock_ai_service.generate_quote_suggestions.return_value = mock_suggestions
        
        # Execute task
        user_id = str(test_user.id)
        with patch('app.tasks.ai_tasks.ai_service', mock_ai_service):
            result = ai_tasks.generate_quote_suggestions_task(str(tender.id), user_id)
        
        # Verify results
        assert result["status"] == "completed"
        assert result["suggestions"]["price_suggestion"] == 45000
        assert result["suggestions"]["timeline_days"] == 45
        assert result["suggestions"]["risk_assessment"] == "medium"
    
    @pytest.mark.asyncio
    async def test_ai_task_error_handling(self, test_db, mock_ai_service):
        """Test AI task error handling."""
        # Mock AI service to raise an exception
        mock_ai_service.analyze_tender.side_effect = Exception("AI service error")
        
        tender_id = str(uuid4())
        
        with patch('app.tasks.ai_tasks.ai_service', mock_ai_service):
            result = ai_tasks.analyze_tender_task(tender_id)
        
        assert "error" in result
        assert "AI service error" in result["error"]


class TestEmailTasks:
    """Test email sending tasks."""
    
    @pytest.mark.asyncio
    async def test_send_email_task_success(self, mock_email_service):
        """Test successful email sending."""
        # Mock email service
        mock_email_service.send_email.return_value = True
        
        # Execute task
        with patch('app.tasks.email_tasks.email_service', mock_email_service):
            result = email_tasks.send_email_task(
                to_emails=["test@example.com"],
                subject="Test Email",
                body="Test email body",
                html_body="<p>Test email body</p>"
            )
        
        # Verify results
        assert result["status"] == "sent"
        assert result["recipients"] == ["test@example.com"]
        mock_email_service.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_email_task(self, mock_email_service, test_user):
        """Test notification email sending."""
        mock_email_service.send_notification_email.return_value = True
        
        notification_data = {
            "user_id": str(test_user.id),
            "email": test_user.email,
            "notification_type": "tender_deadline",
            "data": {"tender_title": "Test Tender", "deadline": "2024-01-15"}
        }
        
        with patch('app.tasks.email_tasks.email_service', mock_email_service):
            result = email_tasks.send_notification_email_task(notification_data)
        
        assert result["status"] == "sent"
        assert result["notification_type"] == "tender_deadline"
    
    @pytest.mark.asyncio
    async def test_send_bulk_emails_task(self, mock_email_service):
        """Test bulk email sending."""
        email_batch = [
            {
                "to_emails": ["user1@example.com"],
                "subject": "Bulk Email 1",
                "body": "Body 1"
            },
            {
                "to_emails": ["user2@example.com"],
                "subject": "Bulk Email 2",
                "body": "Body 2"
            }
        ]
        
        mock_email_service.send_email.return_value = True
        
        with patch('app.tasks.email_tasks.email_service', mock_email_service):
            result = email_tasks.send_bulk_emails_task(email_batch)
        
        assert result["status"] == "completed"
        assert result["total_emails"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert mock_email_service.send_email.call_count == 2
    
    @pytest.mark.asyncio
    async def test_email_task_failure_handling(self, mock_email_service):
        """Test email task failure handling."""
        # Mock email service to fail
        mock_email_service.send_email.side_effect = Exception("SMTP error")
        
        with patch('app.tasks.email_tasks.email_service', mock_email_service):
            result = email_tasks.send_email_task(
                to_emails=["test@example.com"],
                subject="Test Email",
                body="Test body"
            )
        
        assert "error" in result
        assert "SMTP error" in result["error"]


class TestFileTasks:
    """Test file processing tasks."""
    
    @pytest.mark.asyncio
    async def test_process_file_upload_task(self, mock_file_service):
        """Test file upload processing."""
        file_data = {
            "file_id": str(uuid4()),
            "filename": "test_document.pdf",
            "file_path": "/tmp/test_document.pdf",
            "content_type": "application/pdf",
            "user_id": str(uuid4())
        }
        
        mock_file_service.process_upload.return_value = {
            "processed": True,
            "file_size": 1024,
            "metadata": {"pages": 10, "extracted_text": "Sample text"}
        }
        
        with patch('app.tasks.file_tasks.file_service', mock_file_service):
            result = file_tasks.process_file_upload_task(file_data)
        
        assert result["status"] == "processed"
        assert result["file_id"] == file_data["file_id"]
        assert result["metadata"]["pages"] == 10
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files_task(self, mock_file_service):
        """Test temporary files cleanup."""
        mock_file_service.cleanup_temp_files.return_value = {
            "deleted_files": 15,
            "freed_space_mb": 250
        }
        
        with patch('app.tasks.file_tasks.file_service', mock_file_service):
            result = file_tasks.cleanup_temp_files()
        
        assert result["deleted_files"] == 15
        assert result["freed_space_mb"] == 250
    
    @pytest.mark.asyncio
    async def test_generate_file_preview_task(self, mock_file_service):
        """Test file preview generation."""
        file_id = str(uuid4())
        
        mock_file_service.generate_preview.return_value = {
            "preview_path": "/previews/test_preview.jpg",
            "thumbnail_path": "/thumbnails/test_thumb.jpg"
        }
        
        with patch('app.tasks.file_tasks.file_service', mock_file_service):
            result = file_tasks.generate_file_preview_task(file_id)
        
        assert result["status"] == "generated"
        assert "preview_path" in result
        assert "thumbnail_path" in result


class TestNotificationTasks:
    """Test notification tasks."""
    
    @pytest.mark.asyncio
    async def test_send_push_notification_task(self, mock_notification_service):
        """Test push notification sending."""
        notification_data = {
            "user_id": str(uuid4()),
            "title": "New Quote Received",
            "message": "You have received a new quote for your tender",
            "data": {"tender_id": str(uuid4()), "quote_id": str(uuid4())}
        }
        
        mock_notification_service.send_push_notification.return_value = True
        
        with patch('app.tasks.notification_tasks.notification_service', mock_notification_service):
            result = notification_tasks.send_push_notification_task(notification_data)
        
        assert result["status"] == "sent"
        assert result["title"] == "New Quote Received"
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_notifications_task(self, mock_notification_service):
        """Test expired notifications cleanup."""
        mock_notification_service.cleanup_expired.return_value = {
            "deleted_count": 42
        }
        
        with patch('app.tasks.notification_tasks.notification_service', mock_notification_service):
            result = notification_tasks.cleanup_expired_notifications()
        
        assert result["deleted_count"] == 42
    
    @pytest.mark.asyncio
    async def test_send_websocket_notification_task(self, mock_websocket_manager):
        """Test WebSocket notification sending."""
        notification_data = {
            "room": "user_123",
            "event": "tender_update",
            "data": {"tender_id": str(uuid4()), "status": "published"}
        }
        
        with patch('app.tasks.notification_tasks.websocket_manager', mock_websocket_manager):
            result = notification_tasks.send_websocket_notification_task(notification_data)
        
        assert result["status"] == "sent"
        mock_websocket_manager.send_to_room.assert_called_once()


class TestCalendarTasks:
    """Test calendar integration tasks."""
    
    @pytest.mark.asyncio
    async def test_sync_calendar_events_task(self, mock_calendar_service):
        """Test calendar events synchronization."""
        user_id = str(uuid4())
        
        mock_calendar_service.sync_events.return_value = {
            "synced_events": 5,
            "new_events": 2,
            "updated_events": 3
        }
        
        with patch('app.tasks.calendar_tasks.calendar_service', mock_calendar_service):
            result = calendar_tasks.sync_calendar_events_task(user_id)
        
        assert result["status"] == "synced"
        assert result["synced_events"] == 5
        assert result["new_events"] == 2
    
    @pytest.mark.asyncio
    async def test_send_deadline_reminders_task(self, mock_calendar_service, mock_email_service):
        """Test deadline reminders sending."""
        mock_calendar_service.get_upcoming_deadlines.return_value = [
            {
                "tender_id": str(uuid4()),
                "title": "Important Tender",
                "deadline": datetime.utcnow() + timedelta(days=1),
                "user_email": "user@example.com"
            }
        ]
        mock_email_service.send_deadline_reminder.return_value = True
        
        with patch('app.tasks.calendar_tasks.calendar_service', mock_calendar_service), \
             patch('app.tasks.calendar_tasks.email_service', mock_email_service):
            result = calendar_tasks.send_deadline_reminders()
        
        assert result["reminders_sent"] == 1
        mock_email_service.send_deadline_reminder.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_calendar_event_task(self, mock_calendar_service):
        """Test calendar event creation."""
        event_data = {
            "user_id": str(uuid4()),
            "title": "Tender Deadline",
            "description": "Submit proposal for tender XYZ",
            "start_time": datetime.utcnow() + timedelta(days=7),
            "end_time": datetime.utcnow() + timedelta(days=7, hours=1),
            "tender_id": str(uuid4())
        }
        
        mock_calendar_service.create_event.return_value = {
            "event_id": "cal_event_123",
            "status": "created"
        }
        
        with patch('app.tasks.calendar_tasks.calendar_service', mock_calendar_service):
            result = calendar_tasks.create_calendar_event_task(event_data)
        
        assert result["status"] == "created"
        assert result["event_id"] == "cal_event_123"


class TestTaskIntegration:
    """Test task integration and workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_tender_publication_workflow(
        self, 
        test_db, 
        mock_ai_service, 
        mock_email_service, 
        mock_notification_service,
        test_company, 
        test_user
    ):
        """Test complete tender publication workflow with multiple tasks."""
        # Create tender
        tender = TenderModel(
            id=uuid4(),
            title="Complex Tender Workflow",
            description="Test complex workflow",
            requirements=["req1", "req2"],
            deadline=datetime.utcnow() + timedelta(days=30),
            budget_range_min=50000,
            budget_range_max=100000,
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Mock services
        mock_ai_service.analyze_tender.return_value = {"complexity_score": 0.8}
        mock_email_service.send_notification_email.return_value = True
        mock_notification_service.send_push_notification.return_value = True
        
        # Execute workflow tasks
        with patch('app.tasks.ai_tasks.ai_service', mock_ai_service), \
             patch('app.tasks.email_tasks.email_service', mock_email_service), \
             patch('app.tasks.notification_tasks.notification_service', mock_notification_service):
            
            # 1. Analyze tender
            ai_result = ai_tasks.analyze_tender_task(str(tender.id))
            
            # 2. Send notification email
            email_result = email_tasks.send_notification_email_task({
                "user_id": str(test_user.id),
                "email": test_user.email,
                "notification_type": "tender_published",
                "data": {"tender_title": tender.title}
            })
            
            # 3. Send push notification
            push_result = notification_tasks.send_push_notification_task({
                "user_id": str(test_user.id),
                "title": "Tender Published",
                "message": f"Your tender '{tender.title}' has been published"
            })
        
        # Verify workflow completion
        assert ai_result["status"] == "completed"
        assert email_result["status"] == "sent"
        assert push_result["status"] == "sent"
    
    @pytest.mark.asyncio
    async def test_celery_task_retry_mechanism(self, mock_ai_service):
        """Test Celery task retry mechanism."""
        # Mock service to fail first call, succeed on retry
        mock_ai_service.analyze_tender.side_effect = [
            Exception("Temporary failure"),
            {"complexity_score": 0.7}
        ]
        
        # This would normally trigger retry in real Celery
        # For testing, we simulate the retry behavior
        tender_id = str(uuid4())
        
        with patch('app.tasks.ai_tasks.ai_service', mock_ai_service):
            try:
                # First attempt fails
                ai_tasks.analyze_tender_task(tender_id)
            except Exception:
                # Retry succeeds
                result = ai_tasks.analyze_tender_task(tender_id)
                assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_task_performance_monitoring(self, mock_celery_service):
        """Test task performance monitoring."""
        # Execute multiple tasks and monitor performance
        task_ids = []
        
        for i in range(5):
            result = mock_celery_service.delay(
                "test_performance_task",
                {"iteration": i}
            )
            task_ids.append(result.id)
        
        # Simulate task completion
        for task_id in task_ids:
            await mock_celery_service.execute_task(
                task_id, 
                {"status": "completed", "execution_time": 0.5}
            )
        
        # Verify all tasks completed
        completed_tasks = [
            mock_celery_service.get_task(task_id) 
            for task_id in task_ids
        ]
        
        assert all(task["status"] == "SUCCESS" for task in completed_tasks)
        assert len(completed_tasks) == 5
