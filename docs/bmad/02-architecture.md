# Architecture - Launch/Landing Simulator

**Created:** 2026-02-09  
**Status:** Approved

## Overview

Monte-Carlo launch simulator integrated into existing SpaceX Orbital Intelligence platform.

```
┌─────────────────────────────────────────────────────────┐
│              FRONTEND (React + Three.js)                 │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │        SimulationTab Component                  │    │
│  │  ┌──────────────┐  ┌──────────────────────┐   │    │
│  │  │  Parameter   │  │  Results Dashboard   │   │    │
│  │  │  Controls    │  │  - Success rate      │   │    │
│  │  │  - Sliders   │  │  - Sensitivity chart │   │    │
│  │  │  - Distribs  │  │  - Trajectory viz    │   │    │
│  │  └──────────────┘  └──────────────────────┘   │    │
│  └────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────┘
                        │ REST + WebSocket
┌───────────────────────┴─────────────────────────────────┐
│              BACKEND (FastAPI)                           │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  POST /api/v1/simulation/launch                 │    │
│  │  - Receives params + distributions              │    │
│  │  - Validates inputs                             │    │
│  │  - Returns sim_id                               │    │
│  └──────────────────┬──────────────────────────────┘    │
│                     │                                    │
│  ┌─────────────────┴───────────────────────────────┐   │
│  │       SimulationService                          │   │
│  │  ┌────────────────────────────────────────┐    │   │
│  │  │  MonteCarloEngine                       │    │   │
│  │  │  - Run N parallel simulations           │    │   │
│  │  │  - Sample from distributions            │    │   │
│  │  │  - Aggregate results                    │    │   │
│  │  └────────────────────────────────────────┘    │   │
│  │                                                  │   │
│  │  ┌────────────────────────────────────────┐    │   │
│  │  │  PhysicsEngine (6-DOF)                  │    │   │
│  │  │  - Simplified but correct physics       │    │   │
│  │  │  - Atmosphere model (exponential)       │    │   │
│  │  │  - Engine thrust/gimbal                 │    │   │
│  │  │  - Success/failure classification       │    │   │
│  │  └────────────────────────────────────────┘    │   │
│  │                                                  │   │
│  │  ┌────────────────────────────────────────┐    │   │
│  │  │  SensitivityAnalyzer                    │    │   │
│  │  │  - Sobol indices calculation            │    │   │
│  │  │  - Parameter ranking                    │    │   │
│  │  │  - Failure mode clustering              │    │   │
│  │  └────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  WS /ws/simulation/{sim_id}                     │    │
│  │  - Streams progress (10%, 20%, ...)            │    │
│  │  - Sends final results when complete           │    │
│  └────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. PhysicsEngine (Backend)

**Responsibility:** Simulate a single launch trajectory

**Implementation:**
```python
class PhysicsEngine:
    def simulate_launch(
        self,
        params: LaunchParameters,
        dt: float = 0.1  # seconds
    ) -> TrajectoryResult:
        """
        Simulate launch from surface to orbit insertion.
        
        Returns:
            TrajectoryResult with:
            - success: bool
            - reason: str (if failure)
            - trajectory: List[State]
            - final_altitude: float
            - final_velocity: float
        """
```

**Physics Model:**
- **Forces:**
  - Thrust: `F_thrust = thrust_N * (1 + thrust_variance)`
  - Drag: `F_drag = 0.5 * rho * v^2 * Cd * A`
  - Gravity: `F_grav = m * g(altitude)`
- **Atmosphere:** Exponential decay `rho = rho_0 * exp(-h / H)`
- **Integration:** RK4 (Runge-Kutta 4th order)
- **Time step:** 0.1s (100Hz)

**Parameters (configurable):**
| Parameter | Default | Range | Distribution |
|-----------|---------|-------|--------------|
| `thrust_N` | 7.5e6 | ±5% | Normal |
| `thrust_variance` | 0.0 | 0-10% | Uniform |
| `Isp` | 310s | ±3% | Normal |
| `dry_mass_kg` | 25000 | ±2% | Normal |
| `fuel_mass_kg` | 420000 | ±1% | Normal |
| `Cd` | 0.3 | ±20% | Uniform |
| `gimbal_delay_s` | 0.1 | 0-0.5 | Exponential |
| `target_altitude_km` | 200 | - | Fixed |

**Success Criteria:**
- Final altitude > target ± 10 km
- Final velocity > 7.5 km/s (orbital)
- No structural failure (acceleration < 5g)
- Fuel remaining > 5%

### 2. MonteCarloEngine (Backend)

**Responsibility:** Run N simulations with parameter sampling

**Implementation:**
```python
class MonteCarloEngine:
    def run_simulation(
        self,
        params: LaunchParameters,
        n_runs: int = 10000,
        seed: Optional[int] = None
    ) -> MonteCarloResult:
        """
        Run N simulations with sampled parameters.
        
        Returns:
            MonteCarloResult with:
            - success_rate: float
            - trajectories_sample: List[Trajectory] (10 samples)
            - parameter_samples: DataFrame
            - failure_modes: Dict[str, int]
        """
