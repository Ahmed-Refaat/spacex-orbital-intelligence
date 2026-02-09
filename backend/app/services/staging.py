"""
Staging logic for multi-stage vehicles.

Story 1.2: Staging Logic
Detects and executes stage separations during simulation.
"""
from dataclasses import dataclass
from typing import Optional
from app.models.vehicle import Vehicle, Stage


@dataclass
class SimulationState:
    """Current state of the simulation."""
    time: float  # seconds
    altitude: float  # km
    velocity: float  # km/s
    mass: float  # kg
    active_stage: int  # 1-indexed (which stage is currently burning)
    stage_fuel_remaining: float  # kg (fuel remaining in active stage)


@dataclass
class StagingEvent:
    """
    Event log for a staging occurrence.
    
    Attributes:
        event_type: "staging" (for consistency with other events)
        stage_number: Which stage was separated (1-indexed)
        time: Time of separation (seconds)
        altitude: Altitude at separation (km)
        velocity: Velocity at separation (km/s)
        description: Human-readable description
    """
    event_type: str
    stage_number: int
    time: float
    altitude: float
    velocity: float
    description: str


class StagingController:
    """
    Controls staging detection and execution.
    
    Responsibilities:
    - Detect when a stage should separate (fuel depletion or max burn time)
    - Execute separation (drop mass, activate next stage)
    - Log staging events
    - Handle optional coast phases
    
    Attributes:
        fuel_safety_margin_kg: Stage early if fuel below this (avoid running dry)
        coast_duration_s: Optional coast phase between stages (seconds)
        stage_ignition_time: Time when current stage was ignited
        in_coast_phase: Whether currently coasting between stages
        coast_end_time: When coast phase ends
    """
    
    def __init__(
        self,
        fuel_safety_margin_kg: float = 10.0,
        coast_duration_s: float = 0.0
    ):
        self.fuel_safety_margin_kg = fuel_safety_margin_kg
        self.coast_duration_s = coast_duration_s
        
        # State tracking
        self.stage_ignition_time: float = 0.0
        self.in_coast_phase: bool = False
        self.coast_end_time: float = 0.0
    
    def should_stage(self, state: SimulationState, stage: Stage) -> bool:
        """
        Check if staging should occur.
        
        Staging conditions:
        1. Fuel depleted (or below safety margin)
        2. Max burn time exceeded
        
        Args:
            state: Current simulation state
            stage: Current stage being burned
        
        Returns:
            True if staging should occur, False otherwise
        """
        # Condition 1: Fuel depleted or below safety margin
        if state.stage_fuel_remaining <= self.fuel_safety_margin_kg:
            return True
        
        # Condition 2: Max burn time exceeded
        burn_duration = state.time - self.stage_ignition_time
        if burn_duration >= stage.burn_time_max_s:
            return True
        
        return False
    
    def execute_staging(
        self,
        state: SimulationState,
        vehicle: Vehicle,
        stage_number: int
    ) -> SimulationState:
        """
        Execute stage separation.
        
        Sequence:
        1. Engine cutoff (already happened if called)
        2. Drop spent stage (reduce mass)
        3. Optional coast phase
        4. Activate next stage
        
        Args:
            state: Current simulation state
            vehicle: Vehicle configuration
            stage_number: Stage being separated (1-indexed)
        
        Returns:
            New simulation state after staging
        
        Raises:
            ValueError: If no next stage available
        """
        # Validate there's a next stage
        if stage_number >= vehicle.num_stages:
            raise ValueError(
                f"No next stage available. Stage {stage_number} is the final stage."
            )
        
        # Get the stage being dropped
        spent_stage = vehicle.get_stage(stage_number)
        
        # Drop the spent stage mass (dry mass only, fuel already burned)
        new_mass = state.mass - spent_stage.dry_mass_kg
        
        # Activate next stage
        new_active_stage = stage_number + 1
        
        # Set ignition time for next stage
        # If coast phase, ignition happens after coast
        if self.coast_duration_s > 0:
            self.in_coast_phase = True
            self.coast_end_time = state.time + self.coast_duration_s
            self.stage_ignition_time = self.coast_end_time
        else:
            self.in_coast_phase = False
            self.stage_ignition_time = state.time
        
        # Get next stage and set its fuel
        next_stage = vehicle.get_stage(new_active_stage)
        new_fuel_remaining = next_stage.prop_mass_kg
        
        # Create new state
        # Note: Velocity and altitude unchanged (instantaneous separation)
        new_state = SimulationState(
            time=state.time,
            altitude=state.altitude,
            velocity=state.velocity,  # Momentum conserved
            mass=new_mass,
            active_stage=new_active_stage,
            stage_fuel_remaining=new_fuel_remaining
        )
        
        return new_state
    
    def create_staging_event(
        self,
        state: SimulationState,
        vehicle: Vehicle,
        stage_number: int
    ) -> StagingEvent:
        """
        Create a staging event for logging.
        
        Args:
            state: Current simulation state
            vehicle: Vehicle configuration
            stage_number: Stage being separated (1-indexed)
        
        Returns:
            StagingEvent object
        """
        stage = vehicle.get_stage(stage_number)
        
        description = f"Stage {stage_number} separation ({stage.name})"
        
        event = StagingEvent(
            event_type="staging",
            stage_number=stage_number,
            time=state.time,
            altitude=state.altitude,
            velocity=state.velocity,
            description=description
        )
        
        return event
    
    def is_in_coast_phase(self, current_time: float) -> bool:
        """
        Check if currently in coast phase.
        
        Args:
            current_time: Current simulation time (seconds)
        
        Returns:
            True if coasting, False if actively burning
        """
        if not self.in_coast_phase:
            return False
        
        if current_time >= self.coast_end_time:
            # Coast phase ended
            self.in_coast_phase = False
            return False
        
        return True
    
    def reset_for_new_stage(self, ignition_time: float):
        """
        Reset controller state for a new stage.
        
        Called when starting a new stage burn.
        
        Args:
            ignition_time: Time when new stage ignites (seconds)
        """
        self.stage_ignition_time = ignition_time
        self.in_coast_phase = False
        self.coast_end_time = 0.0
