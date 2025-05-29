"""
General helper utilities for the application.
"""
import re
import hashlib
import secrets
import string
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
import phonenumbers
from email_validator import validate_email, EmailNotValidError


class ValidationUtils:
    """Utility class for data validation."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address."""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    @staticmethod
    def is_valid_phone(phone: str, country_code: str = None) -> bool:
        """Validate phone number."""
        try:
            parsed = phonenumbers.parse(phone, country_code)
            return phonenumbers.is_valid_number(parsed)
        except phonenumbers.NumberParseException:
            return False
    
    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """Validate UUID string."""
        try:
            UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_strong_password(password: str) -> tuple[bool, List[str]]:
        """
        Validate password strength.
        Returns (is_valid, list_of_issues)
        """
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        if len(password) > 100:
            issues.append("Password must be less than 100 characters")
        
        # Check for common patterns
        common_patterns = [
            r'123456',
            r'password',
            r'qwerty',
            r'abc123',
            r'admin'
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                issues.append(f"Password contains common pattern: {pattern}")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        if not text:
            return ""
        
        # Remove potential XSS characters
        text = re.sub(r'[<>&"\']', '', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Strip whitespace
        text = text.strip()
        
        # Limit length
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None


class StringUtils:
    """Utility class for string operations."""
    
    @staticmethod
    def generate_random_string(length: int = 12, include_special: bool = False) -> str:
        """Generate random string."""
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += "!@#$%^&*"
        
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def slug_from_string(text: str, max_length: int = 50) -> str:
        """Generate URL-friendly slug from string."""
        # Convert to lowercase and replace spaces with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # Limit length
        if len(slug) > max_length:
            slug = slug[:max_length].rsplit('-', 1)[0]
        
        return slug
    
    @staticmethod
    def truncate_string(text: str, length: int, suffix: str = "...") -> str:
        """Truncate string with suffix."""
        if len(text) <= length:
            return text
        
        return text[:length - len(suffix)] + suffix
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Extract all numbers from text."""
        pattern = r'-?\d+\.?\d*'
        matches = re.findall(pattern, text)
        return [float(match) for match in matches if match]
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text."""
        pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(pattern, text)
    
    @staticmethod
    def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
        """Mask sensitive data in string."""
        # Mask email addresses
        text = re.sub(
            r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
            lambda m: f"{m.group(1)[:2]}{mask_char * 3}@{m.group(2)}",
            text
        )
        
        # Mask phone numbers
        text = re.sub(
            r'\b\d{3}-?\d{3}-?\d{4}\b',
            lambda m: f"{m.group(0)[:3]}{mask_char * 6}{m.group(0)[-1:]}",
            text
        )
        
        return text


class HashUtils:
    """Utility class for hashing operations."""
    
    @staticmethod
    def hash_string(text: str, algorithm: str = 'sha256') -> str:
        """Hash string using specified algorithm."""
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(text.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def hash_file(file_content: bytes, algorithm: str = 'sha256') -> str:
        """Hash file content."""
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(file_content)
        return hash_obj.hexdigest()
    
    @staticmethod
    def generate_checksum(data: Union[str, bytes], algorithm: str = 'md5') -> str:
        """Generate checksum for data."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data)
        return hash_obj.hexdigest()


class DataUtils:
    """Utility class for data operations."""
    
    @staticmethod
    def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DataUtils.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    @staticmethod
    def unflatten_dict(d: Dict, sep: str = '.') -> Dict:
        """Unflatten dictionary with nested keys."""
        result = {}
        for key, value in d.items():
            parts = key.split(sep)
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        return result
    
    @staticmethod
    def remove_none_values(d: Dict) -> Dict:
        """Remove None values from dictionary."""
        return {k: v for k, v in d.items() if v is not None}
    
    @staticmethod
    def convert_keys_to_snake_case(d: Dict) -> Dict:
        """Convert dictionary keys to snake_case."""
        def to_snake_case(name: str) -> str:
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        if isinstance(d, dict):
            return {to_snake_case(k): DataUtils.convert_keys_to_snake_case(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [DataUtils.convert_keys_to_snake_case(item) for item in d]
        else:
            return d
    
    @staticmethod
    def convert_keys_to_camel_case(d: Dict) -> Dict:
        """Convert dictionary keys to camelCase."""
        def to_camel_case(name: str) -> str:
            components = name.split('_')
            return components[0] + ''.join(x.title() for x in components[1:])
        
        if isinstance(d, dict):
            return {to_camel_case(k): DataUtils.convert_keys_to_camel_case(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [DataUtils.convert_keys_to_camel_case(item) for item in d]
        else:
            return d


class FormatUtils:
    """Utility class for formatting operations."""
    
    @staticmethod
    def format_currency(
        amount: float,
        currency: str = 'USD',
        locale: str = 'en_US'
    ) -> str:
        """Format currency amount."""
        try:
            import babel.numbers
            return babel.numbers.format_currency(amount, currency, locale=locale)
        except ImportError:
            # Fallback formatting
            return f"{amount:,.2f} {currency}"
    
    @staticmethod
    def format_number(
        number: Union[int, float],
        precision: int = 2,
        locale: str = 'en_US'
    ) -> str:
        """Format number with locale-specific formatting."""
        try:
            import babel.numbers
            return babel.numbers.format_decimal(number, locale=locale)
        except ImportError:
            # Fallback formatting
            if isinstance(number, float):
                return f"{number:,.{precision}f}"
            else:
                return f"{number:,}"
    
    @staticmethod
    def format_percentage(value: float, precision: int = 1) -> str:
        """Format percentage value."""
        return f"{value:.{precision}f}%"
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours}h {remaining_minutes}m"


class IDGenerator:
    """Utility class for generating various types of IDs."""
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID4."""
        return str(uuid4())
    
    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        """Generate short alphanumeric ID."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    @staticmethod
    def generate_invoice_number(prefix: str = "INV", year: int = None) -> str:
        """Generate invoice number."""
        from datetime import datetime
        if year is None:
            year = datetime.now().year
        
        # Generate random 6-digit number
        random_part = ''.join(secrets.choice(string.digits) for _ in range(6))
        return f"{prefix}-{year}-{random_part}"
    
    @staticmethod
    def generate_order_number(prefix: str = "ORD") -> str:
        """Generate order number."""
        timestamp = int(datetime.now().timestamp())
        random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
        return f"{prefix}-{timestamp}-{random_part}"
    
    @staticmethod
    def generate_reference_code(length: int = 10) -> str:
        """Generate reference code."""
        chars = string.ascii_uppercase + string.digits
        # Exclude confusing characters
        chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1')
        return ''.join(secrets.choice(chars) for _ in range(length))
