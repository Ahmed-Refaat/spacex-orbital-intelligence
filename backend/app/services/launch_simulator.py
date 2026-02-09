"""
Launch Simulator - Monte Carlo Engine with 6-DOF Physics

This module implements a probabilistic launch simulator that runs thousands
of simulations to explore parameter sensitivity and identify optimal test strategies.

Architecture:
    PhysicsEngine -> Single trajectory simulation (6-DOF)
    MonteCarloEngine -> N parallel simulations with parameter sampling
    SensitivityAnalyzer -> Sobol indices calculation

Usage:
    >>> engine = MonteCarloEngine()
    >>> result = engine.run_simulation(params, n_runs=10000)
    >>> print(f"Success rate: {result.success_rate:.1%}")
    >>> print(f"Top parameter: {result.sensitivity[0].param}")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Tuple, Callable
from datetime import datetime
import numpy as np
import math
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class State:
    """State vector at a given time during trajectory simulation."""
    time: float  # seconds since launch
    altitude: float  # km above sea level
    velocity: float  # km/s vertical component
    mass: float  # kg total vehicle mass
    acceleration: float  # m/s^2 vertical acceleration
    
    def is_valid(self) -> bool:
        """Check if state is numerically stable."""
        return all(
            not (math.isnan(x) or math.isinf(x))
            for x in [self.altitude, self.velocity, self.mass, self.acceleration]
        )


@dataclass
class TrajectoryResult:
    """Result of a single trajectory simulation."""
    success: bool
    reason: Optional[str] = None  # Failure reason if success=False
    trajectory: List[State] = field(default_factory=list)
    final_altitude: float = 0.0  # km
    final_velocity: float = 0.0  # km/s
    runtime_seconds: float = 0.0
    
    def is_valid(self) -> bool:
        """Check if trajectory is numerically stable."""
        return all(state.is_valid() for state in self.trajectory)


@dataclass
class ParameterDistribution:
    """
    Statistical distribution for a parameter.
    
    Examples:
        >>> # Fixed value
        >>> ParameterDistribution(type='fixed', value=7.5e6)
        
        >>> # Normal distribution
        >>> ParameterDistribution(type='normal', mean=7.5e6, std=0.05*7.5e6)
        
        >>> # Uniform distribution
        >>> ParameterDistribution(type='uniform', min=0.0, max=0.5)
    """
    type: Literal['fixed', 'normal', 'uniform', 'exponential']
    
    # For fixed
    value: Optional[float] = None
    
    # For normal
    mean: Optional[float] = None
    std: Optional[float] = None
    
    # For uniform
    min: Optional[float] = None
    max: Optional[float] = None
    
    # For exponential
    scale: Optional[float] = None
    
    def sample(self, n: int = 1, seed: Optional[int] = None) -> np.ndarray:
        """
        Sample n values from this distribution.
        
        Args:
            n: Number of samples
            seed: Random seed for reproducibility
            
        Returns:
            Array of shape (n,) with sampled values
        """
        rng = np.random.default_rng(seed)
        
        if self.type == 'fixed':
            return np.full(n, self.value)
        
        elif self.type == 'normal':
            return rng.normal(self.mean, self.std, n)
        
        elif self.type == 'uniform':
            return rng.uniform(self.min, self.max, n)
        
        elif self.type == 'exponential':
            return rng.exponential(self.scale, n)
        
        else:
            raise ValueError(f"Unknown distribution type: {self.type}")


@dataclass
class LaunchParameters:
    """
    Launch vehicle parameters with uncertainty distributions.
    
    All parameters can be specified as distributions to explore
    sensitivity to uncertainties.
    """
    # Engine performance
    thrust_N: ParameterDistribution
    Isp: ParameterDistribution  # seconds, specific impulse
    
    # Vehicle mass
    dry_mass_kg: ParameterDistribution
    fuel_mass_kg: ParameterDistribution
    
    # Aerodynamics
    Cd: ParameterDistribution  # drag coefficient
    reference_area_m2: ParameterDistribution
    
    # Control uncertainties
    thrust_variance: ParameterDistribution  # fractional (e.g., 0.05 = ±5%)
    gimbal_delay_s: ParameterDistribution  # control system lag
    
    # Target orbit
    target_altitude_km: float = 200.0
    target_inclination_deg: float = 28.5  # Not used in 2D model yet
    
    # Simulation config
    n_runs: int = 10000
    seed: Optional[int] = None


@dataclass
class SensitivityResult:
    """Sensitivity analysis results (Sobol indices)."""
    param: str
    first_order: float  # Main effect
    total_order: float  # Total effect (includes interactions)
    rank: int  # 1 = most important
    
    @property
    def interaction_effect(self) -> float:
        """Estimate of interaction effects with other parameters."""
        return self.total_order - self.first_order


@dataclass
class MonteCarloResult:
    """Aggregate results from Monte Carlo simulation."""
    sim_id: str
    params: LaunchParameters
    n_runs: int
    runtime_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Aggregate metrics
    success_rate: float = 0.0
    mean_final_altitude_km: float = 0.0
    std_final_altitude_km: float = 0.0
    mean_final_velocity_km_s: float = 0.0
    std_final_velocity_km_s: float = 0.0
    
    # Sensitivity analysis
    sensitivity: List[SensitivityResult] = field(default_factory=list)
    
    # Failure analysis
    failure_modes: Dict[str, int] = field(default_factory=dict)
    
    # Sample trajectories for visualization
    trajectories_sample: List[TrajectoryResult] = field(default_factory=list)
    
    # Quality metrics
    unstable_count: int = 0  # Trajectories with NaN/Inf
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            'sim_id': self.sim_id,
            'n_runs': self.n_runs,
            'runtime_seconds': self.runtime_seconds,
            'timestamp': self.timestamp.isoformat(),
            'success_rate': self.success_rate,
            'mean_final_altitude_km': self.mean_final_altitude_km,
            'std_final_altitude_km': self.std_final_altitude_km,
            'mean_final_velocity_km_s': self.mean_final_velocity_km_s,
            'std_final_velocity_km_s': self.std_final_velocity_km_s,
            'sensitivity': [
                {
                    'param': s.param,
                    'first_order': s.first_order,
                    'total_order': s.total_order,
                    'rank': s.rank
                }
                for s in self.sensitivity
            ],
            'failure_modes': [
                {'mode': mode, 'count': count, 'percentage': count / self.n_runs * 100}
                for mode, count in self.failure_modes.items()
            ],
            'unstable_count': self.unstable_count
        }


# ============================================================================
# Physics Constants
# ============================================================================

class Constants:
    """Physical constants for simulation."""
    EARTH_RADIUS_KM = 6371.0  # km
    G = 9.81  # m/s^2 at surface
    SCALE_HEIGHT_KM = 8.5  # km, atmospheric scale height
    RHO_0 = 1.225  # kg/m^3, sea level air density
    G0 = 9.80665  # m/s^2, standard gravity (for Isp calculation)


# ============================================================================
# Physics Engine
# ============================================================================

class PhysicsEngine:
    """
    Single-trajectory launch simulation with 6-DOF physics (simplified 2D).
    
    Assumptions/Simplifications (MVP):
    - 2D vertical ascent (no pitch program yet)
    - Exponential atmosphere model
    - Constant thrust and Isp during burn
    - No staging (single stage to orbit)
    - No Earth rotation effects
    - No wind
    
    Future (P1):
    - 3D with pitch/yaw control
    - Multi-stage separation
    - Realistic atmosphere (US Standard Atmosphere 1976)
    - Propellant sloshing dynamics
    """
    
    def __init__(self, dt: float = 0.1):
        """
        Initialize physics engine.
        
        Args:
            dt: Time step in seconds (default 0.1s = 100Hz)
        """
        self.dt = dt
        self.max_time = 600  # Max 10 minutes
    
    def simulate_launch(
        self,
        thrust_N: float,
        Isp: float,
        dry_mass_kg: float,
        fuel_mass_kg: float,
        Cd: float,
        reference_area_m2: float,
        thrust_variance: float,
        gimbal_delay_s: float,
        target_altitude_km: float
    ) -> TrajectoryResult:
        """
        Simulate a single launch trajectory.
        
        Args:
            thrust_N: Nominal thrust in Newtons
            Isp: Specific impulse in seconds
            dry_mass_kg: Dry mass (structure) in kg
            fuel_mass_kg: Initial fuel mass in kg
            Cd: Drag coefficient (dimensionless)
            reference_area_m2: Reference area for drag in m^2
            thrust_variance: Fractional thrust variation (e.g., 0.05 = ±5%)
            gimbal_delay_s: Control system lag in seconds
            target_altitude_km: Target final altitude in km
            
        Returns:
            TrajectoryResult with success/failure and trajectory data
        """
        # TODO: Implement in S1.1
        # For now, return mock data
        return TrajectoryResult(
            success=False,
            reason="Not implemented yet - S1.1 in progress"
        )
    
    def _calculate_forces(
        self,
        state: State,
        thrust_N: float,
        Cd: float,
        reference_area_m2: float
    ) -> Tuple[float, float, float]:
        """
        Calculate forces acting on vehicle.
        
        Returns:
            Tuple of (F_thrust, F_drag, F_gravity) in Newtons
        """
        # TODO: Implement in S1.1, S1.3
        pass
    
    def _atmosphere_density(self, altitude_km: float) -> float:
        """
        Atmospheric density using exponential model.
        
        Args:
            altitude_km: Altitude above sea level in km
            
        Returns:
            Air density in kg/m^3
        """
        return Constants.RHO_0 * np.exp(-altitude_km / Constants.SCALE_HEIGHT_KM)
    
    def _gravity(self, altitude_km: float) -> float:
        """
        Gravitational acceleration at altitude.
        
        Args:
            altitude_km: Altitude above sea level in km
            
        Returns:
            Gravity in m/s^2
        """
        r = Constants.EARTH_RADIUS_KM + altitude_km
        return Constants.G * (Constants.EARTH_RADIUS_KM / r) ** 2
    
    def _check_failure(
        self,
        state: State,
        target_altitude_km: float,
        fuel_remaining_kg: float
    ) -> Optional[str]:
        """
        Check for failure conditions.
        
        Returns:
            Failure reason string, or None if no failure
        """
        # TODO: Implement in S1.4
        pass


# ============================================================================
# Monte Carlo Engine
# ============================================================================

class MonteCarloEngine:
    """
    Parallel Monte Carlo simulation runner.
    
    Runs N simulations with parameter sampling and aggregates results.
    """
    
    def __init__(self, physics_engine: Optional[PhysicsEngine] = None):
        """
        Initialize Monte Carlo engine.
        
        Args:
            physics_engine: PhysicsEngine instance (creates new one if None)
        """
        self.physics = physics_engine or PhysicsEngine()
        self.max_workers = min(multiprocessing.cpu_count(), 8)
    
    def run_simulation(
        self,
        params: LaunchParameters,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation with parameter sampling.
        
        Args:
            params: Launch parameters with distributions
            progress_callback: Optional callback(completed, total) for progress updates
            
        Returns:
            MonteCarloResult with aggregated metrics
        """
        # TODO: Implement in S2.2, S2.3
        # For now, return mock data
        import uuid
        return MonteCarloResult(
            sim_id=str(uuid.uuid4()),
            params=params,
            n_runs=params.n_runs,
            runtime_seconds=0.0,
            success_rate=0.0,
            failure_modes={"not_implemented": params.n_runs}
        )
    
    def _sample_parameters(
        self,
        params: LaunchParameters
    ) -> np.ndarray:
        """
        Sample parameters from distributions.
        
        Returns:
            Array of shape (n_runs, n_params) with sampled values
        """
        # TODO: Implement in S2.1
        pass


