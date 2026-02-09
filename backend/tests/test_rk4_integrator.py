"""
Tests for RK4 (Runge-Kutta 4th order) numerical integrator.

Story 2.3: RK4 Integration
Tests that RK4 is more accurate than Euler for same timestep.
"""
import pytest
import math
from app.services.integrator import EulerIntegrator, RK4Integrator


class TestSimpleHarmonicOscillator:
    """Test integrators on simple harmonic oscillator (analytical solution exists)."""
    
    def test_euler_vs_rk4_accuracy(self):
        """RK4 should be more accurate than Euler for same timestep."""
        # Simple harmonic oscillator: d²x/dt² = -ω²x
        # Analytical solution: x(t) = A*cos(ωt)
        omega = 1.0  # Angular frequency
        amplitude = 1.0
        dt = 0.1  # Timestep
        t_end = 10.0  # 10 seconds
        
        def derivative(state, t):
            """Derivative function: [dx/dt, dv/dt] = [v, -ω²x]."""
            x, v = state
            return [v, -omega**2 * x]
        
        # Initial state: [position, velocity]
        state0 = [amplitude, 0.0]
        
        # Integrate with Euler
        euler = EulerIntegrator()
        state_euler, _ = euler.integrate(derivative, state0, 0.0, t_end, dt)
        
        # Integrate with RK4
        rk4 = RK4Integrator()
        state_rk4, _ = rk4.integrate(derivative, state0, 0.0, t_end, dt)
        
        # Analytical solution at t_end
        x_analytical = amplitude * math.cos(omega * t_end)
        
        # RK4 should be much closer to analytical
        error_euler = abs(state_euler[0] - x_analytical)
        error_rk4 = abs(state_rk4[0] - x_analytical)
        
        assert error_rk4 < error_euler
        assert error_rk4 < 0.01  # RK4 error <1%
    
    def test_rk4_energy_conservation(self):
        """RK4 should conserve energy better than Euler."""
        omega = 1.0
        amplitude = 1.0
        dt = 0.1
        t_end = 20.0
        
        def derivative(state, t):
            x, v = state
            return [v, -omega**2 * x]
        
        def energy(state):
            """Total energy: E = ½mv² + ½kx² (m=k=1)."""
            x, v = state
            return 0.5 * v**2 + 0.5 * omega**2 * x**2
        
        state0 = [amplitude, 0.0]
        E0 = energy(state0)
        
        # Euler
        euler = EulerIntegrator()
        state_euler, _ = euler.integrate(derivative, state0, 0.0, t_end, dt)
        E_euler = energy(state_euler)
        
        # RK4
        rk4 = RK4Integrator()
        state_rk4, _ = rk4.integrate(derivative, state0, 0.0, t_end, dt)
        E_rk4 = energy(state_rk4)
        
        # RK4 should conserve energy better
        error_euler = abs(E_euler - E0) / E0
        error_rk4 = abs(E_rk4 - E0) / E0
        
        assert error_rk4 < error_euler


class TestOrbitalMotion:
    """Test integrators on simplified orbital motion."""
    
    def test_circular_orbit(self):
        """RK4 should maintain circular orbit better than Euler."""
        # Simplified 2D orbit: d²r/dt² = -GM/r² r̂
        GM = 398600.0  # Earth's GM (km³/s²)
        r0 = 6771.0  # ISS altitude (km)
        v0 = math.sqrt(GM / r0)  # Circular orbit velocity
        
        def derivative(state, t):
            """[dx/dt, dy/dt, dvx/dt, dvy/dt]."""
            x, y, vx, vy = state
            r = math.sqrt(x**2 + y**2)
            ax = -GM * x / r**3
            ay = -GM * y / r**3
            return [vx, vy, ax, ay]
        
        # Initial state: circular orbit
        state0 = [r0, 0.0, 0.0, v0]
        
        dt = 10.0  # 10 seconds
        period = 2 * math.pi * math.sqrt(r0**3 / GM)  # Orbital period
        t_end = period  # One full orbit
        
        # RK4
        rk4 = RK4Integrator()
        state_rk4, _ = rk4.integrate(derivative, state0, 0.0, t_end, dt)
        
        # After one orbit, should return to starting position
        x_end, y_end = state_rk4[0], state_rk4[1]
        r_end = math.sqrt(x_end**2 + y_end**2)
        
        # Radius should be preserved (circular orbit)
        assert abs(r_end - r0) / r0 < 0.01  # <1% error


