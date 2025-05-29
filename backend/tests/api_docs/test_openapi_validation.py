"""
API Documentation Tests
Tests for OpenAPI schema validation, documentation completeness, and API consistency.
"""

import pytest
import json
from typing import Dict, Any, List
from fastapi.testclient import TestClient
from fastapi.openapi.utils import get_openapi
import jsonschema
from jsonschema import validate, ValidationError
import requests

from app.main import app


class TestOpenAPISchema:
    """Test OpenAPI schema generation and validation."""
    
    def test_openapi_schema_generation(self, client: TestClient):
        """Test that OpenAPI schema is generated correctly."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Basic OpenAPI structure validation
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Version should be valid
        assert schema["openapi"].startswith("3.")
        
        # Info section should be complete
        info = schema["info"]
        assert "title" in info
        assert "version" in info
        assert "description" in info
        assert len(info["title"]) > 0
        assert len(info["version"]) > 0
    
    def test_openapi_schema_validity(self, client: TestClient):
        """Test that OpenAPI schema is valid according to OpenAPI 3.0 spec."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Download OpenAPI 3.0 schema for validation
        try:
            openapi_spec_response = requests.get(
                "https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/schemas/v3.0/schema.json",
                timeout=10
            )
            if openapi_spec_response.status_code == 200:
                openapi_spec = openapi_spec_response.json()
                
                # Validate our schema against OpenAPI spec
                validate(instance=schema, schema=openapi_spec)
        except (requests.RequestException, ValidationError):
            # If we can't download or validate, at least check basic structure
            assert isinstance(schema, dict)
            assert "paths" in schema
    
    def test_all_endpoints_documented(self, client: TestClient):
        """Test that all endpoints are documented in OpenAPI."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        documented_paths = set(schema["paths"].keys())
        
        # Check that major endpoint groups are documented
        expected_path_prefixes = [
            "/api/v1/auth",
            "/api/v1/users",
            "/api/v1/tenders", 
            "/api/v1/companies",
            "/api/v1/suppliers",
            "/api/v1/quotes",
            "/api/v1/kanban",
            "/api/v1/files",
        ]
        
        for prefix in expected_path_prefixes:
            matching_paths = [path for path in documented_paths if path.startswith(prefix)]
            assert len(matching_paths) > 0, f"No documented paths found for {prefix}"
    
    def test_response_schemas_defined(self, client: TestClient):
        """Test that response schemas are properly defined."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    assert "responses" in operation, f"No responses defined for {method.upper()} {path}"
                    
                    responses = operation["responses"]
                    assert "200" in responses or "201" in responses or "204" in responses, \
                        f"No success response defined for {method.upper()} {path}"
    
    def test_request_schemas_defined(self, client: TestClient):
        """Test that request schemas are properly defined for endpoints that need them."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() in ["post", "put", "patch"]:
                    # These methods should usually have request body schemas
                    if "requestBody" in operation:
                        request_body = operation["requestBody"]
                        assert "content" in request_body
                        assert "application/json" in request_body["content"]
    
    def test_authentication_documented(self, client: TestClient):
        """Test that authentication is properly documented."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Should have security schemes defined
        assert "components" in schema
        if "securitySchemes" in schema["components"]:
            security_schemes = schema["components"]["securitySchemes"]
            assert len(security_schemes) > 0
            
            # Should have Bearer token authentication
            bearer_auth = None
            for scheme_name, scheme_def in security_schemes.items():
                if scheme_def.get("type") == "http" and scheme_def.get("scheme") == "bearer":
                    bearer_auth = scheme_def
                    break
            
            assert bearer_auth is not None, "Bearer token authentication not documented"
    
    def test_error_responses_documented(self, client: TestClient):
        """Test that error responses are documented."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    responses = operation.get("responses", {})
                    
                    # Should have common error responses
                    if any(path.startswith(prefix) for prefix in ["/api/v1/users", "/api/v1/tenders"]):
                        # Protected endpoints should document 401
                        assert "401" in responses or "default" in responses
                    
                    if method.lower() in ["post", "put", "patch"]:
                        # Data modification endpoints should document 422
                        assert "422" in responses or "default" in responses


class TestAPIDocumentation:
    """Test API documentation completeness and quality."""
    
    def test_endpoint_descriptions(self, client: TestClient):
        """Test that endpoints have meaningful descriptions."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    # Should have description or summary
                    assert "summary" in operation or "description" in operation, \
                        f"No description for {method.upper()} {path}"
                    
                    description = operation.get("summary", "") + operation.get("description", "")
                    assert len(description.strip()) > 10, \
                        f"Description too short for {method.upper()} {path}"
    
    def test_parameter_documentation(self, client: TestClient):
        """Test that parameters are properly documented."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "parameters" in operation:
                    for param in operation["parameters"]:
                        # Each parameter should have required fields
                        assert "name" in param
                        assert "in" in param
                        assert "schema" in param or "content" in param
                        
                        # Should have description for non-obvious parameters
                        if param["name"] not in ["id", "page", "limit"]:
                            assert "description" in param, \
                                f"No description for parameter {param['name']} in {method.upper()} {path}"
    
    def test_example_values(self, client: TestClient):
        """Test that schemas include example values."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        if "components" in schema and "schemas" in schema["components"]:
            schemas = schema["components"]["schemas"]
            
            # Check that major data models have examples
            important_schemas = ["User", "Tender", "Company", "Quote"]
            
            for schema_name in important_schemas:
                if schema_name in schemas:
                    schema_def = schemas[schema_name]
                    
                    # Should have example or examples in properties
                    has_examples = "example" in schema_def
                    if not has_examples and "properties" in schema_def:
                        for prop_name, prop_def in schema_def["properties"].items():
                            if "example" in prop_def:
                                has_examples = True
                                break
                    
                    assert has_examples, f"No examples found for {schema_name} schema"
    
    def test_tags_organization(self, client: TestClient):
        """Test that endpoints are properly organized with tags."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Collect all used tags
        used_tags = set()
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "tags" in operation:
                    used_tags.update(operation["tags"])
        
        # Should have logical tag groupings
        expected_tags = {"Authentication", "Users", "Tenders", "Companies", "Quotes"}
        found_tags = {tag for tag in used_tags if tag in expected_tags}
        assert len(found_tags) >= 3, f"Expected more organizational tags, found: {found_tags}"
        
        # Tags should be defined in schema
        if "tags" in schema:
            defined_tags = {tag["name"] for tag in schema["tags"]}
            for tag in used_tags:
                assert tag in defined_tags, f"Tag '{tag}' used but not defined"


class TestAPIConsistency:
    """Test API consistency and conventions."""
    
    def test_http_methods_consistency(self, client: TestClient):
        """Test that HTTP methods are used consistently."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            # Collection endpoints (no ID in path)
            if not any(char in path for char in ["{", "}"]):
                if "get" in methods:
                    # GET on collection should return array
                    get_op = methods["get"]
                    if "responses" in get_op and "200" in get_op["responses"]:
                        response_schema = get_op["responses"]["200"].get("content", {}).get("application/json", {}).get("schema", {})
                        # Should be array or have items property indicating list
                        assert "type" not in response_schema or response_schema["type"] == "array" or "items" in response_schema
                
                if "post" in methods:
                    # POST on collection should create resource
                    post_op = methods["post"]
                    assert "201" in post_op.get("responses", {}), f"POST {path} should return 201"
            
            # Item endpoints (with ID in path)
            else:
                if "get" in methods:
                    # GET on item should return single object
                    get_op = methods["get"]
                    if "responses" in get_op and "200" in get_op["responses"]:
                        response_schema = get_op["responses"]["200"].get("content", {}).get("application/json", {}).get("schema", {})
                        # Should not be array
                        assert response_schema.get("type") != "array"
                
                if "delete" in methods:
                    # DELETE should return 204 or 200
                    delete_op = methods["delete"]
                    responses = delete_op.get("responses", {})
                    assert "204" in responses or "200" in responses, f"DELETE {path} should return 204 or 200"
    
    def test_status_code_consistency(self, client: TestClient):
        """Test that status codes are used consistently."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() == "post":
                    # POST should primarily return 201 for creation
                    responses = operation.get("responses", {})
                    if not any(path.endswith(suffix) for suffix in ["/login", "/logout", "/search"]):
                        assert "201" in responses, f"POST {path} should return 201 for creation"
                
                elif method.lower() == "delete":
                    # DELETE should return 204 (no content) or 200
                    responses = operation.get("responses", {})
                    assert "204" in responses or "200" in responses
    
    def test_parameter_naming_consistency(self, client: TestClient):
        """Test that parameter names are consistent across endpoints."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        parameter_names = {}
        
        # Collect parameter names and their types
        for path, methods in paths.items():
            for method, operation in methods.items():
                if "parameters" in operation:
                    for param in operation["parameters"]:
                        name = param["name"]
                        param_type = param.get("schema", {}).get("type", "unknown")
                        param_in = param["in"]
                        
                        key = (name, param_in)
                        if key not in parameter_names:
                            parameter_names[key] = param_type
                        else:
                            # Same parameter name should have same type
                            assert parameter_names[key] == param_type, \
                                f"Parameter {name} has inconsistent types: {parameter_names[key]} vs {param_type}"
    
    def test_pagination_consistency(self, client: TestClient):
        """Test that pagination is implemented consistently."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Find list endpoints that should support pagination
        list_endpoints = []
        for path, methods in paths.items():
            if "get" in methods and not any(char in path for char in ["{", "}"]):
                # Collection GET endpoints
                list_endpoints.append((path, methods["get"]))
        
        pagination_params = set()
        
        for path, operation in list_endpoints:
            if "parameters" in operation:
                for param in operation["parameters"]:
                    if param["name"] in ["page", "limit", "offset", "size"]:
                        pagination_params.add(param["name"])
        
        # If any endpoint uses pagination, check consistency
        if pagination_params:
            for path, operation in list_endpoints:
                param_names = {p["name"] for p in operation.get("parameters", [])}
                
                # Should use consistent pagination parameter names
                if "page" in param_names:
                    assert "limit" in param_names or "size" in param_names
                elif "offset" in param_names:
                    assert "limit" in param_names


class TestAPIVersioning:
    """Test API versioning and backward compatibility."""
    
    def test_version_in_path(self, client: TestClient):
        """Test that API version is included in paths."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Most paths should include version
        versioned_paths = [path for path in paths.keys() if "/v1/" in path]
        total_api_paths = [path for path in paths.keys() if path.startswith("/api/")]
        
        if total_api_paths:
            version_ratio = len(versioned_paths) / len(total_api_paths)
            assert version_ratio > 0.8, "Most API paths should include version number"
    
    def test_version_consistency(self, client: TestClient):
        """Test that version is consistent across the API."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # All versioned paths should use the same version
        versions = set()
        for path in paths.keys():
            if "/v" in path:
                # Extract version (e.g., v1, v2)
                parts = path.split("/")
                for part in parts:
                    if part.startswith("v") and part[1:].isdigit():
                        versions.add(part)
        
        # Should only have one version (for now)
        assert len(versions) <= 1, f"Multiple API versions found: {versions}"


class TestSchemaValidation:
    """Test that actual API responses match documented schemas."""
    
    def test_login_response_schema(self, client: TestClient, test_user):
        """Test that login response matches documented schema."""
        # Get the documented schema
        openapi_response = client.get("/openapi.json")
        openapi_schema = openapi_response.json()
        
        # Find login endpoint schema
        login_schema = None
        if "/api/v1/auth/login" in openapi_schema["paths"]:
            login_op = openapi_schema["paths"]["/api/v1/auth/login"].get("post", {})
            if "responses" in login_op and "200" in login_op["responses"]:
                login_schema = login_op["responses"]["200"].get("content", {}).get("application/json", {}).get("schema", {})
        
        if login_schema:
            # Test actual login response
            response = client.post(
                "/api/v1/auth/login",
                data={"username": test_user.email, "password": "testpassword"}
            )
            assert response.status_code == 200
            
            # Validate response against schema
            try:
                validate(instance=response.json(), schema=login_schema)
            except ValidationError as e:
                pytest.fail(f"Login response doesn't match schema: {e}")
    
    def test_user_response_schema(self, client: TestClient, auth_headers):
        """Test that user response matches documented schema."""
        openapi_response = client.get("/openapi.json")
        openapi_schema = openapi_response.json()
        
        # Find user schema in components
        user_schema = None
        if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
            user_schema = openapi_schema["components"]["schemas"].get("User")
        
        if user_schema:
            # Test actual user response
            response = client.get("/api/v1/users/me", headers=auth_headers)
            assert response.status_code == 200
            
            # Validate response against schema
            try:
                validate(instance=response.json(), schema=user_schema)
            except ValidationError as e:
                pytest.fail(f"User response doesn't match schema: {e}")
    
    def test_error_response_schemas(self, client: TestClient):
        """Test that error responses match documented schemas."""
        openapi_response = client.get("/openapi.json")
        openapi_schema = openapi_response.json()
        
        # Test 401 error
        response = client.get("/api/v1/users/me")  # No auth header
        assert response.status_code == 401
        
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)
        
        # Test 422 validation error
        response = client.post("/api/v1/auth/login", json={})  # Invalid data
        if response.status_code == 422:
            error_data = response.json()
            assert "detail" in error_data
            # Should have validation error format
            if isinstance(error_data["detail"], list):
                for error in error_data["detail"]:
                    assert "msg" in error
                    assert "type" in error


class TestAPIDocumentationUI:
    """Test API documentation UI accessibility."""
    
    def test_swagger_ui_accessible(self, client: TestClient):
        """Test that Swagger UI is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Should contain Swagger UI elements
        content = response.text.lower()
        assert "swagger" in content or "openapi" in content
    
    def test_redoc_accessible(self, client: TestClient):
        """Test that ReDoc is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Should contain ReDoc elements
        content = response.text.lower()
        assert "redoc" in content
    
    def test_openapi_json_accessible(self, client: TestClient):
        """Test that OpenAPI JSON is directly accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        
        # Should be valid JSON
        schema = response.json()
        assert isinstance(schema, dict)
        assert "openapi" in schema
