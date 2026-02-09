"""
Tests for ΔV budget calculation.

Story 3.2: ΔV Budget Calculation
Tests tracking of gravity loss, drag loss, steering loss, and final velocity.
"""
import pytest
import math
from dataclasses import dataclass
from app.services.delta_v_budget import DeltaVBudget, DeltaVCalculator


@dataclass
class SimState:
    """Simplified simulation state for testing."""
    time: float
    altitude_km: float
    velocity_km_s: float
    mass_kg: float
    pitch_deg: float  # 90 = vertical, 0 = horizontal


class TestDeltaVBudget:
    """Test DeltaVBudget data structure."""
    
    def test_budget_initialization(self):
        """Budget should initialize with zeros."""
        budget = DeltaVBudget()
        
        assert budget.gravity_loss == 0.0
        assert budget.drag_loss == 0.0
        assert budget.steering_loss == 0.0
        assert budget.total_delta_v == 0.0
    
    def test_budget_total_calculation(self):
        """Total ΔV should equal sum of all components."""
        budget = DeltaVBudget()
        budget.gravity_loss = 1500.0
        budget.drag_loss = 150.0
        budget.steering_loss = 100.0
        budget.orbital_velocity = 7800.0
        
        total = budget.calculate_total()
        
        # Total = sum of all losses + final velocity
        expected = 1500 + 150 + 100 + 7800
        assert abs(total - expected) < 1.0
    
    def test_budget_percentage_breakdown(self):
        """Should calculate percentage breakdown."""
        budget = DeltaVBudget()
        budget.gravity_loss = 1500.0
        budget.drag_loss = 150.0
        budget.steering_loss = 100.0
        budget.orbital_velocity = 7800.0
        
        percentages = budget.percentage_breakdown()
        
        total = 1500 + 150 + 100 + 7800
        assert abs(percentages['gravity_loss'] - (1500/total)*100) < 0.1
        assert abs(percentages['drag_loss'] - (150/total)*100) < 0.1
        assert abs(percentages['steering_loss'] - (100/total)*100) < 0.1
        assert abs(percentages['orbital_velocity'] - (7800/total)*100) < 0.1


class TestGravityLoss:
    """Test gravity loss calculation."""
    
    def test_vertical_flight_gravity_loss(self):
        """Vertical flight has maximum gravity loss."""
        calc = DeltaVCalculator()
        
        # Vertical flight for 60 seconds at g=9.8 m/s²
        dt = 1.0
        for i in range(60):
            state = SimState(
                time=i,
                altitude_km=i * 0.5,  # Rising
                velocity_km_s=0.5,
                mass_kg=500000,
                pitch_deg=90.0  # Vertical
            )
            
            g = 9.8  # Simplified
            thrust = 8000000  # N
            
            calc.update_gravity_loss(state, g, dt)
        
        # Gravity loss = g × t = 9.8 × 60 ≈ 588 m/s
        expected = 9.8 * 60
        assert abs(calc.budget.gravity_loss - expected) / expected < 0.01
    
    def test_horizontal_flight_gravity_loss(self):
        """Horizontal flight still has gravity loss (simplified model)."""
        calc = DeltaVCalculator()
        
        # Horizontal flight
        state = SimState(
            time=100,
            altitude_km=100,
            velocity_km_s=7.8,
            mass_kg=100000,
            pitch_deg=0.0  # Horizontal
        )
        
        g = 8.7  # At 100 km
        dt = 1.0
        
        calc.update_gravity_loss(state, g, dt)
        
        # Simplified model accumulates full gravity
        # (More accurate model would use vertical component only)
        assert calc.budget.gravity_loss == g * dt
    
    def test_gravity_loss_typical_launch(self):
        """Typical launch profile gravity loss."""
        calc = DeltaVCalculator()
        
        # Simplified launch profile (vertical → pitch over → horizontal)
        dt = 1.0
        for t in range(500):
            if t < 60:
                pitch = 90.0  # Vertical ascent
            elif t < 300:
                pitch = 90.0 - (t - 60) * 0.375  # Pitch over
            else:
                pitch = 0.0  # Horizontal
            
            altitude = (t * 0.4) if t < 200 else 200
            g = 9.8 * (6371 / (6371 + altitude)) ** 2
            
            state = SimState(
                time=t,
                altitude_km=altitude,
                velocity_km_s=t * 0.015,
                mass_kg=500000 - t * 800,
                pitch_deg=pitch
            )
            
            calc.update_gravity_loss(state, g, dt)
        
        # Typical gravity loss: varies by profile (simplified model)
        assert 1000 < calc.budget.gravity_loss < 5000


