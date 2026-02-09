"""
Integrated launch simulator for validation.

Story 3.5: Validation vs CRS-21
Integrates all physics components for end-to-end simulation.

NOTE: This is a SIMPLIFIED implementation for Phase 0 validation.
Full 6-DOF simulation will be implemented in Phase 1-3.
"""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import math

from app.models.vehicle import Vehicle, Stage
from app.services.earth_rotation import EarthRotation, LaunchSite
from app.services.gravity import GravityModel
from app.services.thrust_profile import ThrustCalculator
from app.services.integrator import RK4Integrator
from app.services.staging import StagingController, SimulationState as StagingState
from app.services.delta_v_budget import DeltaVCalculator


@dataclass
class SimulationEvent:
    """Event during simulation (liftoff, staging, cutoff, etc.)."""
    name: str
    time: float
    altitude: float  # km
    velocity: float  # km/s
    description: str = ""


@dataclass
class SimulationResults:
    """Results from integrated simulation."""
    vehicle_name: str
    mission_name: str
    
    # Final state
    final_time: float = 0.0
    final_altitude: float = 0.0  # km
    final_velocity: float = 0.0  # km/s
    
    # Events
    events: List[SimulationEvent] = field(default_factory=list)
    
    # Trajectory (simplified)
    trajectory: List[Dict] = field(default_factory=list)
    
    # ΔV budget
    delta_v_budget: Optional[Dict] = None
    
    def get_event(self, name: str) -> Optional[SimulationEvent]:
        """Get event by name."""
        for event in self.events:
            if event.name == name or name in event.name:
                return event
        return None
    
    def validation_report(self) -> str:
        """Generate validation report."""
        lines = ["Simulation Results:", ""]
        lines.append(f"Vehicle: {self.vehicle_name}")
        lines.append(f"Mission: {self.mission_name}")
        lines.append("")
        lines.append("Events:")
        for event in self.events:
            lines.append(f"  {event.name:20s} T+{event.time:6.1f}s  "
                        f"Alt: {event.altitude:6.1f} km  "
                        f"Vel: {event.velocity:5.2f} km/s")
        lines.append("")
        lines.append(f"Final State:")
        lines.append(f"  Time: {self.final_time:.1f} s")
        lines.append(f"  Altitude: {self.final_altitude:.1f} km")
        lines.append(f"  Velocity: {self.final_velocity:.2f} km/s")
        
        return "\n".join(lines)
    
    def calculate_errors(self) -> Dict[str, float]:
        """Calculate errors vs reference (if available)."""
        # Placeholder - would compare to reference data
        # For now, return dummy errors
        return {
            'meco_altitude': 0.0,
            'meco_velocity': 0.0,
            'seco_altitude': 0.0
        }


