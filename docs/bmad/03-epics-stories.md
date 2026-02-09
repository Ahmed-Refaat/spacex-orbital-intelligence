# Epics & Stories - Launch Simulator

**Created:** 2026-02-09  
**Sprint Duration:** 1 week  
**Total Timeline:** 6 weeks

## Epic Breakdown

| Epic | Stories | Points | Priority | Sprint |
|------|---------|--------|----------|--------|
| E1: Physics Engine | 5 | 21 | P0 | 1-2 |
| E2: Monte Carlo Engine | 4 | 13 | P0 | 2-3 |
| E3: Sensitivity Analysis | 3 | 8 | P0 | 3 |
| E4: API Layer | 4 | 8 | P0 | 3-4 |
| E5: Frontend UI | 6 | 21 | P0 | 4-5 |
| E6: Testing & Docs | 4 | 8 | P0 | 5-6 |
| E7: Polish & Launch | 3 | 5 | P1 | 6-7 |

**Total:** 29 stories, 84 points

---

## Epic 1: Physics Engine (Sprint 1-2)

**Goal:** Build correct, validated 6-DOF launch physics

### S1.1: Basic 2D Physics Model
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Implement State dataclass (position, velocity, acceleration, fuel)
- [ ] Implement forces: thrust, drag, gravity
- [ ] RK4 integration with dt=0.1s
- [ ] Basic atmosphere model (exponential decay)
- [ ] Unit test: vertical ascent reaches expected altitude

**Implementation Notes:**
```python
@dataclass
class State:
    time: float
    altitude: float  # km
    velocity: float  # km/s
    mass: float  # kg
    acceleration: float  # m/s^2
```

**DoD:**
- Code passes mypy strict
- 100% test coverage on physics functions
- Validated against known trajectory (e.g., Falcon 9 flight)

---

### S1.2: Engine Model with Thrust Variance
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Thrust calculation with variance parameter
- [ ] Isp-based fuel consumption
- [ ] Gimbal delay simulation (simple lag)
- [ ] Engine cutoff at fuel depletion
- [ ] Unit test: fuel depletion triggers failure

**Implementation Notes:**
```python
def calculate_thrust(
    base_thrust: float,
    thrust_variance: float,
    Isp: float,
    mass: float
) -> Tuple[float, float]:  # (thrust_N, fuel_rate_kg_s)
```

**DoD:**
- Thrust variance correctly affects trajectory
- Fuel consumption matches Tsiolkovsky equation
- Edge case: zero fuel handled gracefully

---

### S1.3: Drag & Atmosphere Model
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Exponential atmosphere density model
- [ ] Drag force: F = 0.5 * rho * v^2 * Cd * A
- [ ] Cd parameter (configurable)
- [ ] Unit test: drag reduces velocity correctly

**Implementation Notes:**
```python
def atmosphere_density(altitude_km: float) -> float:
    """Exponential atmosphere model."""
    H = 8.5  # scale height, km
    rho_0 = 1.225  # sea level density, kg/m^3
    return rho_0 * np.exp(-altitude_km / H)
```

**DoD:**
- Drag values match NASA standard atmosphere
- Performance: <1ms per step
- No numerical instabilities up to 1000km

---

### S1.4: Success/Failure Classification
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Success criteria configurable
- [ ] Failure modes: altitude_miss, fuel_depletion, structural, timeout
- [ ] Structural failure: acceleration > 5g
- [ ] Return TrajectoryResult with reason
- [ ] Unit tests for each failure mode

**Implementation Notes:**
```python
@dataclass
class TrajectoryResult:
    success: bool
    reason: Optional[str]  # if failure
    trajectory: List[State]
    final_altitude: float
    final_velocity: float
    runtime_seconds: float
```

**DoD:**
- All failure modes tested
- Clear error messages
- Performance: <0.5s per trajectory

---

### S1.5: Validation Against Real Data
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Find public Falcon 9 trajectory data (e.g., CRS-1)
- [ ] Configure parameters to match real launch
- [ ] Simulated trajectory within 10% of real data
- [ ] Document assumptions/simplifications
- [ ] Add as regression test

**Implementation Notes:**
- Use telemetry from SpaceX streams (altitude/velocity plots)
- Compare: max altitude, burnout velocity, MECO time

**DoD:**
- Validation documented in docs/validation.md
- Regression test passes
- Known limitations documented

