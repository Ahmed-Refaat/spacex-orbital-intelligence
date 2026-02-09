"""
ANISE Planetary Ephemeris Service - Simplified MVP.

Focus: High-precision planetary positions (Sun, Moon, Earth)
Complexity: LOW (no frame transforms, no TLE integration yet)

This is Phase 1 - planetary queries only.
"""
from datetime import datetime, timezone
from typing import Tuple, Optional
from pathlib import Path
import time
import structlog

# ANISE imports
try:
    from anise import Almanac
    from anise.time import Epoch
    from anise.constants import Frames
    ANISE_AVAILABLE = True
except ImportError:
    ANISE_AVAILABLE = False

logger = structlog.get_logger(__name__)


class AnisePlanetaryService:
    """
    ANISE-powered planetary ephemeris service.
    
    Provides high-precision positions for:
    - Sun
    - Moon  
    - Earth
    - Other planets (Mercury, Venus, Mars, Jupiter, Saturn)
    
    Uses JPL DE440s ephemeris (1900-2050).
    
    Thread-safe: Yes (ANISE Rust core)
    External dependencies: None (self-contained)
    """
    
    def __init__(self, kernel_path: str = "./kernels"):
        """Initialize ANISE planetary service."""
        if not ANISE_AVAILABLE:
            raise RuntimeError("ANISE not installed. Run: pip install anise")
        
        self.kernel_path = Path(kernel_path)
        self._almanac: Optional[Almanac] = None
        self._ready = False
        
        # Load kernels
        self._load_kernels()
    
    def _load_kernels(self):
        """Load ANISE kernels (de440s.bsp + pck08.pca)."""
        start = time.time()
        
        try:
            # Primary ephemeris kernel
            spk_path = self.kernel_path / "de440s.bsp"
            if not spk_path.exists():
                logger.error("de440s.bsp not found", path=str(spk_path))
                return
            
            # Load almanac
            self._almanac = Almanac(str(spk_path))
            
            # Load planetary constants (optional but recommended)
            pca_path = self.kernel_path / "pck08.pca"
            if pca_path.exists():
                self._almanac = self._almanac.load(str(pca_path))
            
            self._ready = True
            
            duration_ms = (time.time() - start) * 1000
            logger.info(
                "anise_kernels_loaded",
                duration_ms=round(duration_ms, 2)
            )
        
        except Exception as e:
            logger.error("anise_kernel_load_failed", error=str(e))
            self._ready = False
    
    def is_ready(self) -> bool:
        """Check if ANISE is ready to serve queries."""
        return self._ready and self._almanac is not None
    
    def get_sun_position(
        self,
        epoch: datetime,
        observer: str = "EARTH"
    ) -> Tuple[float, float, float]:
        """
        Get Sun position relative to observer.
        
        Args:
            epoch: Time of query (UTC)
            observer: Observer body ("EARTH", "MOON", etc.)
        
        Returns:
            (x, y, z) position in km (J2000 frame)
        
        Raises:
            RuntimeError: If ANISE not ready
        """
        if not self.is_ready():
            raise RuntimeError("ANISE not ready. Kernels not loaded.")
        
        start = time.perf_counter()
        
        # Convert datetime → ANISE Epoch
        anise_epoch = self._datetime_to_epoch(epoch)
        
        # Query Sun position from observer
        # Using translate: SUN relative to EARTH
        observer_frame = self._get_frame_id(observer)
        sun_frame = Frames.SUN_J2000
        
        # Get translation vector (returns Orbit object)
        orbit = self._almanac.translate(sun_frame, observer_frame, anise_epoch)
        
        # Extract Cartesian position [x, y, z, vx, vy, vz]
        state = orbit.cartesian_pos_vel()
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        logger.debug(
            "sun_position_query",
            observer=observer,
            epoch=epoch.isoformat(),
            duration_ms=round(duration_ms, 3)
        )
        
        # Return position as tuple (first 3 elements)
        return (float(state[0]), float(state[1]), float(state[2]))
    
    def get_moon_position(
        self,
        epoch: datetime,
        observer: str = "EARTH"
    ) -> Tuple[float, float, float]:
        """
        Get Moon position relative to observer.
        
        Args:
            epoch: Time of query (UTC)
            observer: Observer body ("EARTH", "SUN", etc.)
        
        Returns:
            (x, y, z) position in km (J2000 frame)
        """
        if not self.is_ready():
            raise RuntimeError("ANISE not ready")
        
        start = time.perf_counter()
        
        anise_epoch = self._datetime_to_epoch(epoch)
        observer_frame = self._get_frame_id(observer)
        moon_frame = Frames.MOON_J2000
        
        orbit = self._almanac.translate(moon_frame, observer_frame, anise_epoch)
        state = orbit.cartesian_pos_vel()
        
        duration_ms = (time.perf_counter() - start) * 1000
        logger.debug("moon_position_query", duration_ms=round(duration_ms, 3))
        
        return (float(state[0]), float(state[1]), float(state[2]))
    
    def get_body_position(
        self,
        body: str,
        epoch: datetime,
        observer: str = "EARTH"
    ) -> Tuple[float, float, float]:
        """
        Get any celestial body position.
        
        Args:
            body: Body name ("SUN", "MOON", "MARS", "JUPITER", etc.)
            epoch: Time of query
            observer: Observer frame
        
        Returns:
            (x, y, z) position in km
        
        Raises:
            ValueError: If body unknown
        """
        if not self.is_ready():
            raise RuntimeError("ANISE not ready")
        
        # Route to specific method for common bodies
        body_upper = body.upper()
        
        if body_upper == "SUN":
            return self.get_sun_position(epoch, observer)
        elif body_upper == "MOON":
            return self.get_moon_position(epoch, observer)
        
        # Generic query for other bodies
        anise_epoch = self._datetime_to_epoch(epoch)
        observer_frame = self._get_frame_id(observer)
        target_frame = self._get_frame_id(body)
        
        orbit = self._almanac.translate(target_frame, observer_frame, anise_epoch)
        state = orbit.cartesian_pos_vel()
        
        return (float(state[0]), float(state[1]), float(state[2]))
    
    def _datetime_to_epoch(self, dt: datetime) -> Epoch:
        """Convert Python datetime → ANISE Epoch."""
        # Ensure UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return Epoch.from_gregorian_utc(
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
            dt.microsecond // 1000  # nanos from millis
        )
    
    def _get_frame_id(self, body: str):
        """Map body name to ANISE frame constant."""
        body_upper = body.upper()
        
        # Map of common bodies
        frame_map = {
            "SUN": Frames.SUN_J2000,
            "MOON": Frames.MOON_J2000,
            "EARTH": Frames.EARTH_J2000,
            "MERCURY": Frames.MERCURY_J2000,
            "VENUS": Frames.VENUS_J2000,
            "MARS": Frames.MARS_BARYCENTER_J2000,
            "JUPITER": Frames.JUPITER_BARYCENTER_J2000,
            "SATURN": Frames.SATURN_BARYCENTER_J2000,
        }
        
        if body_upper not in frame_map:
            raise ValueError(
                f"Unknown body: {body}. "
                f"Available: {', '.join(frame_map.keys())}"
            )
        
        return frame_map[body_upper]


# Singleton instance
_planetary_service: Optional[AnisePlanetaryService] = None


def get_planetary_service() -> AnisePlanetaryService:
    """Get global ANISE planetary service instance."""
    global _planetary_service
    
    if _planetary_service is None:
        _planetary_service = AnisePlanetaryService(kernel_path="./kernels")
    
    return _planetary_service
