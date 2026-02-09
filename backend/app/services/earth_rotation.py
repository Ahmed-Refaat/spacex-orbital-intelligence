"""
Earth rotation effects on launch.

Story 2.4: Earth Rotation
Calculates velocity bonus and orbital inclination from launch azimuth.
"""
import math
from dataclasses import dataclass
from typing import List


# Physical constants
R_EARTH_KM = 6371.0  # Earth mean radius (km)
OMEGA_EARTH = 7.2921159e-5  # Earth angular velocity (rad/s)


@dataclass
class LaunchSite:
    """
    Launch site with geographic coordinates.
    
    Attributes:
        name: Site name (e.g., "Cape Canaveral")
        latitude_deg: Latitude (degrees, positive = North)
        longitude_deg: Longitude (degrees, positive = East)
        altitude_km: Altitude above sea level (km)
        azimuth_deg: Default launch azimuth (degrees, 0 = North, 90 = East)
    """
    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float = 0.0
    azimuth_deg: float = 90.0  # Default: due east
    
    @staticmethod
    def cape_canaveral() -> 'LaunchSite':
        """Cape Canaveral Space Force Station (Florida, USA)."""
        return LaunchSite(
            name="Cape Canaveral",
            latitude_deg=28.5,
            longitude_deg=-80.5,
            altitude_km=0.0,
            azimuth_deg=90.0  # Typically eastward
        )
    
    @staticmethod
    def vandenberg() -> 'LaunchSite':
        """Vandenberg Space Force Base (California, USA)."""
        return LaunchSite(
            name="Vandenberg",
            latitude_deg=34.7,
            longitude_deg=-120.6,
            altitude_km=0.0,
            azimuth_deg=180.0  # Typically southward (polar orbits)
        )
    
    @staticmethod
    def kourou() -> 'LaunchSite':
        """Guiana Space Centre (French Guiana)."""
        return LaunchSite(
            name="Kourou",
            latitude_deg=5.2,
            longitude_deg=-52.8,
            altitude_km=0.0,
            azimuth_deg=90.0  # Near equator, eastward launches
        )
    
    @staticmethod
    def baikonur() -> 'LaunchSite':
        """Baikonur Cosmodrome (Kazakhstan)."""
        return LaunchSite(
            name="Baikonur",
            latitude_deg=45.6,
            longitude_deg=63.3,
            altitude_km=0.0,
            azimuth_deg=90.0
        )


