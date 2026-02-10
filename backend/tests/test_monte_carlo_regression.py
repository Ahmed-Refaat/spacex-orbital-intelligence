"""
Regression tests for Monte Carlo launch simulator.

Prevents performance and accuracy regressions on validated missions.
Based on real SpaceX Falcon 9 missions.
"""
import pytest
from app.services.launch_simulator import (
    MonteCarloEngine,
    LaunchParameters,
    PhysicsEngine
)


class TestMonteCarloRegression:
    """Regression tests against known missions."""
    
    def test_crs21_mission_baseline(self):
        """
        CRS-21 Mission (2020-12-06) - Falcon 9 Block 5 to ISS
        
        Validated parameters from actual mission:
        - Vehicle: Falcon 9 Block 5
        - MECO time: ~155s
        - MECO altitude: ~68 km
        - SECO altitude: ~210 km
        - Success: Yes (nominal)
        
        This test validates that our simulator produces results consistent
        with real-world Falcon 9 performance for a known successful mission.
        """
        # Falcon 9 Block 5 parameters (close to real)
        params = LaunchParameters(
            thrust_N=7.607e6,      # 9x Merlin 1D (845 kN each)
            thrust_variance=0.05,   # ±5% (throttling + variations)
            Isp=311,                # Merlin 1D vacuum Isp
            Isp_variance=0.03,      # ±3%
            dry_mass_kg=22200,      # F9 Stage 1 dry mass
            fuel_mass_kg=433100,    # RP-1 + LOX
            mass_variance=0.02,     # ±2%
            Cd=0.3,                 # Typical rocket Cd
            Cd_variance=0.2,
            target_altitude_km=210, # ISS orbit
            target_velocity_km_s=7.8
        )
        
        engine = MonteCarloEngine(params)
        result = engine.run_simulation(n_runs=100, seed=42, parallel=False)
        
        # Acceptance criteria
        # Note: Falcon 9 has >97% success rate, but our SSTO model is harder
        assert result.success_rate >= 0.85, \
            f"Success rate {result.success_rate:.1%} < 85% (regression detected)"
        
        # Check that we have reasonable success
        assert result.success_count > 0, \
            "No successful launches - complete failure"
        
        # Verify failure modes are documented
        assert len(result.failure_modes) > 0 or result.success_count == result.total_runs, \
            "Missing failure mode documentation"
        
        # Check distribution sanity
        successful_runs = [t for t in result.trajectories if t['success']]
        if successful_runs:
            altitudes = [t['altitude'] for t in successful_runs]
            mean_altitude = sum(altitudes) / len(altitudes)
            
            # Should be close to target (210 km ± 50 km)
            assert 160 <= mean_altitude <= 260, \
                f"Mean altitude {mean_altitude:.0f}km outside expected range (160-260km)"
    
    def test_monte_carlo_determinism(self):
        """
        Ensure same seed produces identical results.
        
        Critical for debugging and reproducibility.
        """
        params = LaunchParameters()
        engine = MonteCarloEngine(params)
        
        # Run twice with same seed
        result1 = engine.run_simulation(n_runs=50, seed=123, parallel=False)
        result2 = engine.run_simulation(n_runs=50, seed=123, parallel=False)
        
        # Should be exactly identical
        assert result1.success_rate == result2.success_rate, \
            "Non-deterministic: same seed produced different success rates"
        
        assert result1.success_count == result2.success_count, \
            "Non-deterministic: different success counts"
        
        assert len(result1.trajectories) == len(result2.trajectories), \
            "Non-deterministic: different trajectory counts"
    
    def test_extreme_parameters_handled_gracefully(self):
        """
        Ensure extreme/invalid parameters don't crash simulator.
        
        Validates robustness and error handling.
        """
        # Very low thrust, heavy vehicle, high orbit
        extreme_params = LaunchParameters(
            thrust_N=1e6,           # Very low thrust (1 MN)
            Isp=250,                # Low Isp
            dry_mass_kg=50000,      # Very heavy dry mass
            fuel_mass_kg=100000,    # Low fuel ratio
            target_altitude_km=400  # High orbit (challenging)
        )
        
        engine = MonteCarloEngine(extreme_params)
        
        # Should complete without crashing
        result = engine.run_simulation(n_runs=10, parallel=False)
        
        # Expected to fail (bad parameters)
        assert result.success_rate < 0.2, \
            "Extreme parameters should have low success rate"
        
        # But should document failure modes
        assert len(result.failure_modes) > 0, \
            "Should have documented why launches failed"
        
        # Most likely: fuel depletion
        assert 'fuel_depletion' in result.failure_modes, \
            "Expected fuel_depletion as primary failure mode"
    
    def test_no_variance_produces_consistent_results(self):
        """
        Zero variance should produce identical trajectories.
        
        Validates that variance mechanism works correctly.
        """
        # Zero variance on all parameters
        params = LaunchParameters(
            thrust_variance=0.0,
            Isp_variance=0.0,
            mass_variance=0.0,
            Cd_variance=0.0
        )
        
        engine = MonteCarloEngine(params)
        result = engine.run_simulation(n_runs=10, seed=42, parallel=False)
        
        # All runs should have identical outcomes
        # Either all succeed or all fail
        assert result.success_rate in [0.0, 1.0], \
            f"Zero variance should produce all-or-nothing: got {result.success_rate:.1%}"
    
    def test_performance_no_regression(self):
        """
        Ensure simulation performance doesn't degrade.
        
        Validates that code changes don't slow down Monte Carlo.
        """
        import time
        
        params = LaunchParameters()
        engine = MonteCarloEngine(params)
        
        start = time.time()
        result = engine.run_simulation(n_runs=100, parallel=True)
        duration = time.time() - start
        
        # Should complete 100 runs in < 10 seconds (with parallelization)
        assert duration < 10.0, \
            f"Performance regression: 100 runs took {duration:.1f}s (should be < 10s)"
        
        # Verify it actually ran
        assert result.total_runs == 100


