"""
Tests for thrust and Isp interpolation with altitude.

Story 1.3: Thrust Profile
Tests realistic thrust/Isp variation from sea level to vacuum.
"""
import pytest
from app.services.thrust_profile import ThrustCalculator, AtmosphereModel
from app.models.vehicle import Stage


class TestAtmosphereModel:
    """Test atmospheric pressure model."""
    
    def test_pressure_at_sea_level(self):
        """Pressure at sea level should be ~101325 Pa."""
        atm = AtmosphereModel()
        pressure = atm.pressure_at_altitude(0.0)
        
        # Standard atmospheric pressure
        assert abs(pressure - 101325) / 101325 < 0.01  # <1% error
    
    def test_pressure_decreases_with_altitude(self):
        """Pressure should decrease with altitude."""
        atm = AtmosphereModel()
        
        p_0 = atm.pressure_at_altitude(0.0)
        p_10 = atm.pressure_at_altitude(10.0)
        p_50 = atm.pressure_at_altitude(50.0)
        p_100 = atm.pressure_at_altitude(100.0)
        
        assert p_0 > p_10 > p_50 > p_100
    
    def test_pressure_near_zero_above_100km(self):
        """Pressure should be near zero above 100 km."""
        atm = AtmosphereModel()
        pressure = atm.pressure_at_altitude(150.0)
        
        # Should be effectively zero (< 1 Pa)
        assert pressure < 1.0
    
    def test_exponential_decay(self):
        """Pressure should decay exponentially (barometric formula)."""
        atm = AtmosphereModel()
        
        # Simplified exponential model: P = P0 * exp(-h/H)
        # where H ~ 8.5 km (scale height)
        p_0 = atm.pressure_at_altitude(0.0)
        p_8_5 = atm.pressure_at_altitude(8.5)
        
        # At scale height, pressure should be ~1/e of sea level
        ratio = p_8_5 / p_0
        expected_ratio = 1.0 / 2.718  # 1/e ≈ 0.368
        
        # Within 20% of theoretical (simplified model)
        assert abs(ratio - expected_ratio) / expected_ratio < 0.2


class TestThrustInterpolation:
    """Test thrust interpolation between sea level and vacuum."""
    
    def test_thrust_at_sea_level(self):
        """At sea level, should use SL thrust."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,  # Falcon 9 S1
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        thrust = calc.effective_thrust(stage, altitude_km=0.0)
        
        # Should be sea level thrust
        assert abs(thrust - stage.thrust_sl_N) / stage.thrust_sl_N < 0.01
    
    def test_thrust_at_vacuum(self):
        """At high altitude (>100 km), should use vacuum thrust."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        thrust = calc.effective_thrust(stage, altitude_km=150.0)
        
        # Should be vacuum thrust
        assert abs(thrust - stage.thrust_vac_N) / stage.thrust_vac_N < 0.01
    
    def test_thrust_increases_with_altitude(self):
        """Thrust should increase as atmospheric pressure decreases."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        
        thrust_0 = calc.effective_thrust(stage, altitude_km=0.0)
        thrust_10 = calc.effective_thrust(stage, altitude_km=10.0)
        thrust_30 = calc.effective_thrust(stage, altitude_km=30.0)
        thrust_50 = calc.effective_thrust(stage, altitude_km=50.0)
        
        # Should increase monotonically (P_vacuum ~100 Pa at ~50 km)
        assert thrust_0 < thrust_10 < thrust_30 < thrust_50
    
    def test_linear_interpolation_at_mid_altitude(self):
        """At mid-altitude, thrust should be between SL and vacuum."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7000000,
            thrust_vac_N=8000000,
            Isp_sl_s=280,
            Isp_vac_s=320,
            burn_time_max_s=150
        )
        
        calc = ThrustCalculator()
        thrust_mid = calc.effective_thrust(stage, altitude_km=30.0)
        
        # Should be between SL and vacuum
        assert stage.thrust_sl_N < thrust_mid < stage.thrust_vac_N
    
    def test_upper_stage_no_sea_level_thrust(self):
        """Upper stage (thrust_sl_N=0) should use vacuum thrust."""
        stage = Stage(
            name="Upper Stage",
            dry_mass_kg=4000,
            prop_mass_kg=107500,
            thrust_sl_N=0,  # No sea level rating
            thrust_vac_N=934000,
            Isp_sl_s=0,
            Isp_vac_s=348,
            burn_time_max_s=397
        )
        
        calc = ThrustCalculator()
        
        # At any altitude, should use vacuum thrust
        thrust_0 = calc.effective_thrust(stage, altitude_km=0.0)
        thrust_100 = calc.effective_thrust(stage, altitude_km=100.0)
        
        assert abs(thrust_0 - stage.thrust_vac_N) / stage.thrust_vac_N < 0.01
        assert abs(thrust_100 - stage.thrust_vac_N) / stage.thrust_vac_N < 0.01