class EarthRotation:
    """
    Calculate Earth rotation effects on launch.
    
    Earth rotates at ω ≈ 7.29×10⁻⁵ rad/s, giving surface velocities:
    - At equator: ~465 m/s
    - At Cape Canaveral (28.5°N): ~410 m/s
    - At poles: ~0 m/s
    
    This "free" velocity bonus is why most launches are eastward.
    
    Methods:
        surface_velocity(): Rotational velocity at a given latitude
        velocity_bonus(): Component of rotational velocity in launch direction
        inclination_from_azimuth(): Orbital inclination from launch azimuth
        initial_velocity_vector(): Initial velocity including Earth rotation
    
    Example:
        >>> earth = EarthRotation()
        >>> site = LaunchSite.cape_canaveral()
        >>> v_bonus = earth.velocity_bonus(site, azimuth=90.0)  # Eastward
        >>> print(f"Velocity bonus: {v_bonus:.0f} m/s")
        Velocity bonus: 410 m/s
    """
    
    def __init__(self):
        self.omega = OMEGA_EARTH  # rad/s
        self.radius_km = R_EARTH_KM  # km
    
    def surface_velocity(self, latitude_deg: float) -> float:
        """
        Calculate Earth's surface velocity at given latitude.
        
        Formula: v = ω × R × cos(latitude)
        
        Where:
        - ω = Earth's angular velocity (7.29×10⁻⁵ rad/s)
        - R = Earth's radius (6371 km)
        - latitude = geographic latitude
        
        Args:
            latitude_deg: Latitude (degrees, positive = North)
        
        Returns:
            Surface velocity (m/s, eastward)
        
        Example:
            >>> earth = EarthRotation()
            >>> earth.surface_velocity(0.0)    # Equator
            465
            >>> earth.surface_velocity(28.5)   # Cape
            410
        """
        lat_rad = math.radians(latitude_deg)
        
        # v = ω × R × cos(lat)
        r_meters = self.radius_km * 1000
        v = self.omega * r_meters * math.cos(lat_rad)
        
        return v
    
    def velocity_bonus(self, site: LaunchSite, azimuth_deg: float) -> float:
        """
        Calculate velocity bonus from Earth's rotation.
        
        The velocity bonus depends on launch azimuth:
        - Eastward (90°): Full bonus (+ rotational velocity)
        - Westward (270°): Negative bonus (- rotational velocity)
        - Northward/Southward (0°/180°): No bonus (perpendicular)
        
        Args:
            site: Launch site
            azimuth_deg: Launch azimuth (degrees, 0 = North, 90 = East)
        
        Returns:
            Velocity bonus (m/s, positive = helping)
        
        Example:
            >>> earth = EarthRotation()
            >>> site = LaunchSite.cape_canaveral()
            >>> earth.velocity_bonus(site, 90.0)   # Eastward
            410
            >>> earth.velocity_bonus(site, 270.0)  # Westward
            -410
        """
        v_surface = self.surface_velocity(site.latitude_deg)
        az_rad = math.radians(azimuth_deg)
        
        # Eastward component of velocity
        # sin(azimuth) = 1 for East (90°), -1 for West (270°), 0 for North/South
        v_bonus = v_surface * math.sin(az_rad)
        
        return v_bonus
    
    def inclination_from_azimuth(
        self,
        site: LaunchSite,
        azimuth_deg: float
    ) -> float:
        """
        Calculate orbital inclination from launch azimuth.
        
        Simplified formula (assumes spherical Earth, ignores rotation during ascent):
            sin(i) = cos(lat) × cos(az)
        
        Where:
        - i = inclination
        - lat = launch site latitude
        - az = launch azimuth (measured from North)
        
        More accurate formula (includes Earth's oblateness and trajectory):
            cos(i) = cos(lat) × sin(az)
        
        We use the more accurate formula.
        
        Args:
            site: Launch site
            azimuth_deg: Launch azimuth (degrees)
        
        Returns:
            Orbital inclination (degrees)
        
        Example:
            >>> earth = EarthRotation()
            >>> site = LaunchSite.cape_canaveral()
            >>> earth.inclination_from_azimuth(site, 90.0)  # Eastward
            28.5  # Equal to latitude
            >>> earth.inclination_from_azimuth(site, 0.0)   # Northward
            90.0  # Polar orbit
        """
        lat_rad = math.radians(site.latitude_deg)
        az_rad = math.radians(azimuth_deg)
        
        # cos(i) = cos(lat) × sin(az)
        cos_i = math.cos(lat_rad) * math.sin(az_rad)
        
        # Clamp to valid range [-1, 1]
        cos_i = max(-1.0, min(1.0, cos_i))
        
        inclination_rad = math.acos(cos_i)
        inclination_deg = math.degrees(inclination_rad)
        
        return inclination_deg
    
    def initial_velocity_vector(
        self,
        site: LaunchSite,
        azimuth_deg: float
    ) -> List[float]:
        """
        Calculate initial velocity vector including Earth's rotation.
        
        Returns velocity in local frame (East, North, Up).
        
        Args:
            site: Launch site
            azimuth_deg: Launch azimuth (degrees)
        
        Returns:
            [v_east, v_north, v_up] in m/s
        
        Example:
            >>> earth = EarthRotation()
            >>> site = LaunchSite.cape_canaveral()
            >>> earth.initial_velocity_vector(site, 90.0)  # Eastward
            [410, 0, 0]
        """
        v_surface = self.surface_velocity(site.latitude_deg)
        az_rad = math.radians(azimuth_deg)
        
        # Decompose into East/North components
        v_east = v_surface * math.sin(az_rad)
        v_north = v_surface * math.cos(az_rad)
        v_up = 0.0  # No vertical component from rotation
        
        return [v_east, v_north, v_up]
    
    def required_azimuth(
        self,
        site: LaunchSite,
        target_inclination_deg: float
    ) -> float:
        """
        Calculate required launch azimuth for target inclination.
        
        Inverse of inclination_from_azimuth().
        
        Args:
            site: Launch site
            target_inclination_deg: Desired orbital inclination (degrees)
        
        Returns:
            Launch azimuth (degrees)
        
        Raises:
            ValueError: If inclination is unachievable from this latitude
        
        Example:
            >>> earth = EarthRotation()
            >>> site = LaunchSite.cape_canaveral()
            >>> earth.required_azimuth(site, 51.6)  # ISS
            45.0  # Northeast launch
        """
        lat_rad = math.radians(site.latitude_deg)
        i_rad = math.radians(target_inclination_deg)
        
        # From cos(i) = cos(lat) × sin(az)
        # We get: sin(az) = cos(i) / cos(lat)
        
        cos_lat = math.cos(lat_rad)
        
        if cos_lat < 1e-6:
            # At poles, any azimuth gives polar orbit
            return 0.0
        
        sin_az = math.cos(i_rad) / cos_lat
        
        # Check if achievable
        if abs(sin_az) > 1.0:
            raise ValueError(
                f"Inclination {target_inclination_deg}° is not achievable "
                f"from latitude {site.latitude_deg}°"
            )
        
        azimuth_rad = math.asin(sin_az)
        azimuth_deg = math.degrees(azimuth_rad)
        
        return azimuth_deg