---

## Epic 2: Monte Carlo Engine (Sprint 2-3)

**Goal:** Run N simulations efficiently with parameter sampling

### S2.1: Parameter Distribution Sampling
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] ParameterDistribution dataclass (type, mean, std, min, max)
- [ ] Sample from normal, uniform, exponential distributions
- [ ] Seed control for reproducibility
- [ ] Unit test: distributions match scipy.stats
- [ ] Latin Hypercube Sampling (LHS) option

**Implementation Notes:**
```python
@dataclass
class ParameterDistribution:
    type: Literal['fixed', 'normal', 'uniform', 'exponential']
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    value: Optional[float] = None  # for fixed
    
    def sample(self, n: int, seed: Optional[int] = None) -> np.ndarray:
        ...
```

**DoD:**
- Supports all 4 distribution types
- Seed reproducibility verified
- LHS gives better coverage than random

---

### S2.2: Parallel Simulation Runner
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Use multiprocessing.Pool for parallelization
- [ ] Chunk size: 100 runs per worker
- [ ] Max workers: min(cpu_count(), 8)
- [ ] Progress callback (for WebSocket updates)
- [ ] Handle worker crashes gracefully

**Implementation Notes:**
```python
class MonteCarloEngine:
    def run_simulation(
        self,
        params: LaunchParameters,
        n_runs: int = 10000,
        progress_callback: Optional[Callable] = None
    ) -> MonteCarloResult:
        ...
```

**DoD:**
- 10K runs in <30s (tested on production server)
- No memory leaks
- Progress updates every 5%

---

### S2.3: Result Aggregation
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Calculate success_rate
- [ ] Calculate mean/std of final altitude, velocity
- [ ] Group failure modes with counts
- [ ] Sample 10 representative trajectories (5 success, 5 failure)
- [ ] Return MonteCarloResult

**Implementation Notes:**
```python
@dataclass
class MonteCarloResult:
    sim_id: str
    n_runs: int
    success_rate: float
    mean_final_altitude_km: float
    std_final_altitude_km: float
    failure_modes: Dict[str, int]
    trajectories_sample: List[TrajectoryResult]
    runtime_seconds: float
```

**DoD:**
- Metrics correct (manual validation)
- Sample trajectories diverse
- JSON serializable

---

### S2.4: Numerical Stability Checks
**Points:** 2  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Detect NaN/Inf in results
- [ ] Flag suspicious results (altitude > 10,000 km, etc.)
- [ ] Log warnings for review
- [ ] Exclude unstable runs from aggregation
- [ ] Alert if >5% runs unstable

**Implementation Notes:**
- Add `is_valid()` check to TrajectoryResult
- Track unstable_count in MonteCarloResult

**DoD:**
- No crashes from bad inputs
- Clear warning messages
- Unstable runs documented

---

## Epic 3: Sensitivity Analysis (Sprint 3)

**Goal:** Identify which parameters matter most

### S3.1: SALib Integration
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Install SALib dependency
- [ ] Implement Sobol sampling (2*(D+1)*N samples)
- [ ] Calculate first-order and total-order indices
- [ ] Return SensitivityResult

**Implementation Notes:**
```python
from SALib.analyze import sobol

class SensitivityAnalyzer:
    def calculate_sobol_indices(
        self,
        param_samples: np.ndarray,  # (N, D)
        outcomes: np.ndarray  # (N,) - success=1, fail=0
    ) -> SensitivityResult:
        ...
```

**DoD:**
- SALib tests pass
- Indices sum to ~1.0 (sanity check)
- Fast: <5s for 10K samples

---

### S3.2: Parameter Ranking
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Rank parameters by total-order index
- [ ] Top 5 most influential parameters
- [ ] Format as list of (param_name, score, rank)
- [ ] Add to MonteCarloResult

**Implementation Notes:**
```python
@dataclass
class SensitivityResult:
    first_order: Dict[str, float]
    total_order: Dict[str, float]
    rankings: List[Tuple[str, float, int]]  # (param, score, rank)
```

**DoD:**
- Rankings intuitive (thrust > Cd, etc.)
- Validated with synthetic data
- Documented interpretation

---

### S3.3: Failure Mode Clustering
**Points:** 2  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Cluster failed trajectories by reason
- [ ] Calculate percentage per failure mode
- [ ] Add to MonteCarloResult
- [ ] Unit test: synthetic failures cluster correctly

