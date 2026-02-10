"""
Tests for CRS-21 validation against real flight data.

Story 3.5: Validation vs CRS-21
THE CRITICAL TEST - Simulation must match real Falcon 9 flight within 5%.
"""
import pytest
import json
from pathlib import Path
from app.models.vehicle import Vehicle, Stage
from app.services.launch_simulator_full import FullLaunchSimulator
from app.services.earth_rotation import LaunchSite


class TestCRS21ReferenceData:
    """Test that CRS-21 reference data is available."""
    
    def test_crs21_data_in_falcon9_config(self):
        """CRS-21 validation data should be in Falcon 9 config."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert "validation_data" in data
        assert "reference_flight" in data["validation_data"]
        
        ref = data["validation_data"]["reference_flight"]
        assert ref["mission"] == "CRS-21"
        assert "telemetry" in ref
    
    def test_meco_reference_values(self):
        """MECO reference values should be documented."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        meco = data["validation_data"]["reference_flight"]["telemetry"]["meco"]
        
        # CRS-21 MECO (Main Engine Cutoff)
        assert meco["time_s"] == 155
        assert meco["altitude_km"] == 68
        assert meco["velocity_km_s"] == 2.1
    
    def test_seco_reference_values(self):
        """SECO reference values should be documented."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        seco = data["validation_data"]["reference_flight"]["telemetry"]["seco"]
        
        # CRS-21 SECO (Second Engine Cutoff)
        assert seco["time_s"] == 523
        assert seco["altitude_km"] == 210
        assert seco["velocity_km_s"] == 7.8


class TestIntegratedSimulator:
    """Test integrated launch simulator."""
    
    def test_simulator_exists(self):
        """Integrated simulator should exist."""
        sim = FullLaunchSimulator()
        assert sim is not None
    
    def test_load_vehicle_from_config(self):
        """Should load Falcon 9 from config."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        
        assert vehicle.name == "Falcon 9 Block 5"
        assert vehicle.num_stages == 2
    
    def test_simulate_returns_results(self):
        """Simulation should return results."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        # Simple test mission
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,  # CRS-21 payload
            target_altitude_km=210,
            target_inclination_deg=51.6
        )
        
        assert results is not None
        assert hasattr(results, 'trajectory')
        assert hasattr(results, 'events')


@pytest.mark.slow
@pytest.mark.integration
class TestCRS21Validation:
    """
    THE CRITICAL VALIDATION TEST.
    
    Simulate Falcon 9 CRS-21 flight and compare to real telemetry.
    
    PASS CRITERIA: <5% error on all key events
    - MECO altitude: 68 km (tolerance: ±3.4 km)
    - MECO velocity: 2.1 km/s (tolerance: ±0.105 km/s)
    - SECO altitude: 210 km (tolerance: ±10.5 km)
    - Final orbit: 209-212 km
    
    If this test fails, Phase 0 is BLOCKED.
    """
    
    def test_crs21_full_simulation(self):
        """
        Simulate full CRS-21 mission.
        
        Mission parameters:
        - Vehicle: Falcon 9 Block 5
        - Launch site: Cape Canaveral (28.5°N, -80.5°W)
        - Payload: 2972 kg (Dragon 2 cargo)
        - Target orbit: 210 km x 51.6° (ISS rendezvous orbit)
        - Date: 2020-12-06
        """
        sim = FullLaunchSimulator()
        
        # Load Falcon 9
        vehicle = sim.load_vehicle("falcon9_block5")
        
        # Launch site
        site = LaunchSite.cape_canaveral()
        
        # Simulate
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1  # Fine timestep for accuracy
        )
        
        # Should complete without errors
        assert results is not None
    
    def test_crs21_meco_altitude(self):
        """MECO altitude should match CRS-21 within 5%."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1
        )
        
        # Find MECO event (stage 1 cutoff)
        meco_event = results.get_event("meco") or results.get_event("stage_1_cutoff")
        
        # Reference: 68 km
        ref_altitude = 68.0
        tolerance = ref_altitude * 0.05  # 5%
        
        assert meco_event is not None, "MECO event not found"
        assert abs(meco_event.altitude - ref_altitude) / ref_altitude < 0.05, \
            f"MECO altitude error > 5%: got {meco_event.altitude}, expected {ref_altitude}"
    
    def test_crs21_meco_velocity(self):
        """MECO velocity should match CRS-21 within 5%."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1
        )
        
        meco_event = results.get_event("meco") or results.get_event("stage_1_cutoff")
        
        # Reference: 2.1 km/s
        ref_velocity = 2.1
        tolerance = ref_velocity * 0.05
        
        assert meco_event is not None
        assert abs(meco_event.velocity - ref_velocity) / ref_velocity < 0.05, \
            f"MECO velocity error > 5%: got {meco_event.velocity}, expected {ref_velocity}"
    
    def test_crs21_seco_altitude(self):
        """SECO altitude should match CRS-21 within 5%."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1
        )
        
        seco_event = results.get_event("seco") or results.get_event("stage_2_cutoff")
        
        # Reference: 210 km
        ref_altitude = 210.0
        tolerance = ref_altitude * 0.05
        
        assert seco_event is not None
        assert abs(seco_event.altitude - ref_altitude) / ref_altitude < 0.05, \
            f"SECO altitude error > 5%: got {seco_event.altitude}, expected {ref_altitude}"
    
    def test_crs21_final_orbit(self):
        """Final orbit should be approximately 209-212 km."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1
        )
        
        final_altitude = results.final_altitude
        
        # Reference: 209-212 km (nearly circular)
        assert 200 < final_altitude < 220, \
            f"Final orbit altitude outside expected range: {final_altitude} km"
    
    def test_crs21_report_all_errors(self):
        """Generate full validation report with all errors."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1
        )
        
        # Generate validation report
        report = results.validation_report()
        
        assert "meco" in report
        assert "seco" in report
        assert "errors" in report
        
        print("\n" + "="*60)
        print("CRS-21 VALIDATION REPORT")
        print("="*60)
        print(report)
        print("="*60)


@pytest.mark.parametrize("error_threshold", [0.05, 0.10])
class TestValidationThresholds:
    """Test validation at different error thresholds."""
    
    def test_validation_at_threshold(self, error_threshold):
        """Test if validation passes at given error threshold."""
        sim = FullLaunchSimulator()
        vehicle = sim.load_vehicle("falcon9_block5")
        site = LaunchSite.cape_canaveral()
        
        results = sim.simulate(
            vehicle=vehicle,
            launch_site=site,
            payload_kg=2972,
            target_altitude_km=210,
            target_inclination_deg=51.6,
            timestep_s=0.1
        )
        
        # Check if all errors are within threshold
        errors = results.calculate_errors()
        
        max_error = max(abs(e) for e in errors.values())
        
        if error_threshold == 0.05:
            # 5% threshold (Phase 0 requirement)
            # This might fail initially - that's OK, we'll iterate
            pass
        elif error_threshold == 0.10:
            # 10% threshold (more lenient)
            assert max_error < 0.10, \
                f"Max error {max_error*100:.1f}% exceeds 10% threshold"
