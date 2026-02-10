"""
TLE data fetching and management service.

COMPLIANCE: Uses centralized session manager to comply with Space-Track API policy.
FALLBACK: Multi-source fallback chain:
  1. Space-Track (primary, when unbanned)
  2. Celestrak (secondary, bulk public data)
  3. N2YO (tertiary, individual fetches only - 300 req/hour free)
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
from app.services.celestrak_fallback import celestrak
from app.services.n2yo_client import n2yo_client
from app.services.tle_loader import local_tle_loader

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
    
    async def fetch_tle_data(self, source: str = "starlink") -> dict[str, tuple[str, str, str]]:
        """
        Fetch TLE data from Space-Track.org or Celestrak fallback.
        
        COMPLIANCE: GP data is cached for minimum 1 hour per Space-Track policy.
        FALLBACK: Space-Track → Celestrak → N2YO (individual)
        """
        
        # Try Space-Track first (if available/unbanned)
        try:
            # Build query based on source - use JSON format to get names
            if source == "starlink":
                query = "/basicspacedata/query/class/gp/OBJECT_NAME/~~STARLINK/orderby/NORAD_CAT_ID/format/json"
            elif source == "stations":
                query = "/basicspacedata/query/class/gp/OBJECT_TYPE/PAYLOAD/PERIOD/90--95/ECCENTRICITY/<0.01/orderby/NORAD_CAT_ID/limit/100/format/json"
            else:
                query = "/basicspacedata/query/class/gp/OBJECT_TYPE/PAYLOAD/DECAY/null-val/orderby/NORAD_CAT_ID/limit/1000/format/json"
            
            logger.info("Attempting Space-Track fetch (may be banned)", source=source)
            
            # CRITICAL: GP ephemerides MUST be cached for minimum 1 hour
            response = await self.session.get(query, cache_ttl=3600)
            
            if response and response.status_code == 200:
                data = response.json()
                result = self._parse_json_tle(data)
                logger.info("Space-Track fetch successful", count=len(result))
                return result
            else:
                logger.warning(
                    "Space-Track fetch failed (may be banned)",
                    status_code=response.status_code if response else None
                )
        
        except Exception as e:
            logger.warning("Space-Track error (may be banned)", error=str(e))
        
        # Fallback to local TLE files FIRST (faster than Celestrak)
        logger.info("Using local TLE files as primary fallback", source=source)
        
        try:
            if source == "starlink":
                result = local_tle_loader.load_starlink()
            elif source == "stations":
                result = local_tle_loader.load_stations()
            else:
                result = local_tle_loader.load_starlink()  # Default to Starlink
            
            if result:
                logger.info("Local TLE file loaded successfully", count=len(result), source="local_file")
                return result
            else:
                logger.warning("Local TLE file empty or not found", source=source)
        except Exception as e:
            logger.error("Local TLE file load failed", error=str(e), source=source)
        
        # Fallback to Celestrak (bulk public data) as last resort
        logger.info("Using Celestrak as TLE source (local file unavailable)", source=source)
        
        try:
            if source == "starlink":
                result = await celestrak.fetch_starlink_tle()
            elif source == "stations":
                result = await celestrak.fetch_stations()
            else:
                result = await celestrak.fetch_active_satellites(limit=1000)
            
            if result:
                logger.info("Celestrak fetch successful", count=len(result), source="celestrak")
                return result
            
        except Exception as e:
            logger.error("Celestrak fetch failed", error=str(e), source=source)
        
        # All sources failed - will use mock satellites
        logger.warning("All TLE sources failed - using mock satellites", source=source)
        return {}
    
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
    
    async def fetch_individual_tle(self, norad_id: str) -> Optional[tuple[str, str, str]]:
        """
        Fetch TLE for a single satellite with multi-source fallback.
        
        Fallback order:
        1. N2YO (if configured)
        2. Space-Track (if available)
        3. Return None
        
        Args:
            norad_id: NORAD catalog number
            
        Returns:
            Tuple of (name, line1, line2) or None
        """
        # Try N2YO first (has quota, cached, fast)
        if n2yo_client.is_configured:
            try:
                tle = await n2yo_client.get_tle(norad_id)
                if tle:
                    logger.info("TLE fetched from N2YO", norad_id=norad_id)
                    # Cache it
                    self._tle_cache[norad_id] = tle
                    return tle
            except Exception as e:
                logger.warning("N2YO individual fetch failed", norad_id=norad_id, error=str(e))
        
        # Try Space-Track as fallback (if not suspended)
        try:
            query = f"/basicspacedata/query/class/tle_latest/NORAD_CAT_ID/{norad_id}/format/json"
            response = await self.session.get(query, cache_ttl=3600)
            
            if response and response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    item = data[0]
                    tle = (
                        item.get('OBJECT_NAME', f'SAT-{norad_id}'),
                        item.get('TLE_LINE1', ''),
                        item.get('TLE_LINE2', '')
                    )
                    logger.info("TLE fetched from Space-Track", norad_id=norad_id)
                    self._tle_cache[norad_id] = tle
                    return tle
        except Exception as e:
            logger.warning("Space-Track individual fetch failed", norad_id=norad_id, error=str(e))
        
        logger.warning("All TLE sources failed for satellite", norad_id=norad_id)
        return None
    
    def get_satellite_name(self, norad_id: str) -> Optional[str]:
        """Get satellite name from cache."""
        if norad_id in self._tle_cache:
            return self._tle_cache[norad_id][0]
        return None
    
    def get_tle(self, norad_id: str) -> Optional[tuple[str, str]]:
        """
        Get TLE lines for a satellite.
        
        Note: This is synchronous. For live fetching, use fetch_individual_tle().
        """
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