**Implementation Notes:**
```python
def cluster_failures(
    results: List[TrajectoryResult]
) -> Dict[str, int]:
    ...
```

**DoD:**
- Failure modes clearly labeled
- Percentages sum to 100%
- Helps debug parameter choices

---

## Epic 4: API Layer (Sprint 3-4)

**Goal:** Expose simulation via REST + WebSocket

### S4.1: POST /api/v1/simulation/launch Endpoint
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Validate LaunchParameters schema
- [ ] Generate unique sim_id
- [ ] Queue simulation (async task)
- [ ] Return sim_id and estimated time
- [ ] Rate limiting: 5 requests/min per IP

**Implementation Notes:**
```python
@router.post("/simulation/launch")
async def start_launch_simulation(
    params: LaunchParameters,
    background_tasks: BackgroundTasks
) -> SimulationResponse:
    ...
```

**DoD:**
- Input validation with FastAPI Pydantic
- Rate limiting enforced
- Error handling (400, 429, 500)

---

### S4.2: WebSocket /ws/simulation/{sim_id}
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Client connects with sim_id
- [ ] Server streams progress updates (every 5%)
- [ ] Server sends final result on completion
- [ ] Handle disconnects gracefully
- [ ] Timeout after 5 minutes

**Implementation Notes:**
```python
@router.websocket("/ws/simulation/{sim_id}")
async def simulation_websocket(
    websocket: WebSocket,
    sim_id: str
):
    ...
```

**DoD:**
- WebSocket tested with mock client
- No memory leaks on disconnect
- Progress updates accurate

---

### S4.3: GET /api/v1/simulation/{sim_id}
**Points:** 1  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Return simulation status (queued | running | complete | failed)
- [ ] Return result if complete
- [ ] 404 if sim_id not found
- [ ] Cache results in Redis (1h TTL)

**Implementation Notes:**
```python
@router.get("/simulation/{sim_id}")
async def get_simulation_result(sim_id: str) -> SimulationStatus:
    ...
```

**DoD:**
- Redis caching works
- TTL expires correctly
- Serialization handles large results

---

### S4.4: API Documentation
**Points:** 1  
**Priority:** P0

**Acceptance Criteria:**
- [ ] OpenAPI docs auto-generated (FastAPI default)
- [ ] Add description to each endpoint
- [ ] Add example requests/responses
- [ ] Test in /docs UI

**DoD:**
- Docs render correctly
- Examples copy-pasteable
- No 500 errors in /docs

---

## Epic 5: Frontend UI (Sprint 4-5)

**Goal:** Interactive simulator in SimulationTab

### S5.1: LaunchSimulatorCard Component
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] New card in SimulationTab
- [ ] Title: "Launch Simulator"
- [ ] Description explaining purpose
- [ ] Collapsible/expandable
- [ ] Responsive design (mobile + desktop)

**Implementation Notes:**
```tsx
export function LaunchSimulatorCard() {
  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Rocket size={16} className="text-spacex-accent" />
        <h3 className="font-medium">Launch Simulator</h3>
      </div>
      <p className="text-sm text-gray-400 mb-4">
        Run Monte-Carlo simulations to explore launch success under uncertainty.
      </p>
      {/* ... */}
    </div>
  )
}
```

**DoD:**
- Matches existing UI style
- No layout shifts
- Accessible (keyboard nav, screen reader)

---

### S5.2: Parameter Controls
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Sliders for 6 key parameters (thrust, Isp, mass, Cd, etc.)
- [ ] Distribution selector (normal, uniform, fixed)
- [ ] Mean + std inputs for normal
- [ ] Min + max inputs for uniform
- [ ] Reset to defaults button
- [ ] Validation: ranges enforced

**Implementation Notes:**
```tsx
function ParameterSlider({
  name,
  value,
  onChange,
  distribution,
  onDistributionChange
}: ParameterSliderProps) {
  // ...
}
```

**DoD:**
- UI intuitive (user testing)
- Validation prevents invalid params
- State synced with form

---

### S5.3: Run Simulation Button + Progress
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] "Run Simulation" button
- [ ] Disabled while running
- [ ] Progress bar (0-100%)
- [ ] Cancel button (optional)
- [ ] Error handling (show toast on failure)

