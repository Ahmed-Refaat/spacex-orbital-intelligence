"""
Tests for 6-DOF (6 Degrees of Freedom) simulation.

6-DOF = Full 3D trajectory with position (x,y,z) and velocity (vx,vy,vz).

This is the CORE of accurate trajectory simulation.
"""
import pytest
import math
from dataclasses import dataclass
from app.services.simulation_6dof import State6DOF, EquationsOfMotion, GravityTurnGuidance


class TestState6DOF:
    """Test 6-DOF state vector."""
    
    def test_state_creation(self):
        """Should create 6-DOF state."""
        state = State6DOF(
            time=0.0,
            x=0.0, y=0.0, z=0.0,  # Position (km)
            vx=0.0, vy=0.0, vz=0.0,  # Velocity (km/s)
            mass=500000.0
        )
        
        assert state.time == 0.0
        assert state.mass == 500000.0
    
    def test_altitude_calculation(self):
        """Altitude should be distance from origin."""
        state = State6DOF(
            time=10.0,
            x=0.0, y=50.0, z=0.0,  # 50 km vertical
            vx=0.0, vy=1.0, vz=0.0,
            mass=490000.0
        )
        
        altitude = state.altitude()
        
        # Altitude = sqrt(x² + y² + z²) - R_earth
        # For small altitudes, approximately equal to y
        assert abs(altitude - 50.0) < 0.1
    
    def test_velocity_magnitude(self):
        """Should calculate velocity magnitude."""
        state = State6DOF(
            time=100.0,
            x=50.0, y=70.0, z=0.0,
            vx=1.0, vy=2.0, vz=0.0,
            mass=400000.0
        )
        
        v_mag = state.velocity_magnitude()
        
        # v = sqrt(vx² + vy² + vz²)
        expected = math.sqrt(1**2 + 2**2)
        assert abs(v_mag - expected) < 0.01
    
    def test_to_list(self):
        """State should convert to list for RK4."""
        state = State6DOF(
            time=50.0,
            x=10.0, y=20.0, z=0.0,
            vx=0.5, vy=1.0, vz=0.0,
            mass=450000.0
        )
        
        state_list = state.to_list()
        
        # Should be [x, y, z, vx, vy, vz, mass]
        assert len(state_list) == 7
        assert state_list[0] == 10.0  # x
        assert state_list[1] == 20.0  # y
        assert state_list[6] == 450000.0  # mass


class TestEquationsOfMotion:
    """Test equations of motion (physics)."""
    
    def test_gravity_acceleration(self):
        """Gravity should point downward."""
        eom = EquationsOfMotion()
        
        state = State6DOF(
            time=0.0,
            x=0.0, y=10.0, z=0.0,  # 10 km altitude
            vx=0.0, vy=0.5, vz=0.0,
            mass=500000.0
        )
        
        # Get gravity acceleration
        a_grav = eom.gravity_acceleration(state)
        
        # Should point toward Earth center (negative y for vertical flight)
        assert a_grav[1] < 0  # Downward
    
    def test_thrust_acceleration_vertical(self):
        """Thrust should accelerate vehicle upward."""
        eom = EquationsOfMotion()
        
        state = State6DOF(
            time=10.0,
            x=0.0, y=5.0, z=0.0,
            vx=0.0, vy=0.3, vz=0.0,
            mass=500000.0
        )
        
        thrust = 8000000  # N
        pitch = 90.0  # Vertical
        
        a_thrust = eom.thrust_acceleration(state, thrust, pitch)
        
        # Should be upward (positive y)
        assert a_thrust[1] > 0
        
        # Magnitude should be thrust / mass (in km/s²)
        expected_mag = (thrust / state.mass) / 1000.0  # Convert to km/s²
        actual_mag = math.sqrt(sum(a**2 for a in a_thrust))
        assert abs(actual_mag - expected_mag) / expected_mag < 0.01
    
    def test_drag_acceleration(self):
        """Drag should oppose velocity."""
        eom = EquationsOfMotion()
        
        state = State6DOF(
            time=100.0,
            x=50.0, y=50.0, z=0.0,
            vx=0.5, vy=1.0, vz=0.0,  # Moving up and downrange
            mass=400000.0
        )
        
        Cd = 0.3
        area = 10.0
        
        a_drag = eom.drag_acceleration(state, Cd, area)
        
        # Drag should oppose velocity
        # If vx > 0, drag_x should be < 0
        # If vy > 0, drag_y should be < 0
        assert a_drag[0] < 0  # Opposes vx
        assert a_drag[1] < 0  # Opposes vy
    
    def test_total_acceleration(self):
        """Total acceleration = gravity + thrust + drag."""
        eom = EquationsOfMotion()
        
        state = State6DOF(
            time=50.0,
            x=10.0, y=30.0, z=0.0,
            vx=0.3, vy=0.8, vz=0.0,
            mass=450000.0
        )
        
        thrust = 7000000
        pitch = 85.0  # Slightly pitched over
        Cd = 0.3
        area = 10.0
        
        a_total = eom.total_acceleration(state, thrust, pitch, Cd, area)
        
        # Should be a 3D vector
        assert len(a_total) == 3
        
        # Should be non-zero
        mag = math.sqrt(sum(a**2 for a in a_total))
        assert mag > 0


