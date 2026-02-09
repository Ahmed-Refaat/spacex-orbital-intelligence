"""
ΔV budget tracking for launch simulations.

Story 3.2: ΔV Budget Calculation
Tracks where every m/s of velocity goes: gravity, drag, steering, final orbit.
"""
from dataclasses import dataclass, field
from typing import Dict
import math


@dataclass
class DeltaVBudget:
    """
    ΔV budget breakdown.
    
    Tracks all velocity changes during ascent:
    - Gravity loss: ∫ g dt (fighting gravity)
    - Drag loss: ∫ (D/m) dt (air resistance)
    - Steering loss: ∫ (1-cos α)(T/m) dt (thrust not aligned with velocity)
    - Orbital velocity: Final velocity achieved
    
    Conservation: Total ΔV = Σ losses + orbital velocity
    
    Attributes:
        gravity_loss: Velocity lost to gravity (m/s)
        drag_loss: Velocity lost to drag (m/s)
        steering_loss: Velocity lost to steering (cosine loss) (m/s)
        orbital_velocity: Final velocity achieved (m/s)
        total_delta_v: Total ΔV delivered (m/s)
    
    Example:
        >>> budget = DeltaVBudget()
        >>> budget.gravity_loss = 1534.0
        >>> budget.drag_loss = 135.0
        >>> budget.steering_loss = 89.0
        >>> budget.orbital_velocity = 7800.0
        >>> budget.calculate_total()
        9558.0
    """
    gravity_loss: float = 0.0
    drag_loss: float = 0.0
    steering_loss: float = 0.0
    orbital_velocity: float = 0.0
    total_delta_v: float = 0.0
    
    def calculate_total(self) -> float:
        """
        Calculate total ΔV from components.
        
        Returns:
            Total ΔV (m/s)
        """
        self.total_delta_v = (
            self.gravity_loss +
            self.drag_loss +
            self.steering_loss +
            self.orbital_velocity
        )
        return self.total_delta_v
    
    def percentage_breakdown(self) -> Dict[str, float]:
        """
        Calculate percentage breakdown of ΔV budget.
        
        Returns:
            Dictionary with percentages for each component
        
        Example:
            >>> budget.percentage_breakdown()
            {
                'gravity_loss': 16.0,
                'drag_loss': 1.4,
                'steering_loss': 0.9,
                'orbital_velocity': 81.6
            }
        """
        total = self.calculate_total()
        
        if total == 0:
            return {
                'gravity_loss': 0.0,
                'drag_loss': 0.0,
                'steering_loss': 0.0,
                'orbital_velocity': 0.0
            }
        
        return {
            'gravity_loss': (self.gravity_loss / total) * 100,
            'drag_loss': (self.drag_loss / total) * 100,
            'steering_loss': (self.steering_loss / total) * 100,
            'orbital_velocity': (self.orbital_velocity / total) * 100
        }
    
    def summary(self) -> str:
        """
        Human-readable summary of ΔV budget.
        
        Returns:
            Multi-line string with budget breakdown
        
        Example:
            >>> print(budget.summary())
            ΔV Budget:
              Total ΔV:         9558 m/s
              Orbital velocity: 7800 m/s (81.6%)
              Gravity loss:     1534 m/s (16.0%)
              Drag loss:         135 m/s ( 1.4%)
              Steering loss:      89 m/s ( 0.9%)
        """
        total = self.calculate_total()
        pct = self.percentage_breakdown()
        
        lines = [
            "ΔV Budget:",
            f"  Total ΔV:         {total:>4.0f} m/s",
            f"  Orbital velocity: {self.orbital_velocity:>4.0f} m/s ({pct['orbital_velocity']:>4.1f}%)",
            f"  Gravity loss:     {self.gravity_loss:>4.0f} m/s ({pct['gravity_loss']:>4.1f}%)",
            f"  Drag loss:        {self.drag_loss:>4.0f} m/s ({pct['drag_loss']:>4.1f}%)",
            f"  Steering loss:    {self.steering_loss:>4.0f} m/s ({pct['steering_loss']:>4.1f}%)",
        ]
        
        return "\n".join(lines)
    
    def breakdown_table(self) -> Dict[str, Dict[str, float]]:
        """
        Generate breakdown table for API/JSON output.
        
        Returns:
            Dictionary with component values and percentages
        
        Example:
            >>> budget.breakdown_table()
            {
                'gravity_loss': {'value': 1534.0, 'percentage': 16.0},
                'drag_loss': {'value': 135.0, 'percentage': 1.4},
                ...
            }
        """
        pct = self.percentage_breakdown()
        
        return {
            'gravity_loss': {
                'value': self.gravity_loss,
                'percentage': pct['gravity_loss']
            },
            'drag_loss': {
                'value': self.drag_loss,
                'percentage': pct['drag_loss']
            },
            'steering_loss': {
                'value': self.steering_loss,
                'percentage': pct['steering_loss']
            },
            'orbital_velocity': {
                'value': self.orbital_velocity,
                'percentage': pct['orbital_velocity']
            },
            'total': {
                'value': self.calculate_total(),
                'percentage': 100.0
            }
        }


