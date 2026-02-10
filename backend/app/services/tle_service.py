"""
TLE data fetching and management service.

COMPLIANCE: Uses centralized session manager to comply with Space-Track API policy.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog
from circuitbreaker import circuit
import httpx

from app.core.config import get_settings
from app.services.orbital_engine import orbital_engine
from app.services.spacetrack_session import session_manager

logger = structlog.get_logger()


class TLEService:
    """
    Service for fetching and managing TLE data from Space-Track.org.
    
    Uses centralized session manager for compliance with API policy:
    - Session reuse (no login/logout per request)
    - GP data caching (minimum 1 hour)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._last_update: Optional[datetime] = None
        self._tle_cache: dict[str, tuple[str, str, str]] = {}  # norad_id -> (name, line1, line2)
        self._update_lock = asyncio.Lock()
        # Use centralized session manager
        self.session = session_manager
    
    @circuit(failure_threshold=3, recovery_timeout=120, expected_exception=httpx.HTTPError)
    async def fetch_tle_data(self, source: str = "starlink") -> dict[str, tuple[str, str, str]]:
        """
        Fetch TLE data from Space-Track.org using JSON format for names.
        
        Circuit breaker protection:
        - Opens after 3 consecutive failures
        - Stays open for 120 seconds (longer recovery for external API)
        
        COMPLIANCE: GP data is cached for minimum 1 hour per Space-Track policy.
        """
        
        # Build query based on source - use JSON format to get names
        if source == "starlink":
            query = "/basicspacedata/query/class/gp/OBJECT_NAME/~~STARLINK/orderby/NORAD_CAT_ID/format/json"
        elif source == "stations":
            query = "/basicspacedata/query/class/gp/OBJECT_TYPE/PAYLOAD/PERIOD/90--95/ECCENTRICITY/<0.01/orderby/NORAD_CAT_ID/limit/100/format/json"
        else:
            query = "/basicspacedata/query/class/gp/OBJECT_TYPE/PAYLOAD/DECAY/null-val/orderby/NORAD_CAT_ID/limit/1000/format/json"
        
        # Fetch TLE data using session manager (auto-caches for 1h minimum)
        logger.info("Fetching TLE data from Space-Track", source=source)
        
        # CRITICAL: GP ephemerides MUST be cached for minimum 1 hour
        response = await self.session.get(query, cache_ttl=3600)
        
        if not response or response.status_code != 200:
            raise Exception(f"Failed to fetch TLE data: {response.status_code if response else 'No response'}")
        
        data = response.json()
        return self._parse_json_tle(data)
    
    def _parse_json_tle(self, data: list) -> dict[str, tuple[str, str, str]]:
        """Parse JSON format TLE data from Space-Track."""
        result = {}
        
        for item in data:
            try:
                norad_id = str(item.get("NORAD_CAT_ID", "")).strip()
                name = item.get("OBJECT_NAME", f"SAT-{norad_id}")
                line1 = item.get("TLE_LINE1", "")
                line2 = item.get("TLE_LINE2", "")
                
                if norad_id and line1 and line2:
                    result[norad_id] = (name, line1, line2)
            except Exception:
                pass
        
        return result
    
    def _parse_tle(self, tle_text: str) -> dict[str, tuple[str, str, str]]:
        """Parse TLE format text into structured data (3-line format)."""
        lines = [l.strip() for l in tle_text.strip().split('\n') if l.strip()]
        result = {}
        
        i = 0
        while i < len(lines) - 2:
            # TLE format: Name, Line 1, Line 2
            name = lines[i]
            line1 = lines[i + 1]
            line2 = lines[i + 2]
            
            # Validate TLE lines
            if line1.startswith('1 ') and line2.startswith('2 '):
                # Extract NORAD catalog ID from line 1
                try:
                    norad_id = line1[2:7].strip()
                    result[norad_id] = (name, line1, line2)
                except:
                    pass
                i += 3
            else:
                i += 1
        
        return result
    
    async def update_orbital_engine(self, source: str = "starlink") -> int:
        """Update the orbital engine with fresh TLE data."""
        async with self._update_lock:
            logger.info("Fetching TLE data", source=source)
            
            try:
                tle_data = await self.fetch_tle_data(source)
                
                loaded = 0
                for norad_id, (name, line1, line2) in tle_data.items():
                    # Use NORAD ID as satellite ID
                    if orbital_engine.load_tle(norad_id, line1, line2):
                        self._tle_cache[norad_id] = (name, line1, line2)
                        loaded += 1
                
                self._last_update = datetime.utcnow()
                logger.info("TLE update complete", loaded=loaded, total=len(tle_data))
                
                return loaded
                
            except Exception as e:
                logger.error("TLE update failed", error=str(e))
                raise
    
    async def ensure_data_loaded(self) -> bool:
        """Ensure TLE data is loaded, fetching if necessary."""
        if self._last_update is None:
            await self.update_orbital_engine()
            return True
        
        # Check if refresh needed
        age = datetime.utcnow() - self._last_update
        if age > timedelta(seconds=self.settings.tle_refresh_interval):
            await self.update_orbital_engine()
            return True
        
        return False
    
    def get_satellite_name(self, norad_id: str) -> Optional[str]:
        """Get satellite name from cache."""
        if norad_id in self._tle_cache:
            return self._tle_cache[norad_id][0]
        return None
    
    def get_tle(self, norad_id: str) -> Optional[tuple[str, str]]:
        """Get TLE lines for a satellite."""
        if norad_id in self._tle_cache:
            _, line1, line2 = self._tle_cache[norad_id]
            return (line1, line2)
        return None
    
    @property
    def satellite_count(self) -> int:
        """Number of satellites with TLE data."""
        return len(self._tle_cache)
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Time of last TLE update."""
        return self._last_update
    
    def get_status(self) -> dict:
        """Get TLE service status."""
        return {
            "satellite_count": self.satellite_count,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "orbital_engine_loaded": orbital_engine.satellite_count
        }


# Global service instance
tle_service = TLEService()