**Implementation Notes:**
```tsx
const { mutate, isPending, progress } = useSimulation()

<button
  onClick={() => mutate(params)}
  disabled={isPending}
>
  {isPending ? `Running... ${progress}%` : 'Run Simulation'}
</button>
```

**DoD:**
- WebSocket connection stable
- Progress updates smooth
- Errors user-friendly

---

### S5.4: Results Dashboard
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Success rate metric (large number)
- [ ] Mean altitude ± std
- [ ] Failure mode breakdown (pie chart or list)
- [ ] Sensitivity bar chart (top 5 params)
- [ ] Show only after simulation complete

**Implementation Notes:**
```tsx
function ResultsDashboard({ result }: { result: MonteCarloResult }) {
  return (
    <div className="space-y-4">
      <SuccessRateMetric rate={result.success_rate} />
      <SensitivityChart data={result.sensitivity} />
      <FailureBreakdown modes={result.failure_modes} />
    </div>
  )
}
```

**DoD:**
- Charts render correctly
- Data formatted nicely
- Responsive layout

---

### S5.5: Trajectory Visualization
**Points:** 3  
**Priority:** P1

**Acceptance Criteria:**
- [ ] 2D altitude vs time chart
- [ ] Show 5 success + 5 failure trajectories
- [ ] Color-coded by outcome
- [ ] Hover to see details
- [ ] Zoom/pan (optional)

**Implementation Notes:**
```tsx
import { LineChart, Line } from 'recharts'

function TrajectoryVisualization({ 
  trajectories 
}: { 
  trajectories: Trajectory[] 
}) {
  // ...
}
```

**DoD:**
- Trajectories clearly visible
- Performance: <100ms render for 10 trajectories
- Tooltip shows time/altitude/velocity

---

### S5.6: Integration with Existing SimulationTab
**Points:** 2  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Add LaunchSimulatorCard to SimulationTab
- [ ] Position above or below existing deorbit simulator
- [ ] No breaking changes to existing features
- [ ] Smooth transition animation

**DoD:**
- Existing features still work
- No console errors
- Tab loads fast (<1s)

---

## Epic 6: Testing & Docs (Sprint 5-6)

**Goal:** Ensure quality and usability

### S6.1: Unit Tests (Backend)
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Test coverage >80% on physics engine
- [ ] Test coverage >80% on Monte Carlo engine
- [ ] Test all failure modes
- [ ] Test parameter sampling
- [ ] Test Sobol calculation

**DoD:**
- pytest passes all tests
- Coverage report generated
- Fast: <10s total

---

### S6.2: Integration Tests (API)
**Points:** 2  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Test POST /api/v1/simulation/launch
- [ ] Test WebSocket connection
- [ ] Test GET /api/v1/simulation/{sim_id}
- [ ] Test rate limiting
- [ ] Test error handling (invalid params)

**DoD:**
- Tests use real server (not mocks)
- Can run in CI
- Clean teardown (no leftover state)

---

### S6.3: Frontend Tests
**Points:** 2  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Test parameter controls render
- [ ] Test run button enables/disables
- [ ] Test results dashboard renders
- [ ] Test WebSocket hook
- [ ] Snapshot tests for UI

**DoD:**
- Jest + React Testing Library
- Tests pass in CI
- No flaky tests

---

### S6.4: Documentation
**Points:** 1  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Update README with simulator section
- [ ] Add docs/simulator-guide.md (user guide)
- [ ] Document parameter choices
- [ ] Document simplifications/limitations
- [ ] Add code examples

**DoD:**
- Docs clear for non-experts
- Examples work copy-paste
- Limitations stated upfront

---

## Epic 7: Polish & Launch (Sprint 6-7)

**Goal:** Make it demo-ready and launch publicly

### S7.1: Performance Optimization
**Points:** 2  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Profile backend (cProfile)
- [ ] Optimize hot paths (<30s for 10K runs)
- [ ] Profile frontend (React DevTools)
- [ ] Lazy load heavy components
- [ ] Test on production hardware

**DoD:**
- Meets performance targets
- No regressions
- Profiling results documented

---

### S7.2: Demo Video + Blog Post
**Points:** 2  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Record 2-minute demo video
- [ ] Write technical blog post (1500 words)
- [ ] Post on personal site + LinkedIn
- [ ] Submit to HN/Reddit
- [ ] Tweet thread

