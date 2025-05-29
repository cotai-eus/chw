"""
Helper utilities for testing.
"""
import json
import random
import string
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import base64

class TestDataGenerator:
    """Generate test data for various testing scenarios."""
    
    @staticmethod
    def generate_random_string(length: int = 10, include_special: bool = False) -> str:
        """Generate a random string of specified length."""
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))
    
    @staticmethod
    def generate_email(domain: str = "example.com") -> str:
        """Generate a random email address."""
        username = TestDataGenerator.generate_random_string(8).lower()
        return f"{username}@{domain}"
    
    @staticmethod
    def generate_cnpj() -> str:
        """Generate a valid-format CNPJ (Brazilian tax ID)."""
        # This generates a format-valid CNPJ, not necessarily a real one
        digits = [random.randint(0, 9) for _ in range(12)]
        cnpj = ''.join(map(str, digits))
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{random.randint(10, 99)}"
    
    @staticmethod
    def generate_phone() -> str:
        """Generate a Brazilian phone number format."""
        ddd = random.randint(11, 99)
        number = random.randint(10000000, 999999999)
        return f"({ddd}) {str(number)[:5]}-{str(number)[5:]}"
    
    @staticmethod
    def generate_future_date(days_ahead: int = 30) -> datetime:
        """Generate a future date."""
        return datetime.now() + timedelta(days=days_ahead)
    
    @staticmethod
    def generate_past_date(days_ago: int = 30) -> datetime:
        """Generate a past date."""
        return datetime.now() - timedelta(days=days_ago)

class TestAssertions:
    """Custom assertion helpers for testing."""
    
    @staticmethod
    def assert_dict_contains(container: Dict, subset: Dict, path: str = ""):
        """Assert that a dictionary contains all key-value pairs from subset."""
        for key, expected_value in subset.items():
            current_path = f"{path}.{key}" if path else key
            assert key in container, f"Missing key '{current_path}' in dictionary"
            
            if isinstance(expected_value, dict) and isinstance(container[key], dict):
                TestAssertions.assert_dict_contains(container[key], expected_value, current_path)
            else:
                assert container[key] == expected_value, \
                    f"Value mismatch at '{current_path}': expected {expected_value}, got {container[key]}"
    
    @staticmethod
    def assert_response_structure(response: Dict, required_fields: List[str]):
        """Assert that a response contains all required fields."""
        for field in required_fields:
            assert field in response, f"Missing required field '{field}' in response"
    
    @staticmethod
    def assert_valid_timestamp(timestamp_str: str):
        """Assert that a string is a valid ISO timestamp."""
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            assert False, f"Invalid timestamp format: {timestamp_str}"

class TestSecurityHelpers:
    """Security-related test helpers."""
    
    @staticmethod
    def generate_jwt_token_mock(payload: Dict[str, Any]) -> str:
        """Generate a mock JWT token (not cryptographically secure)."""
        header = {"alg": "HS256", "typ": "JWT"}
        
        # Base64 encode header and payload
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Mock signature
        signature = hashlib.sha256(f"{header_b64}.{payload_b64}".encode()).hexdigest()[:32]
        
        return f"{header_b64}.{payload_b64}.{signature}"
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a mock API key."""
        return TestDataGenerator.generate_random_string(32, include_special=True)

class TestFileHelpers:
    """File-related test helpers."""
    
    @staticmethod
    def create_mock_file_content(file_type: str = "json") -> bytes:
        """Create mock file content based on type."""
        if file_type == "json":
            data = {"test": True, "timestamp": datetime.now().isoformat()}
            return json.dumps(data).encode()
        elif file_type == "csv":
            content = "id,name,email\n1,Test User,test@example.com\n"
            return content.encode()
        elif file_type == "txt":
            return b"This is a test file content."
        else:
            return b"Binary file content"
    
    @staticmethod
    def validate_file_structure(file_content: str, expected_keys: List[str]):
        """Validate file structure contains expected keys."""
        try:
            data = json.loads(file_content)
            for key in expected_keys:
                assert key in data, f"Missing key '{key}' in file content"
        except json.JSONDecodeError:
            assert False, "File content is not valid JSON"

def wait_for_condition(condition_func, timeout: int = 10, interval: float = 0.1) -> bool:
    """Wait for a condition to become true within a timeout."""
    import time
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False
