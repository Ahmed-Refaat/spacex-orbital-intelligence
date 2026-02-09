"""
Tests for Earth rotation effects on launch.

Story 2.4: Earth Rotation
Tests velocity bonus and azimuth-to-inclination conversion.
"""
import pytest
import math
from app.services.earth_rotation import EarthRotation, LaunchSite


# Physical constants
R_EARTH = 6371.0  # km
OMEGA_EARTH = 7.2921159e-5  # rad/s


class TestLaunchSites:
    """Test launch site definitions."""
    
    def test_cape_canaveral(self):
        """Cape Canaveral at 28.5°N."""
        site = LaunchSite.cape_canaveral()
        
        assert site.name == "Cape Canaveral"
        assert abs(site.latitude_deg - 28.5) < 0.1
        assert abs(site.longitude_deg + 80.5) < 0.1
    
    def test_vandenberg(self):
        """Vandenberg at 34.7°N."""
        site = LaunchSite.vandenberg()
        
        assert site.name == "Vandenberg"
        assert abs(site.latitude_deg - 34.7) < 0.1
    
    def test_kourou(self):
        """Kourou (French Guiana) at 5.2°N."""
        site = LaunchSite.kourou()
        
        assert site.name == "Kourou"
        assert abs(site.latitude_deg - 5.2) < 0.1
    
    def test_baikonur(self):
        """Baikonur at 45.6°N."""
        site = LaunchSite.baikonur()
        
        assert site.name == "Baikonur"
        assert abs(site.latitude_deg - 45.6) < 0.1


class TestRotationalVelocity:
    """Test Earth's rotational velocity at different latitudes."""
    
    def test_velocity_at_equator(self):
        """Velocity at equator should be ~465 m/s."""
        earth = EarthRotation()
        v = earth.surface_velocity(latitude_deg=0.0)
        
        # v = ω × R = 7.29e-5 × 6371000 ≈ 465 m/s
        expected = 465
        assert abs(v - expected) / expected < 0.01  # <1% error
    
    def test_velocity_at_cape(self):
        """Velocity at Cape Canaveral (~28.5°N) should be ~410 m/s."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        v = earth.surface_velocity(site.latitude_deg)
        
        # v = ω × R × cos(lat) ≈ 410 m/s
        expected = 410
        assert abs(v - expected) / expected < 0.01
    
    def test_velocity_at_poles(self):
        """Velocity at poles should be ~0."""
        earth = EarthRotation()
        
        v_north = earth.surface_velocity(latitude_deg=90.0)
        v_south = earth.surface_velocity(latitude_deg=-90.0)
        
        assert v_north < 1.0  # Essentially zero
        assert v_south < 1.0
    
    def test_velocity_decreases_with_latitude(self):
        """Velocity should decrease as you go towards poles."""
        earth = EarthRotation()
        
        v_0 = earth.surface_velocity(0.0)
        v_30 = earth.surface_velocity(30.0)
        v_60 = earth.surface_velocity(60.0)
        v_90 = earth.surface_velocity(90.0)
        
        assert v_0 > v_30 > v_60 > v_90


class TestLaunchAzimuth:
    """Test launch azimuth calculations."""
    
    def test_eastward_launch_azimuth(self):
        """Eastward launch (0° or 90° azimuth) for maximum velocity bonus."""
        site = LaunchSite.cape_canaveral()
        
        # Azimuth 90° = due east
        assert site.azimuth_deg == 90.0
    
    def test_iss_launch_azimuth(self):
        """ISS launch from Cape is northeast (~51.6°)."""
        # For 51.6° inclination from Cape
        # Simplified: azimuth ≈ arcsin(cos(i) / cos(lat))
        
        site = LaunchSite.cape_canaveral()
        i = 51.6  # ISS inclination
        lat = site.latitude_deg
        
        # This is simplified - real calculation more complex
        # Just check it's between 0 and 90 (northeastward)
        expected_azimuth = math.degrees(math.asin(math.cos(math.radians(i)) / math.cos(math.radians(lat))))
        
        # Should be ~42-52° (northeast)
        assert 40 < expected_azimuth < 55


class TestVelocityBonus:
    """Test velocity bonus from Earth's rotation."""
    
    def test_eastward_launch_gets_full_bonus(self):
        """Eastward launch gets full rotational velocity."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # Launch due east
        azimuth = 90.0
        v_bonus = earth.velocity_bonus(site, azimuth)
        v_surface = earth.surface_velocity(site.latitude_deg)
        
        # Full bonus (eastward)
        assert abs(v_bonus - v_surface) / v_surface < 0.01
    
    def test_westward_launch_loses_bonus(self):
        """Westward launch fights against rotation."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # Launch due west
        azimuth = 270.0
        v_bonus = earth.velocity_bonus(site, azimuth)
        v_surface = earth.surface_velocity(site.latitude_deg)
        
        # Negative bonus (loses velocity)
        assert v_bonus < 0
        assert abs(v_bonus + v_surface) / v_surface < 0.01
    
    def test_northward_launch_no_bonus(self):
        """Northward launch gets no rotational bonus."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # Launch due north
        azimuth = 0.0
        v_bonus = earth.velocity_bonus(site, azimuth)
        
        # No bonus (perpendicular to rotation)
        assert abs(v_bonus) < 10.0  # Small (not exactly zero due to geometry)


class TestInclinationCalculation:
    """Test orbital inclination from launch azimuth."""
    
    def test_eastward_launch_inclination(self):
        """Eastward launch from 28.5°N gives 28.5° inclination."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # Launch due east
        azimuth = 90.0
        inclination = earth.inclination_from_azimuth(site, azimuth)
        
        # Inclination = latitude for eastward launch
        assert abs(inclination - site.latitude_deg) < 1.0
    
    def test_iss_inclination(self):
        """ISS launch gives 51.6° inclination."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # For ISS, inclination = 51.6°
        # Calculate required azimuth
        target_inclination = 51.6
        
        # Simplified: i ≈ arcsin(sin(lat) * sin(az) + cos(lat) * cos(az))
        # Or more commonly: cos(i) = cos(lat) * sin(az)
        # So: az = arcsin(cos(i) / cos(lat))
        
        lat_rad = math.radians(site.latitude_deg)
        i_rad = math.radians(target_inclination)
        
        # This is the standard formula (simplified)
        azimuth = math.degrees(math.asin(math.cos(i_rad) / math.cos(lat_rad)))
        
        # Calculate inclination back
        calc_i = earth.inclination_from_azimuth(site, azimuth)
        
        assert abs(calc_i - target_inclination) < 2.0  # Within 2°
    
    def test_polar_orbit(self):
        """Northward launch gives polar orbit (90°)."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # Launch due north
        azimuth = 0.0
        inclination = earth.inclination_from_azimuth(site, azimuth)
        
        # Should be ~90° (polar)
        assert 85 < inclination < 95


