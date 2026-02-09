"""
Tests for cache key prefixing.

Story 1.4: Prefixed Cache Keys (P1-9)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache import CacheService
from app.core.config import Settings


class TestCachePrefixing:
    """Test cache key prefix functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with custom prefix."""
        settings = MagicMock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        settings.cache_ttl = 300
        settings.cache_prefix = "test_prefix:"
        return settings
    
    @pytest.fixture
    def cache_service(self, mock_settings):
        """Create cache service with mock settings."""
        with patch('app.services.cache.get_settings', return_value=mock_settings):
            service = CacheService()
            service._connected = True
            service._client = AsyncMock()
            return service
    
    @pytest.mark.asyncio
    async def test_make_key_adds_prefix(self, cache_service):
        """Test _make_key() adds prefix to key."""
        result = cache_service._make_key("test_key")
        assert result == "test_prefix:test_key"
    
    @pytest.mark.asyncio
    async def test_get_uses_prefixed_key(self, cache_service):
        """Test get() uses prefixed key when calling Redis."""
        cache_service._client.get = AsyncMock(return_value='{"data": "test"}')
        
        await cache_service.get("my_key")
        
        # Verify Redis get was called with prefixed key
        cache_service._client.get.assert_called_once_with("test_prefix:my_key")
    
    @pytest.mark.asyncio
    async def test_set_uses_prefixed_key(self, cache_service):
        """Test set() uses prefixed key when calling Redis."""
        cache_service._client.setex = AsyncMock()
        
        await cache_service.set("my_key", {"data": "test"}, ttl=60)
        
        # Verify Redis setex was called with prefixed key
        cache_service._client.setex.assert_called_once()
        call_args = cache_service._client.setex.call_args
        assert call_args[0][0] == "test_prefix:my_key"  # First arg is key
        assert call_args[0][1] == 60  # Second arg is TTL
    
    @pytest.mark.asyncio
    async def test_delete_uses_prefixed_key(self, cache_service):
        """Test delete() uses prefixed key when calling Redis."""
        cache_service._client.delete = AsyncMock()
        
        await cache_service.delete("my_key")
        
        # Verify Redis delete was called with prefixed key
        cache_service._client.delete.assert_called_once_with("test_prefix:my_key")
    
    @pytest.mark.asyncio
    async def test_clear_pattern_uses_prefixed_pattern(self, cache_service):
        """Test clear_pattern() prefixes the pattern."""
        # Mock scan_iter to return some keys
        async def mock_scan_iter(match):
            # Verify pattern is prefixed
            assert match == "test_prefix:user:*"
            # Return async iterator
            for key in ["test_prefix:user:1", "test_prefix:user:2"]:
                yield key
        
        cache_service._client.scan_iter = mock_scan_iter
        cache_service._client.delete = AsyncMock()
        
        result = await cache_service.clear_pattern("user:*")
        
        # Should have deleted 2 keys
        assert result == 2
        cache_service._client.delete.assert_called_once()


class TestCachePrefixWithDefaultSettings:
    """Test with actual default settings."""
    
    def test_default_prefix_in_settings(self):
        """Test default settings include cache_prefix."""
        from app.core.config import Settings
        settings = Settings()
        
        assert hasattr(settings, 'cache_prefix')
        assert settings.cache_prefix == "spacex_orbital:"
    
    @pytest.mark.asyncio
    async def test_prefix_applied_to_real_keys(self):
        """Test prefix is applied in realistic scenarios."""
        from app.services.cache import CacheService
        from app.core.config import get_settings
        
        settings = get_settings()
        service = CacheService()
        
        # Verify prefix matches expected
        prefixed = service._make_key("satellites:positions")
        assert prefixed == f"{settings.cache_prefix}satellites:positions"
        assert prefixed == "spacex_orbital:satellites:positions"


class TestCachePrefixCollisionPrevention:
    """Test that prefixing prevents collisions."""
    
    @pytest.mark.asyncio
    async def test_different_services_dont_collide(self, cache_service):
        """
        Test that different services using Redis don't collide.
        
        If service A uses key "user:123" and service B uses key "user:123",
        with prefixes they become:
        - service_a:user:123
        - service_b:user:123
        """
        cache_service._client.get = AsyncMock(return_value=None)
        
        # Service uses key "user:123"
        await cache_service.get("user:123")
        
        # Redis actually receives "test_prefix:user:123"
        cache_service._client.get.assert_called_once_with("test_prefix:user:123")
        
        # Another service with different prefix wouldn't see this key
    
    @pytest.mark.asyncio
    async def test_no_prefix_leakage(self, cache_service):
        """Test that keys without prefix are not accidentally accessed."""
        cache_service._client.get = AsyncMock(return_value=None)
        
        # Try to get unprefixed key
        await cache_service.get("satellites")
        
        # Should try to get prefixed version
        cache_service._client.get.assert_called_once_with("test_prefix:satellites")
        
        # NOT called with unprefixed "satellites"


class TestCachePrefixEdgeCases:
    """Test edge cases for cache prefixing."""
    
    @pytest.mark.asyncio
    async def test_empty_key(self, cache_service):
        """Test empty key is still prefixed."""
        result = cache_service._make_key("")
        assert result == "test_prefix:"
    
    @pytest.mark.asyncio
    async def test_key_with_colon(self, cache_service):
        """Test key containing colon works correctly."""
        result = cache_service._make_key("namespace:key:subkey")
        assert result == "test_prefix:namespace:key:subkey"
    
    @pytest.mark.asyncio
    async def test_wildcard_pattern(self, cache_service):
        """Test wildcard pattern is prefixed correctly."""
        result = cache_service._make_key("user:*")
        assert result == "test_prefix:user:*"
    
    @pytest.mark.asyncio
    async def test_unicode_key(self, cache_service):
        """Test unicode characters in key are preserved."""
        result = cache_service._make_key("用户:123")
        assert result == "test_prefix:用户:123"


@pytest.mark.integration
class TestCachePrefixIntegration:
    """Integration tests for cache prefixing."""
    
    @pytest.mark.asyncio
    async def test_full_cache_flow_with_prefix(self):
        """Test complete cache flow with prefixing."""
        # This would require actual Redis connection
        # Placeholder for integration testing
        pass
    
    @pytest.mark.asyncio
    async def test_prefix_in_all_api_endpoints(self):
        """Test all API endpoints use prefixed cache."""
        # Verify no endpoint bypasses the cache service
        # Placeholder for integration testing
        pass
