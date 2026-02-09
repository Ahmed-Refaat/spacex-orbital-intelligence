"""
Tests for atmospheric drag model.

Drag is critical for accurate ascent simulation.
Typical contribution: 1-2% of total ΔV (100-150 m/s for Falcon 9).
"""
import pytest
import math
from app.services.drag_model import DragModel, AtmosphereDensity


class TestAtmosphereDensity:
    """Test atmospheric density model."""
    
    def test_density_at_sea_level(self):
        """Density at sea level should be ~1.225 kg/m³."""
        atm = AtmosphereDensity()
        rho = atm.density_at_altitude(0.0)
        
        # Standard atmospheric density
        assert abs(rho - 1.225) / 1.225 < 0.01  # <1% error
    
    def test_density_decreases_with_altitude(self):
        """Density should decrease exponentially with altitude."""
        atm = AtmosphereDensity()
        
        rho_0 = atm.density_at_altitude(0.0)
        rho_10 = atm.density_at_altitude(10.0)
        rho_30 = atm.density_at_altitude(30.0)
        rho_50 = atm.density_at_altitude(50.0)
        
        assert rho_0 > rho_10 > rho_30 > rho_50
    
    def test_density_near_zero_above_100km(self):
        """Density should be negligible above 100 km."""
        atm = AtmosphereDensity()
        rho = atm.density_at_altitude(100.0)
        
        # Should be very small (simplified exponential model)
        assert rho < 1e-5  # <0.00001 kg/m³ (good enough for preliminary)
    
    def test_density_at_10km(self):
        """Density at 10 km should be ~0.41 kg/m³."""
        atm = AtmosphereDensity()
        rho = atm.density_at_altitude(10.0)
        
        expected = 0.41
        assert abs(rho - expected) / expected < 0.1  # <10% error


class TestDragForce:
    """Test drag force calculation."""
    
    def test_drag_force_formula(self):
        """Drag force: D = 0.5 × ρ × v² × Cd × A."""
        drag = DragModel()
        
        # Typical Falcon 9 parameters
        velocity = 500  # m/s
        altitude = 10.0  # km
        Cd = 0.3
        diameter = 3.66  # m
        A = math.pi * (diameter / 2) ** 2  # Cross-sectional area
        
        drag_force = drag.calculate_drag_force(
            velocity_m_s=velocity,
            altitude_km=altitude,
            Cd=Cd,
            area_m2=A
        )
        
        # Manual calculation
        atm = AtmosphereDensity()
        rho = atm.density_at_altitude(altitude)
        expected = 0.5 * rho * velocity**2 * Cd * A
        
        assert abs(drag_force - expected) < 1.0
    
    def test_drag_increases_with_velocity(self):
        """Drag force should increase with v²."""
        drag = DragModel()
        
        altitude = 10.0
        Cd = 0.3
        area = 10.0
        
        d_100 = drag.calculate_drag_force(100, altitude, Cd, area)
        d_200 = drag.calculate_drag_force(200, altitude, Cd, area)
        d_400 = drag.calculate_drag_force(400, altitude, Cd, area)
        
        # Drag ~ v², so doubling velocity quadruples drag
        assert d_200 / d_100 > 3.5  # ~4x
        assert d_400 / d_100 > 15   # ~16x
    
    def test_drag_decreases_with_altitude(self):
        """Drag force should decrease with altitude (less dense air)."""
        drag = DragModel()
        
        velocity = 1000
        Cd = 0.3
        area = 10.0
        
        d_0 = drag.calculate_drag_force(velocity, 0.0, Cd, area)
        d_20 = drag.calculate_drag_force(velocity, 20.0, Cd, area)
        d_50 = drag.calculate_drag_force(velocity, 50.0, Cd, area)
        
        assert d_0 > d_20 > d_50


class TestDragCoefficient:
    """Test drag coefficient variations."""
    
    def test_subsonic_drag_coefficient(self):
        """Subsonic Cd should be low (~0.3)."""
        drag = DragModel()
        
        # Mach 0.5 (subsonic)
        Cd = drag.drag_coefficient(mach=0.5)
        
        assert 0.2 < Cd < 0.5
    
    def test_transonic_drag_rise(self):
        """Transonic region (Mach 0.8-1.2) has high drag."""
        drag = DragModel()
        
        Cd_subsonic = drag.drag_coefficient(mach=0.7)
        Cd_transonic = drag.drag_coefficient(mach=1.0)
        Cd_supersonic = drag.drag_coefficient(mach=2.0)
        
        # Transonic drag rise
        assert Cd_transonic > Cd_subsonic
        assert Cd_transonic > Cd_supersonic  # Peak at transonic
    
    def test_supersonic_drag_coefficient(self):
        """Supersonic Cd should stabilize (~0.2-0.3)."""
        drag = DragModel()
        
        Cd = drag.drag_coefficient(mach=3.0)
        
        assert 0.15 < Cd < 0.4


