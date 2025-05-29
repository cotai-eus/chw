"""
Integration tests for company management API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.models.company import Company


@pytest.mark.integration
class TestCompanyEndpoints:
    """Test company management API endpoints."""
    
    def test_get_companies_list(self, client: TestClient, auth_headers):
        """Test getting list of companies."""
        response = client.get("/api/v1/companies/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_companies_pagination(self, client: TestClient, auth_headers):
        """Test company list pagination."""
        response = client.get("/api/v1/companies/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_get_company_by_id(self, client: TestClient, auth_headers, test_company):
        """Test getting specific company by ID."""
        response = client.get(f"/api/v1/companies/{test_company.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_company.id
        assert data["name"] == test_company.name
        assert data["cnpj"] == test_company.cnpj
    
    def test_get_nonexistent_company(self, client: TestClient, auth_headers):
        """Test getting non-existent company."""
        response = client.get("/api/v1/companies/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_company_success(self, client: TestClient, auth_headers):
        """Test successful company creation."""
        company_data = {
            "name": "New Company",
            "cnpj": "12345678000199",
            "email": "new@company.com",
            "phone": "11999999999",
            "address": "New Address, 123",
            "city": "New City",
            "state": "SP",
            "zip_code": "12345-678"
        }
        
        response = client.post("/api/v1/companies/", json=company_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == company_data["name"]
        assert data["cnpj"] == company_data["cnpj"]
        assert data["email"] == company_data["email"]
    
    def test_create_company_missing_required_fields(self, client: TestClient, auth_headers):
        """Test creating company with missing required fields."""
        company_data = {
            "name": "Incomplete Company"
            # Missing required fields
        }
        
        response = client.post("/api/v1/companies/", json=company_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_create_company_invalid_cnpj(self, client: TestClient, auth_headers):
        """Test creating company with invalid CNPJ."""
        company_data = {
            "name": "Invalid CNPJ Company",
            "cnpj": "invalid-cnpj",
            "email": "invalid@company.com",
            "phone": "11999999999",
            "address": "Address, 123",
            "city": "City",
            "state": "SP",
            "zip_code": "12345-678"
        }
        
        response = client.post("/api/v1/companies/", json=company_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_create_company_duplicate_cnpj(self, client: TestClient, auth_headers, test_company):
        """Test creating company with duplicate CNPJ."""
        company_data = {
            "name": "Duplicate CNPJ Company",
            "cnpj": test_company.cnpj,  # Using existing CNPJ
            "email": "duplicate@company.com",
            "phone": "11999999999",
            "address": "Address, 123",
            "city": "City",
            "state": "SP",
            "zip_code": "12345-678"
        }
        
        response = client.post("/api/v1/companies/", json=company_data, headers=auth_headers)
        assert response.status_code == 400
    
    def test_update_company_success(self, client: TestClient, auth_headers, test_company):
        """Test successful company update."""
        update_data = {
            "name": "Updated Company Name",
            "email": "updated@company.com",
            "phone": "11888888888"
        }
        
        response = client.put(
            f"/api/v1/companies/{test_company.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]
        assert data["phone"] == update_data["phone"]
    
    def test_update_nonexistent_company(self, client: TestClient, auth_headers):
        """Test updating non-existent company."""
        update_data = {
            "name": "Updated Name"
        }
        
        response = client.put(
            "/api/v1/companies/99999", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_delete_company_success(self, client: TestClient, auth_headers, test_company):
        """Test successful company deletion."""
        response = client.delete(f"/api/v1/companies/{test_company.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify company is deleted
        get_response = client.get(f"/api/v1/companies/{test_company.id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_company(self, client: TestClient, auth_headers):
        """Test deleting non-existent company."""
        response = client.delete("/api/v1/companies/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_search_companies(self, client: TestClient, auth_headers, test_company):
        """Test searching companies."""
        response = client.get(
            f"/api/v1/companies/search?q={test_company.name[:5]}", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(company["id"] == test_company.id for company in data)
    
    def test_get_company_statistics(self, client: TestClient, auth_headers, test_company):
        """Test getting company statistics."""
        response = client.get(
            f"/api/v1/companies/{test_company.id}/stats", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "users_count" in data
        assert "tenders_count" in data
        assert "suppliers_count" in data
    
    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to company endpoints."""
        response = client.get("/api/v1/companies/")
        assert response.status_code == 401
    
    def test_rate_limiting(self, client: TestClient, auth_headers):
        """Test rate limiting on company endpoints."""
        # Make multiple requests to trigger rate limiting
        for _ in range(55):  # Burst limit is 50
            response = client.get("/api/v1/companies/", headers=auth_headers)
        
        # Should get rate limited
        assert response.status_code == 429
    
    @pytest.mark.slow
    def test_company_performance(self, client: TestClient, auth_headers):
        """Test company endpoint performance."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/companies/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second


@pytest.mark.integration
@pytest.mark.asyncio
class TestCompanyEndpointsAsync:
    """Test company endpoints with async client."""
    
    async def test_create_and_update_company_async(self, async_client: AsyncClient, auth_headers):
        """Test async company creation and update."""
        # Create company
        company_data = {
            "name": "Async Test Company",
            "cnpj": "98765432000188",
            "email": "async@test.com",
            "phone": "11777777777",
            "address": "Async Address, 456",
            "city": "Async City",
            "state": "RJ",
            "zip_code": "87654-321"
        }
        
        create_response = await async_client.post(
            "/api/v1/companies/", 
            json=company_data, 
            headers=auth_headers
        )
        
        assert create_response.status_code == 201
        created_company = create_response.json()
        
        # Update company
        update_data = {
            "name": "Updated Async Company",
            "email": "updated-async@test.com"
        }
        
        update_response = await async_client.put(
            f"/api/v1/companies/{created_company['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated_company = update_response.json()
        assert updated_company["name"] == update_data["name"]
        assert updated_company["email"] == update_data["email"]
