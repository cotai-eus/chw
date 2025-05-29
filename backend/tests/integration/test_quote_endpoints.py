"""
Integration tests for quote management API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.models.quote import Quote


@pytest.mark.integration
class TestQuoteEndpoints:
    """Test quote management API endpoints."""
    
    def test_get_quotes_list(self, client: TestClient, auth_headers):
        """Test getting list of quotes."""
        response = client.get("/api/v1/quotes/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_quotes_pagination(self, client: TestClient, auth_headers):
        """Test quote list pagination."""
        response = client.get("/api/v1/quotes/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_get_quote_by_id(self, client: TestClient, auth_headers, test_quote):
        """Test getting specific quote by ID."""
        response = client.get(f"/api/v1/quotes/{test_quote.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_quote.id
        assert data["tender_id"] == test_quote.tender_id
        assert data["supplier_id"] == test_quote.supplier_id
        assert data["total_value"] == test_quote.total_value
    
    def test_get_nonexistent_quote(self, client: TestClient, auth_headers):
        """Test getting non-existent quote."""
        response = client.get("/api/v1/quotes/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_quote_success(self, client: TestClient, auth_headers, test_tender, test_supplier):
        """Test successful quote creation."""
        quote_data = {
            "tender_id": test_tender.id,
            "supplier_id": test_supplier.id,
            "total_value": 75000.0,
            "status": "draft",
            "valid_until": "2024-12-31T23:59:59",
            "items": [
                {
                    "description": "Item 1",
                    "quantity": 10,
                    "unit_price": 1000.0,
                    "total_price": 10000.0
                },
                {
                    "description": "Item 2", 
                    "quantity": 5,
                    "unit_price": 13000.0,
                    "total_price": 65000.0
                }
            ]
        }
        
        response = client.post("/api/v1/quotes/", json=quote_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["tender_id"] == quote_data["tender_id"]
        assert data["supplier_id"] == quote_data["supplier_id"]
        assert data["total_value"] == quote_data["total_value"]
        assert data["status"] == quote_data["status"]
        assert len(data["items"]) == 2
    
    def test_create_quote_missing_required_fields(self, client: TestClient, auth_headers):
        """Test creating quote with missing required fields."""
        quote_data = {
            "total_value": 50000.0
            # Missing required fields
        }
        
        response = client.post("/api/v1/quotes/", json=quote_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_create_quote_invalid_tender(self, client: TestClient, auth_headers, test_supplier):
        """Test creating quote with invalid tender ID."""
        quote_data = {
            "tender_id": 99999,  # Non-existent tender
            "supplier_id": test_supplier.id,
            "total_value": 50000.0,
            "status": "draft",
            "valid_until": "2024-12-31T23:59:59"
        }
        
        response = client.post("/api/v1/quotes/", json=quote_data, headers=auth_headers)
        assert response.status_code == 400
    
    def test_create_quote_invalid_supplier(self, client: TestClient, auth_headers, test_tender):
        """Test creating quote with invalid supplier ID."""
        quote_data = {
            "tender_id": test_tender.id,
            "supplier_id": 99999,  # Non-existent supplier
            "total_value": 50000.0,
            "status": "draft",
            "valid_until": "2024-12-31T23:59:59"
        }
        
        response = client.post("/api/v1/quotes/", json=quote_data, headers=auth_headers)
        assert response.status_code == 400
    
    def test_create_quote_negative_value(self, client: TestClient, auth_headers, test_tender, test_supplier):
        """Test creating quote with negative value."""
        quote_data = {
            "tender_id": test_tender.id,
            "supplier_id": test_supplier.id,
            "total_value": -1000.0,  # Negative value
            "status": "draft",
            "valid_until": "2024-12-31T23:59:59"
        }
        
        response = client.post("/api/v1/quotes/", json=quote_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_update_quote_success(self, client: TestClient, auth_headers, test_quote):
        """Test successful quote update."""
        update_data = {
            "total_value": 60000.0,
            "status": "submitted",
            "notes": "Updated quote with better pricing"
        }
        
        response = client.put(
            f"/api/v1/quotes/{test_quote.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_value"] == update_data["total_value"]
        assert data["status"] == update_data["status"]
        assert data["notes"] == update_data["notes"]
    
    def test_update_nonexistent_quote(self, client: TestClient, auth_headers):
        """Test updating non-existent quote."""
        update_data = {
            "total_value": 60000.0
        }
        
        response = client.put(
            "/api/v1/quotes/99999", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_update_quote_invalid_status_transition(self, client: TestClient, auth_headers, test_quote):
        """Test invalid quote status transition."""
        # First, submit the quote
        client.put(
            f"/api/v1/quotes/{test_quote.id}", 
            json={"status": "submitted"}, 
            headers=auth_headers
        )
        
        # Try to change back to draft (should fail)
        update_data = {
            "status": "draft"
        }
        
        response = client.put(
            f"/api/v1/quotes/{test_quote.id}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_delete_quote_success(self, client: TestClient, auth_headers, test_quote):
        """Test successful quote deletion."""
        response = client.delete(f"/api/v1/quotes/{test_quote.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify quote is deleted
        get_response = client.get(f"/api/v1/quotes/{test_quote.id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_quote(self, client: TestClient, auth_headers):
        """Test deleting non-existent quote."""
        response = client.delete("/api/v1/quotes/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_submit_quote(self, client: TestClient, auth_headers, test_quote):
        """Test submitting a quote."""
        response = client.post(f"/api/v1/quotes/{test_quote.id}/submit", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert "submitted_at" in data
    
    def test_submit_invalid_quote(self, client: TestClient, auth_headers):
        """Test submitting non-existent quote."""
        response = client.post("/api/v1/quotes/99999/submit", headers=auth_headers)
        assert response.status_code == 404
    
    def test_withdraw_quote(self, client: TestClient, auth_headers, test_quote):
        """Test withdrawing a submitted quote."""
        # First submit the quote
        client.post(f"/api/v1/quotes/{test_quote.id}/submit", headers=auth_headers)
        
        # Then withdraw it
        response = client.post(f"/api/v1/quotes/{test_quote.id}/withdraw", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "withdrawn"
    
    def test_get_quotes_by_tender(self, client: TestClient, auth_headers, test_tender, test_quote):
        """Test getting quotes for a specific tender."""
        response = client.get(f"/api/v1/quotes/tender/{test_tender.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(quote["tender_id"] == test_tender.id for quote in data)
    
    def test_get_quotes_by_supplier(self, client: TestClient, auth_headers, test_supplier, test_quote):
        """Test getting quotes for a specific supplier."""
        response = client.get(f"/api/v1/quotes/supplier/{test_supplier.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(quote["supplier_id"] == test_supplier.id for quote in data)
    
    def test_search_quotes(self, client: TestClient, auth_headers, test_quote):
        """Test searching quotes."""
        response = client.get(
            f"/api/v1/quotes/search?status={test_quote.status}", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(quote["status"] == test_quote.status for quote in data)
    
    def test_quote_statistics(self, client: TestClient, auth_headers):
        """Test getting quote statistics."""
        response = client.get("/api/v1/quotes/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_quotes" in data
        assert "quotes_by_status" in data
        assert "average_value" in data
    
    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to quote endpoints."""
        response = client.get("/api/v1/quotes/")
        assert response.status_code == 401
    
    def test_rate_limiting(self, client: TestClient, auth_headers):
        """Test rate limiting on quote endpoints."""
        # Make multiple requests to trigger rate limiting
        for _ in range(55):  # Burst limit is 50
            response = client.get("/api/v1/quotes/", headers=auth_headers)
        
        # Should get rate limited
        assert response.status_code == 429
    
    @pytest.mark.slow
    def test_quote_performance(self, client: TestClient, auth_headers):
        """Test quote endpoint performance."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/quotes/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second


@pytest.mark.integration
@pytest.mark.asyncio
class TestQuoteEndpointsAsync:
    """Test quote endpoints with async client."""
    
    async def test_quote_workflow_async(self, async_client: AsyncClient, auth_headers, test_tender, test_supplier):
        """Test complete quote workflow asynchronously."""
        # Create quote
        quote_data = {
            "tender_id": test_tender.id,
            "supplier_id": test_supplier.id,
            "total_value": 85000.0,
            "status": "draft",
            "valid_until": "2024-12-31T23:59:59",
            "items": [
                {
                    "description": "Async Item",
                    "quantity": 1,
                    "unit_price": 85000.0,
                    "total_price": 85000.0
                }
            ]
        }
        
        create_response = await async_client.post(
            "/api/v1/quotes/", 
            json=quote_data, 
            headers=auth_headers
        )
        
        assert create_response.status_code == 201
        created_quote = create_response.json()
        
        # Update quote
        update_data = {
            "total_value": 80000.0,
            "notes": "Async updated pricing"
        }
        
        update_response = await async_client.put(
            f"/api/v1/quotes/{created_quote['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated_quote = update_response.json()
        assert updated_quote["total_value"] == update_data["total_value"]
        
        # Submit quote
        submit_response = await async_client.post(
            f"/api/v1/quotes/{created_quote['id']}/submit", 
            headers=auth_headers
        )
        
        assert submit_response.status_code == 200
        submitted_quote = submit_response.json()
        assert submitted_quote["status"] == "submitted"
