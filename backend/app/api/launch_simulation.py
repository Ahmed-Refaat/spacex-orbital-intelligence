"""
Launch Simulation API endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from pydantic import BaseModel, Field
import structlog
import uuid

from app.services.launch_simulator import (
    LaunchParameters,
    MonteCarloEngine,
    get_launch_simulator
)
from app.services.cache import cache

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/simulation/launch", tags=["Launch Simulation"])


class LaunchParametersRequest(BaseModel):
    """Request model for launch simulation."""
    
    # Engine
    thrust_N: float = Field(7.5e6, description="Thrust in Newtons")
    thrust_variance: float = Field(0.05, ge=0.0, le=0.5, description="Thrust variance (0-50%)")
    Isp: float = Field(310.0, gt=200, lt=500, description="Specific impulse (seconds)")
    Isp_variance: float = Field(0.03, ge=0.0, le=0.2, description="Isp variance")
    
    # Mass
    dry_mass_kg: float = Field(25000.0, gt=1000, description="Dry mass (kg)")
    fuel_mass_kg: float = Field(420000.0, gt=10000, description="Fuel mass (kg)")
    mass_variance: float = Field(0.02, ge=0.0, le=0.1, description="Mass variance")
    
    # Aerodynamics
    Cd: float = Field(0.3, gt=0.1, lt=2.0, description="Drag coefficient")
    Cd_variance: float = Field(0.2, ge=0.0, le=0.5, description="Cd variance")
    
    # Mission
    target_altitude_km: float = Field(200.0, gt=100, lt=500, description="Target orbit altitude (km)")
    target_velocity_km_s: float = Field(7.8, gt=7.0, lt=12.0, description="Target orbital velocity (km/s)")
    
    # Simulation
    n_runs: int = Field(1000, ge=100, le=10000, description="Number of Monte Carlo runs")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thrust_N": 7500000,
                "thrust_variance": 0.05,
                "Isp": 310,
                "n_runs": 1000
            }
        }


class SimulationResponse(BaseModel):
    """Response model for simulation."""
    sim_id: str
    status: str  # "running", "complete", "failed"
    message: str


class SimulationResult(BaseModel):
    """Simulation results."""
    sim_id: str
    status: str
    success_rate: float
    total_runs: int
    success_count: int
    failure_modes: dict
    trajectories_sample: list
    runtime_seconds: float
    parameters_summary: dict


@router.post("")
async def run_launch_simulation(
    params: LaunchParametersRequest,
    background_tasks: BackgroundTasks
):
    """
    Run Monte Carlo launch simulation.
    
    **Process:**
    1. Validates parameters
    2. Creates simulation ID
    3. Runs simulation in background (or returns immediately for large N)
    4. Returns sim_id to poll results
    
    **Parameters:**
    - thrust_N: Base thrust (Newtons)
    - thrust_variance: Fractional variance (e.g., 0.05 = ±5%)
    - Isp: Specific impulse (seconds)
    - n_runs: Number of Monte Carlo runs (100-10,000)
    
    **Returns:**
    - sim_id: Use to fetch results via GET /{sim_id}
    - status: "running" or "complete"
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/simulation/launch \\
      -H "Content-Type: application/json" \\
      -d '{
        "thrust_N": 7500000,
        "thrust_variance": 0.05,
        "n_runs": 1000
      }'
    ```
    """
    try:
        # Generate simulation ID
        sim_id = str(uuid.uuid4())[:8]
        
        # Create LaunchParameters
        launch_params = LaunchParameters(
            thrust_N=params.thrust_N,
            thrust_variance=params.thrust_variance,
            Isp=params.Isp,
            Isp_variance=params.Isp_variance,
            dry_mass_kg=params.dry_mass_kg,
            fuel_mass_kg=params.fuel_mass_kg,
            mass_variance=params.mass_variance,
            Cd=params.Cd,
            Cd_variance=params.Cd_variance,
            target_altitude_km=params.target_altitude_km,
            target_velocity_km_s=params.target_velocity_km_s
        )
        
        logger.info(
            "launch_simulation_request",
            sim_id=sim_id,
            n_runs=params.n_runs,
            thrust_variance=params.thrust_variance
        )
        
        # For small simulations (<1000 runs), run synchronously
        if params.n_runs <= 1000:
            simulator = MonteCarloEngine(launch_params)
            result = simulator.run_simulation(
                n_runs=params.n_runs,
                seed=params.seed,
                parallel=True
            )
            
            # Build full result dict
            result_dict = {
                "sim_id": sim_id,
                "status": "complete",
                **result.to_dict()
            }
            
            # Cache result
            await cache.set(
                f"launch_sim:{sim_id}",
                result_dict,
                ttl=3600  # 1 hour
            )
            
            # Return full result immediately (not just minimal response)
            return result_dict
        
        else:
            # For large simulations, run in background
            await cache.set(
                f"launch_sim:{sim_id}",
                {"sim_id": sim_id, "status": "running"},
                ttl=3600
            )
            
            # Background task
            background_tasks.add_task(
                _run_simulation_background,
                sim_id,
                launch_params,
                params.n_runs,
                params.seed
            )
            
            return SimulationResponse(
                sim_id=sim_id,
                status="running",
                message=f"Simulation started with {params.n_runs} runs. Poll GET /{sim_id} for results."
            )
    
    except Exception as e:
        logger.error("launch_simulation_error", error=str(e))
        raise HTTPException(500, detail=f"Simulation failed: {str(e)}")


@router.get("/{sim_id}", response_model=SimulationResult)
async def get_simulation_result(sim_id: str):
    """
    Get simulation results by ID.
    
    **Parameters:**
    - sim_id: Simulation ID from POST request
    
    **Returns:**
    - status: "running", "complete", or "failed"
    - success_rate: Fraction of successful launches (if complete)
    - trajectories_sample: Sample trajectories for visualization
    - failure_modes: Breakdown of failure types
    
    **Example:**
    ```bash
    curl http://localhost:8000/api/v1/simulation/launch/abc123
    ```
    """
    cached = await cache.get(f"launch_sim:{sim_id}")
    
    if not cached:
        raise HTTPException(404, detail=f"Simulation {sim_id} not found or expired")
    
    return SimulationResult(**cached)


@router.delete("/{sim_id}")
async def delete_simulation(sim_id: str):
    """
    Delete simulation results.
    
    **Use case:** Clean up after retrieving results
    """
    deleted = await cache.delete(f"launch_sim:{sim_id}")
    
    if deleted:
        return {"message": f"Simulation {sim_id} deleted"}
    else:
        raise HTTPException(404, detail=f"Simulation {sim_id} not found")


async def _run_simulation_background(
    sim_id: str,
    params: LaunchParameters,
    n_runs: int,
    seed: Optional[int]
):
    """Background task to run large simulations."""
    try:
        simulator = MonteCarloEngine(params)
        result = simulator.run_simulation(n_runs=n_runs, seed=seed, parallel=True)
        
        # Update cache with result
        await cache.set(
            f"launch_sim:{sim_id}",
            {
                "sim_id": sim_id,
                "status": "complete",
                **result.to_dict()
            },
            ttl=3600
        )
        
        logger.info("launch_simulation_complete", sim_id=sim_id, success_rate=result.success_rate)
    
    except Exception as e:
        logger.error("launch_simulation_background_error", sim_id=sim_id, error=str(e))
        await cache.set(
            f"launch_sim:{sim_id}",
            {
                "sim_id": sim_id,
                "status": "failed",
                "error": str(e)
            },
            ttl=3600
        )


@router.get("/examples/default")
async def get_default_parameters():
    """
    Get default launch parameters.
    
    **Use case:** Pre-fill UI form with sensible defaults
    """
    params = LaunchParameters()
    return {
        "thrust_N": params.thrust_N,
        "thrust_variance": params.thrust_variance,
        "Isp": params.Isp,
        "Isp_variance": params.Isp_variance,
        "dry_mass_kg": params.dry_mass_kg,
        "fuel_mass_kg": params.fuel_mass_kg,
        "mass_variance": params.mass_variance,
        "Cd": params.Cd,
        "Cd_variance": params.Cd_variance,
        "target_altitude_km": params.target_altitude_km,
        "target_velocity_km_s": params.target_velocity_km_s,
        "n_runs": 1000
    }
