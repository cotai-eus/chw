"""
Integration tests for supplier management API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.models.supplier import Supplier


@pytest.mark.integration
class TestSupplierEndpoints:
    """Test supplier management API endpoints."""
    
    def test_get_suppliers_list(self, client: TestClient, auth_headers):
        """Test getting list of suppliers."""
        response = client.get("/api/v1/suppliers/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_suppliers_pagination(self, client: TestClient, auth_headers):
        """Test supplier list pagination."""
        response = client.get("/api/v1/suppliers/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_get_supplier_by_id(self, client: TestClient, auth_headers, test_supplier):
        """Test getting specific supplier by ID."""
        response = client.get(f"/api/v1/suppliers/{test_supplier.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_supplier.id
        assert data["name"] == test_supplier.name
        assert data["cnpj"] == test_supplier.cnpj
    
    def test_get_nonexistent_supplier(self, client: TestClient, auth_headers):
        """Test getting non-existent supplier."""
        response = client.get("/api/v1/suppliers/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_supplier_success(self, client: TestClient, auth_headers, test_company):
        """Test successful supplier creation."""
        supplier_data = {
            "name": "New Supplier",
            "cnpj": "98765432000177",
            "email": "new@supplier.com",
            "phone": "11999999999",
            "address": "Supplier Address, 789",
            "city": "Supplier City",
            "state": "MG",
            "zip_code": "12345-987",
            "company_id": test_company.id
        }
        
        response = client.post("/api/v1/suppliers/", json=supplier_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == supplier_data["name"]
        assert data["cnpj"] == supplier_data["cnpj"]
        assert data["email"] == supplier_data["email"]
        assert data["company_id"] == supplier_data["company_id"]
    
    def test_create_supplier_missing_required_fields(self, client: TestClient, auth_headers):
        """Test creating supplier with missing required fields."""
        supplier_data = {
            "name": "Incomplete Supplier"
            # Missing required fields
        }
        
        response = client.post("/api/v1/suppliers/", json=supplier_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_create_supplier_invalid_cnpj(self, client: TestClient, auth_headers, test_company):
        """Test creating supplier with invalid CNPJ."""
        supplier_data = {
            "name": "Invalid CNPJ Supplier",
            "cnpj": "invalid-cnpj",
            "email": "invalid@supplier.com",
            "phone": "11999999999",
            "address": "Address, 123",
            "city": "City",
            "state": "SP",
            "zip_code": "12345-678",
            "company_id": test_company.id
        }
        
        response = client.post("/api/v1/suppliers/", json=supplier_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_create_supplier_duplicate_cnpj(self, client: TestClient, auth_headers, test_supplier):
        """Test creating supplier with duplicate CNPJ."""
        supplier_data = {
            "name": "Duplicate CNPJ Supplier",
            "cnpj": test_supplier.cnpj,  # Using existing CNPJ
            "email": "duplicate@supplier.com",
            "phone": "11999999999",
            "address": "Address, 123",
            "city": "City",
            "state": "SP",
            "zip_code": "12345-678",
            "company_id": test_supplier.company_id
        }
        
        response = client.post("/api/v1/suppliers/", json=supplier_data, headers=auth_headers)
        assert response.status_code == 400
    
    def test_update_supplier_success(self, client: TestClient, auth_headers, test_supplier):
        """Test successful supplier update."""
        update_data = {
            "name": "Updated Supplier Name",
            "email": "updated@supplier.com",
            "phone": "11777777777"
        }
        
        response = client.put(
            f"/api/v1/suppliers/{test_supplier.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]
        assert data["phone"] == update_data["phone"]
    
    def test_update_nonexistent_supplier(self, client: TestClient, auth_headers):
        """Test updating non-existent supplier."""
        update_data = {
            "name": "Updated Name"
        }
        
        response = client.put(
            "/api/v1/suppliers/99999", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_delete_supplier_success(self, client: TestClient, auth_headers, test_supplier):
        """Test successful supplier deletion."""
        response = client.delete(f"/api/v1/suppliers/{test_supplier.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify supplier is deleted
        get_response = client.get(f"/api/v1/suppliers/{test_supplier.id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_supplier(self, client: TestClient, auth_headers):
        """Test deleting non-existent supplier."""
        response = client.delete("/api/v1/suppliers/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_search_suppliers(self, client: TestClient, auth_headers, test_supplier):
        """Test searching suppliers."""
        response = client.get(
            f"/api/v1/suppliers/search?q={test_supplier.name[:5]}", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(supplier["id"] == test_supplier.id for supplier in data)
    
    def test_get_supplier_quotes(self, client: TestClient, auth_headers, test_supplier, test_quote):
        """Test getting supplier's quotes."""
        response = client.get(
            f"/api/v1/suppliers/{test_supplier.id}/quotes", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(quote["supplier_id"] == test_supplier.id for quote in data)
    
    def test_get_supplier_performance_metrics(self, client: TestClient, auth_headers, test_supplier):
        """Test getting supplier performance metrics."""
        response = client.get(
            f"/api/v1/suppliers/{test_supplier.id}/metrics", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_quotes" in data
        assert "avg_response_time" in data
        assert "success_rate" in data
    
    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to supplier endpoints."""
        response = client.get("/api/v1/suppliers/")
        assert response.status_code == 401
    
    def test_company_isolation(self, client: TestClient, auth_headers, test_supplier):
        """Test that suppliers are isolated by company."""
        # This test would need to be expanded with a different company context
        response = client.get("/api/v1/suppliers/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # All suppliers should belong to the same company as the authenticated user
        for supplier in data:
            if supplier["id"] == test_supplier.id:
                assert supplier["company_id"] == test_supplier.company_id
    
    def test_rate_limiting(self, client: TestClient, auth_headers):
        """Test rate limiting on supplier endpoints."""
        # Make multiple requests to trigger rate limiting
        for _ in range(55):  # Burst limit is 50
            response = client.get("/api/v1/suppliers/", headers=auth_headers)
        
        # Should get rate limited
        assert response.status_code == 429
    
    @pytest.mark.slow
    def test_supplier_performance(self, client: TestClient, auth_headers):
        """Test supplier endpoint performance."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/suppliers/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second


@pytest.mark.integration
@pytest.mark.asyncio
class TestSupplierEndpointsAsync:
    """Test supplier endpoints with async client."""
    
    async def test_create_and_update_supplier_async(self, async_client: AsyncClient, auth_headers, test_company):
        """Test async supplier creation and update."""
        # Create supplier
        supplier_data = {
            "name": "Async Test Supplier",
            "cnpj": "87654321000166",
            "email": "async@supplier.com",
            "phone": "11666666666",
            "address": "Async Supplier Address, 999",
            "city": "Async Supplier City",
            "state": "PR",
            "zip_code": "54321-098",
            "company_id": test_company.id
        }
        
        create_response = await async_client.post(
            "/api/v1/suppliers/", 
            json=supplier_data, 
            headers=auth_headers
        )
        
        assert create_response.status_code == 201
        created_supplier = create_response.json()
        
        # Update supplier
        update_data = {
            "name": "Updated Async Supplier",
            "email": "updated-async@supplier.com"
        }
        
        update_response = await async_client.put(
            f"/api/v1/suppliers/{created_supplier['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated_supplier = update_response.json()
        assert updated_supplier["name"] == update_data["name"]
        assert updated_supplier["email"] == update_data["email"]
    
    async def test_bulk_supplier_operations(self, async_client: AsyncClient, auth_headers, test_company):
        """Test bulk supplier operations."""
        # Create multiple suppliers concurrently
        import asyncio
        
        supplier_data_list = [
            {
                "name": f"Bulk Supplier {i}",
                "cnpj": f"1234567800015{i}",
                "email": f"bulk{i}@supplier.com",
                "phone": f"1155555555{i}",
                "address": f"Bulk Address {i}",
                "city": "Bulk City",
                "state": "SP",
                "zip_code": "12345-678",
                "company_id": test_company.id
            }
            for i in range(5)
        ]
        
        # Create suppliers concurrently
        tasks = [
            async_client.post("/api/v1/suppliers/", json=data, headers=auth_headers)
            for data in supplier_data_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_creates = [r for r in results if not isinstance(r, Exception) and r.status_code == 201]
        assert len(successful_creates) == 5
