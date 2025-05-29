"""
Celery Task Stress Tests

Tests for background task processing under high load.
"""
import asyncio
import pytest
from celery.result import AsyncResult
from unittest.mock import patch, MagicMock

from tests.stress.conftest import StressTestRunner
from app.celery_app import celery_app
from app.tasks.ai_tasks import analyze_tender_ai, generate_quote_ai
from app.tasks.email_tasks import send_email_task, send_bulk_emails
from app.tasks.notification_tasks import send_notification, send_bulk_notifications
from app.tasks.file_tasks import process_document, generate_pdf_report


class TestCeleryTaskStress:
    """Stress tests for Celery task execution."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_task_queue_stress(self, stress_runner: StressTestRunner):
        """Test Celery task queue under stress."""
        task_results = []
        
        async def queue_task(user_id: int, request_id: int):
            """Queue a Celery task."""
            try:
                # Use different task types to stress different parts
                task_types = [
                    lambda: send_notification.delay(
                        user_id=user_id,
                        title=f"Test Notification {request_id}",
                        message="Test message",
                        type="info"
                    ),
                    lambda: process_document.delay(
                        file_path=f"/tmp/test_file_{user_id}_{request_id}.txt",
                        user_id=user_id
                    ),
                    lambda: send_email_task.delay(
                        to_email=f"user{user_id}@test.com",
                        subject=f"Test Email {request_id}",
                        template_name="notification",
                        context={"message": "Test"}
                    )
                ]
                
                task_func = task_types[request_id % len(task_types)]
                result = task_func()
                task_results.append(result)
                
                # Don't wait for completion in stress test
                assert result.id is not None
                
            except Exception as e:
                print(f"Task queue error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(queue_task)
        
        # Wait a bit for some tasks to complete
        await asyncio.sleep(5)
        
        # Check task results
        completed_tasks = 0
        failed_tasks = 0
        
        for result in task_results[:20]:  # Check first 20 tasks
            try:
                if result.ready():
                    if result.successful():
                        completed_tasks += 1
                    else:
                        failed_tasks += 1
            except Exception:
                failed_tasks += 1
        
        print(f"Task queue stress: {metrics.total_requests} tasks queued, {completed_tasks} completed, {failed_tasks} failed")
        
        # Cleanup - revoke remaining tasks
        for result in task_results:
            try:
                result.revoke(terminate=True)
            except:
                pass
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, light_stress_config):
        """Test concurrent task execution."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def concurrent_task(user_id: int, request_id: int):
            """Execute tasks that might run concurrently."""
            try:
                # Simulate AI analysis task
                with patch('app.services.ai_service.analyze_with_ollama') as mock_ai:
                    mock_ai.return_value = {"analysis": f"Result {user_id}-{request_id}"}
                    
                    result = analyze_tender_ai.delay(
                        tender_data={
                            "title": f"Test Tender {request_id}",
                            "description": "Test description",
                            "budget": 100000
                        },
                        user_id=user_id
                    )
                    
                    # Wait briefly for task to start
                    await asyncio.sleep(0.1)
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Concurrent task error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(concurrent_task)
        print(f"Concurrent task execution: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestTaskTypeStress:
    """Stress tests for specific task types."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_email_task_stress(self, light_stress_config):
        """Test email tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def email_task_test(user_id: int, request_id: int):
            """Test email task execution."""
            try:
                with patch('app.services.email_service.send_email') as mock_send:
                    mock_send.return_value = True
                    
                    result = send_email_task.delay(
                        to_email=f"user{user_id}@test.com",
                        subject=f"Stress Test Email {request_id}",
                        template_name="notification",
                        context={
                            "user_name": f"User {user_id}",
                            "message": f"Test message {request_id}"
                        }
                    )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Email task error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(email_task_test)
        print(f"Email task stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_ai_task_stress(self, light_stress_config):
        """Test AI tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def ai_task_test(user_id: int, request_id: int):
            """Test AI task execution."""
            try:
                with patch('app.services.ai_service.analyze_with_ollama') as mock_ai:
                    mock_ai.return_value = {
                        "analysis": f"AI analysis result {request_id}",
                        "confidence": 0.85,
                        "recommendations": ["recommendation 1", "recommendation 2"]
                    }
                    
                    # Test different AI tasks
                    if request_id % 2 == 0:
                        result = analyze_tender_ai.delay(
                            tender_data={
                                "title": f"Tender {request_id}",
                                "description": "Description for analysis",
                                "budget": 50000 + (request_id * 1000)
                            },
                            user_id=user_id
                        )
                    else:
                        result = generate_quote_ai.delay(
                            tender_requirements={
                                "items": [{"description": "Item 1", "quantity": 10}],
                                "budget": 25000
                            },
                            supplier_id=user_id,
                            user_id=user_id
                        )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"AI task error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(ai_task_test)
        print(f"AI task stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_file_processing_stress(self, light_stress_config):
        """Test file processing tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def file_task_test(user_id: int, request_id: int):
            """Test file processing task execution."""
            try:
                with patch('app.services.file_service.process_file') as mock_process:
                    mock_process.return_value = {
                        "processed": True,
                        "file_size": 1024 * request_id,
                        "pages": request_id % 10 + 1
                    }
                    
                    # Test different file processing tasks
                    if request_id % 3 == 0:
                        result = process_document.delay(
                            file_path=f"/tmp/test_document_{user_id}_{request_id}.pdf",
                            user_id=user_id
                        )
                    elif request_id % 3 == 1:
                        result = generate_pdf_report.delay(
                            report_type="tender_analysis",
                            data={
                                "tender_id": request_id,
                                "analysis_data": {"score": 85}
                            },
                            user_id=user_id
                        )
                    else:
                        result = process_document.delay(
                            file_path=f"/tmp/test_spreadsheet_{user_id}_{request_id}.xlsx",
                            user_id=user_id
                        )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"File processing task error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(file_task_test)
        print(f"File processing stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestTaskFailureHandling:
    """Stress tests for task failure scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_task_retry_stress(self, light_stress_config):
        """Test task retry behavior under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def retry_task_test(user_id: int, request_id: int):
            """Test task retry scenarios."""
            try:
                # Mock a service that fails sometimes
                with patch('app.services.email_service.send_email') as mock_send:
                    # Fail 30% of the time to test retry logic
                    if request_id % 3 == 0:
                        mock_send.side_effect = Exception("Temporary service failure")
                    else:
                        mock_send.return_value = True
                    
                    result = send_email_task.delay(
                        to_email=f"retry_test{user_id}@test.com",
                        subject=f"Retry Test {request_id}",
                        template_name="notification",
                        context={"message": "Retry test"}
                    )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Retry task error: {e}")
                # Allow some failures for retry testing
                if "Temporary service failure" not in str(e):
                    raise e
        
        metrics = await stress_runner.run_concurrent_test(retry_task_test)
        print(f"Task retry stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_task_timeout_stress(self, light_stress_config):
        """Test task timeout handling under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def timeout_task_test(user_id: int, request_id: int):
            """Test task timeout scenarios."""
            try:
                with patch('app.services.ai_service.analyze_with_ollama') as mock_ai:
                    # Simulate long-running tasks that might timeout
                    if request_id % 4 == 0:
                        # Simulate a task that would timeout
                        mock_ai.side_effect = Exception("Task timeout")
                    else:
                        mock_ai.return_value = {"analysis": "quick result"}
                    
                    result = analyze_tender_ai.delay(
                        tender_data={
                            "title": f"Timeout Test Tender {request_id}",
                            "description": "Complex analysis required",
                            "budget": 1000000
                        },
                        user_id=user_id
                    )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Timeout task error: {e}")
                # Allow timeout errors
                if "timeout" not in str(e).lower():
                    raise e
        
        metrics = await stress_runner.run_concurrent_test(timeout_task_test)
        print(f"Task timeout stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestBulkTaskStress:
    """Stress tests for bulk task operations."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_bulk_email_stress(self, light_stress_config):
        """Test bulk email tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def bulk_email_test(user_id: int, request_id: int):
            """Test bulk email task execution."""
            try:
                with patch('app.services.email_service.send_email') as mock_send:
                    mock_send.return_value = True
                    
                    # Create email list
                    emails = [
                        {
                            "to_email": f"bulk_user_{request_id}_{i}@test.com",
                            "subject": f"Bulk Email {request_id}-{i}",
                            "template_name": "notification",
                            "context": {"message": f"Bulk message {i}"}
                        }
                        for i in range(5)  # 5 emails per bulk task
                    ]
                    
                    result = send_bulk_emails.delay(emails)
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Bulk email error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(bulk_email_test)
        print(f"Bulk email stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_bulk_notification_stress(self, light_stress_config):
        """Test bulk notification tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def bulk_notification_test(user_id: int, request_id: int):
            """Test bulk notification task execution."""
            try:
                with patch('app.services.notification_service.send_notification') as mock_send:
                    mock_send.return_value = True
                    
                    # Create notification list
                    notifications = [
                        {
                            "user_id": user_id + i,
                            "title": f"Bulk Notification {request_id}-{i}",
                            "message": f"Bulk notification message {i}",
                            "type": "info"
                        }
                        for i in range(3)  # 3 notifications per bulk task
                    ]
                    
                    result = send_bulk_notifications.delay(notifications)
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Bulk notification error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(bulk_notification_test)
        print(f"Bulk notification stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestTaskResourceUsage:
    """Stress tests for task resource usage."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_memory_intensive_tasks(self, light_stress_config):
        """Test memory-intensive tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def memory_task_test(user_id: int, request_id: int):
            """Test memory-intensive task execution."""
            try:
                with patch('app.services.file_service.process_large_file') as mock_process:
                    # Simulate processing large files
                    mock_process.return_value = {
                        "processed": True,
                        "memory_used": f"{request_id * 10}MB",
                        "processing_time": f"{request_id}s"
                    }
                    
                    result = process_document.delay(
                        file_path=f"/tmp/large_file_{user_id}_{request_id}.pdf",
                        user_id=user_id,
                        processing_options={"high_quality": True, "ocr": True}
                    )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"Memory task error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(memory_task_test)
        print(f"Memory-intensive task stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio 
    async def test_cpu_intensive_tasks(self, light_stress_config):
        """Test CPU-intensive tasks under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def cpu_task_test(user_id: int, request_id: int):
            """Test CPU-intensive task execution."""
            try:
                with patch('app.services.ai_service.complex_analysis') as mock_analysis:
                    # Simulate CPU-intensive AI analysis
                    mock_analysis.return_value = {
                        "analysis": f"Complex analysis result {request_id}",
                        "computation_time": f"{request_id * 2}s",
                        "cpu_usage": f"{request_id * 5}%"
                    }
                    
                    result = analyze_tender_ai.delay(
                        tender_data={
                            "title": f"Complex Tender {request_id}",
                            "description": "Requires extensive analysis",
                            "budget": 5000000,
                            "complexity": "high"
                        },
                        user_id=user_id,
                        analysis_type="comprehensive"
                    )
                    
                    assert result.id is not None
                    
            except Exception as e:
                print(f"CPU task error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(cpu_task_test)
        print(f"CPU-intensive task stress: {metrics.successful_requests}/{metrics.total_requests} successful")
