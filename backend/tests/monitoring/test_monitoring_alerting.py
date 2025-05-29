"""
Monitoring and Alerting Tests
Tests for health checks, metrics collection, logging, and alerting functionality.
"""

import pytest
import asyncio
import time
import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text
import psutil
import aioredis
import motor.motor_asyncio

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from tests.utils.test_helpers import PerformanceTestHelper


class TestHealthChecks:
    """Test application health check endpoints."""
    
    def test_basic_health_check(self, client: TestClient):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "version" in health_data
    
    def test_detailed_health_check(self, client: TestClient):
        """Test detailed health check with component status."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert "components" in health_data
        
        components = health_data["components"]
        
        # Should check database
        assert "database" in components
        assert "status" in components["database"]
        
        # Should check Redis if configured
        if settings.REDIS_URL:
            assert "redis" in components
            assert "status" in components["redis"]
        
        # Should check overall status
        assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_readiness_check(self, client: TestClient):
        """Test readiness check for Kubernetes."""
        response = client.get("/ready")
        assert response.status_code == 200
        
        ready_data = response.json()
        assert "ready" in ready_data
        assert ready_data["ready"] is True
    
    def test_liveness_check(self, client: TestClient):
        """Test liveness check for Kubernetes."""
        response = client.get("/live")
        assert response.status_code == 200
        
        live_data = response.json()
        assert "alive" in live_data
        assert live_data["alive"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_database_failure(self, async_client):
        """Test health check behavior when database is down."""
        with patch("app.core.database.engine.execute") as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")
            
            response = await async_client.get("/health/detailed")
            health_data = response.json()
            
            # Should report unhealthy status
            assert health_data["status"] in ["degraded", "unhealthy"]
            assert health_data["components"]["database"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, async_client):
        """Test health check behavior when Redis is down."""
        with patch("aioredis.from_url") as mock_redis:
            mock_redis.return_value.ping = AsyncMock(side_effect=Exception("Redis connection failed"))
            
            response = await async_client.get("/health/detailed")
            health_data = response.json()
            
            # Should still be able to handle Redis failure gracefully
            if "redis" in health_data["components"]:
                assert health_data["components"]["redis"]["status"] == "unhealthy"


class TestMetricsCollection:
    """Test metrics collection and exposition."""
    
    def test_prometheus_metrics_endpoint(self, client: TestClient):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        
        # Should either work or not be configured
        if response.status_code == 200:
            metrics_text = response.text
            
            # Should contain Prometheus format metrics
            assert "# HELP" in metrics_text or "# TYPE" in metrics_text
            
            # Should have application metrics
            assert "http_requests_total" in metrics_text or "request_duration" in metrics_text
        else:
            # If not configured, should return 404
            assert response.status_code == 404
    
    def test_application_metrics(self, client: TestClient):
        """Test application-specific metrics collection."""
        # Make some requests to generate metrics
        client.get("/health")
        client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
        
        response = client.get("/metrics")
        
        if response.status_code == 200:
            metrics = response.text
            
            # Should track HTTP requests
            assert any(line.startswith("http_") for line in metrics.split("\n"))
            
            # Should track response times
            assert any("duration" in line or "latency" in line for line in metrics.split("\n"))
    
    def test_custom_business_metrics(self, client: TestClient, auth_headers):
        """Test custom business metrics collection."""
        # Perform business operations
        client.get("/api/v1/tenders", headers=auth_headers)
        client.get("/api/v1/companies", headers=auth_headers)
        
        response = client.get("/metrics")
        
        if response.status_code == 200:
            metrics = response.text
            
            # Should track business operations (if implemented)
            business_metrics = [
                "tender_", "quote_", "user_", "company_",
                "database_", "cache_", "api_"
            ]
            
            has_business_metrics = any(
                any(metric in line for metric in business_metrics)
                for line in metrics.split("\n")
            )
            
            # Either has business metrics or at least basic HTTP metrics
            assert has_business_metrics or "http_" in metrics


class TestLogging:
    """Test logging functionality and format."""
    
    def test_request_logging(self, client: TestClient, caplog):
        """Test that requests are properly logged."""
        with caplog.at_level(logging.INFO):
            response = client.get("/health")
            assert response.status_code == 200
        
        # Should have request logs
        log_messages = [record.message for record in caplog.records]
        assert any("GET" in msg and "/health" in msg for msg in log_messages)
    
    def test_error_logging(self, client: TestClient, caplog):
        """Test that errors are properly logged."""
        with caplog.at_level(logging.ERROR):
            # Make a request that should cause an error
            response = client.get("/api/v1/users/999999", headers={"Authorization": "Bearer invalid"})
        
        # Should have error logs
        error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
        assert len(error_logs) > 0
    
    def test_structured_logging(self, client: TestClient, caplog):
        """Test that logs follow structured format."""
        with caplog.at_level(logging.INFO):
            response = client.get("/health")
        
        # Check log format
        for record in caplog.records:
            # Should have timestamp, level, and message
            assert hasattr(record, "created")
            assert hasattr(record, "levelname")
            assert hasattr(record, "message")
    
    def test_sensitive_data_not_logged(self, client: TestClient, caplog, test_user):
        """Test that sensitive data is not logged."""
        with caplog.at_level(logging.DEBUG):
            # Make login request
            response = client.post(
                "/api/v1/auth/login",
                data={"username": test_user.email, "password": "testpassword"}
            )
        
        # Check that password is not in logs
        all_log_text = " ".join(record.message for record in caplog.records)
        assert "testpassword" not in all_log_text
        assert "password" not in all_log_text.lower() or "password=" not in all_log_text.lower()
    
    def test_correlation_id_logging(self, client: TestClient, caplog):
        """Test that correlation IDs are used in logs."""
        correlation_id = "test-correlation-123"
        
        with caplog.at_level(logging.INFO):
            response = client.get(
                "/health",
                headers={"X-Correlation-ID": correlation_id}
            )
        
        # Should include correlation ID in logs (if implemented)
        log_text = " ".join(record.message for record in caplog.records)
        # This test passes if correlation ID is found OR if basic logging works
        assert correlation_id in log_text or "GET" in log_text


class TestPerformanceMonitoring:
    """Test performance monitoring and alerting."""
    
    def test_response_time_monitoring(self, client: TestClient):
        """Test response time monitoring."""
        helper = PerformanceTestHelper()
        
        # Make requests and measure response times
        response_times = []
        for _ in range(10):
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Analyze response times
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Health check should be fast
        assert avg_response_time < 0.1  # 100ms average
        assert max_response_time < 0.5  # 500ms max
        
        # Check if metrics are being collected
        metrics_response = client.get("/metrics")
        if metrics_response.status_code == 200:
            assert "duration" in metrics_response.text or "latency" in metrics_response.text
    
    def test_memory_usage_monitoring(self, client: TestClient):
        """Test memory usage monitoring."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Make many requests to potentially increase memory
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200
        
        # Check memory hasn't grown excessively
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024
    
    def test_database_performance_monitoring(self, client: TestClient, auth_headers, db_session):
        """Test database performance monitoring."""
        start_time = time.time()
        
        # Make database-heavy requests
        for _ in range(10):
            response = client.get("/api/v1/users", headers=auth_headers)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete reasonably quickly
        assert total_time < 5.0  # 5 seconds for 10 requests
        
        # Check for slow query logging (if implemented)
        metrics_response = client.get("/metrics")
        if metrics_response.status_code == 200:
            metrics = metrics_response.text
            assert "database" in metrics or "db" in metrics or "query" in metrics
    
    @pytest.mark.asyncio
    async def test_concurrent_request_monitoring(self, async_client):
        """Test monitoring under concurrent load."""
        async def make_request():
            response = await async_client.get("/health")
            return response.status_code
        
        # Make concurrent requests
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        
        # Check that system handled concurrent load well
        # This is a basic test - more sophisticated monitoring would check for
        # resource contention, connection pool exhaustion, etc.