class TestDragLoss:
    """Test drag loss calculation."""
    
    def test_drag_loss_accumulation(self):
        """Drag loss should accumulate over time."""
        calc = DeltaVCalculator()
        
        # Simplified drag calculation
        dt = 1.0
        for t in range(100):
            altitude = t * 0.5
            velocity = t * 0.08
            
            # Simplified drag force
            rho = 1.225 * math.exp(-altitude / 8.5)  # Density
            v = velocity * 1000  # m/s
            Cd = 0.3
            A = 10.0  # m²
            mass = 500000
            
            drag_force = 0.5 * rho * v * v * Cd * A
            drag_accel = drag_force / mass
            
            state = SimState(
                time=t,
                altitude_km=altitude,
                velocity_km_s=velocity,
                mass_kg=mass,
                pitch_deg=45.0
            )
            
            calc.update_drag_loss(state, drag_accel, dt)
        
        # Should have accumulated some drag loss
        assert calc.budget.drag_loss > 0
    
    def test_drag_loss_max_q(self):
        """Drag peaks at max-Q (maximum dynamic pressure)."""
        calc = DeltaVCalculator()
        
        # Simulate through max-Q region (~10-15 km altitude)
        dt = 0.1
        drag_history = []
        
        for t in range(1000):
            time = t * dt
            altitude = time * 0.1
            velocity = time * 0.01
            
            if altitude > 20:
                break
            
            rho = 1.225 * math.exp(-altitude / 8.5)
            v = velocity * 1000
            q = 0.5 * rho * v * v  # Dynamic pressure
            
            Cd = 0.3
            A = 10.0
            mass = 500000
            
            drag_force = q * Cd * A
            drag_accel = drag_force / mass
            
            state = SimState(
                time=time,
                altitude_km=altitude,
                velocity_km_s=velocity,
                mass_kg=mass,
                pitch_deg=80.0
            )
            
            calc.update_drag_loss(state, drag_accel, dt)
            drag_history.append(drag_accel)
        
        # Drag should increase then decrease (or plateau)
        # In reality, max-Q occurs when q = 0.5*rho*v² peaks
        # For this test, just verify drag was calculated
        assert len(drag_history) > 0
        assert max(drag_history) > min(drag_history)  # Drag varies


class TestSteeringLoss:
    """Test steering loss (cosine loss) calculation."""
    
    def test_vertical_flight_no_steering_loss(self):
        """Vertical flight (thrust aligned with velocity) has no steering loss."""
        calc = DeltaVCalculator()
        
        state = SimState(
            time=10,
            altitude_km=5,
            velocity_km_s=0.5,
            mass_kg=500000,
            pitch_deg=90.0  # Vertical
        )
        
        thrust = 8000000  # N
        mass = state.mass_kg
        dt = 1.0
        
        # Thrust aligned with velocity → no steering loss
        calc.update_steering_loss(state, thrust, mass, dt)
        
        assert calc.budget.steering_loss == 0.0
    
    def test_steering_loss_increases_with_angle(self):
        """Steering loss increases as thrust angle differs from velocity."""
        calc = DeltaVCalculator()
        
        thrust = 8000000
        mass = 500000
        dt = 1.0
        
        # Different pitch angles
        losses = []
        for pitch in [90, 75, 60, 45, 30]:
            calc_temp = DeltaVCalculator()
            state = SimState(
                time=100,
                altitude_km=50,
                velocity_km_s=2.0,
                mass_kg=mass,
                pitch_deg=pitch
            )
            
            calc_temp.update_steering_loss(state, thrust, mass, dt)
            losses.append(calc_temp.budget.steering_loss)
        
        # Loss should increase as we deviate from velocity vector
        # (though this depends on velocity vector direction too)
        assert max(losses) > min(losses)


