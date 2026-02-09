"""
Tests for Falcon 9 Block 5 configuration.

Story 3.1: Falcon 9 Configuration
Tests loading and validation of vehicle configuration from JSON.
"""
import pytest
import json
from pathlib import Path
from app.models.vehicle import Vehicle, Stage


class TestFalcon9ConfigFile:
    """Test Falcon 9 JSON configuration file."""
    
    def test_config_file_exists(self):
        """Falcon 9 config file should exist."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        assert config_path.exists()
    
    def test_config_is_valid_json(self):
        """Config file should be valid JSON."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
    
    def test_config_has_required_fields(self):
        """Config should have all required fields."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        # Top-level fields
        assert "vehicle_id" in data
        assert "name" in data
        assert "manufacturer" in data
        assert "stages" in data
        assert "payload" in data
        
        # Stages
        assert len(data["stages"]) == 2
        
        # Each stage should have required fields
        for stage in data["stages"]:
            assert "stage_number" in stage
            assert "name" in stage
            assert "mass" in stage
            assert "propulsion" in stage


class TestFalcon9Parameters:
    """Test Falcon 9 parameters match known values."""
    
    def test_stage_1_mass(self):
        """Stage 1 mass should match published data."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        stage1 = data["stages"][0]
        
        # From SpaceX user guide
        assert stage1["mass"]["dry_mass_kg"] == 22200
        assert stage1["mass"]["propellant_mass_kg"] == 409500
    
    def test_stage_1_thrust(self):
        """Stage 1 thrust should match published data."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        stage1 = data["stages"][0]
        propulsion = stage1["propulsion"]
        
        # 9 Merlin 1D+ engines
        assert propulsion["engines"] == 9
        assert propulsion["thrust_sea_level_N"] == 7607000
        assert propulsion["thrust_vacuum_N"] == 8227000
    
    def test_stage_1_isp(self):
        """Stage 1 Isp should match published data."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        stage1 = data["stages"][0]
        propulsion = stage1["propulsion"]
        
        assert propulsion["isp_sea_level_s"] == 282
        assert propulsion["isp_vacuum_s"] == 311
    
    def test_stage_2_mass(self):
        """Stage 2 mass should be reasonable."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        stage2 = data["stages"][1]
        
        # Estimated (not publicly disclosed)
        assert stage2["mass"]["dry_mass_kg"] == 4000
        assert stage2["mass"]["propellant_mass_kg"] == 107500
    
    def test_stage_2_mvac_engine(self):
        """Stage 2 should use Merlin Vacuum engine."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        stage2 = data["stages"][1]
        propulsion = stage2["propulsion"]
        
        assert propulsion["engines"] == 1
        assert propulsion["engine_type"] == "Merlin Vacuum (MVac)"
        assert propulsion["thrust_vacuum_N"] == 934000
        assert propulsion["isp_vacuum_s"] == 348
    
    def test_max_payload_leo(self):
        """Max payload to LEO should be 22.8 tons."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert data["payload"]["max_payload"]["leo_kg"] == 22800


class TestFalcon9ToVehicleModel:
    """Test converting JSON config to Vehicle model."""
    
    def test_load_falcon9_as_vehicle(self):
        """Should convert Falcon 9 config to Vehicle object."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        # Create stages
        stages = []
        for stage_data in data["stages"]:
            stage = Stage(
                name=stage_data["name"],
                dry_mass_kg=stage_data["mass"]["dry_mass_kg"],
                prop_mass_kg=stage_data["mass"]["propellant_mass_kg"],
                thrust_sl_N=stage_data["propulsion"]["thrust_sea_level_N"],
                thrust_vac_N=stage_data["propulsion"]["thrust_vacuum_N"],
                Isp_sl_s=stage_data["propulsion"]["isp_sea_level_s"],
                Isp_vac_s=stage_data["propulsion"]["isp_vacuum_s"],
                burn_time_max_s=stage_data["propulsion"]["burn_time_max_s"]
            )
            stages.append(stage)
        
        # Create vehicle
        vehicle = Vehicle(
            name=data["name"],
            stages=stages,
            payload_kg=15000,  # Example payload
            fairing_mass_kg=data["payload"]["fairing_mass_kg"]
        )
        
        assert vehicle.name == "Falcon 9 Block 5"
        assert vehicle.num_stages == 2
        assert vehicle.fairing_mass_kg == 1750
    
    def test_falcon9_mass_budget(self):
        """Falcon 9 total mass should match expected."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        # Calculate total mass
        stage1_mass = data["stages"][0]["mass"]["total_mass_kg"]
        stage2_mass = data["stages"][1]["mass"]["total_mass_kg"]
        fairing_mass = data["payload"]["fairing_mass_kg"]
        payload_mass = 15000  # Example
        
        total_mass = stage1_mass + stage2_mass + fairing_mass + payload_mass
        
        # Should be ~560 tons for 15t payload
        assert 555000 < total_mass < 565000


class TestCRS21ValidationData:
    """Test CRS-21 reference flight data."""
    
    def test_crs21_reference_exists(self):
        """CRS-21 validation data should exist."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert "validation_data" in data
        assert "reference_flight" in data["validation_data"]
        
        ref = data["validation_data"]["reference_flight"]
        assert ref["mission"] == "CRS-21"
    
    def test_crs21_meco_data(self):
        """CRS-21 MECO (Main Engine Cutoff) data should be present."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        meco = data["validation_data"]["reference_flight"]["telemetry"]["meco"]
        
        # MECO at T+2:35, ~68 km, ~2.1 km/s
        assert meco["time_s"] == 155
        assert meco["altitude_km"] == 68
        assert meco["velocity_km_s"] == 2.1
    
    def test_crs21_seco_data(self):
        """CRS-21 SECO (Second Engine Cutoff) data should be present."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        seco = data["validation_data"]["reference_flight"]["telemetry"]["seco"]
        
        # SECO at T+8:43, ~210 km, ~7.8 km/s
        assert seco["time_s"] == 523
        assert seco["altitude_km"] == 210
        assert seco["velocity_km_s"] == 7.8
    
    def test_crs21_final_orbit(self):
        """CRS-21 final orbit should match ISS parameters."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        orbit = data["validation_data"]["reference_flight"]["telemetry"]["final_orbit"]
        
        # ISS orbit: ~410 km, 51.6°
        assert orbit["perigee_km"] == 209
        assert orbit["apogee_km"] == 212
        assert abs(orbit["inclination_deg"] - 51.6) < 0.1


class TestConfigDocumentation:
    """Test that configuration is well-documented."""
    
    def test_sources_documented(self):
        """Sources should be documented."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert "sources" in data
        assert len(data["sources"]) > 0
        
        # Should include SpaceX user guide
        sources_str = " ".join(data["sources"])
        assert "User" in sources_str or "guide" in sources_str.lower()
    
    def test_assumptions_documented(self):
        """Assumptions should be documented."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert "assumptions" in data
        assert len(data["assumptions"]) > 0
    
    def test_version_tracked(self):
        """Config version should be tracked."""
        config_path = Path("data/vehicles/falcon9_block5.json")
        
        with open(config_path) as f:
            data = json.load(f)
        
        assert "version" in data
        assert "last_updated" in data
