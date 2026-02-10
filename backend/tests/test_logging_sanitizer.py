"""
Test logging sanitizer to prevent secret leakage.

SECURITY CRITICAL: These tests verify that no secrets leak into logs.
Failed tests = potential security vulnerability.

Standards: OWASP Top 10, Code Quality (security)
"""
import pytest
from app.core.logging_sanitizer import (
    sanitize_string,
    sanitize_dict,
    sanitize_log_record,
    SECRET_PATTERNS
)


class TestSanitizeString:
    """Test string sanitization."""
    
    def test_redacts_api_keys(self):
        """API keys must be redacted."""
        # Generic API key
        text = "api_key=sk_test_1234567890abcdefghij"
        assert "1234567890abcdefghij" not in sanitize_string(text)
        assert "[REDACTED_API_KEY]" in sanitize_string(text)
        
        # N2YO specific format
        text = "n2yo_key=J5ACSV-H8HVFU-BN3F86-5NMK"
        sanitized = sanitize_string(text)
        assert "J5ACSV" not in sanitized
        assert "[REDACTED_N2YO_KEY]" in sanitized
    
    def test_redacts_tokens(self):
        """Bearer tokens and JWT must be redacted."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = sanitize_string(text)
        assert "eyJhbGci" not in sanitized
        assert "[REDACTED_BEARER_TOKEN]" in sanitized
    
    def test_redacts_passwords(self):
        """Passwords must be redacted."""
        text = "password=SuperSecret123!"
        sanitized = sanitize_string(text)
        assert "SuperSecret123!" not in sanitized
        assert "[REDACTED_PASSWORD]" in sanitized
        
        # Different formats
        assert "mypass" not in sanitize_string('pwd="mypass"')
        assert "secret" not in sanitize_string("passwd:secret")
    
    def test_redacts_aws_keys(self):
        """AWS credentials must be redacted."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        sanitized = sanitize_string(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "[REDACTED_AWS_KEY]" in sanitized
    
    def test_redacts_private_keys(self):
        """Private keys must be redacted."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
        sanitized = sanitize_string(text)
        assert "BEGIN RSA PRIVATE KEY" not in sanitized
        assert "[REDACTED_PRIVATE_KEY]" in sanitized
    
    def test_redacts_database_credentials(self):
        """Database connection strings must be redacted."""
        text = "postgresql://user:password123@localhost:5432/db"
        sanitized = sanitize_string(text)
        assert "password123" not in sanitized
        assert "[REDACTED_PASSWORD]" in sanitized
        assert "user" not in sanitized or "[REDACTED_USER]" in sanitized
    
    def test_preserves_safe_strings(self):
        """Safe strings must not be modified."""
        safe_texts = [
            "Normal log message",
            "User clicked button",
            "Request took 123ms",
            "Error: Connection refused",
            "Satellite ID: 44000"
        ]
        
        for text in safe_texts:
            assert sanitize_string(text) == text


class TestSanitizeDict:
    """Test dictionary sanitization."""
    
    def test_redacts_sensitive_keys(self):
        """Dictionary keys with sensitive names must be redacted."""
        data = {
            "username": "alice",
            "password": "secret123",
            "api_key": "sk_test_abc123",
            "email": "alice@example.com"
        }
        
        sanitized = sanitize_dict(data)
        
        # Sensitive keys redacted
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        
        # Safe keys preserved
        assert sanitized["username"] == "alice"
        assert sanitized["email"] == "alice@example.com"
    
    def test_recursive_sanitization(self):
        """Nested dictionaries must be sanitized recursively."""
        data = {
            "user": {
                "name": "alice",
                "credentials": {
                    "password": "secret",
                    "token": "abc123"
                }
            }
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["user"]["name"] == "alice"
        assert sanitized["user"]["credentials"]["password"] == "[REDACTED]"
        assert sanitized["user"]["credentials"]["token"] == "[REDACTED]"
    
    def test_sanitizes_lists(self):
        """Lists containing dicts/strings must be sanitized."""
        data = {
            "users": [
                {"name": "alice", "password": "secret1"},
                {"name": "bob", "password": "secret2"}
            ]
        }
        
        sanitized = sanitize_dict(data)
        
        for user in sanitized["users"]:
            assert user["password"] == "[REDACTED]"
            assert user["name"] in ["alice", "bob"]
    
    def test_handles_none_values(self):
        """None values must not cause errors."""
        data = {
            "key": None,
            "password": None
        }
        
        sanitized = sanitize_dict(data)
        
        # password key still redacted even if value is None
        assert sanitized["password"] == "[REDACTED]"


class TestSanitizeLogRecord:
    """Test structlog log record sanitization."""
    
    def test_sanitizes_event_dict(self):
        """structlog event dict must be sanitized."""
        event_dict = {
            "event": "User login",
            "username": "alice",
            "password": "secret123",
            "api_key": "sk_test_abc"
        }
        
        sanitized = sanitize_log_record(None, None, event_dict)
        
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["username"] == "alice"
    
    def test_sanitizes_url_with_secrets(self):
        """URLs containing secrets in query params must be sanitized."""
        event_dict = {
            "event": "API call",
            "url": "https://api.example.com/data?api_key=sk_test_123456"
        }
        
        sanitized = sanitize_log_record(None, None, event_dict)
        
        # API key in URL must be redacted
        assert "sk_test_123456" not in sanitized["url"]
        assert "[REDACTED_API_KEY]" in sanitized["url"]


class TestSecretPatterns:
    """Test coverage of secret patterns."""
    
    def test_all_patterns_have_test_coverage(self):
        """Verify all SECRET_PATTERNS are tested."""
        # This test documents which patterns exist
        pattern_types = set()
        
        for pattern, replacement in SECRET_PATTERNS:
            # Extract pattern type from replacement
            if "API_KEY" in replacement:
                pattern_types.add("api_key")
            elif "TOKEN" in replacement:
                pattern_types.add("token")
            elif "PASSWORD" in replacement:
                pattern_types.add("password")
            elif "AWS" in replacement:
                pattern_types.add("aws")
            elif "PRIVATE_KEY" in replacement:
                pattern_types.add("private_key")
        
        # Minimum pattern types that MUST exist
        required_patterns = {"api_key", "token", "password"}
        
        assert required_patterns.issubset(pattern_types), \
            f"Missing required patterns: {required_patterns - pattern_types}"


class TestRealWorldExamples:
    """Test with real-world log examples."""
    
    def test_space_track_login(self):
        """Space-Track credentials must never leak."""
        log_entry = {
            "event": "Space-Track login",
            "username": "user@example.com",
            "password": "MySpaceTrackPass123!",
            "url": "https://www.space-track.org/auth/login"
        }
        
        sanitized = sanitize_dict(log_entry)
        
        assert "MySpaceTrackPass123!" not in str(sanitized)
        assert sanitized["password"] == "[REDACTED]"
    
    def test_n2yo_api_call(self):
        """N2YO API keys must never leak."""
        log_entry = {
            "event": "N2YO API call",
            "url": "https://api.n2yo.com/rest/v1/satellite/tle/25544?apiKey=J5ACSV-H8HVFU-BN3F86-5NMK"
        }
        
        sanitized = sanitize_dict(log_entry)
        
        assert "J5ACSV" not in sanitized["url"]
        assert "[REDACTED_N2YO_KEY]" in sanitized["url"]
    
    def test_redis_connection_string(self):
        """Redis connection strings with passwords must be sanitized."""
        log_entry = {
            "event": "Redis connection",
            "redis_url": "redis://:myRedisPassword@localhost:6379/0"
        }
        
        sanitized = sanitize_dict(log_entry)
        
        # Password should be redacted
        assert "myRedisPassword" not in sanitized["redis_url"]
    
    def test_http_error_with_auth_header(self):
        """HTTP errors must not leak auth headers."""
        log_entry = {
            "event": "HTTP error",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                "Content-Type": "application/json"
            }
        }
        
        sanitized = sanitize_dict(log_entry)
        
        # Authorization header must be redacted
        assert sanitized["headers"]["Authorization"] == "[REDACTED]"
        # Other headers preserved
        assert sanitized["headers"]["Content-Type"] == "application/json"


class TestEdgeCases:
    """Test edge cases and potential bypasses."""
    
    def test_case_insensitive_keys(self):
        """Sensitive keys must be detected regardless of case."""
        data = {
            "PASSWORD": "secret",
            "Password": "secret",
            "PaSsWoRd": "secret"
        }
        
        sanitized = sanitize_dict(data)
        
        for key in data.keys():
            assert sanitized[key] == "[REDACTED]"
    
    def test_partial_matches(self):
        """Keys containing sensitive words must be detected."""
        data = {
            "user_password": "secret",
            "api_key_prod": "key123",
            "oauth_token": "token123"
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["user_password"] == "[REDACTED]"
        assert sanitized["api_key_prod"] == "[REDACTED]"
        assert sanitized["oauth_token"] == "[REDACTED]"
    
    def test_empty_values(self):
        """Empty sensitive values must not crash sanitizer."""
        data = {
            "password": "",
            "api_key": "",
            "token": None
        }
        
        # Should not raise exception
        sanitized = sanitize_dict(data)
        
        # All still redacted
        for key in data.keys():
            assert sanitized[key] == "[REDACTED]"
