"""
Tests for API key security.

Story 1.2: Mandatory API Key in Production (P0-4)
"""
import pytest
import os
from unittest.mock import patch

from app.core.security import get_api_key


class TestAPIKeyProduction:
    """Test API key behavior in production environment."""
    
    def test_production_without_key_raises_error(self):
        """Test production mode without API key raises RuntimeError."""
        with patch.dict(os.environ, {"ENV": "production", "SPACEX_API_KEY": ""}, clear=True):
            # Clear cached key
            import app.core.security
            app.core.security._api_key = None
            
            with pytest.raises(RuntimeError) as exc_info:
                get_api_key()
            
            assert "SPACEX_API_KEY must be set in production" in str(exc_info.value)
            assert "python -c" in str(exc_info.value)  # Includes generation instructions
    
    def test_production_with_key_returns_key(self):
        """Test production mode with API key returns the key."""
        test_key = "test_production_key_12345"
        
        with patch.dict(os.environ, {"ENV": "production", "SPACEX_API_KEY": test_key}, clear=True):
            # Clear cached key
            import app.core.security
            app.core.security._api_key = None
            
            key = get_api_key()
            
            assert key == test_key
    
    def test_production_case_insensitive(self):
        """Test ENV=Production (capital P) is also treated as production."""
        with patch.dict(os.environ, {"ENV": "Production", "SPACEX_API_KEY": ""}, clear=True):
            import app.core.security
            app.core.security._api_key = None
            
            with pytest.raises(RuntimeError):
                get_api_key()


class TestAPIKeyDevelopment:
    """Test API key behavior in development environment."""
    
    def test_dev_without_key_generates_temporary(self, capsys):
        """Test dev mode without key generates temporary key with warning."""
        with patch.dict(os.environ, {"ENV": "development", "SPACEX_API_KEY": ""}, clear=True):
            # Clear cached key
            import app.core.security
            app.core.security._api_key = None
            
            key = get_api_key()
            
            # Should generate a key
            assert key is not None
            assert len(key) > 20  # urlsafe(32) generates ~43 chars
            
            # Should print warning
            captured = capsys.readouterr()
            assert "[DEV]" in captured.out
            assert "temporary" in captured.out.lower()
    
    def test_dev_with_key_uses_key(self):
        """Test dev mode with API key uses that key."""
        test_key = "test_dev_key_67890"
        
        with patch.dict(os.environ, {"ENV": "development", "SPACEX_API_KEY": test_key}, clear=True):
            import app.core.security
            app.core.security._api_key = None
            
            key = get_api_key()
            
            assert key == test_key
    
    def test_no_env_defaults_to_development(self, capsys):
        """Test missing ENV variable defaults to development behavior."""
        with patch.dict(os.environ, {"SPACEX_API_KEY": ""}, clear=True):
            # Remove ENV key entirely
            if "ENV" in os.environ:
                del os.environ["ENV"]
            
            import app.core.security
            app.core.security._api_key = None
            
            key = get_api_key()
            
            # Should generate temporary key (dev behavior)
            assert key is not None
            
            captured = capsys.readouterr()
            assert "[DEV]" in captured.out


class TestAPIKeyCaching:
    """Test API key caching mechanism."""
    
    def test_key_cached_after_first_call(self):
        """Test API key is cached after first retrieval."""
        test_key = "cached_key_test"
        
        with patch.dict(os.environ, {"ENV": "development", "SPACEX_API_KEY": test_key}, clear=True):
            import app.core.security
            app.core.security._api_key = None
            
            # First call
            key1 = get_api_key()
            
            # Second call (should use cached value)
            key2 = get_api_key()
            
            assert key1 == key2 == test_key


class TestSecurityDocumentation:
    """Test that security documentation is updated."""
    
    def test_security_md_mentions_api_key_requirement(self):
        """Test SECURITY.md documents API key requirement."""
        with open("SECURITY.md", "r") as f:
            content = f.read()
        
        # Check for API key documentation
        assert "SPACEX_API_KEY" in content or "API" in content
    
    def test_env_example_includes_api_key(self):
        """Test .env.example includes API key placeholder."""
        try:
            with open(".env.example", "r") as f:
                content = f.read()
            
            assert "SPACEX_API_KEY" in content or "API_KEY" in content
        except FileNotFoundError:
            pytest.skip(".env.example not found")


@pytest.mark.integration
class TestAPIKeyInEndpoints:
    """Test API key is enforced in protected endpoints."""
    
    def test_protected_endpoint_without_key_fails(self):
        """Test protected endpoint without API key returns 401."""
        # This test depends on which endpoints are actually protected
        # Placeholder for integration testing
        pass
    
    def test_protected_endpoint_with_valid_key_succeeds(self):
        """Test protected endpoint with valid API key succeeds."""
        # Placeholder for integration testing
        pass
