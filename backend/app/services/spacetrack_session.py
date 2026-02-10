"""
Centralized Space-Track.org session management.

This module ensures compliance with Space-Track API usage policy:
1. Session reuse: One login per 2h (we refresh at 1h50min to be safe)
2. GP data caching: Minimum 1 hour cache for identical queries
3. No unnecessary login/logout cycles

Space-Track session lasts 2 hours and auto-renews on each query.
"""
import httpx
import redis.asyncio as redis
from datetime import datetime, timezone, timedelta
from typing import Optional
import json
import hashlib
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

BASE_URL = "https://www.space-track.org"
SESSION_DURATION = timedelta(hours=1, minutes=50)  # Refresh before 2h expiry
GP_CACHE_TTL = 3600  # 1 hour minimum cache for GP data


class SpaceTrackSessionManager:
    """
    Singleton session manager for Space-Track.org API.
    
    Ensures:
    - One session shared across all services
    - Auto-refresh every ~1h50min (before 2h expiry)
    - Redis caching of GP ephemerides (min 1h)
    - Compliance with Space-Track API policy
    """
    
    _instance: Optional['SpaceTrackSessionManager'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._session_cookies: Optional[httpx.Cookies] = None
        self._session_created_at: Optional[datetime] = None
        self._redis: Optional[redis.Redis] = None
        
        self.username = self.settings.spacetrack_username
        self.password = self.settings.spacetrack_password
        
        self._initialized = True
        logger.info("SpaceTrack session manager initialized")
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection for caching."""
        if self._redis is None:
            # Parse Redis URL from settings
            redis_url = getattr(self.settings, 'redis_url', 'redis://localhost:6379/0')
            self._redis = redis.from_url(redis_url, decode_responses=False)
        return self._redis
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=60.0,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
    
    def _is_session_valid(self) -> bool:
        """Check if current session is still valid."""
        if not self._session_cookies or not self._session_created_at:
            return False
        
        age = datetime.now(timezone.utc) - self._session_created_at
        return age < SESSION_DURATION
    
    async def _authenticate(self) -> bool:
        """
        Authenticate with Space-Track.org.
        
        Only called when:
        - No session exists
        - Session is older than 1h50min
        """
        if not self.username or not self.password:
            logger.error("Space-Track credentials not configured")
            return False
        
        # Check if we already have a valid session
        if self._is_session_valid():
            logger.debug("Using existing Space-Track session")
            return True
        
        client = await self._get_client()
        
        try:
            logger.info("Authenticating with Space-Track.org (session expired or first login)")
            
            response = await client.post(
                "/ajaxauth/login",
                data={
                    "identity": self.username,
                    "password": self.password
                }
            )
            
            if response.status_code == 200:
                self._session_cookies = response.cookies
                self._session_created_at = datetime.now(timezone.utc)
                
                logger.info(
                    "Space-Track authentication successful",
                    session_valid_until=(self._session_created_at + SESSION_DURATION).isoformat()
                )
                return True
            else:
                logger.error(
                    "Space-Track authentication failed",
                    status_code=response.status_code,
                    response_preview=response.text[:200]
                )
                return False
                
        except Exception as e:
            logger.error("Space-Track authentication error", error=str(e))
            return False
    
    def _get_cache_key(self, query_path: str) -> str:
        """Generate Redis cache key for a query."""
        # Hash the query path to create a stable key
        query_hash = hashlib.md5(query_path.encode()).hexdigest()
        return f"spacetrack:gp:{query_hash}"
    
    async def get(
        self,
        path: str,
        cache_ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Optional[httpx.Response]:
        """
        Execute a GET request to Space-Track with automatic caching.
        
        Args:
            path: API path (e.g., "/basicspacedata/query/class/gp/...")
            cache_ttl: Cache TTL in seconds (default: 3600 for GP queries, None for others)
            force_refresh: Skip cache and force fresh fetch
            
        Returns:
            Response object or None on error
        """
        # Auto-detect GP queries for caching
        is_gp_query = "/class/gp" in path or "/class/tle" in path
        
        if cache_ttl is None and is_gp_query:
            cache_ttl = GP_CACHE_TTL  # Default 1h cache for GP data
        
        # Try cache first (only for GP queries)
        if not force_refresh and cache_ttl and is_gp_query:
            try:
                redis_client = await self._get_redis()
                cache_key = self._get_cache_key(path)
                cached_data = await redis_client.get(cache_key)
                
                if cached_data:
                    logger.info(
                        "Cache hit for Space-Track GP query",
                        path_preview=path[:80]
                    )
                    # Return a mock response with cached data
                    return _MockResponse(200, cached_data)
                
            except Exception as e:
                logger.warning("Cache lookup failed, continuing with API call", error=str(e))
        
        # Authenticate if needed
        if not await self._authenticate():
            logger.error("Failed to authenticate with Space-Track")
            return None
        
        client = await self._get_client()
        
        try:
            logger.info(
                "Executing Space-Track API request",
                path_preview=path[:80],
                cached=False
            )
            
            response = await client.get(path, cookies=self._session_cookies)
            
            # Session renews automatically on each query (Space-Track behavior)
            # So we update our timestamp
            self._session_created_at = datetime.now(timezone.utc)
            
            if response.status_code != 200:
                logger.error(
                    "Space-Track API error",
                    status_code=response.status_code,
                    path_preview=path[:80]
                )
                return None
            
            # Cache GP data
            if cache_ttl and is_gp_query:
                try:
                    redis_client = await self._get_redis()
                    cache_key = self._get_cache_key(path)
                    await redis_client.setex(
                        cache_key,
                        cache_ttl,
                        response.content
                    )
                    logger.info(
                        "Cached Space-Track GP data",
                        ttl_seconds=cache_ttl,
                        size_bytes=len(response.content)
                    )
                except Exception as e:
                    logger.warning("Failed to cache response", error=str(e))
            
            return response
            
        except Exception as e:
            logger.error("Space-Track API request failed", error=str(e), path_preview=path[:80])
            return None
    
    async def close(self):
        """Close all connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        self._session_cookies = None
        self._session_created_at = None
        logger.info("Space-Track session manager closed")
    
    def get_status(self) -> dict:
        """Get session status for monitoring."""
        if self._session_created_at:
            age = datetime.now(timezone.utc) - self._session_created_at
            valid_until = self._session_created_at + SESSION_DURATION
            time_remaining = valid_until - datetime.now(timezone.utc)
            
            return {
                "authenticated": self._is_session_valid(),
                "session_age_seconds": int(age.total_seconds()),
                "session_remaining_seconds": int(time_remaining.total_seconds()),
                "session_valid_until": valid_until.isoformat(),
                "credentials_configured": bool(self.username and self.password)
            }
        else:
            return {
                "authenticated": False,
                "credentials_configured": bool(self.username and self.password)
            }


class _MockResponse:
    """Mock response for cached data."""
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content
        self.text = content.decode('utf-8')
    
    def json(self):
        return json.loads(self.text)


# Global singleton instance
session_manager = SpaceTrackSessionManager()
