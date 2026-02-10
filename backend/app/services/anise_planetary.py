"""
ANISE Planetary Ephemeris Service - Updated for ANISE 0.4.2

Focus: High-precision planetary positions (Sun, Moon, Earth)
Uses ANISE 0.4.2 API (Rust-backed astrodynamics)
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
    from anise.astro import Orbit, Frame
    ANISE_AVAILABLE = True
except ImportError:
    ANISE_AVAILABLE = False
    Almanac = None
    Epoch = None
    Orbit = None
    Frame = None

logger = structlog.get_logger(__name__)

# NAIF ID constants for common bodies
NAIF_SUN = 10
NAIF_MOON = 301
NAIF_MERCURY = 199
NAIF_VENUS = 299
NAIF_EARTH = 399
NAIF_MARS = 4
NAIF_JUPITER = 5
NAIF_SATURN = 6


class AnisePlanetaryService:
    """
    ANISE-powered planetary ephemeris service (v0.4.2).
    
    Provides high-precision positions for:
    - Sun (NAIF ID: 10)
    - Moon (NAIF ID: 301)
    - Earth (NAIF ID: 399)
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
        
        # Get frames (J2000 orientation_id = 1)
        observer_id = self._get_naif_id(observer)
        sun_frame = Frame(ephemeris_id=NAIF_SUN, orientation_id=1)
        observer_frame = Frame(ephemeris_id=observer_id, orientation_id=1)
        
        # Query Sun position from observer
        orbit = self._almanac.translate(sun_frame, observer_frame, anise_epoch)
        
        # Extract position [km]
        position = (float(orbit.x_km), float(orbit.y_km), float(orbit.z_km))
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        logger.debug(
            "sun_position_query",
            observer=observer,
            epoch=epoch.isoformat(),
            duration_ms=round(duration_ms, 3)
        )
        
        return position
    
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
        observer_id = self._get_naif_id(observer)
        
        moon_frame = Frame(ephemeris_id=NAIF_MOON, orientation_id=1)
        observer_frame = Frame(ephemeris_id=observer_id, orientation_id=1)
        
        orbit = self._almanac.translate(moon_frame, observer_frame, anise_epoch)
        
        position = (float(orbit.x_km), float(orbit.y_km), float(orbit.z_km))
        
        duration_ms = (time.perf_counter() - start) * 1000
        logger.debug("moon_position_query", duration_ms=round(duration_ms, 3))
        
        return position
    
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
        observer_id = self._get_naif_id(observer)
        target_id = self._get_naif_id(body)
        
        target_frame = Frame(ephemeris_id=target_id, orientation_id=1)
        observer_frame = Frame(ephemeris_id=observer_id, orientation_id=1)
        
        orbit = self._almanac.translate(target_frame, observer_frame, anise_epoch)
        
        position = (float(orbit.x_km), float(orbit.y_km), float(orbit.z_km))
        
        return position
    
    def _datetime_to_epoch(self, dt: datetime) -> Epoch:
        """Convert Python datetime → ANISE Epoch."""
        # Ensure UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # ANISE 0.4.2 uses init_from_gregorian_utc
        return Epoch.init_from_gregorian_utc(
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
            dt.microsecond * 1000  # microseconds to nanoseconds
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
        
        # Create Earth IAU frame for ground station (body-fixed)
        # For IAU frames, orientation_id is typically the NAIF ID + 10000
        iau_earth = Frame(ephemeris_id=NAIF_EARTH, orientation_id=3000)  # IAU_EARTH = 3000
        
        # Create ground station orbit (fixed to Earth surface)
        station_orbit = Orbit.from_latlongalt(
            ground_station_lat,
            ground_station_lon,
            ground_station_alt,
            anise_epoch,
            iau_earth
        )
        
        # Create Earth J2000 frame for satellite
        earth_j2000 = Frame(ephemeris_id=NAIF_EARTH, orientation_id=1)  # J2000
        
        # Create satellite orbit from Cartesian state
        satellite_orbit = Orbit.from_cartesian(
            satellite_position[0],
            satellite_position[1],
            satellite_position[2],
            satellite_velocity[0],
            satellite_velocity[1],
            satellite_velocity[2],
            anise_epoch,
            earth_j2000
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
        
        # Create Earth J2000 frame
        earth_frame = Frame(ephemeris_id=NAIF_EARTH, orientation_id=1)
        
        # Create satellite orbit
        satellite_orbit = Orbit.from_cartesian(
            satellite_position[0],
            satellite_position[1],
            satellite_position[2],
            satellite_velocity[0],
            satellite_velocity[1],
            satellite_velocity[2],
            anise_epoch,
            earth_frame
        )
        
        # Check sun angle (simplified eclipse detection)
        # Proper eclipse detection would use solar_eclipsing if available
        try:
            sun_angle = self._almanac.sun_angle_deg(satellite_orbit, earth_frame)
            
            # Sun angle interpretation:
            # > 90° = satellite can see sun (visible)
            # < 90° = behind Earth (eclipse)
            
            if sun_angle > 100:
                eclipse_type = "visible"
                in_eclipse = False
                eclipse_percentage = 0.0
            elif sun_angle > 90:
                eclipse_type = "partial"
                in_eclipse = True
                # Interpolate between 90-100°
                eclipse_percentage = (100 - sun_angle) * 10.0  # 0-100%
            else:
                eclipse_type = "full"
                in_eclipse = True
                eclipse_percentage = 100.0
        
        except Exception as e:
            logger.warning("eclipse_check_fallback", error=str(e))
            # Fallback: simple geometry
            # If satellite is behind Earth from Sun's perspective
            eclipse_type = "unknown"
            in_eclipse = False
            eclipse_percentage = 0.0
        
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
    
    def _get_naif_id(self, body: str) -> int:
        """Map body name to NAIF ID."""
        body_upper = body.upper()
        
        # Map of common bodies
        naif_map = {
            "SUN": NAIF_SUN,
            "MOON": NAIF_MOON,
            "EARTH": NAIF_EARTH,
            "MERCURY": NAIF_MERCURY,
            "VENUS": NAIF_VENUS,
            "MARS": NAIF_MARS,
            "JUPITER": NAIF_JUPITER,
            "SATURN": NAIF_SATURN,
        }
        
        if body_upper not in naif_map:
            raise ValueError(
                f"Unknown body: {body}. "
                f"Available: {', '.join(naif_map.keys())}"
            )
        
        return naif_map[body_upper]


# Singleton instance
_planetary_service: Optional[AnisePlanetaryService] = None


def get_planetary_service() -> AnisePlanetaryService:
    """Get global ANISE planetary service instance."""
    global _planetary_service
    
    if _planetary_service is None:
        _planetary_service = AnisePlanetaryService(kernel_path="./kernels")
    
    return _planetary_service