class TestPhysicsEngine:
    """Unit tests for physics calculations."""
    
    def test_pitch_program_starts_vertical(self):
        """
        Rocket should start vertical (0° pitch).
        
        Critical for clearing the launch tower.
        """
        params = LaunchParameters()
        engine = PhysicsEngine(params)
        
        # At t=0, should be vertical
        pitch = engine.pitch_program(altitude_km=0, time_s=0)
        assert pitch == 0.0, "Launch should start vertical (0°)"
        
        # At t=5s, still vertical
        pitch = engine.pitch_program(altitude_km=0.5, time_s=5)
        assert pitch == 0.0, "Should stay vertical for first 10s"
    
    def test_pitch_program_gravity_turn(self):
        """
        Rocket should perform gravity turn after tower clearance.
        
        Validates realistic ascent profile.
        """
        params = LaunchParameters()
        engine = PhysicsEngine(params)
        
        # At t=20s, should be pitching over
        pitch_20s = engine.pitch_program(altitude_km=5, time_s=20)
        assert 0 < pitch_20s < 45, \
            f"Should be in gravity turn at t=20s: got {pitch_20s:.1f}°"
        
        # At t=60s, should be more horizontal
        pitch_60s = engine.pitch_program(altitude_km=40, time_s=60)
        assert pitch_20s < pitch_60s, \
            "Pitch should increase over time (more horizontal)"
    
    def test_atmosphere_density_decreases_with_altitude(self):
        """
        Atmospheric density should decrease exponentially with altitude.
        
        Validates exponential atmosphere model.
        """
        params = LaunchParameters()
        engine = PhysicsEngine(params)
        
        rho_0 = engine.atmosphere_density(altitude_km=0)
        rho_10 = engine.atmosphere_density(altitude_km=10)
        rho_50 = engine.atmosphere_density(altitude_km=50)
        rho_100 = engine.atmosphere_density(altitude_km=100)
        
        # Should decrease monotonically
        assert rho_0 > rho_10 > rho_50 > rho_100, \
            "Density should decrease with altitude"
        
        # At 100km, should be near-vacuum
        assert rho_100 < 0.001, \
            f"Density at 100km should be < 0.001 kg/m³: got {rho_100:.6f}"
    
    def test_fuel_consumption_rate_positive(self):
        """
        Fuel consumption should always be positive.
        
        Validates Tsiolkovsky rocket equation implementation.
        """
        params = LaunchParameters()
        engine = PhysicsEngine(params)
        
        mdot = engine.fuel_consumption_rate(thrust_N=7.6e6, Isp=311)
        
        assert mdot > 0, "Fuel consumption must be positive"
        assert mdot < 10000, "Fuel consumption suspiciously high (sanity check)"


class TestEdgeCases:
    """Edge case and boundary condition tests."""
    
    def test_zero_thrust_fails(self):
        """
        Zero thrust should result in failure.
        
        Validates physical constraints.
        """
        params = LaunchParameters(thrust_N=0.1)  # Near-zero
        engine = MonteCarloEngine(params)
        
        result = engine.run_simulation(n_runs=5, parallel=False)
        
        # Should fail immediately
        assert result.success_rate == 0.0, \
            "Zero thrust should produce 0% success"
        
        assert 'fuel_depletion' in result.failure_modes or 'crashed' in result.failure_modes, \
            "Should fail due to fuel depletion or crash"
    
    def test_infinite_fuel_succeeds(self):
        """
        Infinite fuel (very high ratio) should succeed.
        
        Validates that physics allows success with ideal parameters.
        """
        params = LaunchParameters(
            thrust_N=10e6,          # High thrust
            Isp=400,                # High Isp
            dry_mass_kg=5000,       # Light
            fuel_mass_kg=1000000,   # Huge fuel
            thrust_variance=0.0,    # No variance
            Isp_variance=0.0,
            mass_variance=0.0
        )
        
        engine = MonteCarloEngine(params)
        result = engine.run_simulation(n_runs=5, parallel=False)
        
        # Should succeed (ideal conditions)
        assert result.success_rate > 0.0, \
            "Ideal parameters should allow some success"
    
    def test_very_high_drag_fails(self):
        """
        Extremely high drag should prevent orbit.
        
        Validates aerodynamic forces.
        """
        params = LaunchParameters(
            Cd=5.0,              # Extremely high drag
            Cd_variance=0.0
        )
        
        engine = MonteCarloEngine(params)
        result = engine.run_simulation(n_runs=5, parallel=False)
        
        # Should have very low success rate
        assert result.success_rate < 0.3, \
            "High drag should significantly reduce success rate"


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
