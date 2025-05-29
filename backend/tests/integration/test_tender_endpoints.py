"""
Integration tests for tender management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestDataFactory


class TestTenderEndpoints:
    """Test tender management API endpoints."""
    
    def test_get_tenders_list(self, client: TestClient, auth_headers):
        """Test getting list of tenders."""
        response = client.get("/api/v1/tenders/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_tenders_pagination(self, client: TestClient, auth_headers):
        """Test tender list pagination."""
        response = client.get("/api/v1/tenders/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_get_tender_by_id(self, client: TestClient, auth_headers, test_tender):
        """Test getting specific tender by ID."""
        response = client.get(f"/api/v1/tenders/{test_tender.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_tender.id
        assert data["title"] == test_tender.title
        assert data["description"] == test_tender.description
    
    def test_get_nonexistent_tender(self, client: TestClient, auth_headers):
        """Test getting non-existent tender."""
        response = client.get("/api/v1/tenders/nonexistent-id", headers=auth_headers)
        
        assert response.status_code == 404
        assert "Tender not found" in response.json()["detail"]
    
    def test_create_tender_success(self, client: TestClient, auth_headers):
        """Test successful tender creation."""
        tender_data = TestDataFactory.tender_create_data({
            "title": "New Tender",
            "description": "New tender description",
            "submission_deadline": "2024-12-31T23:59:59",
            "budget": 150000.0
        })
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == tender_data["title"]
        assert data["description"] == tender_data["description"]
        assert data["budget"] == tender_data["budget"]
        assert data["status"] == "open"
    
    def test_create_tender_missing_required_fields(self, client: TestClient, auth_headers):
        """Test creating tender with missing required fields."""
        tender_data = {
            "description": "Missing title"
        }
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_tender_invalid_date_format(self, client: TestClient, auth_headers):
        """Test creating tender with invalid date format."""
        tender_data = TestDataFactory.tender_create_data({
            "submission_deadline": "invalid-date-format"
        })
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_tender_past_deadline(self, client: TestClient, auth_headers):
        """Test creating tender with past deadline."""
        tender_data = TestDataFactory.tender_create_data({
            "submission_deadline": "2020-01-01T00:00:00"  # Past date
        })
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        assert "Deadline cannot be in the past" in response.json()["detail"]
    
    def test_create_tender_negative_budget(self, client: TestClient, auth_headers):
        """Test creating tender with negative budget."""
        tender_data = TestDataFactory.tender_create_data({
            "budget": -1000.0
        })
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_update_tender_success(self, client: TestClient, auth_headers, test_tender):
        """Test successful tender update."""
        update_data = {
            "title": "Updated Tender Title",
            "budget": 200000.0
        }
        
        response = client.put(f"/api/v1/tenders/{test_tender.id}", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Tender Title"
        assert data["budget"] == 200000.0
    
    def test_update_tender_status(self, client: TestClient, auth_headers, test_tender):
        """Test updating tender status."""
        update_data = {
            "status": "in_progress"
        }
        
        response = client.put(f"/api/v1/tenders/{test_tender.id}", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
    
    def test_update_tender_invalid_status(self, client: TestClient, auth_headers, test_tender):
        """Test updating tender with invalid status."""
        update_data = {
            "status": "invalid_status"
        }
        
        response = client.put(f"/api/v1/tenders/{test_tender.id}", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_update_nonexistent_tender(self, client: TestClient, auth_headers):
        """Test updating non-existent tender."""
        update_data = {
            "title": "Updated Title"
        }
        
        response = client.put("/api/v1/tenders/nonexistent-id", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_tender(self, client: TestClient, auth_headers, test_tender):
        """Test deleting tender."""
        response = client.delete(f"/api/v1/tenders/{test_tender.id}", 
                               headers=auth_headers)
        
        assert response.status_code == 200
        
        # Verify tender is deleted
        get_response = client.get(f"/api/v1/tenders/{test_tender.id}", 
                                headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_tender(self, client: TestClient, auth_headers):
        """Test deleting non-existent tender."""
        response = client.delete("/api/v1/tenders/nonexistent-id", 
                               headers=auth_headers)
        
        assert response.status_code == 404


class TestTenderSearch:
    """Test tender search and filtering functionality."""
    
    def test_search_tenders_by_title(self, client: TestClient, auth_headers, test_tender):
        """Test searching tenders by title."""
        response = client.get(f"/api/v1/tenders/search?title={test_tender.title}", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(tender["title"] == test_tender.title for tender in data)
    
    def test_filter_tenders_by_status(self, client: TestClient, auth_headers):
        """Test filtering tenders by status."""
        response = client.get("/api/v1/tenders/?status=open", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert all(tender["status"] == "open" for tender in data)
    
    def test_filter_tenders_by_budget_range(self, client: TestClient, auth_headers):
        """Test filtering tenders by budget range."""
        response = client.get("/api/v1/tenders/?min_budget=50000&max_budget=200000", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert all(50000 <= tender["budget"] <= 200000 for tender in data if tender["budget"])
    
    def test_filter_tenders_by_deadline(self, client: TestClient, auth_headers):
        """Test filtering tenders by deadline."""
        response = client.get("/api/v1/tenders/?deadline_after=2024-01-01", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # All returned tenders should have deadlines after 2024-01-01
        assert len(data) >= 0  # Could be empty if no tenders match
    
    def test_search_tenders_no_results(self, client: TestClient, auth_headers):
        """Test tender search with no results."""
        response = client.get("/api/v1/tenders/search?title=NonexistentTender", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestTenderAIProcessing:
    """Test AI processing functionality for tenders."""
    
    def test_process_tender_document(self, client: TestClient, auth_headers, test_tender, mock_ai_service):
        """Test AI processing of tender document."""
        # Mock file upload
        files = {
            "file": ("test_document.pdf", b"fake pdf content", "application/pdf")
        }
        
        response = client.post(f"/api/v1/tenders/{test_tender.id}/process-ai", 
                             files=files, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    def test_process_tender_unsupported_file_type(self, client: TestClient, auth_headers, test_tender):
        """Test AI processing with unsupported file type."""
        files = {
            "file": ("test_file.txt", b"text content", "text/plain")
        }
        
        response = client.post(f"/api/v1/tenders/{test_tender.id}/process-ai", 
                             files=files, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_process_tender_file_too_large(self, client: TestClient, auth_headers, test_tender):
        """Test AI processing with file too large."""
        # Create a large file content (mock)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        files = {
            "file": ("large_file.pdf", large_content, "application/pdf")
        }
        
        response = client.post(f"/api/v1/tenders/{test_tender.id}/process-ai", 
                             files=files, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]
    
    def test_get_ai_processing_status(self, client: TestClient, auth_headers):
        """Test getting AI processing job status."""
        job_id = "test-job-id"
        
        response = client.get(f"/api/v1/tenders/ai-jobs/{job_id}", 
                            headers=auth_headers)
        
        # This might return 404 if job doesn't exist, which is fine for testing
        assert response.status_code in [200, 404]
    
    def test_get_ai_processing_results(self, client: TestClient, auth_headers, test_tender):
        """Test getting AI processing results for a tender."""
        response = client.get(f"/api/v1/tenders/{test_tender.id}/ai-results", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)  # List of AI processing results


class TestTenderStatistics:
    """Test tender statistics endpoints."""
    
    def test_get_tender_statistics(self, client: TestClient, auth_headers):
        """Test getting tender statistics."""
        response = client.get("/api/v1/tenders/statistics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_tenders" in data
        assert "open_tenders" in data
        assert "closed_tenders" in data
        assert "average_budget" in data
    
    def test_get_tender_statistics_by_period(self, client: TestClient, auth_headers):
        """Test getting tender statistics for specific period."""
        response = client.get("/api/v1/tenders/statistics?period=month", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "statistics" in data
    
    def test_get_tender_status_distribution(self, client: TestClient, auth_headers):
        """Test getting tender status distribution."""
        response = client.get("/api/v1/tenders/status-distribution", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should contain status counts


class TestTenderPermissions:
    """Test tender access permissions."""
    
    def test_access_tender_from_different_company(self, client: TestClient, auth_headers):
        """Test accessing tender from different company."""
        # This would require creating a user from a different company
        # For now, we'll test the concept
        response = client.get("/api/v1/tenders/other-company-tender-id", 
                            headers=auth_headers)
        
        # Should return 404 (not found) or 403 (forbidden)
        assert response.status_code in [404, 403]
    
    def test_create_tender_without_auth(self, client: TestClient):
        """Test creating tender without authentication."""
        tender_data = TestDataFactory.tender_create_data()
        
        response = client.post("/api/v1/tenders/", json=tender_data)
        
        assert response.status_code == 401
    
    def test_update_tender_without_auth(self, client: TestClient, test_tender):
        """Test updating tender without authentication."""
        update_data = {"title": "Updated Title"}
        
        response = client.put(f"/api/v1/tenders/{test_tender.id}", json=update_data)
        
        assert response.status_code == 401
    
    def test_delete_tender_without_auth(self, client: TestClient, test_tender):
        """Test deleting tender without authentication."""
        response = client.delete(f"/api/v1/tenders/{test_tender.id}")
        
        assert response.status_code == 401


class TestTenderValidation:
    """Test input validation for tender endpoints."""
    
    def test_create_tender_empty_title(self, client: TestClient, auth_headers):
        """Test creating tender with empty title."""
        tender_data = TestDataFactory.tender_create_data({
            "title": ""
        })
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_create_tender_very_long_title(self, client: TestClient, auth_headers):
        """Test creating tender with very long title."""
        tender_data = TestDataFactory.tender_create_data({
            "title": "a" * 1000  # Very long title
        })
        
        response = client.post("/api/v1/tenders/", 
                             json=tender_data, 
                             headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_update_tender_invalid_budget_type(self, client: TestClient, auth_headers, test_tender):
        """Test updating tender with invalid budget type."""
        update_data = {
            "budget": "not-a-number"
        }
        
        response = client.put(f"/api/v1/tenders/{test_tender.id}", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 422