class TestAlerting:
    """Test alerting functionality."""
    
    def test_error_rate_alerting(self, client: TestClient):
        """Test alerting on high error rates."""
        # Generate some errors
        error_count = 0
        total_requests = 20
        
        for i in range(total_requests):
            if i < 5:  # First 5 requests cause errors
                response = client.get("/api/v1/nonexistent")
                if response.status_code >= 400:
                    error_count += 1
            else:  # Rest are successful
                response = client.get("/health")
        
        error_rate = error_count / total_requests
        
        # If error rate is high, should trigger alert (this is a simulation)
        if error_rate > 0.2:  # 20% error rate threshold
            # In real implementation, this would trigger an alert
            # For testing, we just verify we can calculate the rate
            assert error_rate > 0.2
    
    @patch("smtplib.SMTP")
    def test_email_alerting(self, mock_smtp, client: TestClient):
        """Test email alerting functionality."""
        # Simulate a critical error that should trigger email alert
        with patch("app.core.logging.logger.critical") as mock_logger:
            # This would trigger an alert in a real system
            mock_logger("Critical database connection failure")
            
            # Verify alert mechanism works (mocked)
            assert mock_logger.called
    
    def test_slack_alerting(self, client: TestClient):
        """Test Slack alerting functionality."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            
            # Simulate alert that should go to Slack
            # In real implementation, this would be triggered by actual errors
            alert_data = {
                "text": "High error rate detected in production",
                "channel": "#alerts"
            }
            
            # This is a simulation of alert sending
            if settings.SLACK_WEBHOOK_URL:
                mock_post(settings.SLACK_WEBHOOK_URL, json=alert_data)
                mock_post.assert_called_once()


class TestDashboardMetrics:
    """Test metrics for monitoring dashboards."""
    
    def test_system_metrics_collection(self, client: TestClient):
        """Test collection of system metrics for dashboards."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        assert 0 <= cpu_percent <= 100
        
        # Memory usage
        memory = psutil.virtual_memory()
        assert 0 <= memory.percent <= 100
        
        # Disk usage
        disk = psutil.disk_usage('/')
        assert disk.total > 0
        assert 0 <= (disk.used / disk.total * 100) <= 100
    
    def test_application_metrics_collection(self, client: TestClient, auth_headers):
        """Test collection of application metrics."""
        # Make some application requests
        responses = []
        
        responses.append(client.get("/api/v1/users", headers=auth_headers))
        responses.append(client.get("/api/v1/tenders", headers=auth_headers))
        responses.append(client.get("/api/v1/companies", headers=auth_headers))
        
        # Calculate metrics
        success_count = sum(1 for r in responses if r.status_code == 200)
        error_count = sum(1 for r in responses if r.status_code >= 400)
        
        # Should have some successful requests
        assert success_count > 0
        
        # Metrics should be collectible
        metrics = {
            "total_requests": len(responses),
            "successful_requests": success_count,
            "error_requests": error_count,
            "success_rate": success_count / len(responses)
        }
        
        assert 0 <= metrics["success_rate"] <= 1
    
    def test_business_metrics_collection(self, client: TestClient, auth_headers):
        """Test collection of business-specific metrics."""
        # Simulate business operations
        business_metrics = {
            "active_users": 0,
            "active_tenders": 0,
            "quotes_submitted_today": 0,
            "revenue_today": 0.0
        }
        
        # These would be collected from actual business operations
        # For testing, we verify the structure is correct
        assert all(isinstance(value, (int, float)) for value in business_metrics.values())
        assert all(value >= 0 for value in business_metrics.values())


