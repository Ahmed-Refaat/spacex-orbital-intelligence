"""
Gravity model with altitude variation.

Story 2.1: Gravity Variation
Implements inverse-square law for accurate gravity at altitude.
"""
from typing import List


# Physical constants
G0_DEFAULT = 9.80665  # Standard gravity at sea level (m/s²)
R_EARTH_DEFAULT = 6371.0  # Mean Earth radius (km)


class GravityModel:
    """
    Calculate gravitational acceleration at different altitudes.
    
    Uses inverse-square law:
        g(h) = g₀ × (R / (R + h))²
    
    Where:
    - g₀ = surface gravity (9.80665 m/s²)
    - R = Earth radius (6371 km)
    - h = altitude above sea level (km)
    
    This is more accurate than constant gravity, especially for high
    trajectories (>50 km).
    
    Attributes:
        g0: Surface gravity (m/s²)
        earth_radius_km: Earth radius (km)
    
    Example:
        >>> grav = GravityModel()
        >>> g = grav.gravity_at_altitude(400.0)  # ISS altitude
        >>> print(f"Gravity at ISS: {g:.2f} m/s²")
        Gravity at ISS: 8.68 m/s²
    """
    
    def __init__(
        self,
        g0: float = G0_DEFAULT,
        earth_radius_km: float = R_EARTH_DEFAULT
    ):
        """
        Initialize gravity model.
        
        Args:
            g0: Surface gravity (m/s²), default 9.80665
            earth_radius_km: Earth radius (km), default 6371
        """
        self.g0 = g0
        self.earth_radius_km = earth_radius_km
    
    def gravity_at_altitude(self, altitude_km: float) -> float:
        """
        Calculate gravitational acceleration at given altitude.
        
        Uses inverse-square law.
        
        Args:
            altitude_km: Altitude above sea level (km)
        
        Returns:
            Gravitational acceleration (m/s²)
        
        Example:
            >>> grav = GravityModel()
            >>> grav.gravity_at_altitude(0.0)    # Sea level
            9.80665
            >>> grav.gravity_at_altitude(400.0)  # ISS
            8.68
        """
        # Inverse-square law: g = g₀ × (R / (R + h))²
        r = self.earth_radius_km
        g = self.g0 * (r / (r + altitude_km)) ** 2
        
        return g
    
    def gravity_acceleration(self, altitude_km: float) -> List[float]:
        """
        Calculate gravity acceleration as a 3D vector.
        
        In local frame (up/down, downrange, crossrange):
        - Gravity points downward (-y direction)
        - No horizontal components
        
        Args:
            altitude_km: Altitude above sea level (km)
        
        Returns:
            3D vector [x, y, z] in m/s²
            (y = vertical, negative = downward)
        
        Example:
            >>> grav = GravityModel()
            >>> grav.gravity_acceleration(100.0)
            [0.0, -9.51, 0.0]
        """
        g = self.gravity_at_altitude(altitude_km)
        
        # Gravity points downward (negative y)
        return [0.0, -g, 0.0]
    
    def gravity_loss(
        self,
        altitude_start_km: float,
        altitude_end_km: float,
        time_delta_s: float
    ) -> float:
        """
        Estimate gravity loss over a trajectory segment.
        
        Gravity loss = ∫ g dt ≈ g_avg × Δt
        
        Args:
            altitude_start_km: Starting altitude (km)
            altitude_end_km: Ending altitude (km)
            time_delta_s: Time duration (seconds)
        
        Returns:
            Gravity loss (m/s)
        
        Example:
            >>> grav = GravityModel()
            >>> loss = grav.gravity_loss(0.0, 100.0, 60.0)  # 60s climb
            >>> print(f"Gravity loss: {loss:.0f} m/s")
            Gravity loss: 573 m/s
        """
        # Average gravity over segment
        g_start = self.gravity_at_altitude(altitude_start_km)
        g_end = self.gravity_at_altitude(altitude_end_km)
        g_avg = (g_start + g_end) / 2.0
        
        # Gravity loss = g × t
        loss = g_avg * time_delta_s
        
        return loss