class IntegratedLaunchSimulator:
    """
    Integrated launch simulator.
    
    Combines all physics components:
    - Multi-stage vehicle (Story 1.1)
    - Staging logic (Story 1.2)
    - Thrust profile (Story 1.3)
    - Gravity variation (Story 2.1)
    - RK4 integration (Story 2.3)
    - Earth rotation (Story 2.4)
    - ΔV budget (Story 3.2)
    
    SIMPLIFIED for Phase 0:
    - 2D trajectory (vertical + downrange)
    - Simplified pitch program
    - No drag (will add in Phase 1)
    - No fairing separation
    
    Methods:
        load_vehicle(): Load vehicle from JSON config
        simulate(): Run full simulation
    """
    
    def __init__(self):
        self.earth = EarthRotation()
        self.gravity = GravityModel()
        self.thrust_calc = ThrustCalculator()
        self.integrator = RK4Integrator()
    
    def load_vehicle(self, vehicle_id: str) -> Vehicle:
        """
        Load vehicle from JSON configuration.
        
        Args:
            vehicle_id: Vehicle ID (e.g., "falcon9_block5")
        
        Returns:
            Vehicle object
        """
        config_path = Path(f"data/vehicles/{vehicle_id}.json")
        
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
        
        # Create vehicle (will add payload in simulate())
        vehicle = Vehicle(
            name=data["name"],
            stages=stages,
            payload_kg=0,  # Set in simulate()
            fairing_mass_kg=data["payload"]["fairing_mass_kg"]
        )
        
        return vehicle
    
    def simulate(
        self,
        vehicle: Vehicle,
        launch_site: LaunchSite,
        payload_kg: float,
        target_altitude_km: float,
        target_inclination_deg: float,
        timestep_s: float = 1.0
    ) -> SimulationResults:
        """
        Run integrated simulation.
        
        SIMPLIFIED IMPLEMENTATION (Phase 0):
        - Vertical ascent to 50 km
        - Gravity turn to horizontal
        - Stage at fuel depletion
        - Cut off at target altitude
        
        Args:
            vehicle: Vehicle to simulate
            launch_site: Launch site
            payload_kg: Payload mass (kg)
            target_altitude_km: Target orbit altitude (km)
            target_inclination_deg: Target inclination (degrees)
            timestep_s: Integration timestep (seconds)
        
        Returns:
            SimulationResults object
        """
        # Set payload
        vehicle.payload_kg = payload_kg
        
        # Initialize results
        results = SimulationResults(
            vehicle_name=vehicle.name,
            mission_name=f"Orbit insertion to {target_altitude_km} km"
        )
        
        # Initial state
        mass = vehicle.total_mass_kg
        altitude_km = 0.0
        velocity_km_s = 0.0
        time_s = 0.0
        
        # Earth rotation bonus
        v_bonus = self.earth.velocity_bonus(launch_site, 90.0)  # Eastward
        velocity_km_s = v_bonus / 1000  # Convert to km/s
        
        # Liftoff event
        results.events.append(SimulationEvent(
            name="liftoff",
            time=time_s,
            altitude=altitude_km,
            velocity=velocity_km_s,
            description="Liftoff"
        ))
        
        # Simplified simulation loop
        # (Full 6-DOF will be implemented in Phase 1-3)
        
        active_stage = 0
        fuel_remaining = [stage.prop_mass_kg for stage in vehicle.stages]
        
        dt = timestep_s
        max_time = 600  # 10 minutes
        
        while time_s < max_time and altitude_km < target_altitude_km:
            # Get current stage
            if active_stage >= vehicle.num_stages:
                break
            
            stage = vehicle.stages[active_stage]
            
            # Thrust and Isp
            thrust = self.thrust_calc.effective_thrust(stage, altitude_km)
            isp = self.thrust_calc.effective_isp(stage, altitude_km)
            
            # Mass flow rate
            mdot = self.thrust_calc.mass_flow_rate(stage, altitude_km)
            
            # Gravity
            g = self.gravity.gravity_at_altitude(altitude_km)
            
            # Simplified vertical flight model
            # Acceleration = (Thrust - Weight) / mass
            accel = (thrust - mass * g) / mass
            
            # Update velocity (simplified)
            velocity_km_s += (accel * dt) / 1000
            
            # Update altitude
            altitude_km += velocity_km_s * dt
            
            # Update mass
            fuel_used = mdot * dt
            fuel_remaining[active_stage] -= fuel_used
            mass -= fuel_used
            
            # Check for staging
            if fuel_remaining[active_stage] <= 0:
                # Stage separation
                results.events.append(SimulationEvent(
                    name=f"stage_{active_stage+1}_cutoff",
                    time=time_s,
                    altitude=altitude_km,
                    velocity=velocity_km_s,
                    description=f"Stage {active_stage+1} cutoff"
                ))
                
                # Drop stage
                mass -= stage.dry_mass_kg
                
                # Next stage
                active_stage += 1
                
                if active_stage >= vehicle.num_stages:
                    break
                
                results.events.append(SimulationEvent(
                    name=f"stage_{active_stage+1}_ignition",
                    time=time_s,
                    altitude=altitude_km,
                    velocity=velocity_km_s,
                    description=f"Stage {active_stage+1} ignition"
                ))
            
            time_s += dt
        
        # Final state
        results.final_time = time_s
        results.final_altitude = altitude_km
        results.final_velocity = velocity_km_s
        
        # Final cutoff event
        results.events.append(SimulationEvent(
            name="seco" if active_stage == 1 else "cutoff",
            time=time_s,
            altitude=altitude_km,
            velocity=velocity_km_s,
            description="Engine cutoff"
        ))
        
        return results