# ============================================================================
# Sensitivity Analyzer
# ============================================================================

class SensitivityAnalyzer:
    """
    Sensitivity analysis using Sobol indices.
    
    Identifies which parameters have the most impact on success/failure.
    """
    
    def calculate_sobol_indices(
        self,
        param_samples: np.ndarray,
        outcomes: np.ndarray,
        param_names: List[str]
    ) -> List[SensitivityResult]:
        """
        Calculate Sobol sensitivity indices.
        
        Args:
            param_samples: Array of shape (N, D) with parameter samples
            outcomes: Array of shape (N,) with binary outcomes (1=success, 0=failure)
            param_names: List of parameter names
            
        Returns:
            List of SensitivityResult ranked by importance
        """
        # TODO: Implement in S3.1, S3.2
        # For now, return mock data
        return [
            SensitivityResult(
                param="thrust_variance",
                first_order=0.45,
                total_order=0.52,
                rank=1
            )
        ]


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    """Example usage of the launch simulator."""
    
    # Define launch parameters with uncertainty
    params = LaunchParameters(
        thrust_N=ParameterDistribution(type='normal', mean=7.5e6, std=0.05 * 7.5e6),
        Isp=ParameterDistribution(type='normal', mean=310, std=3),
        dry_mass_kg=ParameterDistribution(type='normal', mean=25000, std=500),
        fuel_mass_kg=ParameterDistribution(type='normal', mean=420000, std=2000),
        Cd=ParameterDistribution(type='uniform', min=0.25, max=0.35),
        reference_area_m2=ParameterDistribution(type='fixed', value=20.0),
        thrust_variance=ParameterDistribution(type='uniform', min=0.0, max=0.1),
        gimbal_delay_s=ParameterDistribution(type='exponential', scale=0.1),
        target_altitude_km=200.0,
        n_runs=10000,
        seed=42
    )
    
    # Run simulation
    print("Running Monte Carlo simulation...")
    print(f"  Parameters: {params.n_runs} runs")
    
    engine = MonteCarloEngine()
    result = engine.run_simulation(params)
    
    print(f"\nResults:")
    print(f"  Success rate: {result.success_rate:.1%}")
    print(f"  Mean altitude: {result.mean_final_altitude_km:.1f} km")
    print(f"  Runtime: {result.runtime_seconds:.1f}s")
    
    print(f"\nTop parameters by sensitivity:")
    for s in result.sensitivity[:5]:
        print(f"  {s.rank}. {s.param}: {s.total_order:.2%}")
    
    print(f"\nFailure modes:")
    for mode, count in result.failure_modes.items():
        pct = count / result.n_runs * 100
        print(f"  {mode}: {count} ({pct:.1f}%)")
