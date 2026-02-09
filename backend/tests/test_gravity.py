"""
Tests for gravity variation with altitude.

Story 2.1: Gravity Variation
Tests accurate gravity calculation at different altitudes.
"""
import pytest
from app.services.gravity import GravityModel


# Physical constants for validation
G = 6.67430e-11  # Gravitational constant (m³ kg⁻¹ s⁻²)
M_EARTH = 5.972e24  # Earth mass (kg)
R_EARTH = 6371.0  # Earth radius (km)
G0 = 9.80665  # Standard gravity at sea level (m/s²)


class TestGravityAtSeaLevel:
    """Test gravity at sea level."""
    
    def test_gravity_at_surface(self):
        """Gravity at sea level should be ~9.80665 m/s²."""
        grav = GravityModel()
        g = grav.gravity_at_altitude(0.0)
        
        # Should match standard gravity
        assert abs(g - G0) / G0 < 0.001  # <0.1% error
    
    def test_gravity_units(self):
        """Gravity should be returned in m/s²."""
        grav = GravityModel()
        g = grav.gravity_at_altitude(0.0)
        
        # Standard gravity is ~9.8 m/s²
        assert 9.7 < g < 9.9


class TestGravityDecreaseWithAltitude:
    """Test that gravity decreases with altitude."""
    
    def test_gravity_decreases_monotonically(self):
        """Gravity should decrease as altitude increases."""
        grav = GravityModel()
        
        g_0 = grav.gravity_at_altitude(0.0)
        g_100 = grav.gravity_at_altitude(100.0)
        g_400 = grav.gravity_at_altitude(400.0)
        g_1000 = grav.gravity_at_altitude(1000.0)
        
        assert g_0 > g_100 > g_400 > g_1000
    
    def test_gravity_at_200km(self):
        """Gravity at 200 km should be ~9.22 m/s²."""
        grav = GravityModel()
        g = grav.gravity_at_altitude(200.0)
        
        # Expected: g = 9.80665 * (6371 / 6571)² ≈ 9.22 m/s²
        expected = 9.22
        assert abs(g - expected) / expected < 0.01  # <1% error
    
    def test_gravity_at_400km(self):
        """Gravity at 400 km (ISS altitude) should be ~8.68 m/s²."""
        grav = GravityModel()
        g = grav.gravity_at_altitude(400.0)
        
        # Expected: g = 9.80665 * (6371 / 6771)² ≈ 8.68 m/s²
        expected = 8.68
        assert abs(g - expected) / expected < 0.01  # <1% error
    
    def test_gravity_at_1000km(self):
        """Gravity at 1000 km should be ~7.32 m/s²."""
        grav = GravityModel()
        g = grav.gravity_at_altitude(1000.0)
        
        # Expected: g = 9.80665 * (6371 / 7371)² ≈ 7.32 m/s²
        expected = 7.32
        assert abs(g - expected) / expected < 0.01  # <1% error


class TestGravityFormula:
    """Test that gravity follows inverse-square law."""
    
    def test_inverse_square_law(self):
        """Gravity should follow g = g₀ × (R/(R+h))²."""
        grav = GravityModel()
        
        altitude = 500.0  # km
        g = grav.gravity_at_altitude(altitude)
        
        # Calculate expected value
        r_earth = grav.earth_radius_km
        g0 = grav.g0
        expected = g0 * (r_earth / (r_earth + altitude)) ** 2
        
        assert abs(g - expected) < 1e-6
    
    def test_analytical_match(self):
        """Gravity should match analytical formula at all altitudes."""
        grav = GravityModel()
        
        altitudes = [0, 50, 100, 200, 400, 800, 1600]
        
        for h in altitudes:
            g_calc = grav.gravity_at_altitude(h)
            
            # Analytical formula
            r = grav.earth_radius_km
            g0 = grav.g0
            g_analytical = g0 * (r / (r + h)) ** 2
            
            # Should match exactly (within floating-point precision)
            assert abs(g_calc - g_analytical) < 1e-9


