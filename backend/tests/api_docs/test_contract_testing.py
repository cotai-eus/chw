"""
Advanced API Contract Testing

Comprehensive contract testing to ensure API compatibility, schema validation,
and backward compatibility across versions.
"""
import pytest
import json
import jsonschema
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import httpx
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from tests.utils.test_helpers import APITestHelper


@dataclass
class APIContract:
    """Represents an API contract for testing."""
    endpoint: str
    method: str
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    status_codes: List[int] = None
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.status_codes is None:
            self.status_codes = [200]


class APIContractValidator:
    """Validates API responses against predefined contracts."""
    
    def __init__(self):
        self.contracts: Dict[str, APIContract] = {}
        self.load_contracts()
    
    def load_contracts(self):
        """Load API contracts from configuration."""
        self.contracts = {
            "get_users": APIContract(
                endpoint="/api/v1/users/",
                method="GET",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "email": {"type": "string", "format": "email"},
                            "full_name": {"type": "string"},
                            "is_active": {"type": "boolean"},
                            "created_at": {"type": "string", "format": "date-time"}
                        },
                        "required": ["id", "email", "full_name", "is_active"]
                    }
                },
                status_codes=[200]
            ),
            "create_user": APIContract(
                endpoint="/api/v1/users/",
                method="POST",
                request_schema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "full_name": {"type": "string", "minLength": 1},
                        "password": {"type": "string", "minLength": 8}
                    },
                    "required": ["email", "full_name", "password"]
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "email": {"type": "string", "format": "email"},
                        "full_name": {"type": "string"},
                        "is_active": {"type": "boolean"}
                    },
                    "required": ["id", "email", "full_name", "is_active"]
                },
                status_codes=[201]
            ),
            "get_tenders": APIContract(
                endpoint="/api/v1/tenders/",
                method="GET",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "deadline": {"type": "string", "format": "date-time"},
                            "status": {"type": "string", "enum": ["draft", "published", "closed", "cancelled"]},
                            "created_by": {"type": "integer"}
                        },
                        "required": ["id", "title", "deadline", "status"]
                    }
                }
            ),
            "create_tender": APIContract(
                endpoint="/api/v1/tenders/",
                method="POST",
                request_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "minLength": 1},
                        "description": {"type": "string"},
                        "deadline": {"type": "string", "format": "date-time"},
                        "requirements": {"type": "string"}
                    },
                    "required": ["title", "deadline"]
                },
                status_codes=[201]
            ),
            "get_quotes": APIContract(
                endpoint="/api/v1/quotes/",
                method="GET",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "tender_id": {"type": "integer"},
                            "supplier_id": {"type": "integer"},
                            "amount": {"type": "number", "minimum": 0},
                            "currency": {"type": "string"},
                            "status": {"type": "string"}
                        },
                        "required": ["id", "tender_id", "supplier_id", "amount"]
                    }
                }
            )
        }
    
    def validate_response(self, contract_name: str, response: httpx.Response) -> Dict[str, Any]:
        """Validate a response against its contract."""
        contract = self.contracts.get(contract_name)
        if not contract:
            raise ValueError(f"Contract '{contract_name}' not found")
        
        validation_results = {
            "contract_name": contract_name,
            "passed": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate status code
        if response.status_code not in contract.status_codes:
            validation_results["passed"] = False
            validation_results["errors"].append(
                f"Invalid status code: expected {contract.status_codes}, got {response.status_code}"
            )
        
        # Validate response schema
        if contract.response_schema and response.status_code < 400:
            try:
                response_data = response.json()
                jsonschema.validate(response_data, contract.response_schema)
            except jsonschema.ValidationError as e:
                validation_results["passed"] = False
                validation_results["errors"].append(f"Schema validation error: {e.message}")
            except json.JSONDecodeError:
                validation_results["passed"] = False
                validation_results["errors"].append("Invalid JSON response")
        
        # Validate headers
        if contract.headers:
            for header, expected_value in contract.headers.items():
                if header not in response.headers:
                    validation_results["warnings"].append(f"Missing header: {header}")
                elif response.headers[header] != expected_value:
                    validation_results["warnings"].append(
                        f"Header mismatch for {header}: expected {expected_value}, got {response.headers[header]}"
                    )
        
        return validation_results


class APIVersionCompatibilityTester:
    """Tests API backward compatibility across versions."""
    
    def __init__(self, client: TestClient):
        self.client = client
        self.validator = APIContractValidator()
    
    async def test_version_compatibility(self, endpoint: str, versions: List[str]) -> Dict[str, Any]:
        """Test endpoint compatibility across multiple API versions."""
        compatibility_results = {
            "endpoint": endpoint,
            "versions_tested": versions,
            "compatible": True,
            "version_results": {},
            "breaking_changes": []
        }
        
        for version in versions:
            versioned_endpoint = f"/api/{version}{endpoint}"
            try:
                response = self.client.get(versioned_endpoint)
                compatibility_results["version_results"][version] = {
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0,
                    "content_type": response.headers.get("content-type", "")
                }
                
                # Check for breaking changes
                if response.status_code >= 400:
                    compatibility_results["compatible"] = False
                    compatibility_results["breaking_changes"].append(
                        f"Version {version}: HTTP {response.status_code}"
                    )
                
            except Exception as e:
                compatibility_results["compatible"] = False
                compatibility_results["version_results"][version] = {"error": str(e)}
                compatibility_results["breaking_changes"].append(
                    f"Version {version}: {str(e)}"
                )
        
        return compatibility_results


class TestAPIContracts:
    """Test API contracts and compatibility."""
    
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, authenticated_user, db_session):
        self.client = client
        self.validator = APIContractValidator()
        self.compatibility_tester = APIVersionCompatibilityTester(client)
        self.authenticated_user = authenticated_user
        self.db_session = db_session
    
    def test_user_endpoints_contract(self):
        """Test user endpoints against their contracts."""
        # Test GET users
        response = self.client.get("/api/v1/users/")
        validation = self.validator.validate_response("get_users", response)
        
        assert validation["passed"], f"Contract validation failed: {validation['errors']}"
        
        # Test POST user
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "testpassword123"
        }
        response = self.client.post("/api/v1/users/", json=user_data)
        validation = self.validator.validate_response("create_user", response)
        
        assert validation["passed"], f"Contract validation failed: {validation['errors']}"
    
    def test_tender_endpoints_contract(self):
        """Test tender endpoints against their contracts."""
        # Test GET tenders
        response = self.client.get(
            "/api/v1/tenders/",
            headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
        )
        validation = self.validator.validate_response("get_tenders", response)
        
        assert validation["passed"], f"Contract validation failed: {validation['errors']}"
        
        # Test POST tender
        tender_data = {
            "title": "Test Tender",
            "description": "Test tender description",
            "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "requirements": "Test requirements"
        }
        response = self.client.post(
            "/api/v1/tenders/",
            json=tender_data,
            headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
        )
        validation = self.validator.validate_response("create_tender", response)
        
        assert validation["passed"], f"Contract validation failed: {validation['errors']}"
    
    def test_quote_endpoints_contract(self):
        """Test quote endpoints against their contracts."""
        response = self.client.get(
            "/api/v1/quotes/",
            headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
        )
        validation = self.validator.validate_response("get_quotes", response)
        
        assert validation["passed"], f"Contract validation failed: {validation['errors']}"
    
    @pytest.mark.asyncio
    async def test_api_version_compatibility(self):
        """Test backward compatibility across API versions."""
        endpoints_to_test = ["/users/", "/tenders/", "/quotes/"]
        versions = ["v1"]  # Add more versions as they become available
        
        for endpoint in endpoints_to_test:
            compatibility = await self.compatibility_tester.test_version_compatibility(
                endpoint, versions
            )
            
            assert compatibility["compatible"], \
                f"API compatibility broken for {endpoint}: {compatibility['breaking_changes']}"
    
    def test_response_time_contracts(self):
        """Test that API responses meet performance contracts."""
        endpoints = [
            "/api/v1/users/",
            "/api/v1/tenders/",
            "/api/v1/quotes/"
        ]
        
        max_response_time = 2.0  # 2 seconds
        
        for endpoint in endpoints:
            start_time = datetime.utcnow()
            
            if "users" in endpoint:
                response = self.client.get(endpoint)
            else:
                response = self.client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
                )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            assert response_time <= max_response_time, \
                f"Response time contract violated for {endpoint}: {response_time}s > {max_response_time}s"
    
    def test_error_response_contracts(self):
        """Test that error responses follow consistent contracts."""
        error_schema = {
            "type": "object",
            "properties": {
                "detail": {"type": ["string", "object"]},
                "type": {"type": "string"},
                "title": {"type": "string"}
            },
            "required": ["detail"]
        }
        
        # Test 404 errors
        response = self.client.get("/api/v1/users/99999")
        assert response.status_code == 404
        
        try:
            jsonschema.validate(response.json(), error_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Error response schema validation failed: {e.message}")
        
        # Test 401 errors
        response = self.client.get("/api/v1/tenders/")
        assert response.status_code == 401
        
        try:
            jsonschema.validate(response.json(), error_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Error response schema validation failed: {e.message}")
    
    def test_pagination_contracts(self):
        """Test pagination response contracts."""
        pagination_schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array"},
                "total": {"type": "integer", "minimum": 0},
                "page": {"type": "integer", "minimum": 1},
                "per_page": {"type": "integer", "minimum": 1},
                "pages": {"type": "integer", "minimum": 0}
            },
            "required": ["items", "total", "page", "per_page", "pages"]
        }
        
        response = self.client.get(
            "/api/v1/tenders/?page=1&per_page=10",
            headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
        )
        
        if response.status_code == 200:
            try:
                jsonschema.validate(response.json(), pagination_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(f"Pagination response schema validation failed: {e.message}")


class TestAPIDocumentationSync:
    """Test that API documentation stays in sync with implementation."""
    
    def test_openapi_schema_completeness(self, client: TestClient):
        """Test that all endpoints are documented in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        
        # Check that main endpoints are documented
        expected_endpoints = [
            "/api/v1/users/",
            "/api/v1/tenders/",
            "/api/v1/quotes/",
            "/api/v1/auth/login",
            "/api/v1/auth/logout"
        ]
        
        documented_paths = list(openapi_spec.get("paths", {}).keys())
        
        for endpoint in expected_endpoints:
            assert endpoint in documented_paths, \
                f"Endpoint {endpoint} is not documented in OpenAPI schema"
    
    def test_schema_definitions_exist(self, client: TestClient):
        """Test that all referenced schemas are properly defined."""
        response = client.get("/openapi.json")
        openapi_spec = response.json()
        
        # Check that schemas section exists and contains expected models
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        
        expected_schemas = [
            "UserCreate",
            "UserResponse",
            "TenderCreate",
            "TenderResponse",
            "QuoteCreate",
            "QuoteResponse",
            "HTTPValidationError"
        ]
        
        for schema_name in expected_schemas:
            assert schema_name in schemas, \
                f"Schema {schema_name} is missing from OpenAPI definitions"