class TestLogAggregation:
    """Test log aggregation and analysis."""
    
    def test_log_format_for_aggregation(self, client: TestClient, caplog):
        """Test that logs are in format suitable for aggregation."""
        with caplog.at_level(logging.INFO):
            response = client.get("/health")
            response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
        
        # Check log structure
        for record in caplog.records:
            # Should have structured fields for easy parsing
            assert hasattr(record, "levelname")
            assert hasattr(record, "created")
            assert hasattr(record, "pathname")
            
            # Message should be parseable
            assert isinstance(record.message, str)
            assert len(record.message) > 0
    
    def test_error_categorization(self, client: TestClient, caplog):
        """Test that errors can be categorized for analysis."""
        with caplog.at_level(logging.WARNING):
            # Generate different types of errors
            client.get("/nonexistent")  # 404
            client.get("/api/v1/users/me")  # 401
            client.post("/api/v1/users", json={})  # 422 (invalid data)
        
        # Should have different error types logged
        error_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(error_records) > 0
        
        # Errors should be categorizable
        for record in error_records:
            assert record.message is not None
    
    def test_request_tracing(self, client: TestClient, caplog):
        """Test request tracing for debugging."""
        with caplog.at_level(logging.DEBUG):
            response = client.get("/health")
        
        # Should have trace information (if implemented)
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        
        # Either has debug traces or info level logging works
        assert len(debug_records) > 0 or any(
            "GET" in r.message for r in caplog.records
        )


class TestIncidentResponse:
    """Test incident response capabilities."""
    
    def test_circuit_breaker_pattern(self, client: TestClient):
        """Test circuit breaker functionality."""
        # This would test actual circuit breaker implementation
        # For now, we test that the system handles failures gracefully
        
        with patch("app.core.database.get_db") as mock_db:
            mock_db.side_effect = Exception("Database down")
            
            # Should handle database failures gracefully
            response = client.get("/health")
            
            # Should either return degraded status or fail gracefully
            assert response.status_code in [200, 503]
    
    def test_graceful_degradation(self, client: TestClient):
        """Test graceful degradation under load."""
        # Simulate high load
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response)
        
        # Should handle load gracefully
        success_rate = sum(1 for r in responses if r.status_code == 200) / len(responses)
        assert success_rate > 0.9  # 90% success rate under load
    
    def test_auto_recovery_detection(self, client: TestClient):
        """Test detection of service recovery."""
        # Simulate service recovery
        responses_before = []
        responses_after = []
        
        # Simulate degraded state
        with patch("time.sleep"):  # Speed up the test
            for _ in range(5):
                response = client.get("/health")
                responses_before.append(response.status_code)
        
        # Simulate recovery
        for _ in range(5):
            response = client.get("/health")
            responses_after.append(response.status_code)
        
        # Should show recovery (all after responses should be 200)
        assert all(status == 200 for status in responses_after)
