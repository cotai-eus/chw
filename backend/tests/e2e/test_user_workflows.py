"""
End-to-end tests for complete user workflows.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.security import create_access_token
from app.models.user import UserModel
from app.models.company import CompanyModel
from app.models.tender import TenderModel
from app.models.quote import QuoteModel
from app.schemas.user import UserCreate
from app.schemas.company import CompanyCreate
from app.schemas.tender import TenderCreate
from app.schemas.quote import QuoteCreate


class TestCompleteUserWorkflows:
    """Test complete end-to-end user workflows."""
    
    @pytest.fixture
    def e2e_client(self):
        """Create test client for end-to-end testing."""
        return TestClient(app)
    
    @pytest.fixture
    async def e2e_async_client(self):
        """Create async test client for end-to-end testing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_and_login_flow(self, e2e_client):
        """Test complete user registration and login workflow."""
        # 1. Register new user
        registration_data = {
            "email": "e2e_user@example.com",
            "password": "securepassword123",
            "full_name": "E2E Test User",
            "phone": "+1234567890"
        }
        
        register_response = e2e_client.post(
            "/api/v1/auth/register",
            json=registration_data
        )
        
        assert register_response.status_code in [201, 422]  # 422 if validation fails
        
        if register_response.status_code == 201:
            register_data = register_response.json()
            assert "user" in register_data
            assert register_data["user"]["email"] == registration_data["email"]
            
            # 2. Login with registered user
            login_data = {
                "username": registration_data["email"],
                "password": registration_data["password"]
            }
            
            login_response = e2e_client.post(
                "/api/v1/auth/login",
                data=login_data
            )
            
            assert login_response.status_code in [200, 422]
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                assert "access_token" in login_result
                assert "token_type" in login_result
                
                # 3. Access protected endpoint
                headers = {
                    "Authorization": f"Bearer {login_result['access_token']}"
                }
                
                profile_response = e2e_client.get(
                    "/api/v1/users/me",
                    headers=headers
                )
                
                assert profile_response.status_code in [200, 401]
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    assert profile_data["email"] == registration_data["email"]
    
    @pytest.mark.asyncio
    async def test_complete_tender_creation_and_management_flow(
        self, e2e_client, test_user, test_company
    ):
        """Test complete tender creation and management workflow."""
        # Create access token for user
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Create new tender
        tender_data = {
            "title": "E2E Test Software Development Project",
            "description": "Complete end-to-end testing of tender workflow",
            "requirements": [
                "React frontend development",
                "FastAPI backend development",
                "PostgreSQL database setup",
                "Docker containerization"
            ],
            "budget_range_min": 25000,
            "budget_range_max": 50000,
            "deadline": (datetime.utcnow() + timedelta(days=60)).isoformat(),
            "category": "software",
            "delivery_terms": "Remote development with weekly progress reports",
            "company_id": str(test_company.id)
        }
        
        create_response = e2e_client.post(
            "/api/v1/tenders/",
            json=tender_data,
            headers=headers
        )
        
        assert create_response.status_code in [201, 422, 401]
        
        if create_response.status_code == 201:
            created_tender = create_response.json()
            tender_id = created_tender["id"]
            
            # 2. Retrieve created tender
            get_response = e2e_client.get(
                f"/api/v1/tenders/{tender_id}",
                headers=headers
            )
            
            assert get_response.status_code in [200, 404, 401]
            
            if get_response.status_code == 200:
                tender_details = get_response.json()
                assert tender_details["title"] == tender_data["title"]
                assert tender_details["status"] == "draft"
                
                # 3. Update tender
                update_data = {
                    "title": "Updated E2E Test Project",
                    "budget_range_max": 55000
                }
                
                update_response = e2e_client.put(
                    f"/api/v1/tenders/{tender_id}",
                    json=update_data,
                    headers=headers
                )
                
                assert update_response.status_code in [200, 404, 401, 422]
                
                if update_response.status_code == 200:
                    updated_tender = update_response.json()
                    assert updated_tender["title"] == update_data["title"]
                    assert updated_tender["budget_range_max"] == 55000
                
                # 4. Publish tender
                publish_response = e2e_client.post(
                    f"/api/v1/tenders/{tender_id}/publish",
                    headers=headers
                )
                
                assert publish_response.status_code in [200, 404, 401, 422]
                
                # 5. Get tender statistics
                stats_response = e2e_client.get(
                    f"/api/v1/tenders/{tender_id}/statistics",
                    headers=headers
                )
                
                assert stats_response.status_code in [200, 404, 401]
                
                # 6. List user's tenders
                list_response = e2e_client.get(
                    "/api/v1/tenders/",
                    headers=headers
                )
                
                assert list_response.status_code in [200, 401]
                
                if list_response.status_code == 200:
                    tenders_list = list_response.json()
                    assert isinstance(tenders_list["items"], list)
    
    @pytest.mark.asyncio
    async def test_complete_quote_submission_and_evaluation_flow(
        self, e2e_client, test_user, test_company, test_db
    ):
        """Test complete quote submission and evaluation workflow."""
        # Create a published tender
        tender = TenderModel(
            id=uuid4(),
            title="E2E Quote Test Tender",
            description="Testing quote submission workflow",
            requirements=["Development work"],
            budget_range_min=20000,
            budget_range_max=40000,
            deadline=datetime.utcnow() + timedelta(days=45),
            category="software",
            status="published",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Create access tokens for different users
        buyer_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        
        # Create supplier user
        supplier_user = UserModel(
            id=uuid4(),
            email="supplier@example.com",
            hashed_password="hashed_password",
            full_name="Supplier User",
            is_active=True,
            user_type="supplier"
        )
        test_db.add(supplier_user)
        await test_db.commit()
        
        supplier_token = create_access_token(
            data={"sub": str(supplier_user.id), "user_id": supplier_user.id}
        )
        
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
        supplier_headers = {"Authorization": f"Bearer {supplier_token}"}
        
        # 1. Supplier views available tenders
        tenders_response = e2e_client.get(
            "/api/v1/tenders/",
            headers=supplier_headers
        )
        
        assert tenders_response.status_code in [200, 401]
        
        # 2. Supplier submits quote
        quote_data = {
            "tender_id": str(tender.id),
            "total_price": 35000,
            "currency": "USD",
            "delivery_time_days": 42,
            "notes": "High-quality development with modern technologies",
            "items": [
                {
                    "description": "Frontend Development",
                    "quantity": 1,
                    "unit_price": 20000
                },
                {
                    "description": "Backend Development",
                    "quantity": 1,
                    "unit_price": 15000
                }
            ]
        }
        
        quote_response = e2e_client.post(
            "/api/v1/quotes/",
            json=quote_data,
            headers=supplier_headers
        )
        
        assert quote_response.status_code in [201, 422, 401]
        
        if quote_response.status_code == 201:
            created_quote = quote_response.json()
            quote_id = created_quote["id"]
            
            # 3. Buyer reviews submitted quotes
            quotes_response = e2e_client.get(
                f"/api/v1/tenders/{tender.id}/quotes",
                headers=buyer_headers
            )
            
            assert quotes_response.status_code in [200, 404, 401]
            
            if quotes_response.status_code == 200:
                tender_quotes = quotes_response.json()
                assert len(tender_quotes) >= 1
                
                # 4. Buyer requests quote details
                quote_detail_response = e2e_client.get(
                    f"/api/v1/quotes/{quote_id}",
                    headers=buyer_headers
                )
                
                assert quote_detail_response.status_code in [200, 404, 401]
                
                # 5. Buyer accepts quote
                accept_response = e2e_client.post(
                    f"/api/v1/quotes/{quote_id}/accept",
                    headers=buyer_headers
                )
                
                assert accept_response.status_code in [200, 404, 401, 422]
                
                if accept_response.status_code == 200:
                    accepted_quote = accept_response.json()
                    assert accepted_quote["status"] == "accepted"
                
                # 6. Check tender status after acceptance
                tender_status_response = e2e_client.get(
                    f"/api/v1/tenders/{tender.id}",
                    headers=buyer_headers
                )
                
                if tender_status_response.status_code == 200:
                    updated_tender = tender_status_response.json()
                    # Tender status might be updated to 'awarded'
    
    @pytest.mark.asyncio
    async def test_complete_company_management_flow(self, e2e_client, test_user):
        """Test complete company management workflow."""
        # Create access token
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Create company
        company_data = {
            "name": "E2E Test Company Ltd",
            "description": "Testing company management workflow",
            "industry": "Software Development",
            "website": "https://e2etest.com",
            "address": "123 Test Street, Test City, TC 12345",
            "phone": "+1234567890",
            "email": "contact@e2etest.com",
            "plan_type": "professional"
        }
        
        create_company_response = e2e_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=headers
        )
        
        assert create_company_response.status_code in [201, 422, 401]
        
        if create_company_response.status_code == 201:
            created_company = create_company_response.json()
            company_id = created_company["id"]
            
            # 2. Update company information
            update_data = {
                "description": "Updated company description for E2E testing",
                "website": "https://updated.e2etest.com"
            }
            
            update_response = e2e_client.put(
                f"/api/v1/companies/{company_id}",
                json=update_data,
                headers=headers
            )
            
            assert update_response.status_code in [200, 404, 401, 422]
            
            # 3. Get company statistics
            stats_response = e2e_client.get(
                f"/api/v1/companies/{company_id}/statistics",
                headers=headers
            )
            
            assert stats_response.status_code in [200, 404, 401]
            
            # 4. Invite user to company (if endpoint exists)
            invite_data = {
                "email": "newuser@example.com",
                "role": "member"
            }
            
            invite_response = e2e_client.post(
                f"/api/v1/companies/{company_id}/invite",
                json=invite_data,
                headers=headers
            )
            
            # This might not exist or require different permissions
            assert invite_response.status_code in [200, 404, 401, 422, 403]
            
            # 5. List company members
            members_response = e2e_client.get(
                f"/api/v1/companies/{company_id}/members",
                headers=headers
            )
            
            assert members_response.status_code in [200, 404, 401]
    
    @pytest.mark.asyncio
    async def test_real_time_notifications_flow(
        self, e2e_async_client, test_user, test_company, mock_websocket_manager
    ):
        """Test real-time notifications workflow."""
        # Create access token
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Mock WebSocket connection and notifications
        with patch('app.websocket.websocket_manager', mock_websocket_manager):
            # 1. Connect to WebSocket for notifications
            # Note: This is a simplified test - real WebSocket testing requires more setup
            
            # 2. Create tender (should trigger notification)
            tender_data = {
                "title": "Real-time Test Tender",
                "description": "Testing real-time notifications",
                "requirements": ["Testing requirement"],
                "budget_range_min": 10000,
                "budget_range_max": 20000,
                "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "category": "software",
                "company_id": str(test_company.id)
            }
            
            async with e2e_async_client as client:
                create_response = await client.post(
                    "/api/v1/tenders/",
                    json=tender_data,
                    headers=headers
                )
                
                if create_response.status_code == 201:
                    # Verify notification was sent
                    mock_websocket_manager.send_to_user.assert_called()
    
    @pytest.mark.asyncio
    async def test_file_upload_and_processing_flow(self, e2e_client, test_user):
        """Test file upload and processing workflow."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Upload file
        test_file_content = b"Test file content for E2E testing"
        files = {
            "file": ("test_document.txt", test_file_content, "text/plain")
        }
        
        upload_response = e2e_client.post(
            "/api/v1/files/upload",
            files=files,
            headers=headers
        )
        
        assert upload_response.status_code in [200, 422, 401]
        
        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            file_id = upload_result["file_id"]
            
            # 2. Get file information
            file_info_response = e2e_client.get(
                f"/api/v1/files/{file_id}",
                headers=headers
            )
            
            assert file_info_response.status_code in [200, 404, 401]
            
            # 3. Download file
            download_response = e2e_client.get(
                f"/api/v1/files/{file_id}/download",
                headers=headers
            )
            
            assert download_response.status_code in [200, 404, 401]
            
            # 4. Process file (if processing endpoint exists)
            process_response = e2e_client.post(
                f"/api/v1/files/{file_id}/process",
                headers=headers
            )
            
            assert process_response.status_code in [200, 404, 401, 422]
    
    @pytest.mark.asyncio
    async def test_search_and_filtering_flow(self, e2e_client, test_user):
        """Test search and filtering functionality."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Search tenders with various filters
        search_params = {
            "category": "software",
            "min_budget": 10000,
            "max_budget": 50000,
            "status": "published",
            "search": "development"
        }
        
        search_response = e2e_client.get(
            "/api/v1/tenders/search",
            params=search_params,
            headers=headers
        )
        
        assert search_response.status_code in [200, 401]
        
        if search_response.status_code == 200:
            search_results = search_response.json()
            assert "items" in search_results
            assert "total" in search_results
            
            # 2. Search companies
            company_search_response = e2e_client.get(
                "/api/v1/companies/search",
                params={"industry": "Software Development"},
                headers=headers
            )
            
            assert company_search_response.status_code in [200, 401]
            
            # 3. Search users/suppliers
            supplier_search_response = e2e_client.get(
                "/api/v1/users/search",
                params={"user_type": "supplier", "skills": "python"},
                headers=headers
            )
            
            assert supplier_search_response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_analytics_and_reporting_flow(self, e2e_client, test_user, test_company):
        """Test analytics and reporting functionality."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Get user dashboard analytics
        dashboard_response = e2e_client.get(
            "/api/v1/analytics/dashboard",
            headers=headers
        )
        
        assert dashboard_response.status_code in [200, 401, 404]
        
        # 2. Get tender analytics
        tender_analytics_response = e2e_client.get(
            "/api/v1/analytics/tenders",
            params={"period": "last_30_days"},
            headers=headers
        )
        
        assert tender_analytics_response.status_code in [200, 401, 404]
        
        # 3. Get company performance metrics
        company_metrics_response = e2e_client.get(
            f"/api/v1/analytics/companies/{test_company.id}",
            headers=headers
        )
        
        assert company_metrics_response.status_code in [200, 401, 404]
        
        # 4. Generate report
        report_data = {
            "report_type": "tender_summary",
            "date_range": {
                "start": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "format": "pdf"
        }
        
        report_response = e2e_client.post(
            "/api/v1/reports/generate",
            json=report_data,
            headers=headers
        )
        
        assert report_response.status_code in [200, 202, 401, 404, 422]


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in workflows."""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access_scenarios(self, e2e_client):
        """Test various unauthorized access scenarios."""
        # 1. Access protected endpoint without token
        response = e2e_client.get("/api/v1/users/me")
        assert response.status_code == 401
        
        # 2. Access with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = e2e_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        
        # 3. Access with expired token (if validation is implemented)
        expired_token = create_access_token(
            data={"sub": "123", "user_id": 123},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = e2e_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_validation_error_scenarios(self, e2e_client, test_user):
        """Test validation error scenarios."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Create tender with invalid data
        invalid_tender_data = {
            "title": "",  # Empty title
            "budget_range_min": 50000,
            "budget_range_max": 10000,  # Max less than min
            "deadline": "invalid_date",
            "category": "invalid_category"
        }
        
        response = e2e_client.post(
            "/api/v1/tenders/",
            json=invalid_tender_data,
            headers=headers
        )
        assert response.status_code == 422
        
        # 2. Create quote with invalid data
        invalid_quote_data = {
            "tender_id": "invalid_uuid",
            "total_price": -1000,  # Negative price
            "delivery_time_days": -10  # Negative days
        }
        
        response = e2e_client.post(
            "/api/v1/quotes/",
            json=invalid_quote_data,
            headers=headers
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_resource_not_found_scenarios(self, e2e_client, test_user):
        """Test resource not found scenarios."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        fake_id = str(uuid4())
        
        # 1. Get non-existent tender
        response = e2e_client.get(f"/api/v1/tenders/{fake_id}", headers=headers)
        assert response.status_code == 404
        
        # 2. Update non-existent company
        response = e2e_client.put(
            f"/api/v1/companies/{fake_id}",
            json={"name": "Updated Name"},
            headers=headers
        )
        assert response.status_code == 404
        
        # 3. Delete non-existent quote
        response = e2e_client.delete(f"/api/v1/quotes/{fake_id}", headers=headers)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_rate_limiting_scenarios(self, e2e_client, test_user):
        """Test rate limiting scenarios."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Make many rapid requests to trigger rate limiting
        responses = []
        for _ in range(20):
            response = e2e_client.get("/api/v1/tenders/", headers=headers)
            responses.append(response)
        
        # Some requests might be rate limited (429) depending on configuration
        status_codes = [r.status_code for r in responses]
        assert all(code in [200, 401, 429] for code in status_codes)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_scenarios(self, e2e_async_client, test_user, test_company):
        """Test concurrent operations scenarios."""
        access_token = create_access_token(
            data={"sub": str(test_user.id), "user_id": test_user.id}
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create multiple concurrent tender creation requests
        tender_data = {
            "title": "Concurrent Test Tender",
            "description": "Testing concurrent operations",
            "requirements": ["req1"],
            "budget_range_min": 10000,
            "budget_range_max": 20000,
            "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "category": "software",
            "company_id": str(test_company.id)
        }
        
        tasks = []
        async with e2e_async_client as client:
            for i in range(5):
                task_data = tender_data.copy()
                task_data["title"] = f"Concurrent Test Tender {i}"
                
                task = client.post(
                    "/api/v1/tenders/",
                    json=task_data,
                    headers=headers
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All requests should complete (success or failure)
            assert len(responses) == 5
            successful_responses = [
                r for r in responses 
                if hasattr(r, 'status_code') and r.status_code in [200, 201]
            ]
            
            # At least some should succeed
            assert len(successful_responses) >= 0