class TestIspInterpolation:
    """Test Isp interpolation between sea level and vacuum."""
    
    def test_isp_at_sea_level(self):
        """At sea level, should use SL Isp."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        isp = calc.effective_isp(stage, altitude_km=0.0)
        
        assert abs(isp - stage.Isp_sl_s) / stage.Isp_sl_s < 0.01
    
    def test_isp_at_vacuum(self):
        """At high altitude, should use vacuum Isp."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        isp = calc.effective_isp(stage, altitude_km=150.0)
        
        assert abs(isp - stage.Isp_vac_s) / stage.Isp_vac_s < 0.01
    
    def test_isp_increases_with_altitude(self):
        """Isp should increase with altitude."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        
        isp_0 = calc.effective_isp(stage, altitude_km=0.0)
        isp_10 = calc.effective_isp(stage, altitude_km=10.0)
        isp_30 = calc.effective_isp(stage, altitude_km=30.0)
        isp_50 = calc.effective_isp(stage, altitude_km=50.0)
        
        assert isp_0 < isp_10 < isp_30 < isp_50
    
    def test_upper_stage_isp(self):
        """Upper stage should use vacuum Isp."""
        stage = Stage(
            name="Upper Stage",
            dry_mass_kg=4000,
            prop_mass_kg=107500,
            thrust_sl_N=0,
            thrust_vac_N=934000,
            Isp_sl_s=0,
            Isp_vac_s=348,
            burn_time_max_s=397
        )
        
        calc = ThrustCalculator()
        isp = calc.effective_isp(stage, altitude_km=0.0)
        
        # Should use vacuum Isp even at sea level
        assert abs(isp - stage.Isp_vac_s) / stage.Isp_vac_s < 0.01


class TestMassFlowRate:
    """Test mass flow rate calculation."""
    
    def test_mass_flow_from_thrust_and_isp(self):
        """Mass flow rate should equal Thrust / (Isp * g0)."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        
        # At sea level
        thrust = stage.thrust_sl_N
        isp = stage.Isp_sl_s
        g0 = 9.80665  # Standard gravity
        
        expected_mdot = thrust / (isp * g0)
        mdot = calc.mass_flow_rate(stage, altitude_km=0.0)
        
        assert abs(mdot - expected_mdot) / expected_mdot < 0.01
    
    def test_mass_flow_decreases_with_altitude(self):
        """Mass flow rate should decrease slightly with altitude (thrust increases, Isp increases more)."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        
        mdot_0 = calc.mass_flow_rate(stage, altitude_km=0.0)
        mdot_100 = calc.mass_flow_rate(stage, altitude_km=100.0)
        
        # Mass flow should be similar but slightly different
        # (For same engine, thrust/Isp ratio changes slightly)
        # Falcon 9: ~2700 kg/s at SL, ~2647 kg/s at vac
        assert mdot_0 > mdot_100
        assert (mdot_0 - mdot_100) / mdot_0 < 0.05  # <5% difference


class TestRealWorldExamples:
    """Test against real vehicle data."""
    
    def test_falcon9_stage1_thrust_profile(self):
        """Falcon 9 Stage 1 thrust profile."""
        stage = Stage(
            name="Falcon 9 Stage 1",
            dry_mass_kg=22200,
            prop_mass_kg=409500,
            thrust_sl_N=7607000,  # 9 Merlin 1D at SL
            thrust_vac_N=8227000,  # 9 Merlin 1D in vacuum
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        calc = ThrustCalculator()
        
        # At MECO (~70 km), thrust should be close to vacuum
        thrust_meco = calc.effective_thrust(stage, altitude_km=70.0)
        
        # Should be >95% of vacuum thrust
        assert thrust_meco / stage.thrust_vac_N > 0.95
    
    def test_falcon9_stage2_always_vacuum(self):
        """Falcon 9 Stage 2 always operates in vacuum conditions."""
        stage = Stage(
            name="Falcon 9 Stage 2",
            dry_mass_kg=4000,
            prop_mass_kg=107500,
            thrust_sl_N=0,  # Not rated for sea level
            thrust_vac_N=934000,  # 1 Merlin Vacuum
            Isp_sl_s=0,
            Isp_vac_s=348,
            burn_time_max_s=397
        )
        
        calc = ThrustCalculator()
        
        # At any altitude (stage 2 ignites >100 km)
        thrust = calc.effective_thrust(stage, altitude_km=200.0)
        isp = calc.effective_isp(stage, altitude_km=200.0)
        
        assert abs(thrust - stage.thrust_vac_N) < 1.0
        assert abs(isp - stage.Isp_vac_s) < 0.1
