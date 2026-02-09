"""
Professional Rate Limiting for External APIs

Prevents overuse of external services like SPICE API.
"""
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class APIRateLimiter:
    """
    Rate limiter for external API calls.
    
    Prevents excessive calls to external services by:
    - Caching results with TTL
    - Tracking call frequency
    - Enforcing minimum intervals between calls
    - Logging rate limit violations
    
    Example:
        >>> limiter = APIRateLimiter(name="spice_health", min_interval_sec=30)
        >>> if limiter.can_call():
        ...     result = await call_external_api()
        ...     limiter.record_call(result)
        >>> else:
        ...     result = limiter.get_cached()
    """
    
    def __init__(
        self,
        name: str,
        min_interval_sec: float = 10.0,
        cache_ttl_sec: float = 60.0,
        max_calls_per_minute: int = 60
    ):
        """
        Initialize rate limiter.
        
        Args:
            name: Name for logging/identification
            min_interval_sec: Minimum seconds between calls
            cache_ttl_sec: How long to cache results
            max_calls_per_minute: Maximum calls per minute
        """
        self.name = name
        self.min_interval_sec = min_interval_sec
        self.cache_ttl_sec = cache_ttl_sec
        self.max_calls_per_minute = max_calls_per_minute
        
        # State tracking
        self._last_call_time: Optional[float] = None
        self._cached_result: Optional[any] = None
        self._cache_expiry: Optional[float] = None
        self._call_history: list[float] = []  # Timestamps of recent calls
        
        logger.info(
            "rate_limiter_initialized",
            name=name,
            min_interval=min_interval_sec,
            cache_ttl=cache_ttl_sec,
            max_per_minute=max_calls_per_minute
        )
    
    def can_call(self) -> bool:
        """
        Check if we can make a call now.
        
        Returns:
            True if call is allowed, False if should use cache
        """
        now = time.time()
        
        # Check if cached result is still valid
        if self._cache_expiry and now < self._cache_expiry:
            logger.debug(
                "rate_limiter_cache_hit",
                name=self.name,
                cache_remaining_sec=round(self._cache_expiry - now, 1)
            )
            return False
        
        # Check minimum interval
        if self._last_call_time:
            elapsed = now - self._last_call_time
            if elapsed < self.min_interval_sec:
                logger.debug(
                    "rate_limiter_throttled_min_interval",
                    name=self.name,
                    elapsed_sec=round(elapsed, 1),
                    required_sec=self.min_interval_sec
                )
                return False
        
        # Check calls per minute limit
        # Clean old history (>1 minute ago)
        cutoff = now - 60.0
        self._call_history = [t for t in self._call_history if t > cutoff]
        
        if len(self._call_history) >= self.max_calls_per_minute:
            logger.warning(
                "rate_limiter_throttled_max_per_minute",
                name=self.name,
                current_calls=len(self._call_history),
                max_allowed=self.max_calls_per_minute
            )
            return False
        
        return True
    
    def record_call(self, result: any) -> None:
        """
        Record that a call was made and cache the result.
        
        Args:
            result: Result to cache
        """
        now = time.time()
        
        self._last_call_time = now
        self._cached_result = result
        self._cache_expiry = now + self.cache_ttl_sec
        self._call_history.append(now)
        
        logger.debug(
            "rate_limiter_call_recorded",
            name=self.name,
            cache_ttl=self.cache_ttl_sec
        )
    
    def get_cached(self) -> Optional[any]:
        """
        Get cached result if available and valid.
        
        Returns:
            Cached result or None
        """
        now = time.time()
        
        if self._cache_expiry and now < self._cache_expiry:
            return self._cached_result
        
        return None
    
    def force_refresh(self) -> None:
        """Force refresh by invalidating cache."""
        self._cache_expiry = None
        logger.info("rate_limiter_cache_invalidated", name=self.name)
    
    def get_stats(self) -> dict:
        """Get limiter statistics."""
        now = time.time()
        
        # Count recent calls
        cutoff = now - 60.0
        recent_calls = [t for t in self._call_history if t > cutoff]
        
        return {
            "name": self.name,
            "can_call_now": self.can_call(),
            "has_cached_result": self._cached_result is not None,
            "cache_valid": self._cache_expiry is not None and now < self._cache_expiry,
            "cache_remaining_sec": round(self._cache_expiry - now, 1) if self._cache_expiry and now < self._cache_expiry else 0,
            "calls_last_minute": len(recent_calls),
            "max_calls_per_minute": self.max_calls_per_minute,
            "last_call_ago_sec": round(now - self._last_call_time, 1) if self._last_call_time else None
        }


class SPICERateLimiter:
    """
    Specialized rate limiter for SPICE API.
    
    Enforces conservative limits:
    - Health checks: Max once per 30 seconds
    - OMM loads: Max 5 per minute
    - Propagations: Max 100 per minute (batch operations count as 1)
    """
    
    def __init__(self):
        self.health_check = APIRateLimiter(
            name="spice_health_check",
            min_interval_sec=30.0,  # Max 1 check per 30s
            cache_ttl_sec=30.0,
            max_calls_per_minute=2
        )
        
        self.omm_load = APIRateLimiter(
            name="spice_omm_load",
            min_interval_sec=1.0,  # Reasonable spacing
            cache_ttl_sec=0,  # Don't cache (each upload unique)
            max_calls_per_minute=5  # Conservative limit
        )
        
        self.propagate = APIRateLimiter(
            name="spice_propagate",
            min_interval_sec=0.1,  # Allow frequent calls
            cache_ttl_sec=0,  # Don't cache (positions change)
            max_calls_per_minute=100  # High limit for batch operations
        )
        
        logger.info("SPICERateLimiter initialized")
    
    def get_all_stats(self) -> dict:
        """Get stats for all limiters."""
        return {
            "health_check": self.health_check.get_stats(),
            "omm_load": self.omm_load.get_stats(),
            "propagate": self.propagate.get_stats()
        }


# Global instance
spice_rate_limiter = SPICERateLimiter()
