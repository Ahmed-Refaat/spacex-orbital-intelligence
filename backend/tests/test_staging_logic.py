"""
Tests for staging logic.

Story 1.2: Staging Logic
Tests detection and execution of stage separations.
"""
import pytest
from dataclasses import dataclass
from app.models.vehicle import Stage, Vehicle
from app.services.staging import StagingController, SimulationState, StagingEvent


@dataclass
class SimulationState:
    """Current state of the simulation."""
    time: float  # seconds
    altitude: float  # km
    velocity: float  # km/s
    mass: float  # kg
    active_stage: int  # 1-indexed
    stage_fuel_remaining: float  # kg


class TestStagingDetection:
    """Test staging detection logic."""
    
    def test_detect_staging_on_fuel_depletion(self):
        """Should detect staging when stage fuel is depleted."""
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
        
        state = SimulationState(
            time=50.0,
            altitude=10.0,
            velocity=0.5,
            mass=10000,
            active_stage=1,
            stage_fuel_remaining=0.0  # Fuel depleted
        )
        
        controller = StagingController()
        should_stage = controller.should_stage(state, stage)
        
        assert should_stage is True
    
    def test_detect_staging_on_max_burn_time(self):
        """Should detect staging when max burn time is exceeded."""
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
        
        state = SimulationState(
            time=101.0,  # Exceeded max burn time
            altitude=20.0,
            velocity=1.0,
            mass=5000,
            active_stage=1,
            stage_fuel_remaining=1000  # Still has fuel
        )
        
        controller = StagingController()
        controller.stage_ignition_time = 0.0  # Stage ignited at t=0
        should_stage = controller.should_stage(state, stage)
        
        assert should_stage is True
    
    def test_no_staging_during_normal_burn(self):
        """Should not stage during normal burn."""
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
        
        state = SimulationState(
            time=50.0,
            altitude=10.0,
            velocity=0.5,
            mass=7000,
            active_stage=1,
            stage_fuel_remaining=5000  # Still has fuel
        )
        
        controller = StagingController()
        controller.stage_ignition_time = 0.0
        should_stage = controller.should_stage(state, stage)
        
        assert should_stage is False
    
    def test_staging_with_safety_margin(self):
        """Should stage with small fuel margin (avoid running dry)."""
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
        
        state = SimulationState(
            time=95.0,
            altitude=15.0,
            velocity=0.8,
            mass=1100,
            active_stage=1,
            stage_fuel_remaining=50  # 50kg remaining (0.5% of total)
        )
        
        controller = StagingController(fuel_safety_margin_kg=100)
        should_stage = controller.should_stage(state, stage)
        
        # Should stage because fuel < safety margin
        assert should_stage is True


