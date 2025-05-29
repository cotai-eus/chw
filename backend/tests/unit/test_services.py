"""
Comprehensive tests for service layer components.
"""
import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from uuid import uuid4
from pathlib import Path
from typing import Dict, Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.file_service import FileService
from app.services.notification_service import NotificationService
from app.services.calendar_service import CalendarService
from app.services.quote_service import QuoteService
from app.models.tender import TenderModel
from app.models.quote import QuoteModel
from app.models.user import UserModel
from app.schemas.tender import TenderCreate
from app.schemas.quote import QuoteCreate


class TestAIService:
    """Test AI processing service."""
    
    @pytest.fixture
    def ai_service(self):
        """Create AI service instance."""
        return AIService()
    
    @pytest.mark.asyncio
    async def test_analyze_tender_success(self, ai_service, test_db, test_company, test_user):
        """Test successful tender analysis."""
        # Create test tender
        tender = TenderModel(
            id=uuid4(),
            title="Software Development Project",
            description="Develop a web application with React and FastAPI",
            requirements=["React frontend", "FastAPI backend", "PostgreSQL database"],
            budget_range_min=50000,
            budget_range_max=100000,
            deadline=datetime.utcnow() + timedelta(days=90),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Mock Ollama API response
        mock_ai_response = {
            "response": json.dumps({
                "complexity_score": 0.8,
                "estimated_hours": 800,
                "risk_factors": ["tight_deadline", "complex_requirements"],
                "technology_stack": ["React", "FastAPI", "PostgreSQL"],
                "recommended_team_size": 4,
                "confidence": 0.85
            })
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_ai_response
            mock_post.return_value.status_code = 200
            
            result = await ai_service.analyze_tender(tender, test_db)
            
            # Verify analysis results
            assert result["complexity_score"] == 0.8
            assert result["estimated_hours"] == 800
            assert "tight_deadline" in result["risk_factors"]
            assert result["technology_stack"] == ["React", "FastAPI", "PostgreSQL"]
            assert result["confidence"] == 0.85
            
            # Verify API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "analyze this tender" in call_args[1]["json"]["prompt"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_quote_suggestions(self, ai_service, test_db, test_company, test_user):
        """Test quote suggestions generation."""
        # Create test tender
        tender = TenderModel(
            id=uuid4(),
            title="Mobile App Development",
            description="iOS and Android app development",
            requirements=["iOS app", "Android app", "Backend API"],
            budget_range_min=30000,
            budget_range_max=60000,
            deadline=datetime.utcnow() + timedelta(days=120),
            category="mobile",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Mock AI response
        mock_ai_response = {
            "response": json.dumps({
                "suggested_price": 45000,
                "price_breakdown": {
                    "ios_development": 20000,
                    "android_development": 18000,
                    "backend_api": 7000
                },
                "timeline_days": 90,
                "risk_assessment": "medium",
                "competitive_position": "competitive"
            })
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_ai_response
            mock_post.return_value.status_code = 200
            
            supplier_profile = {
                "company_name": "Tech Solutions Inc",
                "specialties": ["mobile", "web"],
                "past_projects": 25,
                "average_rating": 4.5
            }
            
            result = await ai_service.generate_quote_suggestions(
                tender, supplier_profile, test_db
            )
            
            # Verify suggestions
            assert result["suggested_price"] == 45000
            assert result["timeline_days"] == 90
            assert result["risk_assessment"] == "medium"
            assert "ios_development" in result["price_breakdown"]
    
    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self, ai_service):
        """Test AI service error handling."""
        tender = TenderModel(
            id=uuid4(),
            title="Test Tender",
            description="Test description",
            requirements=["req1"],
            budget_range_min=10000,
            budget_range_max=20000,
            deadline=datetime.utcnow() + timedelta(days=30)
        )
        
        # Mock HTTP error
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection error")
            
            with pytest.raises(Exception):
                await ai_service.analyze_tender(tender, None)
    
    @pytest.mark.asyncio
    async def test_ai_response_parsing_error(self, ai_service):
        """Test handling of malformed AI responses."""
        tender = TenderModel(
            id=uuid4(),
            title="Test Tender",
            description="Test description",
            requirements=["req1"]
        )
        
        # Mock invalid JSON response
        mock_ai_response = {"response": "invalid json {"}
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.json.return_value = mock_ai_response
            mock_post.return_value.status_code = 200
            
            with pytest.raises(json.JSONDecodeError):
                await ai_service.analyze_tender(tender, None)


class TestEmailService:
    """Test email service."""
    
    @pytest.fixture
    def email_service(self):
        """Create email service instance."""
        return EmailService()
    
    @pytest.mark.asyncio
    async def test_send_simple_email(self, email_service):
        """Test sending a simple email."""
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = (200, "OK")
            
            result = await email_service.send_email(
                to_emails=["test@example.com"],
                subject="Test Email",
                body="This is a test email"
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_html_email(self, email_service):
        """Test sending HTML email."""
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = (200, "OK")
            
            result = await email_service.send_email(
                to_emails=["test@example.com"],
                subject="HTML Test Email",
                body="Plain text body",
                html_body="<h1>HTML Body</h1><p>This is HTML content</p>"
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self, email_service):
        """Test sending email with attachments."""
        # Mock file existence and reading
        with patch('pathlib.Path.exists', return_value=True), \
             patch('aiofiles.open', mock_open(read_data=b"file content")), \
             patch('aiosmtplib.send') as mock_send:
            
            mock_send.return_value = (200, "OK")
            
            result = await email_service.send_email(
                to_emails=["test@example.com"],
                subject="Email with Attachment",
                body="Email with attachment",
                attachments=["/tmp/test_file.pdf"]
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_email(self, email_service):
        """Test sending notification email with template."""
        notification_data = {
            "user_name": "John Doe",
            "tender_title": "Software Development Project",
            "deadline": "2024-01-15",
            "company_name": "Tech Corp"
        }
        
        # Mock template rendering
        with patch.object(email_service.jinja_env, 'get_template') as mock_template:
            mock_template.return_value.render.return_value = "<p>Notification content</p>"
            
            with patch('aiosmtplib.send') as mock_send:
                mock_send.return_value = (200, "OK")
                
                result = await email_service.send_notification_email(
                    to_email="john@example.com",
                    template_name="tender_deadline_reminder",
                    data=notification_data
                )
                
                assert result is True
                mock_template.assert_called_once_with("tender_deadline_reminder.html")
    
    @pytest.mark.asyncio
    async def test_send_bulk_emails(self, email_service):
        """Test sending bulk emails."""
        email_list = [
            {
                "to_emails": ["user1@example.com"],
                "subject": "Bulk Email 1",
                "body": "Content 1"
            },
            {
                "to_emails": ["user2@example.com"],
                "subject": "Bulk Email 2",
                "body": "Content 2"
            }
        ]
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = (200, "OK")
            
            results = await email_service.send_bulk_emails(email_list)
            
            assert results["total"] == 2
            assert results["successful"] == 2
            assert results["failed"] == 0
            assert mock_send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_email_sending_failure(self, email_service):
        """Test email sending failure handling."""
        with patch('aiosmtplib.send') as mock_send:
            mock_send.side_effect = Exception("SMTP error")
            
            result = await email_service.send_email(
                to_emails=["test@example.com"],
                subject="Test Email",
                body="Test body"
            )
            
            assert result is False


class TestFileService:
    """Test file service."""
    
    @pytest.fixture
    def file_service(self):
        """Create file service instance."""
        return FileService()
    
    @pytest.mark.asyncio
    async def test_upload_file(self, file_service):
        """Test file upload."""
        mock_file_content = b"test file content"
        
        with patch('aiofiles.open', mock_open()) as mock_file, \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=False):
            
            result = await file_service.upload_file(
                file_content=mock_file_content,
                filename="test_document.pdf",
                content_type="application/pdf",
                user_id=str(uuid4())
            )
            
            assert result["success"] is True
            assert result["filename"] == "test_document.pdf"
            assert "file_path" in result
            assert "file_id" in result
    
    @pytest.mark.asyncio
    async def test_process_document(self, file_service):
        """Test document processing."""
        file_path = "/uploads/test_document.pdf"
        
        # Mock PDF processing
        with patch('PyPDF2.PdfReader') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Extracted PDF text content"
            mock_pdf.return_value.pages = [mock_page, mock_page]
            
            with patch('builtins.open', mock_open(read_data=b"PDF content")):
                result = await file_service.process_document(file_path)
                
                assert result["success"] is True
                assert result["document_type"] == "pdf"
                assert result["page_count"] == 2
                assert "Extracted PDF text" in result["extracted_text"]
    
    @pytest.mark.asyncio
    async def test_generate_file_preview(self, file_service):
        """Test file preview generation."""
        file_path = "/uploads/test_image.jpg"
        
        # Mock image processing
        with patch('PIL.Image.open') as mock_image:
            mock_img = MagicMock()
            mock_img.size = (1920, 1080)
            mock_image.return_value = mock_img
            
            result = await file_service.generate_preview(file_path)
            
            assert result["success"] is True
            assert "preview_path" in result
            assert "thumbnail_path" in result
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, file_service):
        """Test temporary files cleanup."""
        # Mock file system operations
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.unlink') as mock_unlink, \
             patch('pathlib.Path.stat') as mock_stat:
            
            # Mock finding temp files
            mock_files = [
                MagicMock(stat=MagicMock(return_value=MagicMock(st_size=1024))),
                MagicMock(stat=MagicMock(return_value=MagicMock(st_size=2048)))
            ]
            mock_glob.return_value = mock_files
            
            result = await file_service.cleanup_temp_files()
            
            assert result["deleted_files"] == 2
            assert result["freed_space_bytes"] == 3072
            assert mock_unlink.call_count == 2


class TestNotificationService:
    """Test notification service."""
    
    @pytest.fixture
    def notification_service(self):
        """Create notification service instance."""
        return NotificationService()
    
    @pytest.mark.asyncio
    async def test_send_push_notification(self, notification_service):
        """Test sending push notification."""
        notification_data = {
            "user_id": str(uuid4()),
            "title": "New Quote Received",
            "message": "You have received a new quote",
            "data": {"tender_id": str(uuid4())}
        }
        
        # Mock Firebase admin
        with patch('firebase_admin.messaging.send') as mock_send:
            mock_send.return_value = "projects/test-project/messages/msg-id"
            
            result = await notification_service.send_push_notification(
                notification_data
            )
            
            assert result["success"] is True
            assert result["message_id"] == "projects/test-project/messages/msg-id"
    
    @pytest.mark.asyncio
    async def test_store_notification(self, notification_service, test_db, test_user):
        """Test storing notification in database."""
        notification_data = {
            "user_id": test_user.id,
            "title": "System Notification",
            "message": "Your account has been verified",
            "type": "account_verification",
            "data": {"verification_date": "2024-01-01"}
        }
        
        result = await notification_service.store_notification(
            notification_data, test_db
        )
        
        assert result["success"] is True
        assert "notification_id" in result
    
    @pytest.mark.asyncio
    async def test_get_user_notifications(self, notification_service, test_db, test_user):
        """Test retrieving user notifications."""
        # First store some notifications
        notifications = [
            {
                "user_id": test_user.id,
                "title": "Notification 1",
                "message": "Message 1",
                "type": "info"
            },
            {
                "user_id": test_user.id,
                "title": "Notification 2",
                "message": "Message 2",
                "type": "warning"
            }
        ]
        
        for notif in notifications:
            await notification_service.store_notification(notif, test_db)
        
        # Retrieve notifications
        result = await notification_service.get_user_notifications(
            test_user.id, test_db, limit=10
        )
        
        assert len(result) >= 2
        assert any(n["title"] == "Notification 1" for n in result)
        assert any(n["title"] == "Notification 2" for n in result)
    
    @pytest.mark.asyncio
    async def test_mark_notification_read(self, notification_service, test_db, test_user):
        """Test marking notification as read."""
        # Store notification
        notification_data = {
            "user_id": test_user.id,
            "title": "Test Notification",
            "message": "Test message",
            "type": "info"
        }
        
        store_result = await notification_service.store_notification(
            notification_data, test_db
        )
        notification_id = store_result["notification_id"]
        
        # Mark as read
        result = await notification_service.mark_as_read(
            notification_id, test_user.id, test_db
        )
        
        assert result["success"] is True


class TestCalendarService:
    """Test calendar integration service."""
    
    @pytest.fixture
    def calendar_service(self):
        """Create calendar service instance."""
        return CalendarService()
    
    @pytest.mark.asyncio
    async def test_create_calendar_event(self, calendar_service):
        """Test creating calendar event."""
        event_data = {
            "title": "Tender Deadline",
            "description": "Submit proposal for XYZ project",
            "start_time": datetime.utcnow() + timedelta(days=7),
            "end_time": datetime.utcnow() + timedelta(days=7, hours=1),
            "attendees": ["user@example.com"],
            "user_id": str(uuid4())
        }
        
        # Mock Google Calendar API
        with patch('google.oauth2.service_account.Credentials.from_service_account_info'), \
             patch('googleapiclient.discovery.build') as mock_build:
            
            mock_service = MagicMock()
            mock_service.events().insert().execute.return_value = {
                "id": "calendar_event_123",
                "status": "confirmed"
            }
            mock_build.return_value = mock_service
            
            result = await calendar_service.create_event(event_data)
            
            assert result["success"] is True
            assert result["event_id"] == "calendar_event_123"
    
    @pytest.mark.asyncio
    async def test_sync_calendar_events(self, calendar_service):
        """Test syncing calendar events."""
        user_id = str(uuid4())
        
        # Mock calendar events from Google
        mock_events = {
            "items": [
                {
                    "id": "event_1",
                    "summary": "Meeting 1",
                    "start": {"dateTime": "2024-01-15T10:00:00Z"},
                    "end": {"dateTime": "2024-01-15T11:00:00Z"}
                },
                {
                    "id": "event_2",
                    "summary": "Meeting 2",
                    "start": {"dateTime": "2024-01-16T14:00:00Z"},
                    "end": {"dateTime": "2024-01-16T15:00:00Z"}
                }
            ]
        }
        
        with patch('google.oauth2.service_account.Credentials.from_service_account_info'), \
             patch('googleapiclient.discovery.build') as mock_build:
            
            mock_service = MagicMock()
            mock_service.events().list().execute.return_value = mock_events
            mock_build.return_value = mock_service
            
            result = await calendar_service.sync_events(user_id)
            
            assert result["success"] is True
            assert result["synced_count"] == 2
            assert result["new_events"] >= 0
    
    @pytest.mark.asyncio
    async def test_get_upcoming_deadlines(self, calendar_service, test_db, test_user):
        """Test getting upcoming tender deadlines."""
        # Mock database query for tenders with approaching deadlines
        mock_tenders = [
            {
                "id": str(uuid4()),
                "title": "Important Tender",
                "deadline": datetime.utcnow() + timedelta(days=1),
                "user_id": test_user.id,
                "company_id": str(uuid4())
            }
        ]
        
        with patch('app.crud.crud_tender.get_upcoming_deadlines') as mock_get_deadlines:
            mock_get_deadlines.return_value = mock_tenders
            
            result = await calendar_service.get_upcoming_deadlines(
                days_ahead=7, db=test_db
            )
            
            assert len(result) == 1
            assert result[0]["title"] == "Important Tender"


class TestQuoteService:
    """Test quote management service."""
    
    @pytest.fixture
    def quote_service(self):
        """Create quote service instance."""
        return QuoteService()
    
    @pytest.mark.asyncio
    async def test_create_quote(self, quote_service, test_db, test_user, test_company):
        """Test creating a quote."""
        # Create test tender
        tender = TenderModel(
            id=uuid4(),
            title="Test Tender for Quote",
            description="Test tender",
            requirements=["req1"],
            budget_range_min=10000,
            budget_range_max=20000,
            deadline=datetime.utcnow() + timedelta(days=30),
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        quote_data = {
            "tender_id": tender.id,
            "supplier_id": test_user.id,
            "total_price": 15000,
            "currency": "USD",
            "delivery_time_days": 45,
            "notes": "Competitive quote with quality delivery",
            "items": [
                {
                    "description": "Development work",
                    "quantity": 1,
                    "unit_price": 15000
                }
            ]
        }
        
        result = await quote_service.create_quote(quote_data, test_db)
        
        assert result["success"] is True
        assert "quote_id" in result
        assert result["total_price"] == 15000
    
    @pytest.mark.asyncio
    async def test_calculate_quote_score(self, quote_service):
        """Test quote scoring algorithm."""
        quote_data = {
            "total_price": 50000,
            "delivery_time_days": 60,
            "supplier_rating": 4.5,
            "proposal_quality": 0.8
        }
        
        tender_criteria = {
            "budget_range_min": 40000,
            "budget_range_max": 80000,
            "max_delivery_days": 90,
            "price_weight": 0.4,
            "time_weight": 0.3,
            "quality_weight": 0.3
        }
        
        score = await quote_service.calculate_quote_score(
            quote_data, tender_criteria
        )
        
        assert 0 <= score <= 100
        assert isinstance(score, (int, float))
    
    @pytest.mark.asyncio
    async def test_compare_quotes(self, quote_service, test_db):
        """Test comparing multiple quotes."""
        quotes_data = [
            {
                "id": str(uuid4()),
                "total_price": 45000,
                "delivery_time_days": 50,
                "supplier_rating": 4.2
            },
            {
                "id": str(uuid4()),
                "total_price": 55000,
                "delivery_time_days": 40,
                "supplier_rating": 4.8
            },
            {
                "id": str(uuid4()),
                "total_price": 50000,
                "delivery_time_days": 45,
                "supplier_rating": 4.5
            }
        ]
        
        comparison = await quote_service.compare_quotes(quotes_data)
        
        assert len(comparison["quotes"]) == 3
        assert "rankings" in comparison
        assert "analysis" in comparison
        assert comparison["best_value_quote"] is not None
    
    @pytest.mark.asyncio
    async def test_generate_quote_report(self, quote_service, test_db, test_user):
        """Test generating quote analysis report."""
        quote_id = str(uuid4())
        
        # Mock quote data
        with patch('app.crud.crud_quote.get') as mock_get_quote:
            mock_quote = MagicMock()
            mock_quote.id = quote_id
            mock_quote.total_price = 50000
            mock_quote.delivery_time_days = 45
            mock_quote.supplier_id = test_user.id
            mock_get_quote.return_value = mock_quote
            
            result = await quote_service.generate_report(
                quote_id, test_db
            )
            
            assert result["success"] is True
            assert "report_url" in result or "report_data" in result


class TestServiceIntegration:
    """Test service integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_tender_workflow(
        self,
        test_db,
        test_user,
        test_company
    ):
        """Test complete tender processing workflow across services."""
        # Initialize services
        ai_service = AIService()
        email_service = EmailService()
        notification_service = NotificationService()
        quote_service = QuoteService()
        
        # Create tender
        tender = TenderModel(
            id=uuid4(),
            title="Full Workflow Test Tender",
            description="Testing complete workflow",
            requirements=["req1", "req2"],
            budget_range_min=20000,
            budget_range_max=50000,
            deadline=datetime.utcnow() + timedelta(days=60),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Mock all external dependencies
        with patch('httpx.AsyncClient.post') as mock_ai, \
             patch('aiosmtplib.send') as mock_email, \
             patch('firebase_admin.messaging.send') as mock_push:
            
            # Mock AI analysis
            mock_ai.return_value.json.return_value = {
                "response": json.dumps({"complexity_score": 0.7})
            }
            mock_ai.return_value.status_code = 200
            
            # Mock email sending
            mock_email.return_value = (200, "OK")
            
            # Mock push notification
            mock_push.return_value = "msg-id-123"
            
            # 1. Analyze tender with AI
            ai_result = await ai_service.analyze_tender(tender, test_db)
            
            # 2. Send notification email
            email_result = await email_service.send_email(
                to_emails=[test_user.email],
                subject="Tender Analysis Complete",
                body="Your tender has been analyzed"
            )
            
            # 3. Send push notification
            push_result = await notification_service.send_push_notification({
                "user_id": str(test_user.id),
                "title": "Analysis Complete",
                "message": "Tender analysis is ready"
            })
            
            # 4. Store notification
            store_result = await notification_service.store_notification({
                "user_id": test_user.id,
                "title": "Analysis Complete",
                "message": "Tender analysis completed",
                "type": "analysis_complete"
            }, test_db)
            
            # Verify workflow completion
            assert ai_result["complexity_score"] == 0.7
            assert email_result is True
            assert push_result["success"] is True
            assert store_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_service_error_propagation(self):
        """Test error handling across service boundaries."""
        ai_service = AIService()
        
        # Test AI service error propagation
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(Exception):
                await ai_service.analyze_tender(MagicMock(), None)
    
    @pytest.mark.asyncio
    async def test_service_performance_monitoring(self):
        """Test service performance and resource usage."""
        email_service = EmailService()
        
        # Test bulk operation performance
        start_time = asyncio.get_event_loop().time()
        
        email_list = [
            {
                "to_emails": [f"user{i}@example.com"],
                "subject": f"Email {i}",
                "body": f"Body {i}"
            } for i in range(10)
        ]
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = (200, "OK")
            
            results = await email_service.send_bulk_emails(email_list)
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            # Should complete within reasonable time
            assert execution_time < 5.0
            assert results["successful"] == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self):
        """Test concurrent service operations."""
        notification_service = NotificationService()
        
        # Create multiple concurrent notification tasks
        tasks = []
        for i in range(5):
            task = notification_service.send_push_notification({
                "user_id": str(uuid4()),
                "title": f"Notification {i}",
                "message": f"Message {i}"
            })
            tasks.append(task)
        
        with patch('firebase_admin.messaging.send') as mock_send:
            mock_send.return_value = "msg-id"
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All tasks should complete successfully
            assert len(results) == 5
            assert all(
                isinstance(r, dict) and r.get("success") is True 
                for r in results if not isinstance(r, Exception)
            )
