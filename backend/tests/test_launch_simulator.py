"""
Unit tests for launch simulator.

Tests are organized by story (S1.1, S1.2, etc.) for easy tracking.

Run tests:
    pytest tests/test_launch_simulator.py -v
    pytest tests/test_launch_simulator.py::test_vertical_ascent -v
    pytest tests/test_launch_simulator.py -k "S1.1" -v
"""

import pytest
import numpy as np
from app.services.launch_simulator import (
    PhysicsEngine,
    MonteCarloEngine,
    SensitivityAnalyzer,
    LaunchParameters,
    ParameterDistribution,
    State,
    TrajectoryResult,
    Constants
)


# ============================================================================
# S1.1: Basic 2D Physics Model
# ============================================================================

class TestS1_1_BasicPhysics:
    """Tests for Story 1.1: Basic 2D Physics Model."""
    
    def test_state_is_valid(self):
        """Test State.is_valid() detects NaN/Inf."""
        # Valid state
        state = State(
            time=0.0,
            altitude=0.0,
            velocity=0.0,
            mass=100000.0,
            acceleration=9.81
        )
        assert state.is_valid()
        
        # Invalid states
        invalid_states = [
            State(0, float('nan'), 0, 100000, 9.81),
            State(0, 0, float('inf'), 100000, 9.81),
            State(0, 0, 0, float('-inf'), 9.81),
        ]
        for s in invalid_states:
            assert not s.is_valid()
    
    def test_atmosphere_density(self):
        """Test exponential atmosphere model."""
        engine = PhysicsEngine()
        
        # Sea level
        rho_0 = engine._atmosphere_density(0.0)
        assert abs(rho_0 - Constants.RHO_0) < 1e-6
        
        # At scale height, density should be 1/e of sea level
        rho_H = engine._atmosphere_density(Constants.SCALE_HEIGHT_KM)
        expected = Constants.RHO_0 / np.e
        assert abs(rho_H - expected) < 0.01
        
        # At high altitude, density should be near zero
        rho_high = engine._atmosphere_density(200.0)
        assert rho_high < 1e-6
    
    def test_gravity_decreases_with_altitude(self):
        """Test gravity decreases correctly with altitude."""
        engine = PhysicsEngine()
        
        # Surface
        g_0 = engine._gravity(0.0)
        assert abs(g_0 - Constants.G) < 0.01
        
        # At 200 km (typical LEO)
        g_200 = engine._gravity(200.0)
        expected = Constants.G * (Constants.EARTH_RADIUS_KM / (Constants.EARTH_RADIUS_KM + 200)) ** 2
        assert abs(g_200 - expected) < 0.01
        
        # Gravity should decrease with altitude
        assert g_200 < g_0
    
    @pytest.mark.skip(reason="S1.1 not implemented yet")
    def test_vertical_ascent_reaches_orbit(self):
        """
        Test that rocket reaches target orbit with nominal parameters.
        
        This is the key validation test for S1.1.
        """
        engine = PhysicsEngine()
        
        # Nominal Falcon 9-like parameters
        result = engine.simulate_launch(
            thrust_N=7.5e6,  # 7.5 MN
            Isp=310,  # seconds
            dry_mass_kg=25000,  # 25 tons
            fuel_mass_kg=420000,  # 420 tons
            Cd=0.3,
            reference_area_m2=20.0,
            thrust_variance=0.0,  # No variance for deterministic test
            gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        # Should succeed
        assert result.success, f"Launch failed: {result.reason}"
        
        # Should reach target altitude (±5% tolerance)
        assert 190 <= result.final_altitude <= 210, \
            f"Altitude {result.final_altitude} km not in range [190, 210] km"
        
        # Should have orbital velocity (>7.5 km/s for LEO)
        assert result.final_velocity > 7.5, \
            f"Velocity {result.final_velocity} km/s too low for orbit"
        
        # Trajectory should be valid (no NaN/Inf)
        assert result.is_valid()
        
        # Should have consumed most fuel
        final_mass = result.trajectory[-1].mass
        assert final_mass < 50000, "Too much fuel remaining"
    
    @pytest.mark.skip(reason="S1.1 not implemented yet")
    def test_trajectory_sampling_rate(self):
        """Test that trajectory is sampled at correct rate."""
        engine = PhysicsEngine(dt=0.1)
        
        result = engine.simulate_launch(
            thrust_N=7.5e6, Isp=310, dry_mass_kg=25000,
            fuel_mass_kg=420000, Cd=0.3, reference_area_m2=20.0,
            thrust_variance=0.0, gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        # Check time steps
        if len(result.trajectory) > 1:
            dt = result.trajectory[1].time - result.trajectory[0].time
            assert abs(dt - 0.1) < 1e-6, f"Time step {dt}s != 0.1s"


# ============================================================================
# S1.2: Engine Model with Thrust Variance
# ============================================================================

class TestS1_2_EngineModel:
    """Tests for Story 1.2: Engine Model with Thrust Variance."""
    
    @pytest.mark.skip(reason="S1.2 not implemented yet")
    def test_thrust_variance_affects_trajectory(self):
        """Test that thrust variance changes trajectory."""
        engine = PhysicsEngine()
        
        # Run with no variance
        result_nominal = engine.simulate_launch(
            thrust_N=7.5e6, Isp=310, dry_mass_kg=25000,
            fuel_mass_kg=420000, Cd=0.3, reference_area_m2=20.0,
            thrust_variance=0.0,
            gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        # Run with high variance
        result_varied = engine.simulate_launch(
            thrust_N=7.5e6, Isp=310, dry_mass_kg=25000,
            fuel_mass_kg=420000, Cd=0.3, reference_area_m2=20.0,
            thrust_variance=0.1,  # ±10%
            gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        # Trajectories should differ
        assert result_nominal.final_altitude != result_varied.final_altitude
    
    @pytest.mark.skip(reason="S1.2 not implemented yet")
    def test_fuel_depletion_triggers_failure(self):
        """Test that running out of fuel causes failure."""
        engine = PhysicsEngine()
        
        # Use very little fuel
        result = engine.simulate_launch(
            thrust_N=7.5e6, Isp=310,
            dry_mass_kg=25000,
            fuel_mass_kg=10000,  # Way too little!
            Cd=0.3, reference_area_m2=20.0,
            thrust_variance=0.0, gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        assert not result.success
        assert "fuel" in result.reason.lower()


# ============================================================================
# S1.3: Drag & Atmosphere Model
# ============================================================================

class TestS1_3_DragModel:
    """Tests for Story 1.3: Drag & Atmosphere Model."""
    
    @pytest.mark.skip(reason="S1.3 not implemented yet")
    def test_drag_reduces_velocity(self):
        """Test that drag force opposes motion."""
        engine = PhysicsEngine()
        
        # High Cd (lots of drag)
        result_high_drag = engine.simulate_launch(
            thrust_N=7.5e6, Isp=310, dry_mass_kg=25000,
            fuel_mass_kg=420000,
            Cd=0.8,  # High drag
            reference_area_m2=20.0,
            thrust_variance=0.0, gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        # Low Cd (little drag)
        result_low_drag = engine.simulate_launch(
            thrust_N=7.5e6, Isp=310, dry_mass_kg=25000,
            fuel_mass_kg=420000,
            Cd=0.1,  # Low drag
            reference_area_m2=20.0,
            thrust_variance=0.0, gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        # High drag should result in lower final velocity
        assert result_high_drag.final_velocity < result_low_drag.final_velocity


# ============================================================================
# S1.4: Success/Failure Classification
# ============================================================================

class TestS1_4_FailureClassification:
    """Tests for Story 1.4: Success/Failure Classification."""
    
    @pytest.mark.skip(reason="S1.4 not implemented yet")
    def test_altitude_miss_failure(self):
        """Test failure when missing target altitude."""
        engine = PhysicsEngine()
        
        # Insufficient thrust to reach target
        result = engine.simulate_launch(
            thrust_N=5e6,  # Too low
            Isp=310, dry_mass_kg=25000, fuel_mass_kg=420000,
            Cd=0.3, reference_area_m2=20.0,
            thrust_variance=0.0, gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        assert not result.success
        assert "altitude" in result.reason.lower()
    
    @pytest.mark.skip(reason="S1.4 not implemented yet")
    def test_structural_failure(self):
        """Test failure when acceleration exceeds structural limits."""
        engine = PhysicsEngine()
        
        # Extreme thrust-to-weight ratio
        result = engine.simulate_launch(
            thrust_N=20e6,  # Way too high
            Isp=310,
            dry_mass_kg=25000,
            fuel_mass_kg=50000,  # Light vehicle
            Cd=0.3, reference_area_m2=20.0,
            thrust_variance=0.0, gimbal_delay_s=0.0,
            target_altitude_km=200.0
        )
        
        assert not result.success
        assert "structural" in result.reason.lower()


# ============================================================================
# S2.1: Parameter Distribution Sampling
# ============================================================================

class TestS2_1_ParameterSampling:
    """Tests for Story 2.1: Parameter Distribution Sampling."""
    
    def test_fixed_distribution(self):
        """Test fixed value distribution."""
        dist = ParameterDistribution(type='fixed', value=100.0)
        samples = dist.sample(n=1000)
        
        assert len(samples) == 1000
        assert np.all(samples == 100.0)
    
    def test_normal_distribution(self):
        """Test normal distribution sampling."""
        dist = ParameterDistribution(type='normal', mean=100.0, std=10.0)
        samples = dist.sample(n=10000, seed=42)
        
        assert len(samples) == 10000
        
        # Check mean and std (should be close for large N)
        assert abs(np.mean(samples) - 100.0) < 1.0
        assert abs(np.std(samples) - 10.0) < 1.0
    
    def test_uniform_distribution(self):
        """Test uniform distribution sampling."""
        dist = ParameterDistribution(type='uniform', min=50.0, max=150.0)
        samples = dist.sample(n=10000, seed=42)
        
        assert len(samples) == 10000
        assert np.all(samples >= 50.0)
        assert np.all(samples <= 150.0)
        
        # Mean should be near midpoint
        assert abs(np.mean(samples) - 100.0) < 5.0
    
    def test_exponential_distribution(self):
        """Test exponential distribution sampling."""
        dist = ParameterDistribution(type='exponential', scale=0.1)
        samples = dist.sample(n=10000, seed=42)
        
        assert len(samples) == 10000
        assert np.all(samples >= 0.0)
        
        # Mean should be near scale
        assert abs(np.mean(samples) - 0.1) < 0.02
    
    def test_seed_reproducibility(self):
        """Test that same seed produces same samples."""
        dist = ParameterDistribution(type='normal', mean=100.0, std=10.0)
        
        samples1 = dist.sample(n=100, seed=42)
        samples2 = dist.sample(n=100, seed=42)
        
        assert np.allclose(samples1, samples2)


# ============================================================================
# S2.2: Parallel Simulation Runner
# ============================================================================

class TestS2_2_MonteCarloEngine:
    """Tests for Story 2.2: Parallel Simulation Runner."""
    
    @pytest.mark.skip(reason="S2.2 not implemented yet")
    def test_monte_carlo_runs_n_simulations(self):
        """Test that Monte Carlo runs correct number of simulations."""
        params = LaunchParameters(
            thrust_N=ParameterDistribution(type='fixed', value=7.5e6),
            Isp=ParameterDistribution(type='fixed', value=310),
            dry_mass_kg=ParameterDistribution(type='fixed', value=25000),
            fuel_mass_kg=ParameterDistribution(type='fixed', value=420000),
            Cd=ParameterDistribution(type='fixed', value=0.3),
            reference_area_m2=ParameterDistribution(type='fixed', value=20.0),
            thrust_variance=ParameterDistribution(type='fixed', value=0.0),
            gimbal_delay_s=ParameterDistribution(type='fixed', value=0.0),
            n_runs=100,
            seed=42
        )
        
        engine = MonteCarloEngine()
        result = engine.run_simulation(params)
        
        assert result.n_runs == 100
        assert result.runtime_seconds > 0
    
    @pytest.mark.skip(reason="S2.2 not implemented yet")
    def test_progress_callback_fires(self):
        """Test that progress callback is called during simulation."""
        params = LaunchParameters(
            thrust_N=ParameterDistribution(type='fixed', value=7.5e6),
            Isp=ParameterDistribution(type='fixed', value=310),
            dry_mass_kg=ParameterDistribution(type='fixed', value=25000),
            fuel_mass_kg=ParameterDistribution(type='fixed', value=420000),
            Cd=ParameterDistribution(type='fixed', value=0.3),
            reference_area_m2=ParameterDistribution(type='fixed', value=20.0),
            thrust_variance=ParameterDistribution(type='fixed', value=0.0),
            gimbal_delay_s=ParameterDistribution(type='fixed', value=0.0),
            n_runs=1000,
            seed=42
        )
        
        progress_calls = []
        
        def callback(completed, total):
            progress_calls.append((completed, total))
        
        engine = MonteCarloEngine()
        result = engine.run_simulation(params, progress_callback=callback)
        
        # Should have received multiple progress updates
        assert len(progress_calls) > 0
        
        # Last call should be 100%
        assert progress_calls[-1] == (1000, 1000)


# ============================================================================
# S3.1: Sobol Sensitivity Analysis
# ============================================================================

class TestS3_1_SensitivityAnalysis:
    """Tests for Story 3.1: SALib Integration."""
    
    @pytest.mark.skip(reason="S3.1 not implemented yet")
    def test_sobol_indices_sum_to_one(self):
        """Test that Sobol indices approximately sum to 1."""
        # Create synthetic data: outcome depends on first param only
        n_samples = 10000
        param_samples = np.random.randn(n_samples, 3)
        outcomes = (param_samples[:, 0] > 0).astype(float)  # First param determines success
        
        analyzer = SensitivityAnalyzer()
        results = analyzer.calculate_sobol_indices(
            param_samples,
            outcomes,
            param_names=['param1', 'param2', 'param3']
        )
        
        # First param should dominate
        param1_result = next(r for r in results if r.param == 'param1')
        assert param1_result.total_order > 0.8  # Should be near 1.0
        
        # Others should be near zero
        other_results = [r for r in results if r.param != 'param1']
        for r in other_results:
            assert r.total_order < 0.2


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance benchmarks (optional, run with -m perf)."""
    
    @pytest.mark.perf
    @pytest.mark.skip(reason="Run manually for performance testing")
    def test_10k_runs_under_30_seconds(self):
        """Test that 10K runs complete in <30s."""
        import time
        
        params = LaunchParameters(
            thrust_N=ParameterDistribution(type='normal', mean=7.5e6, std=0.05*7.5e6),
            Isp=ParameterDistribution(type='normal', mean=310, std=3),
            dry_mass_kg=ParameterDistribution(type='normal', mean=25000, std=500),
            fuel_mass_kg=ParameterDistribution(type='normal', mean=420000, std=2000),
            Cd=ParameterDistribution(type='uniform', min=0.25, max=0.35),
            reference_area_m2=ParameterDistribution(type='fixed', value=20.0),
            thrust_variance=ParameterDistribution(type='uniform', min=0.0, max=0.1),
            gimbal_delay_s=ParameterDistribution(type='exponential', scale=0.1),
            n_runs=10000,
            seed=42
        )
        
        engine = MonteCarloEngine()
        
        start = time.time()
        result = engine.run_simulation(params)
        elapsed = time.time() - start
        
        assert elapsed < 30, f"Simulation took {elapsed:.1f}s (target: <30s)"
        print(f"✓ 10K runs completed in {elapsed:.1f}s")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.skip(reason="E2E not implemented yet")
    def test_full_simulation_pipeline(self):
        """Test complete simulation pipeline: params → MC → sensitivity."""
        # Define parameters
        params = LaunchParameters(
            thrust_N=ParameterDistribution(type='normal', mean=7.5e6, std=0.05*7.5e6),
            Isp=ParameterDistribution(type='normal', mean=310, std=3),
            dry_mass_kg=ParameterDistribution(type='normal', mean=25000, std=500),
            fuel_mass_kg=ParameterDistribution(type='normal', mean=420000, std=2000),
            Cd=ParameterDistribution(type='uniform', min=0.25, max=0.35),
            reference_area_m2=ParameterDistribution(type='fixed', value=20.0),
            thrust_variance=ParameterDistribution(type='uniform', min=0.0, max=0.1),
            gimbal_delay_s=ParameterDistribution(type='exponential', scale=0.1),
            n_runs=1000,  # Smaller for faster testing
            seed=42
        )
        
        # Run simulation
        engine = MonteCarloEngine()
        result = engine.run_simulation(params)
        
        # Validate results
        assert 0 <= result.success_rate <= 1.0
        assert len(result.sensitivity) > 0
        assert result.sensitivity[0].rank == 1  # Top param is rank 1
        assert len(result.trajectories_sample) > 0
        assert sum(result.failure_modes.values()) <= result.n_runs


if __name__ == "__main__":
    """Run tests from command line."""
    pytest.main([__file__, "-v", "--tb=short"])
