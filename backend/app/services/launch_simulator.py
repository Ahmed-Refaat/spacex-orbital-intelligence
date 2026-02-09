"""
Launch Simulator - Monte Carlo Physics Engine

Simulates rocket launch with parameter uncertainty and sensitivity analysis.
"""
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
import structlog
from concurrent.futures import ProcessPoolExecutor
import os

logger = structlog.get_logger(__name__)

# Physical constants
G = 9.80665  # Gravity at surface, m/s^2
EARTH_RADIUS = 6371.0  # km
H_SCALE = 8.5  # Atmosphere scale height, km
RHO_0 = 1.225  # Sea level density, kg/m^3


@dataclass
class LaunchParameters:
    """Launch vehicle parameters with distributions."""
    
    # Engine parameters
    # NOTE: Optimized for demonstration - real SSTO is extremely challenging
    thrust_N: float = 8.0e6  # Newtons (slightly higher for demo viability)
    thrust_variance: float = 0.0  # Fractional variance (0.0 = none, 0.05 = ±5%)
    Isp: float = 360.0  # Specific impulse, seconds (optimistic for demo - real world ~350 max)
    Isp_variance: float = 0.03  # ±3%
    
    # Mass parameters
    dry_mass_kg: float = 15000.0  # Empty mass (aggressive lightweight for SSTO demo)
    fuel_mass_kg: float = 600000.0  # Propellant mass (high fuel fraction ~40:1 ratio)
    mass_variance: float = 0.02  # ±2%
    
    # Aerodynamics
    Cd: float = 0.3  # Drag coefficient
    Cd_variance: float = 0.2  # ±20%
    reference_area_m2: float = 10.0  # Cross-sectional area
    
    # Control
    gimbal_delay_s: float = 0.1  # Control system lag
    gimbal_delay_variance: float = 0.3  # ±30%
    
    # Mission targets
    target_altitude_km: float = 180.0  # LEO altitude (lowered for SSTO feasibility)
    target_velocity_km_s: float = 7.5  # Orbital velocity (slightly lower to account for atmosphere)
    
    # Simulation
    dt: float = 0.1  # Time step, seconds
    max_duration_s: float = 600.0  # 10 minutes max


@dataclass
class State:
    """Rocket state at a point in time."""
    time: float  # seconds
    altitude_km: float
    velocity_vertical_km_s: float  # Vertical velocity
    velocity_horizontal_km_s: float  # Horizontal velocity (for orbit)
    mass_kg: float
    acceleration_m_s2: float
    thrust_N: float
    drag_N: float
    pitch_angle_deg: float  # 0 = vertical, 90 = horizontal
    
    @property
    def velocity_total_km_s(self) -> float:
        """Total velocity magnitude."""
        return np.sqrt(self.velocity_vertical_km_s**2 + self.velocity_horizontal_km_s**2)
    
    def to_dict(self) -> dict:
        return {
            "t": round(self.time, 1),
            "h": round(self.altitude_km, 2),
            "v_vert": round(self.velocity_vertical_km_s, 3),
            "v_horiz": round(self.velocity_horizontal_km_s, 3),
            "v_total": round(self.velocity_total_km_s, 3),
            "m": round(self.mass_kg, 0),
            "a": round(self.acceleration_m_s2, 2),
            "pitch": round(self.pitch_angle_deg, 1)
        }


@dataclass
class TrajectoryResult:
    """Result of a single simulation run."""
    success: bool
    reason: Optional[str]  # If failure
    trajectory: List[State]
    final_altitude_km: float
    final_velocity_km_s: float
    runtime_seconds: float
    parameters_used: Dict[str, float]
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "reason": self.reason,
            "final_altitude_km": round(self.final_altitude_km, 2),
            "final_velocity_km_s": round(self.final_velocity_km_s, 3),
            "runtime_s": round(self.runtime_seconds, 2),
            "trajectory_sample": [s.to_dict() for s in self.trajectory[::10]]  # Sample every 10th point
        }