class TestGravityEdgeCases:
    """Test edge cases and extreme altitudes."""
    
    def test_negative_altitude(self):
        """Should handle negative altitude (below sea level)."""
        grav = GravityModel()
        
        # -1 km (underground)
        g = grav.gravity_at_altitude(-1.0)
        
        # Should be slightly higher than sea level
        # (though technically we'd need Earth's density profile for accuracy)
        assert g >= grav.g0
    
    def test_very_high_altitude(self):
        """Should handle very high altitudes (GEO and beyond)."""
        grav = GravityModel()
        
        # GEO altitude: ~35,786 km
        g_geo = grav.gravity_at_altitude(35786.0)
        
        # Should be much weaker but still positive
        assert 0.1 < g_geo < 1.0  # ~0.22 m/s²
    
    def test_gravity_never_zero(self):
        """Gravity should never reach exactly zero."""
        grav = GravityModel()
        
        # Even at extreme altitudes
        g = grav.gravity_at_altitude(1000000.0)  # 1 million km
        
        assert g > 0
    
    def test_gravity_never_negative(self):
        """Gravity should never be negative."""
        grav = GravityModel()
        
        altitudes = [0, 100, 1000, 10000, 100000]
        for h in altitudes:
            g = grav.gravity_at_altitude(h)
            assert g > 0


class TestGravityConfiguration:
    """Test configuration options."""
    
    def test_custom_g0(self):
        """Should accept custom surface gravity."""
        custom_g0 = 10.0
        grav = GravityModel(g0=custom_g0)
        
        g = grav.gravity_at_altitude(0.0)
        
        assert abs(g - custom_g0) < 1e-9
    
    def test_custom_earth_radius_affects_high_altitude(self):
        """Custom Earth radius should affect gravity at high altitudes."""
        grav_default = GravityModel(earth_radius_km=6371.0)
        grav_larger = GravityModel(earth_radius_km=6378.137)
        
        # At high altitude, larger radius means slightly less gravity drop-off
        g_default = grav_default.gravity_at_altitude(400.0)
        g_larger = grav_larger.gravity_at_altitude(400.0)
        
        # Larger radius → relatively less gravity decrease
        assert g_larger > g_default


class TestGravityAcceleration:
    """Test gravity acceleration vector."""
    
    def test_gravity_acceleration_magnitude(self):
        """Gravity acceleration should match scalar gravity."""
        grav = GravityModel()
        
        altitude = 400.0
        g_scalar = grav.gravity_at_altitude(altitude)
        g_vector = grav.gravity_acceleration(altitude)
        
        # Vector should be [0, -g, 0] in local frame
        assert abs(g_vector[1] + g_scalar) < 1e-9
    
    def test_gravity_points_down(self):
        """Gravity acceleration should point downward (-y direction)."""
        grav = GravityModel()
        
        g_vector = grav.gravity_acceleration(100.0)
        
        # Should be negative in y-direction
        assert g_vector[1] < 0
        
        # No acceleration in x or z
        assert g_vector[0] == 0.0
        assert g_vector[2] == 0.0


class TestRealWorldApplications:
    """Test gravity in real scenarios."""
    
    def test_iss_orbital_velocity(self):
        """At ISS altitude, orbital velocity ~7.66 km/s."""
        grav = GravityModel()
        
        altitude = 408.0  # ISS altitude (km)
        g = grav.gravity_at_altitude(altitude)
        
        # Orbital velocity: v = sqrt(g * r)
        import math
        r = (grav.earth_radius_km + altitude) * 1000  # meters
        v_orbital = math.sqrt(g * r)
        
        # ISS orbits at ~7660 m/s
        expected = 7660
        assert abs(v_orbital - expected) / expected < 0.01  # <1% error
    
    def test_escape_velocity(self):
        """Escape velocity at surface ~11.2 km/s."""
        grav = GravityModel()
        
        g = grav.gravity_at_altitude(0.0)
        
        # Escape velocity: v_e = sqrt(2 * g * R)
        import math
        r = grav.earth_radius_km * 1000  # meters
        v_escape = math.sqrt(2 * g * r)
        
        # Expected: ~11,186 m/s
        expected = 11186
        assert abs(v_escape - expected) / expected < 0.01  # <1% error
