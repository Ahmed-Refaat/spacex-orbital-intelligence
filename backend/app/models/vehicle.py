"""
Multi-stage vehicle model.

Story 1.1: Refactor Vehicle Model
Supports 1, 2, or 3+ stage vehicles with realistic parameters.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Stage:
    """
    Single rocket stage with propulsion and mass properties.
    
    Attributes:
        name: Stage identifier (e.g., "First Stage", "Booster")
        dry_mass_kg: Empty mass without propellant (kg)
        prop_mass_kg: Propellant mass (kg)
        thrust_sl_N: Thrust at sea level (N), 0 if upper stage
        thrust_vac_N: Thrust in vacuum (N)
        Isp_sl_s: Specific impulse at sea level (seconds), 0 if upper stage
        Isp_vac_s: Specific impulse in vacuum (seconds)
        burn_time_max_s: Maximum burn time (seconds)
    """
    name: str
    dry_mass_kg: float
    prop_mass_kg: float
    thrust_sl_N: float
    thrust_vac_N: float
    Isp_sl_s: float
    Isp_vac_s: float
    burn_time_max_s: float
    
    @property
    def total_mass_kg(self) -> float:
        """Total stage mass (dry + propellant)."""
        return self.dry_mass_kg + self.prop_mass_kg
    
    @property
    def mass_ratio(self) -> float:
        """
        Stage mass ratio (wet / dry).
        
        Higher is better (more propellant relative to structure).
        Typical values: 10-20 for modern rockets.
        """
        return self.total_mass_kg / self.dry_mass_kg
    
    def __repr__(self) -> str:
        return (
            f"Stage(name='{self.name}', "
            f"mass={self.total_mass_kg/1000:.1f}t, "
            f"Isp_vac={self.Isp_vac_s}s)"
        )


@dataclass
class Vehicle:
    """
    Multi-stage launch vehicle.
    
    Supports 1, 2, or 3+ stages. Stages should be ordered from bottom to top
    (stage 1 = first to ignite/drop, stage N = final stage).
    
    Attributes:
        name: Vehicle name (e.g., "Falcon 9 Block 5")
        stages: List of Stage objects (ordered bottom → top)
        payload_kg: Payload mass (kg)
        fairing_mass_kg: Fairing/shroud mass (kg)
    
    Example:
        >>> stage_1 = Stage("Booster", ...)
        >>> stage_2 = Stage("Upper", ...)
        >>> vehicle = Vehicle("Falcon 9", [stage_1, stage_2], 15000, 1750)
    """
    name: str
    stages: List[Stage]
    payload_kg: float
    fairing_mass_kg: float = 0.0
    
    def __post_init__(self):
        """Validate vehicle configuration."""
        if len(self.stages) < 1:
            raise ValueError("Vehicle must have at least one stage")
        
        if self.payload_kg < 0:
            raise ValueError("Payload mass cannot be negative")
        
        if self.fairing_mass_kg < 0:
            raise ValueError("Fairing mass cannot be negative")
    
    @property
    def total_mass_kg(self) -> float:
        """
        Total vehicle mass at liftoff (all stages + payload + fairing).
        
        This is the "wet mass" - maximum mass including all propellant.
        """
        stage_mass = sum(stage.total_mass_kg for stage in self.stages)
        return stage_mass + self.payload_kg + self.fairing_mass_kg
    
    @property
    def num_stages(self) -> int:
        """Number of stages in vehicle."""
        return len(self.stages)
    
    def get_stage(self, stage_number: int) -> Stage:
        """
        Get stage by number (1-indexed).
        
        Args:
            stage_number: Stage number (1 = first stage, 2 = second, etc.)
        
        Returns:
            Stage object
        
        Raises:
            IndexError: If stage number is invalid
        
        Example:
            >>> vehicle.get_stage(1)  # First stage
            >>> vehicle.get_stage(2)  # Second stage
        """
        if stage_number < 1 or stage_number > len(self.stages):
            raise IndexError(
                f"Invalid stage number {stage_number}. "
                f"Vehicle has {len(self.stages)} stage(s)."
            )
        
        # Convert to 0-indexed
        return self.stages[stage_number - 1]
    
    def summary(self) -> str:
        """
        Human-readable vehicle summary.
        
        Returns:
            Multi-line string with vehicle info
        
        Example:
            >>> print(vehicle.summary())
            Falcon 9 Block 5
            - 2 stages
            - Total mass: 549.5 t
            - Payload: 15.0 t
        """
        lines = [
            f"{self.name}",
            f"- {self.num_stages} stage{'s' if self.num_stages > 1 else ''}",
            f"- Total mass: {self.total_mass_kg / 1000:.1f} t",
            f"- Payload: {self.payload_kg / 1000:.1f} t (payload)",
        ]
        
        if self.fairing_mass_kg > 0:
            lines.append(f"- Fairing: {self.fairing_mass_kg / 1000:.1f} t")
        
        for i, stage in enumerate(self.stages, 1):
            lines.append(
                f"  Stage {i}: {stage.name} "
                f"({stage.total_mass_kg / 1000:.1f} t, "
                f"Isp {stage.Isp_vac_s}s)"
            )
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return (
            f"Vehicle(name='{self.name}', "
            f"stages={self.num_stages}, "
            f"mass={self.total_mass_kg/1000:.1f}t)"
        )
