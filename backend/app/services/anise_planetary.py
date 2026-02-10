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
    from anise.astro import Frame
    ANISE_AVAILABLE = True
except ImportError:
    ANISE_AVAILABLE = False
    Frame = None

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
    
    def calculate_aer(
        self,
        satellite_position: Tuple[float, float, float],
        satellite_velocity: Tuple[float, float, float],
        ground_station_lat: float,
        ground_station_lon: float,
        ground_station_alt: float,
        epoch: datetime
    ) -> Tuple[float, float, float]:
        """
        Calculate Azimuth, Elevation, Range from ground station to satellite.
        
        Args:
            satellite_position: (x, y, z) in km (ECI J2000 frame)
            satellite_velocity: (vx, vy, vz) in km/s (ECI J2000 frame)
            ground_station_lat: Latitude in degrees (-90 to +90)
            ground_station_lon: Longitude in degrees (-180 to +180)
            ground_station_alt: Altitude in km above sea level
            epoch: Time of calculation (UTC)
        
        Returns:
            (azimuth_deg, elevation_deg, range_km)
            - azimuth: 0-360° (North = 0°, East = 90°)
            - elevation: -90 to +90° (horizon = 0°)
            - range: Distance in km
        """
        if not self.is_ready():
            raise RuntimeError("ANISE not ready")
        
        start = time.perf_counter()
        
        # Convert datetime to ANISE epoch
        anise_epoch = self._datetime_to_epoch(epoch)
        
        # Create ground station orbit (fixed to Earth surface)
        from anise.astro import Orbit
        from anise.constants import Frames
        
        iau_earth = self._almanac.frame_info(Frames.IAU_EARTH_FRAME)
        station_orbit = Orbit.from_latlongalt(
            ground_station_lat,
            ground_station_lon,
            ground_station_alt,
            anise_epoch,
            iau_earth
        )
        
        # Create satellite orbit from Cartesian state
        eme2k = self._almanac.frame_info(Frames.EARTH_J2000)
        satellite_orbit = Orbit.from_cartesian(
            satellite_position[0],
            satellite_position[1],
            satellite_position[2],
            satellite_velocity[0],
            satellite_velocity[1],
            satellite_velocity[2],
            anise_epoch,
            eme2k
        )
        
        # Calculate AER using ANISE
        aer = self._almanac.azimuth_elevation_range_sez(
            satellite_orbit,
            station_orbit
        )
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        logger.debug(
            "aer_calculation",
            azimuth=round(aer.azimuth_deg, 2),
            elevation=round(aer.elevation_deg, 2),
            range_km=round(aer.range_km, 2),
            duration_ms=round(duration_ms, 3)
        )
        
        return (
            float(aer.azimuth_deg),
            float(aer.elevation_deg),
            float(aer.range_km)
        )
    
    def check_eclipse(
        self,
        satellite_position: Tuple[float, float, float],
        satellite_velocity: Tuple[float, float, float],
        epoch: datetime
    ) -> dict:
        """
        Check if satellite is in Earth's shadow (eclipse).
        
        Args:
            satellite_position: (x, y, z) in km (ECI J2000 frame)
            satellite_velocity: (vx, vy, vz) in km/s
            epoch: Time of check (UTC)
        
        Returns:
            {
                "in_eclipse": bool,
                "eclipse_type": "visible" | "partial" | "full",
                "eclipse_percentage": float (0-100),
                "computation_time_ms": float
            }
        """
        if not self.is_ready():
            raise RuntimeError("ANISE not ready")
        
        start = time.perf_counter()
        
        # Convert datetime to ANISE epoch
        anise_epoch = self._datetime_to_epoch(epoch)
        
        # Create satellite orbit
        from anise.astro import Orbit
        from anise.constants import Frames
        
        eme2k = self._almanac.frame_info(Frames.EARTH_J2000)
        satellite_orbit = Orbit.from_cartesian(
            satellite_position[0],
            satellite_position[1],
            satellite_position[2],
            satellite_velocity[0],
            satellite_velocity[1],
            satellite_velocity[2],
            anise_epoch,
            eme2k
        )
        
        # Check solar eclipsing
        occultation = self._almanac.solar_eclipsing(
            Frames.EARTH_J2000,  # Earth blocks Sun
            satellite_orbit,
            None  # No aberration correction
        )
        
        # Determine eclipse state
        if occultation.is_visible:
            eclipse_type = "visible"
            in_eclipse = False
        elif occultation.is_partial:
            eclipse_type = "partial"
            in_eclipse = True
        elif occultation.is_obstructed:
            eclipse_type = "full"
            in_eclipse = True
        else:
            eclipse_type = "unknown"
            in_eclipse = False
        
        # Get eclipse percentage
        # occultation.percentage = fraction of Sun visible (1.0 = fully visible, 0.0 = fully blocked)
        # Eclipse percentage = 100 - (Sun visible percentage)
        sun_visible_pct = occultation.percentage * 100.0
        eclipse_percentage = 100.0 - sun_visible_pct
        
        # Clamp to valid range [0, 100]
        eclipse_percentage = max(0.0, min(100.0, eclipse_percentage))
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        logger.debug(
            "eclipse_check",
            eclipse_type=eclipse_type,
            percentage=round(eclipse_percentage, 1),
            duration_ms=round(duration_ms, 3)
        )
        
        return {
            "in_eclipse": in_eclipse,
            "eclipse_type": eclipse_type,
            "eclipse_percentage": round(eclipse_percentage, 2),
            "computation_time_ms": round(duration_ms, 3)
        }
    
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
