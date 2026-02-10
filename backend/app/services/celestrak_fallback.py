"""
Celestrak TLE fallback source.

When Space-Track is unavailable, fetch TLEs from Celestrak's public API.
No authentication required.

RATE LIMITING:
- Celestrak is a free public service - MUST respect their bandwidth
- Cache TLE data for 24 hours minimum (orbital elements don't change fast)
- Circuit breaker to prevent spamming on errors
- Max 1 request per hour per dataset

Celestrak API docs: https://celestrak.org/NORAD/documentation/gp-data-formats.php
"""
import httpx
from typing import Optional
from datetime import datetime, timezone, timedelta
import redis.asyncio as redis
import hashlib
import json
import structlog
from circuitbreaker import circuit

logger = structlog.get_logger()

CELESTRAK_BASE = "https://celestrak.org/NORAD/elements/gp.php"
CELESTRAK_CACHE_TTL = 86400  # 24 hours - Celestrak data doesn't change frequently
CELESTRAK_TIMEOUT = 120  # 120 seconds for large datasets
CELESTRAK_MIN_INTERVAL = 3600  # Minimum 1 hour between identical requests


class CelestrakFallback:
    """
    Celestrak TLE data source (public, no auth required).
    
    Use this when Space-Track is unavailable or during account suspension.
    
    IMPORTANT: Celestrak is a FREE public service - we MUST be respectful:
    - Cache everything for 24h minimum
    - Max 1 request per hour per dataset
    - Circuit breaker on errors
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._last_fetch: dict[str, datetime] = {}  # Track last fetch time per dataset
    
    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis connection for caching."""
        if self._redis is None:
            try:
                from app.core.config import get_settings
                settings = get_settings()
                redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
                self._redis = redis.from_url(redis_url, decode_responses=False)
            except Exception as e:
                logger.warning("Redis connection failed for Celestrak cache", error=str(e))
                return None
        return self._redis
    
    def _get_cache_key(self, dataset: str) -> str:
        """Generate Redis cache key for a dataset."""
        return f"celestrak:tle:{dataset}"
    
    def _can_fetch(self, dataset: str) -> bool:
        """Check if we can fetch (rate limiting)."""
        if dataset in self._last_fetch:
            elapsed = datetime.now(timezone.utc) - self._last_fetch[dataset]
            if elapsed.total_seconds() < CELESTRAK_MIN_INTERVAL:
                logger.warning(
                    "Celestrak rate limit - request too soon",
                    dataset=dataset,
                    elapsed_seconds=int(elapsed.total_seconds()),
                    min_interval=CELESTRAK_MIN_INTERVAL
                )
                return False
        return True
    
    async def _fetch_with_cache(
        self,
        dataset: str,
        params: dict
    ) -> dict[str, tuple[str, str, str]]:
        """
        Fetch from Celestrak with Redis caching and rate limiting.
        
        Cache TTL: 24 hours (orbital elements don't change fast)
        Rate limit: Max 1 request per hour per dataset
        """
        cache_key = self._get_cache_key(dataset)
        
        # Try cache first
        redis_client = await self._get_redis()
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    logger.info(
                        "Cache hit for Celestrak TLE data",
                        dataset=dataset,
                        source="celestrak_cache"
                    )
                    data = json.loads(cached_data)
                    return {k: tuple(v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Celestrak cache lookup failed", error=str(e))
        
        # Check rate limit
        if not self._can_fetch(dataset):
            raise Exception(f"Celestrak rate limit: Must wait {CELESTRAK_MIN_INTERVAL}s between requests for {dataset}")
        
        # Fetch from Celestrak
        logger.info(
            "Fetching TLE data from Celestrak (no cache)",
            dataset=dataset,
            cache_ttl=CELESTRAK_CACHE_TTL
        )
        
        try:
            async with httpx.AsyncClient(timeout=CELESTRAK_TIMEOUT) as client:
                response = await client.get(CELESTRAK_BASE, params=params)
                response.raise_for_status()
                
                data = response.json()
                result = {}
                
                for sat in data:
                    try:
                        norad_id = str(sat.get("NORAD_CAT_ID", "")).strip()
                        name = sat.get("OBJECT_NAME", f"SAT-{norad_id}")
                        line1 = sat.get("TLE_LINE1", "")
                        line2 = sat.get("TLE_LINE2", "")
                        
                        if norad_id and line1 and line2:
                            result[norad_id] = (name, line1, line2)
                    except Exception as e:
                        logger.warning("Failed to parse satellite", error=str(e))
                        continue
                
                # Update last fetch time
                self._last_fetch[dataset] = datetime.now(timezone.utc)
                
                # Cache the result (24h TTL)
                if redis_client:
                    try:
                        # Convert tuples to lists for JSON serialization
                        cache_data = {k: list(v) for k, v in result.items()}
                        await redis_client.setex(
                            cache_key,
                            CELESTRAK_CACHE_TTL,
                            json.dumps(cache_data)
                        )
                        logger.info(
                            "Cached Celestrak TLE data",
                            dataset=dataset,
                            count=len(result),
                            ttl_hours=CELESTRAK_CACHE_TTL // 3600
                        )
                    except Exception as e:
                        logger.warning("Failed to cache Celestrak data", error=str(e))
                
                logger.info(
                    "Celestrak TLE fetch successful",
                    dataset=dataset,
                    count=len(result),
                    source="celestrak_api"
                )
                return result
                
        except Exception as e:
            logger.error("Celestrak fetch failed", dataset=dataset, error=str(e))
            raise
    
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    async def fetch_starlink_tle(self) -> dict[str, tuple[str, str, str]]:
        """
        Fetch Starlink TLEs from Celestrak in JSON format.
        
        Circuit breaker: Fails fast after 5 consecutive failures, recovers after 60s.
        
        Returns:
            Dict mapping NORAD ID to (name, line1, line2)
            
        Caching: 24 hours
        Rate limit: Max 1 request per hour
        
        Raises:
            CircuitBreakerError: When circuit is open
        """
        params = {
            "GROUP": "starlink",
            "FORMAT": "json"
        }
        return await self._fetch_with_cache("starlink", params)
    
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    async def fetch_active_satellites(self, limit: int = 1000) -> dict[str, tuple[str, str, str]]:
        """
        Fetch active satellites from Celestrak.
        
        Circuit breaker: Fails fast after 5 consecutive failures, recovers after 60s.
        
        Args:
            limit: Maximum number of satellites to fetch
            
        Returns:
            Dict mapping NORAD ID to (name, line1, line2)
            
        Caching: 24 hours
        Rate limit: Max 1 request per hour
        
        Raises:
            CircuitBreakerError: When circuit is open
        """
        params = {
            "GROUP": "active",
            "FORMAT": "json"
        }
        result = await self._fetch_with_cache("active", params)
        # Limit after cache to preserve full cache
        if len(result) > limit:
            result = dict(list(result.items())[:limit])
        return result
    
    async def fetch_stations(self) -> dict[str, tuple[str, str, str]]:
        """
        Fetch space stations (ISS, Tiangong, etc.) from Celestrak.
        
        Returns:
            Dict mapping NORAD ID to (name, line1, line2)
            
        Caching: 24 hours
        Rate limit: Max 1 request per hour
        """
        params = {
            "GROUP": "stations",
            "FORMAT": "json"
        }
        return await self._fetch_with_cache("stations", params)


# Global instance
celestrak = CelestrakFallback()
