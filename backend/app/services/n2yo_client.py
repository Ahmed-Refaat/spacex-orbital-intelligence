"""
N2YO.com API Client for TLE data and satellite tracking.

API: https://www.n2yo.com/api/
Rate Limits: 300 requests/hour (free tier)
Coverage: Excellent (all satellites including Starlink)

Security: API key never logged (redacted by logging_sanitizer)
"""
import httpx
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import redis.asyncio as redis
import json
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"


class N2YORateLimiter:
    """
    Rate limiter for N2YO API.
    
    Free tier limits: 300 requests/hour
    Implementation: Redis-backed sliding window counter
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._max_requests = 300
        self._window_seconds = 3600  # 1 hour
        self._counter_key = "n2yo:rate_limit:counter"
        self._timestamps_key = "n2yo:rate_limit:timestamps"
    
    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis connection."""
        if self._redis is None:
            try:
                settings = get_settings()
                redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
                self._redis = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                logger.warning("Redis connection failed for N2YO rate limiter", error=str(e))
                return None
        return self._redis
    
    async def can_make_request(self) -> tuple[bool, int]:
        """
        Check if we can make a request.
        
        Returns:
            Tuple of (can_request, requests_remaining)
        """
        redis_client = await self._get_redis()
        if not redis_client:
            # No Redis - allow but warn
            logger.warning("N2YO rate limiter: Redis unavailable, allowing request")
            return True, self._max_requests
        
        try:
            now = datetime.now(timezone.utc).timestamp()
            window_start = now - self._window_seconds
            
            # Remove old timestamps outside window
            await redis_client.zremrangebyscore(
                self._timestamps_key,
                '-inf',
                window_start
            )
            
            # Count requests in current window
            count = await redis_client.zcard(self._timestamps_key)
            
            if count < self._max_requests:
                return True, self._max_requests - count
            else:
                logger.warning(
                    "N2YO rate limit reached",
                    count=count,
                    max=self._max_requests,
                    window_seconds=self._window_seconds
                )
                return False, 0
        
        except Exception as e:
            logger.error("N2YO rate limiter error", error=str(e))
            # Fail open - allow request
            return True, self._max_requests
    
    async def record_request(self):
        """Record that a request was made."""
        redis_client = await self._get_redis()
        if not redis_client:
            return
        
        try:
            now = datetime.now(timezone.utc).timestamp()
            
            # Add timestamp to sorted set
            await redis_client.zadd(
                self._timestamps_key,
                {str(now): now}
            )
            
            # Set expiry on key (cleanup)
            await redis_client.expire(
                self._timestamps_key,
                self._window_seconds + 60  # Extra buffer
            )
        
        except Exception as e:
            logger.error("N2YO rate limiter record error", error=str(e))


class N2YOClient:
    """
    N2YO API client with rate limiting and caching.
    
    Features:
    - Rate limiting (300 req/hour)
    - Redis caching (24h for TLE data)
    - API key security (never logged)
    - Graceful degradation
    
    Usage:
        client = N2YOClient()
        tle = await client.get_tle("25544")
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = getattr(self.settings, 'n2yo_api_key', None)
        self.rate_limiter = N2YORateLimiter()
        self._redis: Optional[redis.Redis] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)
    
    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis connection."""
        if self._redis is None:
            try:
                redis_url = getattr(self.settings, 'redis_url', 'redis://localhost:6379/0')
                self._redis = redis.from_url(redis_url, decode_responses=True)
            except Exception:
                return None
        return self._redis
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            )
        return self._client
    
    def _get_cache_key(self, endpoint: str, params: dict) -> str:
        """Generate cache key for request."""
        import hashlib
        param_str = json.dumps(params, sort_keys=True)
        hash_str = hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()
        return f"n2yo:cache:{hash_str}"
    
    async def _cached_request(
        self,
        endpoint: str,
        params: dict,
        cache_ttl: int = 86400  # 24 hours default
    ) -> Optional[dict]:
        """
        Make cached API request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters (API key added automatically)
            cache_ttl: Cache TTL in seconds
            
        Returns:
            Response JSON or None
        """
        if not self.is_configured:
            logger.error("N2YO API key not configured")
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(endpoint, params)
        redis_client = await self._get_redis()
        
        if redis_client:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info("N2YO cache hit", endpoint=endpoint)
                    return json.loads(cached)
            except Exception as e:
                logger.warning("N2YO cache lookup failed", error=str(e))
        
        # Check rate limit
        can_request, remaining = await self.rate_limiter.can_make_request()
        if not can_request:
            logger.error(
                "N2YO rate limit exceeded",
                endpoint=endpoint,
                max_per_hour=300
            )
            return None
        
        # Make API request
        try:
            client = await self._get_client()
            
            # Add API key to params
            request_params = {**params, 'apiKey': self.api_key}
            
            # Security: Log params WITHOUT API key
            safe_params = {k: v for k, v in params.items()}
            logger.info(
                "N2YO API request",
                endpoint=endpoint,
                params=safe_params,
                remaining_quota=remaining
            )
            
            url = f"{N2YO_BASE_URL}{endpoint}"
            response = await client.get(url, params=request_params)
            
            # Record request for rate limiting
            await self.rate_limiter.record_request()
            
            if response.status_code == 200:
                data = response.json()
                
                # Cache the result
                if redis_client:
                    try:
                        await redis_client.setex(
                            cache_key,
                            cache_ttl,
                            json.dumps(data)
                        )
                        logger.info(
                            "N2YO response cached",
                            endpoint=endpoint,
                            ttl_hours=cache_ttl // 3600
                        )
                    except Exception as e:
                        logger.warning("N2YO cache write failed", error=str(e))
                
                return data
            else:
                logger.error(
                    "N2YO API error",
                    endpoint=endpoint,
                    status_code=response.status_code,
                    response_preview=response.text[:200]
                )
                return None
        
        except Exception as e:
            logger.error(
                "N2YO API request failed",
                endpoint=endpoint,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def get_tle(self, norad_id: str) -> Optional[tuple[str, str, str]]:
        """
        Get TLE for a satellite.
        
        Args:
            norad_id: NORAD catalog number
            
        Returns:
            Tuple of (name, line1, line2) or None
        """
        # N2YO endpoint: /tle/{id}
        endpoint = f"/tle/{norad_id}"
        
        data = await self._cached_request(
            endpoint,
            {},
            cache_ttl=86400  # 24 hours
        )
        
        if not data:
            return None
        
        # Parse N2YO TLE format
        try:
            name = data.get('info', {}).get('satname', f'SAT-{norad_id}')
            line1 = data.get('tle', '')
            
            # N2YO returns TLE as single string, need to split
            if line1:
                lines = line1.strip().split('\n')
                if len(lines) >= 2:
                    logger.info(
                        "N2YO TLE retrieved",
                        norad_id=norad_id,
                        name=name
                    )
                    return (name, lines[0], lines[1])
            
            logger.warning("N2YO TLE format unexpected", norad_id=norad_id)
            return None
        
        except Exception as e:
            logger.error(
                "N2YO TLE parse error",
                norad_id=norad_id,
                error=str(e)
            )
            return None
    
    async def get_status(self) -> dict:
        """Get N2YO client status."""
        can_request, remaining = await self.rate_limiter.can_make_request()
        
        return {
            "configured": self.is_configured,
            "rate_limit": {
                "max_per_hour": 300,
                "remaining": remaining,
                "can_request": can_request
            }
        }
    
    async def close(self):
        """Close connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global instance
n2yo_client = N2YOClient()