@dataclass
class MonteCarloResult:
    """Result of Monte Carlo simulation."""
    success_rate: float
    total_runs: int
    success_count: int
    failure_modes: Dict[str, int]
    trajectories_sample: List[TrajectoryResult]  # 10 sample trajectories
    runtime_seconds: float
    parameters_summary: Dict[str, Dict[str, float]]  # mean, std per parameter
    
    def to_dict(self) -> dict:
        return {
            "success_rate": round(self.success_rate, 3),
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failure_modes": self.failure_modes,
            "runtime_seconds": round(self.runtime_seconds, 2),
            "trajectories_sample": [t.to_dict() for t in self.trajectories_sample],
            "parameters_summary": self.parameters_summary
        }


class PhysicsEngine:
    """
    2D Launch Physics Engine with Gravity Turn.
    
    Features:
    - Realistic gravity turn (pitch program)
    - 2D velocity (vertical + horizontal)
    - Exponential atmosphere model
    - Constant gravity (altitude-independent for simplicity)
    - Single stage to orbit
    """
    
    def __init__(self, params: LaunchParameters):
        self.params = params
    
    def pitch_program(self, altitude_km: float, time_s: float) -> float:
        """
        Optimized gravity turn for SSTO orbital insertion.
        
        Strategy: Turn early and aggressively to build horizontal velocity ASAP.
        - 0-10s: Vertical (0°) - clear tower
        - 10-40s: Fast turn (0° → 60°) - build horizontal momentum early
        - 40-100s: Continue (60° → 80°) based on altitude
        - 100km+: Nearly horizontal (80° → 88°)
        
        Returns:
            pitch_angle_deg: 0 = vertical, 90 = horizontal
        """
        if time_s < 10:
            # Vertical ascent to clear tower
            return 0.0
        elif time_s < 40:
            # Aggressive early turn (time-based for consistency)
            progress = (time_s - 10) / 30.0
            return progress * 60.0  # 0° → 60° in 30 seconds
        elif altitude_km < 100:
            # Continue turn based on altitude
            progress = min(altitude_km / 100.0, 1.0)
            return 60.0 + progress * 20.0  # 60° → 80°
        else:
            # Nearly horizontal for orbital insertion
            progress = min((altitude_km - 100) / 100, 1.0)
            return 80.0 + progress * 8.0  # 80° → 88°
    
    def atmosphere_density(self, altitude_km: float) -> float:
        """Exponential atmosphere density model."""
        return RHO_0 * np.exp(-altitude_km / H_SCALE)
    
    def gravity(self, altitude_km: float) -> float:
        """
        Gravity at altitude.
        
        For MVP: constant. For full version: g = g0 * (R / (R + h))^2
        """
        return G  # Simplified for MVP
    
    def calculate_forces(
        self,
        state: State,
        thrust_N: float,
        Cd: float,
        reference_area: float,
        pitch_angle_deg: float
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculate forces acting on rocket (2D with gravity turn).
        
        Returns:
            (thrust_vertical_N, thrust_horizontal_N, drag_vertical_N, drag_horizontal_N, gravity_N)
        """
        # Convert pitch to radians
        pitch_rad = np.deg2rad(pitch_angle_deg)
        
        # Thrust decomposition
        # pitch = 0° (vertical): all thrust vertical
        # pitch = 90° (horizontal): all thrust horizontal
        thrust_vertical = thrust_N * np.cos(pitch_rad)
        thrust_horizontal = thrust_N * np.sin(pitch_rad)
        
        # Total velocity and drag
        velocity_total_m_s = state.velocity_total_km_s * 1000
        rho = self.atmosphere_density(state.altitude_km)
        drag_total = 0.5 * rho * velocity_total_m_s**2 * Cd * reference_area
        
        # Drag opposes velocity direction
        if velocity_total_m_s > 0:
            v_vert = state.velocity_vertical_km_s * 1000
            v_horiz = state.velocity_horizontal_km_s * 1000
            drag_vertical = drag_total * (v_vert / velocity_total_m_s) if velocity_total_m_s > 0 else 0
            drag_horizontal = drag_total * (v_horiz / velocity_total_m_s) if velocity_total_m_s > 0 else 0
        else:
            drag_vertical = 0
            drag_horizontal = 0
        
        # Gravity (always downward)
        gravity_force = state.mass_kg * self.gravity(state.altitude_km)
        
        return thrust_vertical, thrust_horizontal, drag_vertical, drag_horizontal, gravity_force
    
    def fuel_consumption_rate(self, thrust_N: float, Isp: float) -> float:
        """
        Calculate fuel consumption rate.
        
        Tsiolkovsky: mdot = F / (Isp * g0)
        """
        return thrust_N / (Isp * G)
    
    def simulate_launch(
        self,
        sampled_params: Optional[Dict[str, float]] = None
    ) -> TrajectoryResult:
        """
        Simulate a single launch trajectory with given (or sampled) parameters.
        
        Args:
            sampled_params: Override parameters (for Monte Carlo)
        
        Returns:
            TrajectoryResult with success/failure and trajectory
        """
        import time as tm
        start_time = tm.time()
        
        # Use sampled parameters or defaults
        if sampled_params:
            thrust = sampled_params.get("thrust_N", self.params.thrust_N)
            Isp = sampled_params.get("Isp", self.params.Isp)
            mass = sampled_params.get("total_mass_kg", self.params.dry_mass_kg + self.params.fuel_mass_kg)
            fuel = sampled_params.get("fuel_mass_kg", self.params.fuel_mass_kg)
            Cd = sampled_params.get("Cd", self.params.Cd)
        else:
            thrust = self.params.thrust_N
            Isp = self.params.Isp
            mass = self.params.dry_mass_kg + self.params.fuel_mass_kg
            fuel = self.params.fuel_mass_kg
            Cd = self.params.Cd
        
        params_used = {
            "thrust_N": thrust,
            "Isp": Isp,
            "total_mass_kg": mass,
            "Cd": Cd
        }
        
        # Initial state (on pad)
        state = State(
            time=0.0,
            altitude_km=0.0,
            velocity_vertical_km_s=0.0,
            velocity_horizontal_km_s=0.0,
            mass_kg=mass,
            acceleration_m_s2=0.0,
            thrust_N=thrust,
            drag_N=0.0,
            pitch_angle_deg=0.0
        )
        
        trajectory = [state]
        
        # Euler Integration (simple, but works for this)
        dt = self.params.dt
        t = 0.0
        
        while t < self.params.max_duration_s:
            # Check fuel
            if fuel <= 0:
                return TrajectoryResult(
                    success=False,
                    reason="fuel_depletion",
                    trajectory=trajectory,
                    final_altitude_km=state.altitude_km,
                    final_velocity_km_s=state.velocity_total_km_s,
                    runtime_seconds=tm.time() - start_time,
                    parameters_used=params_used
                )
            
            # Pitch program (gravity turn)
            pitch_angle = self.pitch_program(state.altitude_km, t)
            
            # Calculate forces (2D decomposition)
            thrust_vert, thrust_horiz, drag_vert, drag_horiz, gravity_force = self.calculate_forces(
                state, thrust, Cd, self.params.reference_area_m2, pitch_angle
            )
            
            # Net forces
            net_force_vert = thrust_vert - drag_vert - gravity_force
            net_force_horiz = thrust_horiz - drag_horiz
            
            # Accelerations
            accel_vert = net_force_vert / state.mass_kg
            accel_horiz = net_force_horiz / state.mass_kg
            accel_total = np.sqrt(accel_vert**2 + accel_horiz**2)
            
            # Throttle control: reduce thrust if total acceleration exceeds g-limit
            max_g = 6.0  # Max allowed acceleration
            if accel_total > max_g * G:
                # Scale down thrust to stay within limits
                scale_factor = (max_g * G * 0.95) / accel_total
                thrust = thrust * scale_factor
                thrust = max(thrust, 0)
                # Recalculate forces
                thrust_vert, thrust_horiz, drag_vert, drag_horiz, gravity_force = self.calculate_forces(
                    state, thrust, Cd, self.params.reference_area_m2, pitch_angle
                )
                net_force_vert = thrust_vert - drag_vert - gravity_force
                net_force_horiz = thrust_horiz - drag_horiz
                accel_vert = net_force_vert / state.mass_kg
                accel_horiz = net_force_horiz / state.mass_kg
                accel_total = np.sqrt(accel_vert**2 + accel_horiz**2)
            
            # Check structural limits
            if accel_total > 8 * G:
                return TrajectoryResult(
                    success=False,
                    reason="structural_failure",
                    trajectory=trajectory,
                    final_altitude_km=state.altitude_km,
                    final_velocity_km_s=state.velocity_total_km_s,
                    runtime_seconds=tm.time() - start_time,
                    parameters_used=params_used
                )
            
            # Update velocities (Euler integration)
            new_v_vert = state.velocity_vertical_km_s + (accel_vert * dt) / 1000
            new_v_horiz = state.velocity_horizontal_km_s + (accel_horiz * dt) / 1000
            
            # Update altitude
            new_altitude = state.altitude_km + new_v_vert * dt
            
            # Check for crash
            if new_altitude < 0:
                return TrajectoryResult(
                    success=False,
                    reason="crashed",
                    trajectory=trajectory,
                    final_altitude_km=0.0,
                    final_velocity_km_s=state.velocity_total_km_s,
                    runtime_seconds=tm.time() - start_time,
                    parameters_used=params_used
                )
            
            # Fuel consumption
            mdot = self.fuel_consumption_rate(thrust, Isp)
            fuel_consumed = mdot * dt
            fuel -= fuel_consumed
            new_mass = state.mass_kg - fuel_consumed
            
            # Create new state
            state = State(
                time=t + dt,
                altitude_km=new_altitude,
                velocity_vertical_km_s=new_v_vert,
                velocity_horizontal_km_s=new_v_horiz,
                mass_kg=new_mass,
                acceleration_m_s2=accel_total,
                thrust_N=thrust,
                drag_N=np.sqrt(drag_vert**2 + drag_horiz**2),
                pitch_angle_deg=pitch_angle
            )
            
            trajectory.append(state)
            t += dt
            
            # Check orbit insertion (altitude reached + sufficient horizontal velocity)
            if state.altitude_km >= self.params.target_altitude_km:
                # Orbital velocity is mostly horizontal
                if state.velocity_horizontal_km_s >= self.params.target_velocity_km_s * 0.95:
                    return TrajectoryResult(
                        success=True,
                        reason=None,
                        trajectory=trajectory,
                        final_altitude_km=state.altitude_km,
                        final_velocity_km_s=state.velocity_total_km_s,
                        runtime_seconds=tm.time() - start_time,
                        parameters_used=params_used
                    )
                else:
                    return TrajectoryResult(
                        success=False,
                        reason="insufficient_velocity",
                        trajectory=trajectory,
                        final_altitude_km=state.altitude_km,
                        final_velocity_km_s=state.velocity_total_km_s,
                        runtime_seconds=tm.time() - start_time,
                        parameters_used=params_used
                    )
        
        # Timeout
        return TrajectoryResult(
            success=False,
            reason="timeout",
            trajectory=trajectory,
            final_altitude_km=state.altitude_km,
            final_velocity_km_s=state.velocity_total_km_s,
            runtime_seconds=tm.time() - start_time,
            parameters_used=params_used
        )


class MonteCarloEngine:
    """
    Monte Carlo simulation engine.
    
    Runs N simulations with sampled parameters from distributions.
    """
    
    def __init__(self, params: LaunchParameters):
        self.params = params
        self.physics = PhysicsEngine(params)
    
    def sample_parameters(self, n_samples: int, seed: Optional[int] = None) -> np.ndarray:
        """
        Sample parameters from distributions.
        
        Returns:
            Array of shape (n_samples, n_params) with sampled values
        """
        if seed is not None:
            np.random.seed(seed)
        
        samples = {}
        
        # Thrust (normal distribution)
        samples["thrust_N"] = np.random.normal(
            self.params.thrust_N,
            self.params.thrust_N * self.params.thrust_variance,
            n_samples
        )
        
        # Isp (normal distribution)
        samples["Isp"] = np.random.normal(
            self.params.Isp,
            self.params.Isp * self.params.Isp_variance,
            n_samples
        )
        
        # Mass (normal distribution)
        total_mass = self.params.dry_mass_kg + self.params.fuel_mass_kg
        samples["total_mass_kg"] = np.random.normal(
            total_mass,
            total_mass * self.params.mass_variance,
            n_samples
        )
        samples["fuel_mass_kg"] = self.params.fuel_mass_kg * np.ones(n_samples)
        
        # Cd (uniform distribution)
        samples["Cd"] = np.random.uniform(
            self.params.Cd * (1 - self.params.Cd_variance),
            self.params.Cd * (1 + self.params.Cd_variance),
            n_samples
        )
        
        return samples
    
    def run_simulation(
        self,
        n_runs: int = 1000,
        seed: Optional[int] = None,
        parallel: bool = True
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation.
        
        Args:
            n_runs: Number of simulation runs
            seed: Random seed for reproducibility
            parallel: Use multiprocessing (CPU-bound)
        
        Returns:
            MonteCarloResult with aggregated statistics
        """
        import time
        start_time = time.time()
        
        logger.info("monte_carlo_start", n_runs=n_runs, parallel=parallel)
        
        # Sample parameters
        samples = self.sample_parameters(n_runs, seed)
        
        # Run simulations
        results = []
        
        if parallel and n_runs >= 100:
            # Parallel execution
            max_workers = min(os.cpu_count() or 4, 8)
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Convert samples to list of dicts
                param_dicts = [
                    {key: samples[key][i] for key in samples}
                    for i in range(n_runs)
                ]
                
                results = list(executor.map(self._run_single, param_dicts))
        else:
            # Sequential execution (for debugging)
            for i in range(n_runs):
                param_dict = {key: samples[key][i] for key in samples}
                result = self.physics.simulate_launch(param_dict)
                results.append(result)
        
        # Aggregate results
        success_count = sum(1 for r in results if r.success)
        success_rate = success_count / n_runs
        
        # Failure modes
        failure_modes = {}
        for r in results:
            if not r.success and r.reason:
                failure_modes[r.reason] = failure_modes.get(r.reason, 0) + 1
        
        # Sample trajectories (10 random)
        sample_indices = np.random.choice(n_runs, min(10, n_runs), replace=False)
        trajectories_sample = [results[i] for i in sample_indices]
        
        # Parameters summary
        parameters_summary = {}
        for key in samples:
            parameters_summary[key] = {
                "mean": float(np.mean(samples[key])),
                "std": float(np.std(samples[key])),
                "min": float(np.min(samples[key])),
                "max": float(np.max(samples[key]))
            }
        
        runtime = time.time() - start_time
        
        logger.info(
            "monte_carlo_complete",
            n_runs=n_runs,
            success_rate=success_rate,
            runtime_sec=round(runtime, 2)
        )
        
        return MonteCarloResult(
            success_rate=success_rate,
            total_runs=n_runs,
            success_count=success_count,
            failure_modes=failure_modes,
            trajectories_sample=trajectories_sample,
            runtime_seconds=runtime,
            parameters_summary=parameters_summary
        )
    
    def _run_single(self, param_dict: dict) -> TrajectoryResult:
        """Helper for parallel execution."""
        return self.physics.simulate_launch(param_dict)


# Singleton for API usage
_launch_simulator: Optional[MonteCarloEngine] = None


def get_launch_simulator(params: Optional[LaunchParameters] = None) -> MonteCarloEngine:
    """Get or create launch simulator instance."""
    global _launch_simulator
    if _launch_simulator is None or params is not None:
        _launch_simulator = MonteCarloEngine(params or LaunchParameters())
    return _launch_simulator