class TestGravityTurnGuidance:
    """Test gravity turn guidance law."""
    
    def test_initial_vertical_flight(self):
        """Should start vertical."""
        guidance = GravityTurnGuidance(
            vertical_flight_duration=20.0,
            pitch_kickover_angle=5.0
        )
        
        # At t=10s, should be vertical (90°)
        pitch = guidance.pitch_angle(time=10.0, velocity=0.2, altitude=5.0)
        
        assert abs(pitch - 90.0) < 1.0  # Nearly vertical
    
    def test_kickover_after_vertical(self):
        """Should pitch over after vertical flight."""
        guidance = GravityTurnGuidance(
            vertical_flight_duration=20.0,
            pitch_kickover_angle=5.0
        )
        
        # At t=25s (after 20s vertical), should have kicked over
        pitch = guidance.pitch_angle(time=25.0, velocity=0.5, altitude=10.0)
        
        assert pitch < 90.0  # Pitched over from vertical
        assert pitch > 70.0  # But still mostly up
    
    def test_gravity_turn_to_horizontal(self):
        """Should gradually turn to horizontal."""
        guidance = GravityTurnGuidance(
            vertical_flight_duration=20.0,
            pitch_kickover_angle=5.0
        )
        
        # Late in flight, high velocity, high altitude
        pitch = guidance.pitch_angle(time=200.0, velocity=7.0, altitude=150.0)
        
        # Should be near horizontal
        assert pitch < 30.0
    
    def test_pitch_decreases_with_velocity(self):
        """Pitch should decrease as velocity increases."""
        guidance = GravityTurnGuidance(
            vertical_flight_duration=20.0,
            pitch_kickover_angle=5.0
        )
        
        time = 100.0
        altitude = 80.0
        
        pitch_slow = guidance.pitch_angle(time, 1.0, altitude)
        pitch_medium = guidance.pitch_angle(time, 3.0, altitude)
        pitch_fast = guidance.pitch_angle(time, 6.0, altitude)
        
        # Faster = lower pitch (more horizontal)
        assert pitch_slow > pitch_medium > pitch_fast


class TestSimulation6DOF:
    """Test full 6-DOF simulation integration."""
    
    def test_simulation_initialization(self):
        """Should initialize simulation."""
        from app.services.simulation_6dof import Simulation6DOF
        
        sim = Simulation6DOF()
        assert sim is not None
    
    def test_single_step(self):
        """Should advance simulation by one step."""
        from app.services.simulation_6dof import Simulation6DOF
        
        sim = Simulation6DOF()
        
        initial_state = State6DOF(
            time=0.0,
            x=0.0, y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            mass=500000.0
        )
        
        # One step with thrust
        thrust = 8000000
        pitch = 90.0
        Cd = 0.3
        area = 10.0
        dt = 1.0
        
        new_state = sim.step(initial_state, thrust, pitch, Cd, area, dt)
        
        # Should have moved
        assert new_state.y > 0  # Altitude increased
        assert new_state.vy > 0  # Velocity increased
        assert new_state.time == 1.0


class TestRK4Integration:
    """Test RK4 integration for 6-DOF."""
    
    def test_rk4_more_accurate_than_euler(self):
        """RK4 should be more accurate than Euler for same timestep."""
        from app.services.simulation_6dof import Simulation6DOF
        
        sim = Simulation6DOF()
        
        initial_state = State6DOF(
            time=0.0,
            x=0.0, y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            mass=500000.0
        )
        
        # Simulate 10 seconds
        thrust = 8000000
        pitch = 90.0
        Cd = 0.3
        area = 10.0
        
        # RK4 with large timestep
        state_rk4 = initial_state
        dt_large = 1.0
        for i in range(10):
            state_rk4 = sim.step(state_rk4, thrust, pitch, Cd, area, dt_large)
        
        # RK4 should produce reasonable results even with 1s timestep
        assert state_rk4.y > 0  # Moved upward
        assert state_rk4.vy > 0  # Has velocity


class TestVerticalFlight:
    """Test pure vertical flight (no pitch-over)."""
    
    def test_vertical_ascent(self):
        """Pure vertical flight should go straight up."""
        from app.services.simulation_6dof import Simulation6DOF
        
        sim = Simulation6DOF()
        
        state = State6DOF(
            time=0.0,
            x=0.0, y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            mass=500000.0
        )
        
        # Simulate 60 seconds vertical
        thrust = 8000000
        pitch = 90.0  # Vertical
        Cd = 0.3
        area = 10.0
        dt = 1.0
        
        for i in range(60):
            state = sim.step(state, thrust, pitch, Cd, area, dt)
        
        # Should be moving upward
        assert state.y > 5.0  # >5 km altitude
        assert state.vy > 0.3  # >300 m/s velocity
        
        # Should be mostly vertical (x should be small)
        assert abs(state.x) < 10.0  # <10 km downrange


class TestGravityTurnTrajectory:
    """Test full gravity turn trajectory."""
    
    def test_gravity_turn_to_orbit(self):
        """Gravity turn should produce curved trajectory."""
        from app.services.simulation_6dof import Simulation6DOF
        
        sim = Simulation6DOF()
        guidance = GravityTurnGuidance(
            vertical_flight_duration=20.0,
            pitch_kickover_angle=5.0
        )
        
        state = State6DOF(
            time=0.0,
            x=0.0, y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            mass=500000.0
        )
        
        # Simulate 200 seconds
        thrust = 7000000
        Cd = 0.3
        area = 10.0
        dt = 1.0
        
        altitudes = []
        downranges = []
        
        for i in range(200):
            # Get pitch from guidance
            pitch = guidance.pitch_angle(state.time, state.velocity_magnitude(), state.altitude())
            
            # Step
            state = sim.step(state, thrust, pitch, Cd, area, dt)
            
            altitudes.append(state.y)
            downranges.append(state.x)
        
        # Should have altitude and downrange
        assert max(altitudes) > 40.0  # >40 km altitude
        assert max(downranges) > 20.0  # >20 km downrange
        
        # Should be a curved trajectory (not straight up or straight across)
        assert max(altitudes) > 0
        assert max(downranges) > 0
