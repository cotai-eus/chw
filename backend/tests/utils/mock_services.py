"""
Mock implementations for external services used in testing.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, Mock

import pytest


class MockAIService:
    """Mock AI service for testing without actual AI calls."""
    
    def __init__(self):
        self.processing_results = {}
        self.processing_delay = 0.1  # Fast for tests
        self.should_fail = False
        self.fail_rate = 0.0
        
    async def process_document(self, document_content: bytes, document_type: str = "pdf") -> Dict[str, Any]:
        """Mock document processing."""
        if self.should_fail or (self.fail_rate > 0 and __import__('random').random() < self.fail_rate):
            raise Exception("AI processing failed")
        
        await asyncio.sleep(self.processing_delay)
        
        return {
            "extracted_text": "Mock extracted text from document",
            "entities": [
                {"type": "organization", "text": "Test Company", "confidence": 0.95},
                {"type": "date", "text": "2024-12-31", "confidence": 0.88},
                {"type": "monetary", "text": "$100,000", "confidence": 0.92}
            ],
            "summary": "Mock AI-generated summary of the document",
            "risk_assessment": {
                "overall_risk": "medium",
                "confidence": 0.85,
                "factors": [
                    {"factor": "complexity", "score": 0.6, "description": "Moderate complexity"},
                    {"factor": "timeline", "score": 0.4, "description": "Adequate timeline"}
                ]
            },
            "suggested_structure": {
                "sections": [
                    {"title": "Executive Summary", "order": 1},
                    {"title": "Technical Specifications", "order": 2},
                    {"title": "Pricing", "order": 3}
                ]
            },
            "processing_time": self.processing_delay,
            "model_used": "mock-ai-model",
            "tokens_used": 1500
        }
    
    async def analyze_tender(self, tender_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tender analysis."""
        await asyncio.sleep(self.processing_delay)
        
        return {
            "complexity_score": 0.7,
            "estimated_hours": 120,
            "recommended_team_size": 3,
            "key_requirements": [
                "Python development experience",
                "Database design knowledge",
                "API development skills"
            ],
            "potential_challenges": [
                "Tight deadline",
                "Complex integration requirements"
            ],
            "success_probability": 0.75
        }
    
    async def generate_quote_template(self, tender_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock quote template generation."""
        await asyncio.sleep(self.processing_delay)
        
        return {
            "template": {
                "sections": [
                    {
                        "title": "Project Overview",
                        "content": "Mock project overview content",
                        "order": 1
                    },
                    {
                        "title": "Technical Approach",
                        "content": "Mock technical approach content",
                        "order": 2
                    },
                    {
                        "title": "Timeline",
                        "content": "Mock timeline content",
                        "order": 3
                    }
                ]
            },
            "estimated_price": 85000.0,
            "confidence": 0.8,
            "assumptions": [
                "Standard development practices",
                "Regular communication cycles",
                "Access to required resources"
            ]
        }
    
    def set_failure_mode(self, should_fail: bool = True, fail_rate: float = 0.0):
        """Configure failure behavior for testing error scenarios."""
        self.should_fail = should_fail
        self.fail_rate = fail_rate
    
    def set_processing_delay(self, delay: float):
        """Set processing delay for performance testing."""
        self.processing_delay = delay


class MockEmailService:
    """Mock email service for testing without sending actual emails."""
    
    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []
        self.should_fail = False
        self.delivery_delay = 0.05  # Fast for tests
        
    async def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Mock email sending."""
        if self.should_fail:
            raise Exception("Email sending failed")
        
        await asyncio.sleep(self.delivery_delay)
        
        email_data = {
            "to": to if isinstance(to, list) else [to],
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "attachments": attachments or [],
            "sent_at": datetime.utcnow(),
            "message_id": f"mock-email-{len(self.sent_emails) + 1}",
            "status": "sent"
        }
        
        self.sent_emails.append(email_data)
        return email_data
    
    async def send_notification_email(self, user_email: str, notification_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock notification email sending."""
        subject_map = {
            "tender_created": "New Tender Available",
            "quote_submitted": "Quote Submitted Successfully",
            "deadline_reminder": "Tender Deadline Reminder",
            "quote_status_changed": "Quote Status Updated"
        }
        
        return await self.send_email(
            to=user_email,
            subject=subject_map.get(notification_type, "Notification"),
            html_content=f"<p>Mock notification: {notification_type}</p><p>Data: {data}</p>",
            text_content=f"Mock notification: {notification_type}\nData: {data}"
        )
    
    async def send_bulk_email(self, recipients: List[str], subject: str, content: str) -> List[Dict[str, Any]]:
        """Mock bulk email sending."""
        results = []
        for recipient in recipients:
            result = await self.send_email(recipient, subject, content)
            results.append(result)
        return results
    
    def get_sent_emails(self, to_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sent emails, optionally filtered by recipient."""
        if to_email:
            return [email for email in self.sent_emails if to_email in email["to"]]
        return self.sent_emails.copy()
    
    def clear_sent_emails(self):
        """Clear sent emails history."""
        self.sent_emails.clear()
    
    def set_failure_mode(self, should_fail: bool = True):
        """Configure failure behavior."""
        self.should_fail = should_fail


class MockFileService:
    """Mock file service for testing without actual file operations."""
    
    def __init__(self):
        self.stored_files: Dict[str, Dict[str, Any]] = {}
        self.should_fail = False
        
    async def upload_file(self, file_content: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """Mock file upload."""
        if self.should_fail:
            raise Exception("File upload failed")
        
        file_id = f"mock-file-{len(self.stored_files) + 1}"
        file_data = {
            "id": file_id,
            "filename": filename,
            "content_type": content_type,
            "size": len(file_content),
            "content": file_content,
            "uploaded_at": datetime.utcnow(),
            "url": f"https://mock-storage.example.com/files/{file_id}",
            "thumbnail_url": f"https://mock-storage.example.com/thumbnails/{file_id}" if content_type.startswith("image/") else None
        }
        
        self.stored_files[file_id] = file_data
        return file_data
    
    async def download_file(self, file_id: str) -> bytes:
        """Mock file download."""
        if self.should_fail:
            raise Exception("File download failed")
        
        if file_id not in self.stored_files:
            raise FileNotFoundError(f"File {file_id} not found")
        
        return self.stored_files[file_id]["content"]
    
    async def delete_file(self, file_id: str) -> bool:
        """Mock file deletion."""
        if self.should_fail:
            raise Exception("File deletion failed")
        
        if file_id in self.stored_files:
            del self.stored_files[file_id]
            return True
        return False
    
    async def process_file(self, file_id: str, processing_type: str = "text_extraction") -> Dict[str, Any]:
        """Mock file processing."""
        if self.should_fail:
            raise Exception("File processing failed")
        
        if file_id not in self.stored_files:
            raise FileNotFoundError(f"File {file_id} not found")
        
        file_data = self.stored_files[file_id]
        
        processing_results = {
            "text_extraction": {
                "extracted_text": "Mock extracted text from file",
                "page_count": 5,
                "word_count": 1200,
                "language": "en"
            },
            "image_analysis": {
                "objects_detected": ["document", "text", "logo"],
                "text_regions": [
                    {"text": "Header Text", "confidence": 0.95, "bbox": [10, 10, 200, 30]},
                    {"text": "Body Content", "confidence": 0.92, "bbox": [10, 50, 400, 300]}
                ]
            },
            "document_validation": {
                "is_valid": True,
                "format_compliance": 0.95,
                "issues": []
            }
        }
        
        return {
            "file_id": file_id,
            "processing_type": processing_type,
            "results": processing_results.get(processing_type, {}),
            "processed_at": datetime.utcnow(),
            "processing_time": 0.1
        }
    
    def get_stored_files(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored files."""
        return self.stored_files.copy()
    
    def clear_stored_files(self):
        """Clear all stored files."""
        self.stored_files.clear()
    
    def set_failure_mode(self, should_fail: bool = True):
        """Configure failure behavior."""
        self.should_fail = should_fail


class MockRedisService:
    """Mock Redis service for testing without actual Redis connection."""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.expiry: Dict[str, datetime] = {}
        self.should_fail = False
        
    async def get(self, key: str) -> Optional[str]:
        """Mock Redis GET."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        
        if key in self.expiry and datetime.utcnow() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock Redis SET."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        
        self.data[key] = value
        
        if ex:
            self.expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
        
        return True
    
    async def delete(self, key: str) -> int:
        """Mock Redis DELETE."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        
        deleted = 0
        if key in self.data:
            del self.data[key]
            deleted += 1
        
        if key in self.expiry:
            del self.expiry[key]
        
        return deleted
    
    async def exists(self, key: str) -> int:
        """Mock Redis EXISTS."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        
        if key in self.expiry and datetime.utcnow() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return 0
        
        return 1 if key in self.data else 0
    
    async def incr(self, key: str) -> int:
        """Mock Redis INCR."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        
        current_value = int(self.data.get(key, 0))
        new_value = current_value + 1
        self.data[key] = str(new_value)
        return new_value
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Mock Redis EXPIRE."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        
        if key in self.data:
            self.expiry[key] = datetime.utcnow() + timedelta(seconds=seconds)
            return True
        return False
    
    def clear_all(self):
        """Clear all data."""
        self.data.clear()
        self.expiry.clear()
    
    def set_failure_mode(self, should_fail: bool = True):
        """Configure failure behavior."""
        self.should_fail = should_fail


class MockMongoService:
    """Mock MongoDB service for testing without actual MongoDB connection."""
    
    def __init__(self):
        self.collections: Dict[str, List[Dict[str, Any]]] = {}
        self.should_fail = False
        
    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Mock MongoDB insert one."""
        if self.should_fail:
            raise Exception("MongoDB connection failed")
        
        if collection not in self.collections:
            self.collections[collection] = []
        
        # Add auto-generated _id
        document_id = f"mock-id-{len(self.collections[collection]) + 1}"
        document_with_id = {**document, "_id": document_id, "created_at": datetime.utcnow()}
        
        self.collections[collection].append(document_with_id)
        return document_id
    
    async def find_one(self, collection: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mock MongoDB find one."""
        if self.should_fail:
            raise Exception("MongoDB connection failed")
        
        if collection not in self.collections:
            return None
        
        for document in self.collections[collection]:
            if all(document.get(key) == value for key, value in filter_dict.items()):
                return document
        
        return None
    
    async def find_many(self, collection: str, filter_dict: Dict[str, Any] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Mock MongoDB find many."""
        if self.should_fail:
            raise Exception("MongoDB connection failed")
        
        if collection not in self.collections:
            return []
        
        documents = self.collections[collection]
        
        if filter_dict:
            documents = [
                doc for doc in documents
                if all(doc.get(key) == value for key, value in filter_dict.items())
            ]
        
        if limit:
            documents = documents[:limit]
        
        return documents
    
    async def update_one(self, collection: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> bool:
        """Mock MongoDB update one."""
        if self.should_fail:
            raise Exception("MongoDB connection failed")
        
        if collection not in self.collections:
            return False
        
        for document in self.collections[collection]:
            if all(document.get(key) == value for key, value in filter_dict.items()):
                document.update(update_dict)
                document["updated_at"] = datetime.utcnow()
                return True
        
        return False
    
    async def delete_one(self, collection: str, filter_dict: Dict[str, Any]) -> bool:
        """Mock MongoDB delete one."""
        if self.should_fail:
            raise Exception("MongoDB connection failed")
        
        if collection not in self.collections:
            return False
        
        for i, document in enumerate(self.collections[collection]):
            if all(document.get(key) == value for key, value in filter_dict.items()):
                del self.collections[collection][i]
                return True
        
        return False
    
    def get_collection_data(self, collection: str) -> List[Dict[str, Any]]:
        """Get all documents from a collection."""
        return self.collections.get(collection, []).copy()
    
    def clear_collection(self, collection: str):
        """Clear a collection."""
        if collection in self.collections:
            self.collections[collection].clear()
    
    def clear_all_collections(self):
        """Clear all collections."""
        self.collections.clear()
    
    def set_failure_mode(self, should_fail: bool = True):
        """Configure failure behavior."""
        self.should_fail = should_fail


class MockCeleryService:
    """Mock Celery service for testing background tasks."""
    
    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
        self.should_fail = False
        self.execution_delay = 0.05  # Fast for tests
        
    def delay(self, task_name: str, *args, **kwargs) -> 'MockCeleryResult':
        """Mock task.delay()."""
        if self.should_fail:
            raise Exception("Task submission failed")
        
        task_id = f"mock-task-{len(self.tasks) + 1}"
        task_data = {
            "id": task_id,
            "name": task_name,
            "args": args,
            "kwargs": kwargs,
            "status": "PENDING",
            "submitted_at": datetime.utcnow(),
            "result": None,
            "error": None
        }
        
        self.tasks.append(task_data)
        return MockCeleryResult(task_id, self)
    
    def apply_async(self, task_name: str, args=None, kwargs=None, **options) -> 'MockCeleryResult':
        """Mock task.apply_async()."""
        return self.delay(task_name, *(args or []), **(kwargs or {}))
    
    async def execute_task(self, task_id: str, result: Any = None, error: Exception = None):
        """Mock task execution."""
        for task in self.tasks:
            if task["id"] == task_id:
                if error:
                    task["status"] = "FAILURE"
                    task["error"] = str(error)
                else:
                    task["status"] = "SUCCESS"
                    task["result"] = result or f"Mock result for {task['name']}"
                
                task["completed_at"] = datetime.utcnow()
                break
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        for task in self.tasks:
            if task["id"] == task_id:
                return task.copy()
        return None
    
    def get_tasks_by_name(self, task_name: str) -> List[Dict[str, Any]]:
        """Get tasks by name."""
        return [task.copy() for task in self.tasks if task["name"] == task_name]
    
    def clear_tasks(self):
        """Clear all tasks."""
        self.tasks.clear()
    
    def set_failure_mode(self, should_fail: bool = True):
        """Configure failure behavior."""
        self.should_fail = should_fail


class MockCeleryResult:
    """Mock Celery task result."""
    
    def __init__(self, task_id: str, celery_service: MockCeleryService):
        self.id = task_id
        self.celery_service = celery_service
    
    @property
    def status(self) -> str:
        """Get task status."""
        task = self.celery_service.get_task(self.id)
        return task["status"] if task else "UNKNOWN"
    
    @property
    def result(self) -> Any:
        """Get task result."""
        task = self.celery_service.get_task(self.id)
        return task["result"] if task else None
    
    @property
    def ready(self) -> bool:
        """Check if task is ready."""
        return self.status in ["SUCCESS", "FAILURE"]
    
    @property
    def successful(self) -> bool:
        """Check if task was successful."""
        return self.status == "SUCCESS"
    
    @property
    def failed(self) -> bool:
        """Check if task failed."""
        return self.status == "FAILURE"
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """Get task result (blocking)."""
        task = self.celery_service.get_task(self.id)
        if task and task["status"] == "SUCCESS":
            return task["result"]
        elif task and task["status"] == "FAILURE":
            raise Exception(task["error"])
        else:
            raise Exception("Task not completed")


class MockCalendarService:
    """Mock calendar service for testing calendar integrations."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.should_fail = False
        
    async def create_event(self, title: str, start_time: datetime, end_time: datetime, description: str = "") -> Dict[str, Any]:
        """Mock calendar event creation."""
        if self.should_fail:
            raise Exception("Calendar service failed")
        
        event_id = f"mock-event-{len(self.events) + 1}"
        event_data = {
            "id": event_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "created_at": datetime.utcnow(),
            "calendar_url": f"https://calendar.google.com/event?eid={event_id}",
            "status": "confirmed"
        }
        
        self.events.append(event_data)
        return event_data
    
    async def update_event(self, event_id: str, **updates) -> Dict[str, Any]:
        """Mock calendar event update."""
        if self.should_fail:
            raise Exception("Calendar service failed")
        
        for event in self.events:
            if event["id"] == event_id:
                event.update(updates)
                event["updated_at"] = datetime.utcnow()
                return event
        
        raise Exception(f"Event {event_id} not found")
    
    async def delete_event(self, event_id: str) -> bool:
        """Mock calendar event deletion."""
        if self.should_fail:
            raise Exception("Calendar service failed")
        
        for i, event in enumerate(self.events):
            if event["id"] == event_id:
                del self.events[i]
                return True
        
        return False
    
    async def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Mock get events in date range."""
        if self.should_fail:
            raise Exception("Calendar service failed")
        
        return [
            event for event in self.events
            if start_date <= event["start_time"] <= end_date
        ]
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all events."""
        return self.events.copy()
    
    def clear_events(self):
        """Clear all events."""
        self.events.clear()
    
    def set_failure_mode(self, should_fail: bool = True):
        """Configure failure behavior."""
        self.should_fail = should_fail