```

**Parallelization:**
- Use `multiprocessing.Pool` (CPU-bound work)
- Chunk size: 100 runs per worker
- Max workers: `min(cpu_count(), 8)`

**Sampling Strategy:**
- Use `scipy.stats` for distributions
- Seed control for reproducibility
- Latin Hypercube Sampling (LHS) for better coverage

### 3. SensitivityAnalyzer (Backend)

**Responsibility:** Identify which parameters matter most

**Implementation:**
```python
class SensitivityAnalyzer:
    def calculate_sobol_indices(
        self,
        results: MonteCarloResult
    ) -> SensitivityResult:
        """
        Calculate Sobol sensitivity indices.
        
        Returns:
            SensitivityResult with:
            - first_order: Dict[param, float]  # Main effects
            - total_order: Dict[param, float]  # Total effects (incl. interactions)
            - rankings: List[Tuple[param, score]]
        """
```

**Method:**
- Use `SALib` (Sensitivity Analysis Library)
- Sobol method (variance-based)
- Requires 2*(D+1)*N samples (D=parameters)
- Rank parameters by Total Order index

### 4. Frontend UI (React)

**Component Structure:**
```tsx
<SimulationTab>
  <LaunchSimulatorCard>
    <ParameterControls />
    <RunButton />
    <ProgressBar />
    <ResultsDashboard>
      <SuccessRateMetric />
      <SensitivityChart />
      <TrajectoryVisualization />
      <FailureBreakdown />
    </ResultsDashboard>
  </LaunchSimulatorCard>
</SimulationTab>
```

**State Management:**
- Use React Query for API calls
- WebSocket hook for live progress
- Zustand for UI state (selected params, etc.)

## Data Models

### LaunchParameters (Request)
```typescript
interface LaunchParameters {
  // Core parameters
  thrust_N: ParameterDistribution
  Isp: ParameterDistribution
  dry_mass_kg: ParameterDistribution
  fuel_mass_kg: ParameterDistribution
  
  // Uncertainties
  thrust_variance: ParameterDistribution
  Cd: ParameterDistribution
  gimbal_delay_s: ParameterDistribution
  
  // Target
  target_altitude_km: number
  target_inclination_deg: number
  
  // Simulation config
  n_runs: number  // 1000-100000
  seed?: number
}

interface ParameterDistribution {
  type: 'fixed' | 'normal' | 'uniform' | 'exponential'
  mean?: number
  std?: number
  min?: number
  max?: number
  value?: number  // for fixed
}
```

### MonteCarloResult (Response)
```typescript
interface MonteCarloResult {
  sim_id: string
  params: LaunchParameters
  n_runs: number
  runtime_seconds: number
  
  // Aggregate metrics
  success_rate: number
  mean_final_altitude_km: number
  std_final_altitude_km: number
  
  // Sensitivity
  sensitivity: {
    param: string
    first_order: number
    total_order: number
    rank: number
  }[]
  
  // Failure analysis
  failure_modes: {
    mode: string  // 'altitude_miss', 'fuel_depletion', 'structural', etc.
    count: number
    percentage: number
  }[]
  
  // Sample trajectories
  trajectories_sample: Trajectory[]  // 10 samples
}

