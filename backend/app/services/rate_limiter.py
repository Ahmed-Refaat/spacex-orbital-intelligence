"""
Rate limiter for external APIs (SpaceTrack, N2YO, etc.)

Ensures compliance with API quotas:
- SpaceTrack: 30 requests/minute, 300/hour
- N2YO: 300 requests/hour (free tier)
"""
from typing import Optional
from datetime import datetime, timedelta
import asyncio
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Uses sliding window to enforce both per-minute and per-hour limits.
    Thread-safe via asyncio locks.
    """
    
    def __init__(
        self,
        name: str,
        requests_per_minute: int,
        requests_per_hour: int
    ):
        self.name = name
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        
        # Sliding windows
        self._minute_requests: list[datetime] = []
        self._hour_requests: list[datetime] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(
            f"{name} rate limiter initialized",
            rpm=requests_per_minute,
            rph=requests_per_hour
        )
    
    async def acquire(self, timeout: float = 60.0) -> bool:
        """
        Acquire permission to make an API call.
        
        Args:
            timeout: Maximum seconds to wait for rate limit clearance
            
        Returns:
            True if acquired, False if timeout
        """
        start_time = datetime.utcnow()
        
        while True:
            async with self._lock:
                now = datetime.utcnow()
                
                # Clean old entries
                self._clean_windows(now)
                
                # Check if we can proceed
                minute_count = len(self._minute_requests)
                hour_count = len(self._hour_requests)
                
                if minute_count < self.rpm_limit and hour_count < self.rph_limit:
                    # Grant access
                    self._minute_requests.append(now)
                    self._hour_requests.append(now)
                    
                    logger.debug(
                        f"{self.name} rate limit OK",
                        minute_count=minute_count + 1,
                        hour_count=hour_count + 1,
                        rpm_limit=self.rpm_limit,
                        rph_limit=self.rph_limit
                    )
                    return True
                
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    logger.warning(
                        f"{self.name} rate limit timeout",
                        timeout_seconds=timeout,
                        minute_count=minute_count,
                        hour_count=hour_count
                    )
                    return False
            
            # Wait before retry
            await asyncio.sleep(1.0)
    
    def _clean_windows(self, now: datetime) -> None:
        """Remove expired entries from sliding windows."""
        # Clean minute window (older than 60s)
        minute_cutoff = now - timedelta(seconds=60)
        self._minute_requests = [
            ts for ts in self._minute_requests
            if ts > minute_cutoff
        ]
        
        # Clean hour window (older than 3600s)
        hour_cutoff = now - timedelta(seconds=3600)
        self._hour_requests = [
            ts for ts in self._hour_requests
            if ts > hour_cutoff
        ]
    
    async def get_status(self) -> dict:
        """Get current rate limit status."""
        async with self._lock:
            now = datetime.utcnow()
            self._clean_windows(now)
            
            minute_count = len(self._minute_requests)
            hour_count = len(self._hour_requests)
            
            return {
                "name": self.name,
                "requests_last_minute": minute_count,
                "requests_last_hour": hour_count,
                "rpm_limit": self.rpm_limit,
                "rph_limit": self.rph_limit,
                "rpm_available": self.rpm_limit - minute_count,
                "rph_available": self.rph_limit - hour_count
            }
    
    async def reset(self) -> None:
        """Reset all counters (for testing)."""
        async with self._lock:
            self._minute_requests.clear()
            self._hour_requests.clear()
            logger.info(f"{self.name} rate limiter reset")


# Global rate limiters
spacetrack_limiter = RateLimiter(
    name="SpaceTrack",
    requests_per_minute=30,   # SpaceTrack enforces 30 RPM
    requests_per_hour=300     # SpaceTrack enforces 300 RPH
)

n2yo_limiter = RateLimiter(
    name="N2YO",
    requests_per_minute=100,  # Conservative (no official RPM limit)
    requests_per_hour=300     # Free tier: 300/hour
)