class TestStagingExecution:
    """Test staging execution (separation sequence)."""
    
    def test_execute_staging_drops_mass(self):
        """Staging should drop the spent stage mass."""
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
            name="Two Stage Rocket",
            stages=[stage_1, stage_2],
            payload_kg=5000,
            fairing_mass_kg=1000
        )
        
        state = SimulationState(
            time=155.0,
            altitude=70.0,
            velocity=2.0,
            mass=10000 + 20000 + 5000 + 1000,  # Stage 1 dry + Stage 2 + payload + fairing
            active_stage=1,
            stage_fuel_remaining=0.0
        )
        
        controller = StagingController()
        new_state = controller.execute_staging(state, vehicle, stage_number=1)
        
        # Mass should drop by stage 1 dry mass (10000 kg)
        expected_mass = 20000 + 5000 + 1000  # Stage 2 + payload + fairing
        assert abs(new_state.mass - expected_mass) < 1.0
        
        # Active stage should increment
        assert new_state.active_stage == 2
    
    def test_execute_staging_creates_event(self):
        """Staging should create a logged event."""
        stage_1 = Stage(
            name="Booster",
            dry_mass_kg=10000,
            prop_mass_kg=90000,
            thrust_sl_N=1000000,
            thrust_vac_N=1100000,
            Isp_sl_s=280,
            Isp_vac_s=310,
            burn_time_max_s=150
        )
        
        stage_2 = Stage(
            name="Upper Stage",
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
        
        state = SimulationState(
            time=155.0,
            altitude=70.0,
            velocity=2.0,
            mass=36000,
            active_stage=1,
            stage_fuel_remaining=0.0
        )
        
        controller = StagingController()
        event = controller.create_staging_event(state, vehicle, stage_number=1)
        
        assert event.event_type == "staging"
        assert event.stage_number == 1
        assert event.time == 155.0
        assert event.altitude == 70.0
        assert event.velocity == 2.0
        assert "Booster" in event.description
    
    def test_staging_preserves_velocity(self):
        """Staging should not change velocity (instantaneous separation)."""
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
        
        state = SimulationState(
            time=155.0,
            altitude=70.0,
            velocity=2.5,
            mass=36000,
            active_stage=1,
            stage_fuel_remaining=0.0
        )
        
        controller = StagingController()
        new_state = controller.execute_staging(state, vehicle, stage_number=1)
        
        # Velocity should be unchanged (momentum conserved)
        assert new_state.velocity == state.velocity
        
        # Altitude should be unchanged (instantaneous)
        assert new_state.altitude == state.altitude
    
    def test_coast_phase_optional(self):
        """Should support optional coast phase between stages."""
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
        
        state = SimulationState(
            time=155.0,
            altitude=70.0,
            velocity=2.0,
            mass=36000,
            active_stage=1,
            stage_fuel_remaining=0.0
        )
        
        # With coast phase
        controller = StagingController(coast_duration_s=5.0)
        new_state = controller.execute_staging(state, vehicle, stage_number=1)
        
        # Should record coast phase
        assert controller.in_coast_phase is True
        assert controller.coast_end_time == 155.0 + 5.0


class TestMultiStageSequence:
    """Test full multi-stage sequence."""
    
    def test_three_stage_vehicle_sequence(self):
        """Should handle 3 stages in sequence."""
        stages = [
            Stage(
                name=f"Stage {i+1}",
                dry_mass_kg=10000 * (3-i),
                prop_mass_kg=90000 * (3-i),
                thrust_sl_N=1000000 if i == 0 else 0,
                thrust_vac_N=1000000 * (3-i),
                Isp_sl_s=280 if i == 0 else 0,
                Isp_vac_s=310 + i*20,
                burn_time_max_s=150
            )
            for i in range(3)
        ]
        
        vehicle = Vehicle(
            name="Three Stage Rocket",
            stages=stages,
            payload_kg=5000,
            fairing_mass_kg=1000
        )
        
        controller = StagingController()
        
        # Start with all stages
        initial_mass = vehicle.total_mass_kg
        
        # Stage 1 → 2
        state1 = SimulationState(
            time=155.0, altitude=70.0, velocity=2.0,
            mass=initial_mass, active_stage=1, stage_fuel_remaining=0.0
        )
        state2 = controller.execute_staging(state1, vehicle, stage_number=1)
        assert state2.active_stage == 2
        
        # Stage 2 → 3
        state3 = controller.execute_staging(state2, vehicle, stage_number=2)
        assert state3.active_stage == 3
        
        # No more stages
        assert state3.active_stage == vehicle.num_stages
    
    def test_cannot_stage_last_stage(self):
        """Should not stage the last stage (final stage)."""
        stage = Stage(
            name="Final Stage",
            dry_mass_kg=2000,
            prop_mass_kg=18000,
            thrust_sl_N=0,
            thrust_vac_N=200000,
            Isp_sl_s=0,
            Isp_vac_s=340,
            burn_time_max_s=300
        )
        
        vehicle = Vehicle(
            name="Single Stage Rocket",
            stages=[stage],
            payload_kg=5000,
            fairing_mass_kg=1000
        )
        
        state = SimulationState(
            time=300.0,
            altitude=200.0,
            velocity=7.8,
            mass=7000,
            active_stage=1,
            stage_fuel_remaining=0.0
        )
        
        controller = StagingController()
        
        # Should not stage (no next stage)
        should_stage = controller.should_stage(state, stage)
        
        # Implementation should check if there's a next stage
        # For now, we'll allow fuel depletion detection
        # but execution should handle "no next stage" case
        if should_stage:
            with pytest.raises(ValueError, match="No next stage"):
                controller.execute_staging(state, vehicle, stage_number=1)


class TestStagingEvent:
    """Test staging event logging."""
    
    def test_staging_event_fields(self):
        """Staging event should have all required fields."""
        event = StagingEvent(
            event_type="staging",
            stage_number=1,
            time=155.0,
            altitude=70.0,
            velocity=2.0,
            description="Stage 1 separation (Booster)"
        )
        
        assert event.event_type == "staging"
        assert event.stage_number == 1
        assert event.time == 155.0
        assert event.altitude == 70.0
        assert event.velocity == 2.0
        assert "Booster" in event.description
    
    def test_staging_event_serializable(self):
        """Staging event should be JSON-serializable."""
        from dataclasses import asdict
        
        event = StagingEvent(
            event_type="staging",
            stage_number=1,
            time=155.0,
            altitude=70.0,
            velocity=2.0,
            description="Stage separation"
        )
        
        event_dict = asdict(event)
        
        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == "staging"
        assert event_dict["time"] == 155.0
