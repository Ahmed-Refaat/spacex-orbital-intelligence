"""Redis cache service with timeout protection."""
import json
from typing import Optional, Any
import asyncio
import redis.asyncio as redis
import structlog

from app.core.config import get_settings
from app.core.metrics import CACHE_HIT_RATE

logger = structlog.get_logger()


class CacheService:
    """Redis-based caching service with comprehensive timeout handling."""
    
    # Timeout configuration (seconds)
    CONNECT_TIMEOUT = 5.0   # Connection establishment
    SOCKET_TIMEOUT = 2.0    # Socket read/write operations
    GET_TIMEOUT = 1.0       # GET operation timeout
    SET_TIMEOUT = 2.0       # SET operation timeout
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """
        Connect to Redis with explicit timeouts.
        
        Returns:
            bool: True if connected successfully, False otherwise
        
        Raises:
            Never raises - failures are logged and return False
        """
        try:
            # Create Redis client with timeout configuration
            self._client = await asyncio.wait_for(
                redis.from_url(
                    self.settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=self.CONNECT_TIMEOUT,
                    socket_timeout=self.SOCKET_TIMEOUT,
                    socket_keepalive=True,
                    max_connections=50,
                    retry_on_timeout=True,
                    health_check_interval=30
                ),
                timeout=self.CONNECT_TIMEOUT
            )
            
            # Test connection
            await asyncio.wait_for(
                self._client.ping(),
                timeout=2.0
            )
            
            self._connected = True
            logger.info(
                "Redis connected",
                timeouts={
                    "connect": self.CONNECT_TIMEOUT,
                    "socket": self.SOCKET_TIMEOUT,
                    "get": self.GET_TIMEOUT,
                    "set": self.SET_TIMEOUT
                }
            )
            return True
        
        except asyncio.TimeoutError:
            logger.error(
                "Redis connection timeout",
                timeout=self.CONNECT_TIMEOUT
            )
            self._connected = False
            return False
        
        except Exception as e:
            logger.warning(
                "Redis connection failed, running without cache",
                error=str(e),
                error_type=type(e).__name__
            )
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False
    
    def _make_key(self, key: str) -> str:
        """
        Add namespace prefix to cache key.
        
        Args:
            key: Unprefixed cache key
        
        Returns:
            Prefixed key (e.g., "spacex_orbital:satellites:positions")
        """
        return f"{self.settings.cache_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with timeout protection.
        
        Args:
            key: Cache key (will be prefixed automatically)
        
        Returns:
            Cached value if found, None otherwise
        
        Metrics:
            Records cache hit/miss/timeout/error to Prometheus
        """
        if not self._connected or not self._client:
            CACHE_HIT_RATE.labels(operation='get', result='disconnected').inc()
            return None
        
        try:
            prefixed_key = self._make_key(key)
            
            # GET with timeout protection
            value = await asyncio.wait_for(
                self._client.get(prefixed_key),
                timeout=self.GET_TIMEOUT
            )
            
            if value:
                CACHE_HIT_RATE.labels(operation='get', result='hit').inc()
                logger.debug("cache_hit", key=key)
                return json.loads(value)
            else:
                CACHE_HIT_RATE.labels(operation='get', result='miss').inc()
                logger.debug("cache_miss", key=key)
                return None
        
        except asyncio.TimeoutError:
            CACHE_HIT_RATE.labels(operation='get', result='timeout').inc()
            logger.warning(
                "Cache GET timeout",
                key=key,
                timeout=self.GET_TIMEOUT
            )
            return None
        
        except json.JSONDecodeError as e:
            CACHE_HIT_RATE.labels(operation='get', result='decode_error').inc()
            logger.error(
                "Cache value JSON decode failed",
                key=key,
                error=str(e)
            )
            return None
        
        except Exception as e:
            CACHE_HIT_RATE.labels(operation='get', result='error').inc()
            logger.warning(
                "Cache GET failed",
                key=key,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with timeout protection.
        
        Args:
            key: Cache key (will be prefixed automatically)
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (defaults to settings.cache_ttl)
        
        Returns:
            bool: True if set successfully, False otherwise
        
        Metrics:
            Records cache set success/timeout/error to Prometheus
        """
        if not self._connected or not self._client:
            CACHE_HIT_RATE.labels(operation='set', result='disconnected').inc()
            return False
        
        try:
            ttl = ttl or self.settings.cache_ttl
            prefixed_key = self._make_key(key)
            
            # Serialize value
            try:
                serialized = json.dumps(value)
            except (TypeError, ValueError) as e:
                CACHE_HIT_RATE.labels(operation='set', result='serialize_error').inc()
                logger.error(
                    "Cache value serialization failed",
                    key=key,
                    error=str(e)
                )
                return False
            
            # SET with timeout protection
            await asyncio.wait_for(
                self._client.setex(prefixed_key, ttl, serialized),
                timeout=self.SET_TIMEOUT
            )
            
            CACHE_HIT_RATE.labels(operation='set', result='success').inc()
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
        
        except asyncio.TimeoutError:
            CACHE_HIT_RATE.labels(operation='set', result='timeout').inc()
            logger.warning(
                "Cache SET timeout",
                key=key,
                timeout=self.SET_TIMEOUT
            )
            return False
        
        except Exception as e:
            CACHE_HIT_RATE.labels(operation='set', result='error').inc()
            logger.warning(
                "Cache SET failed",
                key=key,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected:
            return False
        
        try:
            prefixed_key = self._make_key(key)
            await self._client.delete(prefixed_key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Note: Pattern is automatically prefixed.
        """
        if not self._connected:
            return 0
        
        try:
            prefixed_pattern = self._make_key(pattern)
            keys = []
            async for key in self._client.scan_iter(match=prefixed_pattern):
                keys.append(key)
            
            if keys:
                await self._client.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.warning("Cache clear failed", pattern=pattern, error=str(e))
            return 0
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected


# Global cache instance
cache = CacheService()