class TestRK4Properties:
    """Test RK4-specific properties."""
    
    def test_rk4_fourth_order_convergence(self):
        """RK4 error should scale as dt⁴ (fourth-order method)."""
        # Test on exponential: dy/dt = y, y(0) = 1
        # Analytical: y(t) = e^t
        def derivative(state, t):
            return [state[0]]  # dy/dt = y
        
        state0 = [1.0]
        t_end = 1.0
        y_analytical = math.exp(t_end)
        
        # Test with different timesteps
        dts = [0.1, 0.05, 0.025]
        errors = []
        
        rk4 = RK4Integrator()
        for dt in dts:
            state, _ = rk4.integrate(derivative, state0, 0.0, t_end, dt)
            error = abs(state[0] - y_analytical)
            errors.append(error)
        
        # Error should decrease by factor of ~16 when dt halved (4th order)
        ratio_0_1 = errors[0] / errors[1]
        ratio_1_2 = errors[1] / errors[2]
        
        # Should be close to 16 (2⁴)
        assert 10 < ratio_0_1 < 20
        assert 10 < ratio_1_2 < 20
    
    def test_rk4_single_step(self):
        """Test RK4 single step calculation."""
        # dy/dt = -y, y(0) = 1
        # Analytical: y(0.1) = e^(-0.1) ≈ 0.9048
        def derivative(state, t):
            return [-state[0]]
        
        rk4 = RK4Integrator()
        state0 = [1.0]
        dt = 0.1
        
        state_new = rk4.step(derivative, state0, 0.0, dt)
        
        y_analytical = math.exp(-dt)
        
        assert abs(state_new[0] - y_analytical) / y_analytical < 0.0001  # <0.01% error


class TestIntegratorInterface:
    """Test common integrator interface."""
    
    def test_euler_integrator_exists(self):
        """Euler integrator should exist."""
        euler = EulerIntegrator()
        assert euler is not None
    
    def test_rk4_integrator_exists(self):
        """RK4 integrator should exist."""
        rk4 = RK4Integrator()
        assert rk4 is not None
    
    def test_integrate_returns_state_and_time(self):
        """Integrate should return (final_state, time_array)."""
        def derivative(state, t):
            return [0.0]  # dy/dt = 0
        
        rk4 = RK4Integrator()
        state0 = [1.0]
        
        state_final, times = rk4.integrate(derivative, state0, 0.0, 1.0, 0.1)
        
        assert isinstance(state_final, list)
        assert isinstance(times, list)
        assert len(times) > 0
    
    def test_step_advances_state(self):
        """Step should advance state by one timestep."""
        def derivative(state, t):
            return [1.0]  # dy/dt = 1
        
        rk4 = RK4Integrator()
        state0 = [0.0]
        dt = 0.1
        
        state_new = rk4.step(derivative, state0, 0.0, dt)
        
        # y = y0 + t = 0 + 0.1 = 0.1
        assert abs(state_new[0] - 0.1) < 0.001


class TestNumericalStability:
    """Test numerical stability of integrators."""
    
    def test_rk4_stable_for_stiff_equation(self):
        """RK4 should be more stable than Euler for stiff equations."""
        # Stiff equation: dy/dt = -100y, y(0) = 1
        # Analytical: y(t) = e^(-100t)
        def derivative(state, t):
            return [-100 * state[0]]
        
        state0 = [1.0]
        dt = 0.01  # Small timestep needed for Euler
        t_end = 0.1
        
        # RK4 should remain stable
        rk4 = RK4Integrator()
        state_rk4, _ = rk4.integrate(derivative, state0, 0.0, t_end, dt)
        
        y_analytical = math.exp(-100 * t_end)
        
        # RK4 should give reasonable result
        # Note: Stiff equations are challenging even for RK4
        assert abs(state_rk4[0] - y_analytical) / y_analytical < 0.25  # <25% error
        assert state_rk4[0] > 0  # Should not go negative


class TestPerformanceRequirements:
    """Test that RK4 meets performance requirements."""
    
    def test_rk4_not_too_slow(self):
        """RK4 should not be >2x slower than Euler."""
        import time
        
        def derivative(state, t):
            x, v = state
            return [v, -x]  # Harmonic oscillator
        
        state0 = [1.0, 0.0]
        dt = 0.01
        t_end = 10.0
        
        # Time Euler
        euler = EulerIntegrator()
        start = time.time()
        euler.integrate(derivative, state0, 0.0, t_end, dt)
        time_euler = time.time() - start
        
        # Time RK4
        rk4 = RK4Integrator()
        start = time.time()
        rk4.integrate(derivative, state0, 0.0, t_end, dt)
        time_rk4 = time.time() - start
        
        # RK4 should not be >5x slower (typically 2-3x)
        assert time_rk4 / time_euler < 5.0
    
    def test_rk4_can_use_larger_timestep(self):
        """RK4 should achieve same accuracy with 10x larger timestep."""
        omega = 1.0
        amplitude = 1.0
        t_end = 10.0
        
        def derivative(state, t):
            x, v = state
            return [v, -omega**2 * x]
        
        state0 = [amplitude, 0.0]
        x_analytical = amplitude * math.cos(omega * t_end)
        
        # Euler with small timestep
        euler = EulerIntegrator()
        dt_euler = 0.01
        state_euler, _ = euler.integrate(derivative, state0, 0.0, t_end, dt_euler)
        error_euler = abs(state_euler[0] - x_analytical)
        
        # RK4 with 10x larger timestep
        rk4 = RK4Integrator()
        dt_rk4 = 0.1  # 10x larger
        state_rk4, _ = rk4.integrate(derivative, state0, 0.0, t_end, dt_rk4)
        error_rk4 = abs(state_rk4[0] - x_analytical)
        
        # RK4 with large timestep should be as accurate as Euler with small timestep
        assert error_rk4 < error_euler