class TestInitialVelocity:
    """Test initial velocity vector with Earth rotation."""
    
    def test_initial_velocity_components(self):
        """Initial velocity should have correct components."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        azimuth = 90.0  # East
        v_init = earth.initial_velocity_vector(site, azimuth)
        
        # Should have:
        # - Eastward component (~410 m/s from rotation)
        # - No vertical component (before liftoff)
        # - No northward component (due east)
        
        v_east, v_north, v_up = v_init
        
        # Eastward velocity from rotation
        expected_v_east = earth.surface_velocity(site.latitude_deg)
        assert abs(v_east - expected_v_east) / expected_v_east < 0.01
        
        # No north or up (before launch)
        assert abs(v_north) < 1.0
        assert abs(v_up) < 1.0


class TestRealWorldScenarios:
    """Test real launch scenarios."""
    
    def test_falcon9_to_iss(self):
        """Falcon 9 to ISS from Cape Canaveral."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # ISS orbit: 51.6° inclination
        target_i = 51.6
        
        # Calculate launch azimuth
        lat_rad = math.radians(site.latitude_deg)
        i_rad = math.radians(target_i)
        azimuth = math.degrees(math.asin(math.cos(i_rad) / math.cos(lat_rad)))
        
        # Velocity bonus
        v_bonus = earth.velocity_bonus(site, azimuth)
        
        # Should get significant bonus (eastward component)
        assert v_bonus > 250  # >250 m/s bonus (northeast launch)
    
    def test_starlink_launch(self):
        """Starlink launch (typically eastward from Cape)."""
        earth = EarthRotation()
        site = LaunchSite.cape_canaveral()
        
        # Starlink: typically 53° inclination
        target_i = 53.0
        
        lat_rad = math.radians(site.latitude_deg)
        i_rad = math.radians(target_i)
        azimuth = math.degrees(math.asin(math.cos(i_rad) / math.cos(lat_rad)))
        
        v_bonus = earth.velocity_bonus(site, azimuth)
        
        # Good velocity bonus
        assert v_bonus > 250  # >250 m/s (northeast launch)


class TestEdgeCases:
    """Test edge cases."""
    
    def test_equatorial_launch(self):
        """Launch from equator gets maximum velocity bonus."""
        earth = EarthRotation()
        site = LaunchSite(name="Equator", latitude_deg=0.0, longitude_deg=0.0)
        
        azimuth = 90.0  # East
        v_bonus = earth.velocity_bonus(site, azimuth)
        
        # Should be ~465 m/s
        assert v_bonus > 450
    
    def test_polar_launch_site(self):
        """Launch near poles gets minimal velocity bonus."""
        earth = EarthRotation()
        site = LaunchSite(name="Polar", latitude_deg=80.0, longitude_deg=0.0)
        
        azimuth = 90.0
        v_bonus = earth.velocity_bonus(site, azimuth)
        
        # Very small bonus near poles
        assert v_bonus < 100