interface Trajectory {
  success: bool
  reason?: string
  states: {
    time: number
    altitude: number
    velocity: number
    acceleration: number
  }[]
}
```

## API Endpoints

### POST /api/v1/simulation/launch
**Request:**
```json
{
  "params": { ... },
  "n_runs": 10000,
  "seed": 42
}
```

**Response:**
```json
{
  "sim_id": "abc123",
  "status": "queued",
  "estimated_time_s": 25
}
```

### WS /ws/simulation/{sim_id}
**Messages:**
```json
// Progress update
{
  "type": "progress",
  "sim_id": "abc123",
  "percent": 45,
  "runs_completed": 4500,
  "runs_total": 10000
}

// Final result
{
  "type": "complete",
  "sim_id": "abc123",
  "result": { ... }  // MonteCarloResult
}

// Error
{
  "type": "error",
  "sim_id": "abc123",
  "error": "Invalid parameters"
}
```

### GET /api/v1/simulation/{sim_id}
**Response:**
```json
{
  "sim_id": "abc123",
  "status": "complete",  // queued | running | complete | failed
  "created_at": "2026-02-09T14:00:00Z",
  "completed_at": "2026-02-09T14:00:25Z",
  "result": { ... }  // MonteCarloResult if complete
}
```

## Technology Choices

### Backend
- **FastAPI** (existing) - async, WebSocket support
- **NumPy** - numerical computation
- **SciPy** - distributions, integration
- **SALib** - Sobol sensitivity analysis
- **multiprocessing** - parallel MC runs
- **Redis** (existing) - cache simulation results (optional)

### Frontend
- **React** (existing)
- **React Query** - API state management
- **Recharts** - sensitivity charts
- **Three.js** (existing) - 3D trajectory visualization

### Performance Targets
- 10,000 runs in <30 seconds
- WebSocket progress updates every 5%
- UI responsiveness <100ms

## Security & Validation

### Input Validation
- Max `n_runs`: 100,000 (prevent DoS)
- Parameter ranges enforced server-side
- Rate limiting: 5 simulations per IP per minute

### Output Validation
- Numerical stability checks (NaN, Inf detection)
- Physical sanity checks (altitude > 0, velocity > 0)
- Log suspicious results for review

## Deployment

### Backend
- Existing FastAPI deployment (Railway/Vercel)
- No additional infrastructure needed
- CPU-only (no GPU required)

### Frontend
- Existing React deployment
- Add new component to SimulationTab
- No breaking changes to existing UI

## Testing Strategy

### Unit Tests
- `PhysicsEngine`: Known trajectory validation
- `MonteCarloEngine`: Seed reproducibility
- `SensitivityAnalyzer`: Sobol index correctness

### Integration Tests
- End-to-end simulation via API
- WebSocket connection & progress updates
- Frontend component rendering

### Performance Tests
- 10K runs benchmark (<30s requirement)
- Memory usage validation (<2GB)
- WebSocket stress test (100 concurrent connections)

## Open Decisions

**Decision 1: 2D vs 3D physics?**
- **Option A:** 2D vertical ascent (fast, simple)
- **Option B:** Full 3D with pitch/yaw control (realistic, complex)
- **Recommendation:** Start 2D, expand to 3D in P1
- **Rationale:** 80% of insights from 2D, 20% effort vs 3D

**Decision 2: Sobol vs Morris for sensitivity?**
- **Option A:** Sobol indices (accurate, slower)
- **Option B:** Morris method (fast, approximate)
- **Recommendation:** Sobol
- **Rationale:** N=10K is enough samples, accuracy matters

**Decision 3: Store simulation history?**
- **Option A:** Store in Redis (24h TTL)
- **Option B:** Ephemeral (no storage)
- **Recommendation:** Redis with 1h TTL
- **Rationale:** Useful for sharing results, minimal cost

---

## References

- [SALib Documentation](https://salib.readthedocs.io/)
- [Sobol Sensitivity Analysis](https://en.wikipedia.org/wiki/Variance-based_sensitivity_analysis)
- [Rocket Equation](https://en.wikipedia.org/wiki/Tsiolkovsky_rocket_equation)
- [Atmospheric Models](https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html)