**DoD:**
- Video HD, clear audio
- Blog post edited
- Posted publicly

---

### S7.3: Launch & Promotion
**Points:** 1  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Deploy to production
- [ ] Monitor for errors (first 24h)
- [ ] Respond to feedback
- [ ] Track metrics (usage, stars, etc.)
- [ ] Plan next iteration (P1 features)

**DoD:**
- Zero P0 bugs in first week
- Positive feedback on HN/Reddit
- 20+ GitHub stars

---

## Sprint Plan

### Sprint 1 (Week 1)
**Goal:** Physics engine foundation

**Stories:**
- S1.1: Basic 2D Physics Model (5pts)
- S1.2: Engine Model with Thrust Variance (3pts)
- S1.3: Drag & Atmosphere Model (3pts)

**Total:** 11 points

---

### Sprint 2 (Week 2)
**Goal:** Complete physics, start Monte Carlo

**Stories:**
- S1.4: Success/Failure Classification (5pts)
- S1.5: Validation Against Real Data (5pts)
- S2.1: Parameter Distribution Sampling (3pts)

**Total:** 13 points

---

### Sprint 3 (Week 3)
**Goal:** Monte Carlo + Sensitivity + API

**Stories:**
- S2.2: Parallel Simulation Runner (5pts)
- S2.3: Result Aggregation (3pts)
- S2.4: Numerical Stability Checks (2pts)
- S3.1: SALib Integration (3pts)

**Total:** 13 points

---

### Sprint 4 (Week 4)
**Goal:** Complete API, start frontend

**Stories:**
- S3.2: Parameter Ranking (3pts)
- S4.1: POST /api/v1/simulation/launch (3pts)
- S4.2: WebSocket /ws/simulation/{sim_id} (3pts)
- S4.3: GET /api/v1/simulation/{sim_id} (1pt)
- S5.1: LaunchSimulatorCard Component (3pts)

**Total:** 13 points

---

### Sprint 5 (Week 5)
**Goal:** Complete frontend UI

**Stories:**
- S5.2: Parameter Controls (5pts)
- S5.3: Run Simulation Button + Progress (3pts)
- S5.4: Results Dashboard (5pts)
- S5.6: Integration with SimulationTab (2pts)

**Total:** 15 points

---

### Sprint 6 (Week 6)
**Goal:** Testing, docs, polish

**Stories:**
- S6.1: Unit Tests (Backend) (3pts)
- S6.2: Integration Tests (API) (2pts)
- S6.4: Documentation (1pt)
- S7.1: Performance Optimization (2pts)

**Total:** 8 points

---

### Sprint 7 (Week 7) - Optional
**Goal:** Launch & promotion

**Stories:**
- S7.2: Demo Video + Blog Post (2pts)
- S7.3: Launch & Promotion (1pt)
- S5.5: Trajectory Visualization (3pts) - if time
- S3.3: Failure Mode Clustering (2pts) - if time

**Total:** 8 points (6 required, 2 optional)

---

## Definition of Done (Global)

**For all stories:**
- [ ] Code reviewed (self or peer)
- [ ] Tests passing (unit + integration)
- [ ] No mypy/eslint errors
- [ ] Documentation updated
- [ ] Merged to main
- [ ] Deployed to staging (if applicable)

**For Epic completion:**
- [ ] All stories done
- [ ] Demo recorded internally
- [ ] Retrospective completed
- [ ] Next epic planned

---

## Risk Mitigation

**Risk 1: Physics too hard**
- **Mitigation:** Start 2D, use ChatGPT/Claude for equations, validate early

**Risk 2: Performance too slow**
- **Mitigation:** Profile early (Sprint 2), optimize hot paths, consider Cython

**Risk 3: Frontend too complex**
- **Mitigation:** Reuse existing components, keep UI simple, defer 3D viz to P1

**Risk 4: Scope creep**
- **Mitigation:** Strict P0/P1 separation, timebox to 6 weeks, launch imperfect MVP

---

## Next Actions

1. **Week 1 Day 1:** Start S1.1 (Basic 2D Physics)
2. **Week 1 Day 3:** Review progress, adjust estimates
3. **Week 2 Day 1:** Sprint review + retrospective
4. **Week 3 Day 1:** API design review
5. **Week 4 Day 1:** Frontend mockup review
6. **Week 6 Day 5:** Launch decision (go/no-go)
