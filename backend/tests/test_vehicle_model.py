"""
Tests for multi-stage vehicle model.

Story 1.1: Refactor Vehicle Model
Following TDD: Write tests BEFORE implementation.
"""
import pytest
from app.models.vehicle import Stage, Vehicle


class TestStageModel:
    """Test Stage dataclass."""
    
    def test_stage_creation_with_all_parameters(self):
        """Stage should accept all required parameters."""
        stage = Stage(
            name="First Stage",
            dry_mass_kg=22200,
            prop_mass_kg=409500,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        assert stage.name == "First Stage"
        assert stage.dry_mass_kg == 22200
        assert stage.prop_mass_kg == 409500
        assert stage.thrust_sl_N == 7607000
        assert stage.thrust_vac_N == 8227000
        assert stage.Isp_sl_s == 282
        assert stage.Isp_vac_s == 311
        assert stage.burn_time_max_s == 162
    
    def test_stage_total_mass(self):
        """Stage should calculate total mass correctly."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=1000,
            prop_mass_kg=9000,
            thrust_sl_N=100000,
            thrust_vac_N=110000,
            Isp_sl_s=300,
            Isp_vac_s=320,
            burn_time_max_s=100
        )
        
        assert stage.total_mass_kg == 10000
    
    def test_stage_mass_ratio(self):
        """Stage should calculate mass ratio correctly."""
        stage = Stage(
            name="Test Stage",
            dry_mass_kg=1000,
            prop_mass_kg=9000,
            thrust_sl_N=100000,
            thrust_vac_N=110000,
            Isp_sl_s=300,
            Isp_vac_s=320,
            burn_time_max_s=100
        )
        
        # Mass ratio = (dry + prop) / dry = 10000 / 1000 = 10
        assert stage.mass_ratio == 10.0


class TestVehicleModel:
    """Test Vehicle with multi-stage support."""
    
    def test_single_stage_vehicle(self):
        """Vehicle should support single stage (backwards compatible)."""
        stage = Stage(
            name="Single Stage",
            dry_mass_kg=5000,
            prop_mass_kg=45000,
            thrust_sl_N=500000,
            thrust_vac_N=550000,
            Isp_sl_s=300,
            Isp_vac_s=320,
            burn_time_max_s=200
        )
        
        vehicle = Vehicle(
            name="Single Stage Rocket",
            stages=[stage],
            payload_kg=1000,
            fairing_mass_kg=500
        )
        
        assert vehicle.name == "Single Stage Rocket"
        assert len(vehicle.stages) == 1
        assert vehicle.payload_kg == 1000
        assert vehicle.fairing_mass_kg == 500
    
    def test_two_stage_vehicle(self):
        """Vehicle should support two stages (Falcon 9 style)."""
        stage_1 = Stage(
            name="First Stage",
            dry_mass_kg=22200,
            prop_mass_kg=409500,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        stage_2 = Stage(
            name="Second Stage",
            dry_mass_kg=4000,
            prop_mass_kg=107500,
            thrust_sl_N=0,  # Upper stage, no sea-level thrust
            thrust_vac_N=934000,
            Isp_sl_s=0,
            Isp_vac_s=348,
            burn_time_max_s=397
        )
        
        vehicle = Vehicle(
            name="Falcon 9 Block 5",
            stages=[stage_1, stage_2],
            payload_kg=15000,
            fairing_mass_kg=1750
        )
        
        assert len(vehicle.stages) == 2
        assert vehicle.stages[0].name == "First Stage"
        assert vehicle.stages[1].name == "Second Stage"
    
    def test_three_stage_vehicle(self):
        """Vehicle should support three stages (Saturn V style)."""
        stages = [
            Stage(
                name=f"Stage {i+1}",
                dry_mass_kg=10000 * (3-i),
                prop_mass_kg=100000 * (3-i),
                thrust_sl_N=1000000 if i == 0 else 0,
                thrust_vac_N=1100000,
                Isp_sl_s=280 if i == 0 else 0,
                Isp_vac_s=310 + i*20,
                burn_time_max_s=150
            )
            for i in range(3)
        ]
        
        vehicle = Vehicle(
            name="Saturn V",
            stages=stages,
            payload_kg=50000,
            fairing_mass_kg=5000
        )
        
        assert len(vehicle.stages) == 3
    
    def test_vehicle_total_mass(self):
        """Vehicle should calculate total initial mass correctly."""
        stage_1 = Stage(
            name="Stage 1",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=1000000,
            thrust_vac_N=1100000,
            Isp_sl_s=280,
            Isp_vac_s=310,
            burn_time_max_s=150
        )
        
        stage_2 = Stage(
            name="Stage 2",
            dry_mass_kg=2000,
            prop_mass_kg=18000,
            thrust_sl_N=0,
            thrust_vac_N=200000,
            Isp_sl_s=0,
            Isp_vac_s=340,
            burn_time_max_s=300
        )
        
        vehicle = Vehicle(
            name="Test Rocket",
            stages=[stage_1, stage_2],
            payload_kg=5000,
            fairing_mass_kg=1000
        )
        
        # Total = stage1 (100k) + stage2 (20k) + payload (5k) + fairing (1k) = 126k
        expected_mass = 100000 + 20000 + 5000 + 1000
        assert vehicle.total_mass_kg == expected_mass
    
    def test_vehicle_must_have_at_least_one_stage(self):
        """Vehicle should require at least one stage."""
        with pytest.raises(ValueError, match="at least one stage"):
            Vehicle(
                name="Invalid Rocket",
                stages=[],
                payload_kg=1000,
                fairing_mass_kg=500
            )
    
    def test_vehicle_stages_must_be_ordered(self):
        """Vehicle stages should be in order (stage 1, 2, 3...)."""
        stage_1 = Stage(
            name="First Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=1000000,
            thrust_vac_N=1100000,
            Isp_sl_s=280,
            Isp_vac_s=310,
            burn_time_max_s=150
        )
        
        stage_2 = Stage(
            name="Second Stage",
            dry_mass_kg=2000,
            prop_mass_kg=18000,
            thrust_sl_N=0,
            thrust_vac_N=200000,
            Isp_sl_s=0,
            Isp_vac_s=340,
            burn_time_max_s=300
        )
        
        vehicle = Vehicle(
            name="Test Rocket",
            stages=[stage_1, stage_2],
            payload_kg=1000,
            fairing_mass_kg=500
        )
        
        # Stages should be accessible in order
        assert vehicle.stages[0] == stage_1
        assert vehicle.stages[1] == stage_2


class TestVehicleHelperMethods:
    """Test vehicle helper methods."""
    
    def test_get_stage_by_number(self):
        """Vehicle should retrieve stage by number (1-indexed)."""
        stages = [
            Stage(
                name=f"Stage {i+1}",
                dry_mass_kg=10000,
                prop_mass_kg=90000,
                thrust_sl_N=1000000 if i == 0 else 0,
                thrust_vac_N=1000000,
                Isp_sl_s=280 if i == 0 else 0,
                Isp_vac_s=310,
                burn_time_max_s=150
            )
            for i in range(2)
        ]
        
        vehicle = Vehicle(
            name="Test Rocket",
            stages=stages,
            payload_kg=1000,
            fairing_mass_kg=500
        )
        
        stage_1 = vehicle.get_stage(1)
        stage_2 = vehicle.get_stage(2)
        
        assert stage_1.name == "Stage 1"
        assert stage_2.name == "Stage 2"
    
    def test_get_invalid_stage_number(self):
        """Getting invalid stage number should raise error."""
        stage = Stage(
            name="Only Stage",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=1000000,
            thrust_vac_N=1100000,
            Isp_sl_s=280,
            Isp_vac_s=310,
            burn_time_max_s=150
        )
        
        vehicle = Vehicle(
            name="Single Stage Rocket",
            stages=[stage],
            payload_kg=1000,
            fairing_mass_kg=500
        )
        
        with pytest.raises(IndexError):
            vehicle.get_stage(2)  # Only has 1 stage
    
    def test_vehicle_summary(self):
        """Vehicle should provide human-readable summary."""
        stage_1 = Stage(
            name="Booster",
            dry_mass_kg=22200,
            prop_mass_kg=409500,
            thrust_sl_N=7607000,
            thrust_vac_N=8227000,
            Isp_sl_s=282,
            Isp_vac_s=311,
            burn_time_max_s=162
        )
        
        stage_2 = Stage(
            name="Upper Stage",
            dry_mass_kg=4000,
            prop_mass_kg=107500,
            thrust_sl_N=0,
            thrust_vac_N=934000,
            Isp_sl_s=0,
            Isp_vac_s=348,
            burn_time_max_s=397
        )
        
        vehicle = Vehicle(
            name="Falcon 9",
            stages=[stage_1, stage_2],
            payload_kg=15000,
            fairing_mass_kg=1750
        )
        
        summary = vehicle.summary()
        
        assert "Falcon 9" in summary
        assert "2 stages" in summary
        assert "15.0 t" in summary  # Payload in tons