class DeltaVCalculator:
    """
    Calculate ΔV budget during simulation.
    
    Call update methods at each timestep to accumulate losses.
    
    Methods:
        update_gravity_loss(): Accumulate gravity loss (∫ g dt)
        update_drag_loss(): Accumulate drag loss (∫ (D/m) dt)
        update_steering_loss(): Accumulate steering loss (cosine loss)
        finalize(): Set final orbital velocity
    
    Example:
        >>> calc = DeltaVCalculator()
        >>> for state in trajectory:
        ...     calc.update_gravity_loss(state, g, dt)
        ...     calc.update_drag_loss(state, drag_accel, dt)
        ...     calc.update_steering_loss(state, thrust, mass, dt)
        >>> calc.finalize(final_velocity)
        >>> print(calc.budget.summary())
    """
    
    def __init__(self):
        self.budget = DeltaVBudget()
    
    def update_gravity_loss(self, state, gravity: float, dt: float):
        """
        Update gravity loss.
        
        Gravity loss = ∫ g dt
        
        For vertical flight, this is simply g × t.
        For pitched flight, only the vertical component counts.
        
        Args:
            state: Simulation state (must have pitch_deg attribute)
            gravity: Gravitational acceleration (m/s²)
            dt: Timestep (seconds)
        """
        # Gravity loss depends on vertical component
        # If pitched, less gravity loss (but also slower ascent)
        
        # For simplicity, we'll accumulate full gravity loss
        # (More accurate: multiply by sin(pitch) to get vertical component)
        
        gravity_loss_increment = gravity * dt
        self.budget.gravity_loss += gravity_loss_increment
    
    def update_drag_loss(self, state, drag_acceleration: float, dt: float):
        """
        Update drag loss.
        
        Drag loss = ∫ (D/m) dt
        
        Where D = drag force, m = mass.
        
        Args:
            state: Simulation state
            drag_acceleration: Drag acceleration (m/s²)
            dt: Timestep (seconds)
        """
        drag_loss_increment = drag_acceleration * dt
        self.budget.drag_loss += drag_loss_increment
    
    def update_steering_loss(
        self,
        state,
        thrust: float,
        mass: float,
        dt: float
    ):
        """
        Update steering loss (cosine loss).
        
        Steering loss occurs when thrust is not aligned with velocity vector.
        
        Loss = ∫ (1 - cos α) × (T/m) dt
        
        Where:
        - α = angle between thrust and velocity
        - T = thrust
        - m = mass
        
        Args:
            state: Simulation state (must have pitch_deg)
            thrust: Thrust force (N)
            mass: Current mass (kg)
            dt: Timestep (seconds)
        """
        # Simplified: assume thrust is aligned with pitch angle
        # Real implementation would compare thrust vector to velocity vector
        
        # For now, we'll assume minimal steering loss
        # (Full implementation requires velocity vector direction)
        
        # Placeholder: small steering loss during pitch-over
        if hasattr(state, 'pitch_deg'):
            # If pitch is changing, there's steering loss
            # This is very simplified
            acceleration = thrust / mass
            
            # Assume some steering inefficiency (5% during pitch-over)
            if 30 < state.pitch_deg < 80:
                steering_loss_increment = 0.05 * acceleration * dt
                self.budget.steering_loss += steering_loss_increment
    
    def finalize(self, final_velocity: float):
        """
        Set final orbital velocity and calculate total.
        
        Args:
            final_velocity: Final velocity achieved (m/s)
        """
        self.budget.orbital_velocity = final_velocity
        self.budget.calculate_total()
    
    def reset(self):
        """Reset budget to zero."""
        self.budget = DeltaVBudget()