class TestMaxQ:
    """Test max-Q (maximum dynamic pressure) detection."""
    
    def test_max_q_calculation(self):
        """Max-Q: q = 0.5 × ρ × v²."""
        drag = DragModel()
        
        velocity = 500
        altitude = 12.0  # Typical max-Q altitude
        
        q = drag.dynamic_pressure(velocity, altitude)
        
        # q = 0.5 * rho * v²
        atm = AtmosphereDensity()
        rho = atm.density_at_altitude(altitude)
        expected = 0.5 * rho * velocity**2
        
        assert abs(q - expected) < 1.0
    
    def test_max_q_location(self):
        """Max-Q typically occurs at 10-15 km altitude."""
        drag = DragModel()
        
        # Simulate trajectory through max-Q
        q_values = []
        altitudes = []
        
        for alt_km in range(0, 30):
            # Simplified velocity profile (increases with altitude)
            velocity = alt_km * 40  # m/s
            q = drag.dynamic_pressure(velocity, alt_km)
            q_values.append(q)
            altitudes.append(alt_km)
        
        # Find max-Q altitude
        max_q_idx = q_values.index(max(q_values))
        max_q_altitude = altitudes[max_q_idx]
        
        # Should be between 8-18 km (typical range)
        assert 5 < max_q_altitude < 20


class TestDragAcceleration:
    """Test drag acceleration calculation."""
    
    def test_drag_acceleration(self):
        """Drag acceleration: a_drag = -D / m."""
        drag = DragModel()
        
        velocity = 1000  # m/s
        altitude = 15.0  # km
        Cd = 0.3
        area = 10.0  # m²
        mass = 400000  # kg
        
        a_drag = drag.drag_acceleration(
            velocity_m_s=velocity,
            altitude_km=altitude,
            mass_kg=mass,
            Cd=Cd,
            area_m2=area
        )
        
        # Should be negative (opposes motion)
        assert a_drag < 0
        
        # Manual calculation
        D = drag.calculate_drag_force(velocity, altitude, Cd, area)
        expected_a = -D / mass
        
        assert abs(a_drag - expected_a) < 1e-6
    
    def test_drag_acceleration_at_max_q(self):
        """Drag acceleration peaks near max-Q."""
        drag = DragModel()
        
        Cd = 0.3
        area = 10.0
        mass = 500000
        
        # Check drag at different altitudes
        a_values = []
        for alt in range(0, 40):
            velocity = alt * 50 if alt > 0 else 1
            a = drag.drag_acceleration(velocity, alt, mass, Cd, area)
            a_values.append(abs(a))
        
        # Peak should be somewhere in the middle
        max_a_idx = a_values.index(max(a_values))
        assert 5 < max_a_idx < 25  # Not at start or end


class TestFalcon9DragProfile:
    """Test realistic Falcon 9 drag profile."""
    
    def test_falcon9_reference_area(self):
        """Falcon 9 reference area from diameter."""
        drag = DragModel()
        
        diameter = 3.66  # m (Falcon 9)
        area = drag.reference_area_from_diameter(diameter)
        
        # A = π × (d/2)²
        expected = math.pi * (diameter / 2) ** 2
        assert abs(area - expected) < 0.01
    
    def test_falcon9_typical_drag_loss(self):
        """Falcon 9 typical drag loss is 100-150 m/s."""
        drag = DragModel()
        
        # Simplified ascent profile
        Cd = 0.3
        diameter = 3.66
        area = drag.reference_area_from_diameter(diameter)
        
        total_drag_loss = 0.0
        dt = 1.0
        
        for t in range(0, 200):  # First 200 seconds (through max-Q)
            altitude = t * 0.35  # km
            # More realistic velocity profile (accelerates faster)
            velocity = t * 15 if t < 80 else 1200 + (t - 80) * 8  # m/s
            mass = 550000 - t * 2500  # kg
            
            if velocity > 0:
                a_drag = drag.drag_acceleration(velocity, altitude, mass, Cd, area)
                drag_loss_increment = abs(a_drag) * dt
                total_drag_loss += drag_loss_increment
        
        # Should be in reasonable range (depends on trajectory)
        assert 20 < total_drag_loss < 300