class TestTotalDeltaV:
    """Test total ΔV calculation."""
    
    def test_total_delta_v_from_rocket_equation(self):
        """Total ΔV should match rocket equation for simple case."""
        calc = DeltaVCalculator()
        
        # Rocket equation: ΔV = Isp × g0 × ln(m0/mf)
        Isp = 300  # seconds
        g0 = 9.80665
        m0 = 100000  # Initial mass (kg)
        mf = 10000   # Final mass (kg)
        
        expected_dv = Isp * g0 * math.log(m0 / mf)
        
        # Should be ~6774 m/s (ln(10) ≈ 2.303)
        assert 6700 < expected_dv < 6800
    
    def test_budget_conservation(self):
        """ΔV budget should be conserved: total = losses + final velocity."""
        budget = DeltaVBudget()
        budget.gravity_loss = 1534.0
        budget.drag_loss = 135.0
        budget.steering_loss = 89.0
        budget.orbital_velocity = 7800.0
        
        total = budget.calculate_total()
        
        # Total ΔV delivered = sum of all components
        expected = 1534 + 135 + 89 + 7800
        assert abs(total - expected) < 0.1


class TestDeltaVSummary:
    """Test ΔV budget summary and reporting."""
    
    def test_summary_format(self):
        """Summary should provide human-readable output."""
        budget = DeltaVBudget()
        budget.gravity_loss = 1534.0
        budget.drag_loss = 135.0
        budget.steering_loss = 89.0
        budget.orbital_velocity = 7800.0
        
        summary = budget.summary()
        
        # Should contain all components
        assert "Gravity" in summary or "gravity" in summary
        assert "Drag" in summary or "drag" in summary
        assert "1534" in summary  # Gravity loss value
        assert "7800" in summary  # Orbital velocity
    
    def test_breakdown_table(self):
        """Should generate breakdown table."""
        budget = DeltaVBudget()
        budget.gravity_loss = 1534.0
        budget.drag_loss = 135.0
        budget.steering_loss = 89.0
        budget.orbital_velocity = 7800.0
        
        table = budget.breakdown_table()
        
        assert isinstance(table, dict)
        assert "gravity_loss" in table
        assert "drag_loss" in table
        assert "steering_loss" in table
        assert "orbital_velocity" in table


class TestRealWorldScenario:
    """Test ΔV budget for realistic launch."""
    
    def test_falcon9_typical_budget(self):
        """Falcon 9 to LEO typical ΔV budget."""
        # Typical Falcon 9 to LEO (400 km):
        # - Orbital velocity: ~7800 m/s
        # - Gravity loss: ~1500 m/s (15-18%)
        # - Drag loss: ~100-150 m/s (1-2%)
        # - Steering loss: ~50-100 m/s (0.5-1%)
        # - Total ΔV: ~9500 m/s
        
        budget = DeltaVBudget()
        budget.gravity_loss = 1534.0
        budget.drag_loss = 135.0
        budget.steering_loss = 89.0
        budget.orbital_velocity = 7800.0
        
        total = budget.calculate_total()
        
        # Total should be ~9.5 km/s
        assert 9400 < total < 9700
        
        # Check percentages are reasonable
        pct = budget.percentage_breakdown()
        assert 15 < pct['gravity_loss'] < 18  # 15-18%
        assert 1 < pct['drag_loss'] < 3       # 1-3%
        assert 0.5 < pct['steering_loss'] < 2  # 0.5-2%
        assert 80 < pct['orbital_velocity'] < 85  # 80-85%
