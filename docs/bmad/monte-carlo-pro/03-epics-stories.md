# Epics & Stories - Professional Monte Carlo Launch Simulator

**Date:** 2026-02-09  
**Method:** BMAD + TDD  
**Estimation:** Story Points (Fibonacci: 1, 2, 3, 5, 8, 13)

---

## Epic Structure by Phase

```
Phase 0: Foundation (Weeks 1-2) ⚡ CRITICAL
  ├─ Epic 1: Multi-Stage Physics
  ├─ Epic 2: Improved Physics Models
  └─ Epic 3: Falcon 9 Validation

Phase 1-3: Core MVP (Weeks 3-9)
  ├─ Epic 4: Vehicle Database
  ├─ Epic 5: Mission Presets
  ├─ Epic 6: Actionable Outputs
  └─ Epic 7: Monte Carlo Professional

Phase 4-6: Professional (Weeks 10-16)
  ├─ Epic 8: Performance Optimization
  ├─ Epic 9: UX Overhaul
  └─ Epic 10: Validation & Trust

Phase 7-8: Advanced (Weeks 17-24)
  ├─ Epic 11: Advanced Features
  └─ Epic 12: Production Hardening
```

---

## Phase 0: Foundation (80 points total)

### Epic 1: Multi-Stage Physics (21 points)

**Goal:** Support 2+ stage vehicles with realistic staging dynamics

**Stories:**

#### Story 1.1: Refactor Vehicle Model (5 points)
**As a** developer  
**I want** Vehicle class to support multiple stages  
**So that** we can simulate real rockets (Falcon 9, Ariane 6, etc.)

**Acceptance Criteria:**
- [ ] `Stage` dataclass created with all necessary parameters
- [ ] `Vehicle` class accepts `List[Stage]`
- [ ] Tests pass for 1-stage, 2-stage, and 3-stage vehicles
- [ ] Backwards compatible with existing single-stage code

**Implementation Notes:**
```python
@dataclass
class Stage:
    name: str
    dry_mass_kg: float
    prop_mass_kg: float
    thrust_sl_N: float
    thrust_vac_N: float
    Isp_sl_s: float
    Isp_vac_s: float
    burn_time_max_s: float

@dataclass
class Vehicle:
    name: str
    stages: List[Stage]
    payload_kg: float
    fairing_mass_kg: float
```

**Tests Required:**
```python
def test_single_stage_vehicle()
def test_two_stage_vehicle()
def test_three_stage_vehicle()
def test_invalid_stage_configuration()
```

---

#### Story 1.2: Staging Logic (8 points)
**As a** simulation engine  
**I want** to detect and execute stage separations  
**So that** trajectories include realistic staging events

**Acceptance Criteria:**
- [ ] Detects when stage fuel depleted or burn time exceeded
- [ ] Executes separation: engine cutoff → drop mass → optional coast → next stage ignition
- [ ] Logs separation event with time, altitude, velocity
- [ ] Tests validate correct mass after separation

**Implementation Notes:**
```python
def check_staging(self, state, stage):
    if stage.fuel <= 0 or state.time > stage.burn_time_max:
        return True
    return False

def perform_staging(self, state):
    # 1. Cut off engine
    # 2. Drop spent stage mass
    # 3. Coast phase (if configured)
    # 4. Ignite next stage
```

**Tests Required:**
```python
def test_staging_on_fuel_depletion()
def test_staging_on_max_burn_time()
def test_staging_mass_conservation()
def test_coast_phase_between_stages()
```

---

#### Story 1.3: Thrust Profile (8 points)
**As a** physics engine  
**I want** to use sea-level and vacuum thrust/Isp correctly  
**So that** performance matches real vehicles

**Acceptance Criteria:**
- [ ] Thrust interpolated based on atmospheric pressure
- [ ] Isp interpolated based on atmospheric pressure
- [ ] First stage uses SL values at launch, transitions to vacuum
- [ ] Second stage uses vacuum values (always above atmosphere)
- [ ] Tests validate correct thrust at different altitudes

**Implementation Notes:**
```python
def effective_thrust(self, altitude_km, stage):
    pressure = atmosphere_pressure(altitude_km)
    # Linear interpolation between SL and vacuum
    # (simplified, real is more complex)
    if pressure > 10000:  # Below ~15 km
        return stage.thrust_sl_N
    elif pressure < 100:  # Above ~50 km
        return stage.thrust_vac_N
    else:
        # Interpolate
        return lerp(stage.thrust_sl_N, stage.thrust_vac_N, ...)
```

**Tests Required:**
```python
def test_thrust_at_sea_level()
def test_thrust_at_vacuum()
def test_thrust_interpolation_mid_atmosphere()
def test_isp_variation_with_altitude()
```

---

### Epic 2: Improved Physics Models (21 points)

**Goal:** Replace simplified physics with industry-standard models

**Stories:**

#### Story 2.1: Gravity Variation (3 points)
**As a** physics model  
**I want** gravity to decrease with altitude  
**So that** high-altitude trajectories are accurate

**Acceptance Criteria:**
- [ ] Gravity calculated as g = g₀ × (R / (R + h))²
- [ ] Tests validate correct values at 0, 200, 400 km
- [ ] Error <1% compared to analytical formula

**Tests Required:**
```python
def test_gravity_at_surface()
def test_gravity_at_200km()
def test_gravity_at_400km()
def test_gravity_analytical_match()
```

---

#### Story 2.2: US Standard Atmosphere (8 points)
**As a** physics model  
**I want** to use US Standard Atmosphere 1976  
**So that** drag calculations are accurate

**Acceptance Criteria:**
- [ ] Atmosphere table loaded (0-200 km, 100m resolution)
- [ ] Density, temperature, pressure, speed of sound available
- [ ] Fast O(1) lookup by altitude
- [ ] Tests validate against published values

**Implementation Notes:**
```python
# Load table on startup
atmosphere_table = load_us_standard_atmosphere_1976()

def atmosphere_density(altitude_km):
    idx = int(altitude_km * 10)  # 100m bins
    return atmosphere_table['density'][idx]
```

**Tests Required:**
```python
def test_atmosphere_density_at_sea_level()
def test_atmosphere_density_at_10km()
def test_atmosphere_density_at_100km()
def test_atmosphere_temperature_profile()
```

---

#### Story 2.3: RK4 Integration (5 points)
**As a** numerical integrator  
**I want** to use Runge-Kutta 4th order  
**So that** trajectories are more accurate than Euler

**Acceptance Criteria:**
- [ ] RK4 integrator implemented and tested
- [ ] Can use 10x larger timestep than Euler for same accuracy
- [ ] Benchmarks show RK4 more accurate than Euler
- [ ] No performance regression (<2x slower)

**Tests Required:**
```python
def test_rk4_vs_euler_accuracy()
def test_rk4_simple_harmonic_oscillator()
def test_rk4_orbital_motion()
```

---

#### Story 2.4: Earth Rotation (5 points)
**As a** launch simulation  
**I want** to account for Earth's rotation  
**So that** launch azimuth and velocity bonus are correct

**Acceptance Criteria:**
- [ ] Launch site velocity added to initial state (~400 m/s at Cape)
- [ ] Launch azimuth affects final inclination
- [ ] Tests validate velocity bonus at different latitudes

**Tests Required:**
```python
def test_earth_rotation_velocity_bonus()
def test_launch_azimuth_to_inclination()
def test_equatorial_vs_polar_launch()
```

---

### Epic 3: Falcon 9 Validation (38 points)

**Goal:** Validate simulation against real Falcon 9 CRS-21 flight

**Stories:**

#### Story 3.1: Falcon 9 Configuration (5 points)
**As a** user  
**I want** Falcon 9 Block 5 configured with real parameters  
**So that** I can simulate SpaceX missions

**Acceptance Criteria:**
- [ ] JSON config file with all Falcon 9 parameters
- [ ] Stage 1 and Stage 2 fully specified
- [ ] Parameters sourced and documented (SpaceX website, user guide)
- [ ] Loaded into vehicle database on startup

**Implementation Notes:**
- Research SpaceX website, Wikipedia, r/SpaceX wiki
- Document sources for every parameter
- Include notes about assumptions

**Tests Required:**
```python
def test_load_falcon9_config()
def test_falcon9_stages_valid()
def test_falcon9_mass_budget()
```

---

#### Story 3.2: ΔV Budget Calculation (8 points)
**As an** engineer  
**I want** to see where every m/s of ΔV goes  
**So that** I understand the mission design

**Acceptance Criteria:**
- [ ] Tracks gravity loss: ∫ g dt
- [ ] Tracks drag loss: ∫ (D/m) dt
- [ ] Tracks steering loss: ∫ (1-cos α)(T/m) dt
- [ ] Displays breakdown with percentages
- [ ] Tests validate sum equals total ΔV

**Implementation Notes:**
```python
@dataclass
class DeltaVBudget:
    gravity_loss: float = 0.0
    drag_loss: float = 0.0
    steering_loss: float = 0.0
    orbital_velocity: float = 0.0
    
    def update(self, dt, state, forces):
        self.gravity_loss += state.gravity * dt
        # etc.
```

**Tests Required:**
```python
def test_delta_v_budget_simple_vertical()
def test_delta_v_budget_with_drag()
def test_delta_v_budget_sum_equals_total()
```

---

#### Story 3.3: Trajectory Plots (8 points)
**As an** engineer  
**I want** interactive plots of the trajectory  
**So that** I can visualize the mission

**Acceptance Criteria:**
- [ ] Altitude vs time plot
- [ ] Velocity (vertical, horizontal, total) vs time plot
- [ ] Downrange vs altitude plot
- [ ] All plots interactive (zoom, pan, hover)
- [ ] Plots use aerospace-standard styling

**Implementation Notes:**
- Use Plotly for interactive plots
- Return as JSON from API
- Frontend renders with react-plotly.js

**Tests Required:**
```python
def test_plot_altitude_vs_time()
def test_plot_velocity_components()
def test_plot_data_correctness()
```

---

#### Story 3.4: CSV Export (3 points)
**As an** engineer  
**I want** to export full trajectory data as CSV  
**So that** I can analyze it in Excel/MATLAB

**Acceptance Criteria:**
- [ ] API endpoint `/export/csv`
- [ ] CSV includes all state variables
- [ ] Proper headers and formatting
- [ ] Downloads with correct filename

**Tests Required:**
```python
def test_csv_export_format()
def test_csv_export_completeness()
```

---

#### Story 3.5: Validation Against CRS-21 (13 points)
**As a** developer  
**I want** simulation to match Falcon 9 CRS-21 flight within 5%  
**So that** the tool is credible

**Acceptance Criteria:**
- [ ] MECO altitude error <5%
- [ ] MECO velocity error <5%
- [ ] SECO altitude error <5%
- [ ] Perigee/apogee error <5%
- [ ] Validation report documented
- [ ] If validation fails, document why and fix

**Reference Data (CRS-21, Dec 6, 2020):**
- MECO: T+02:35, ~68 km, ~2.1 km/s
- SECO: T+08:43, ~210 km
- Insertion orbit: 209 × 212 km, 51.6° inclination

**Tests Required:**
```python
def test_falcon9_crs21_validation()
def test_validation_within_tolerance()
```

---

## Phase 1-3: Core MVP (120 points total)

### Epic 4: Vehicle Database (13 points)

**Goal:** Support 5+ real vehicles with community contributions

**Stories:**

#### Story 4.1: Vehicle Schema & Database (5 points)
**As a** system  
**I want** vehicles stored in database  
**So that** they're searchable and maintainable

**Acceptance Criteria:**
- [ ] PostgreSQL table for vehicles
- [ ] JSON files in `data/vehicles/` version-controlled
- [ ] Loaded into DB on startup
- [ ] API endpoints to list/get vehicles

---

#### Story 4.2: Add 4 More Vehicles (8 points)
**As a** user  
**I want** multiple vehicles to choose from  
**So that** I can compare options

**Acceptance Criteria:**
- [ ] Ariane 6-2 configured
- [ ] Ariane 6-4 configured
- [ ] Atlas V 551 configured
- [ ] Long March 2C configured
- [ ] All validated against published performance

---

### Epic 5: Mission Presets (8 points)

**Goal:** Common missions pre-configured

**Stories:**

#### Story 5.1: Mission Types (5 points)
**As a** user  
**I want** common missions pre-configured  
**So that** I don't have to enter orbital parameters manually

**Missions:**
- LEO (400 km, ISS inclination 51.6°)
- GTO (185 × 35786 km)
- Sun-synchronous polar orbit (800 km, ~98°)

---

#### Story 5.2: Launch Sites (3 points)
**As a** user  
**I want** to select launch site  
**So that** Earth rotation effects are correct

**Sites:**
- Cape Canaveral (28.5°N)
- Vandenberg (34.7°N)
- Kourou (5.2°N)
- Baikonur (45.6°N)

---

### Epic 6: Actionable Outputs (21 points)

**Goal:** Results engineers can actually use

[Stories: Orbital elements, event timeline, better plots, etc.]

---

### Epic 7: Monte Carlo Professional (34 points)

**Goal:** Industry-grade uncertainty quantification

[Stories: Realistic distributions, correlations, sensitivity analysis, etc.]

---

## Phase 4-6: Professional (90 points total)

### Epic 8: Performance Optimization (34 points)

[Stories: Cython, GPU, benchmarks]

---

### Epic 9: UX Overhaul (34 points)

[Stories: Batch mode, comparison view, simulation library, sharing]

---

### Epic 10: Validation & Trust (22 points)

[Stories: Validation suite, documentation, academic review]

---

## Phase 7-8: Advanced (80 points total)

### Epic 11: Advanced Features (55 points)

[Stories: Optimization, 3D viz, APIs]

---

### Epic 12: Production Hardening (25 points)

[Stories: Kubernetes, auth, monitoring]

---

## Sprint Planning

### Sprint 0 (Week 1-2): Foundation - 80 points
- Epic 1: Multi-Stage Physics (21 pts)
- Epic 2: Improved Physics (21 pts)
- Epic 3: Falcon 9 Validation (38 pts)

**Goal:** Validation <5% error

---

### Sprint 1 (Week 3-4): Vehicles - 21 points
- Epic 4: Vehicle Database (13 pts)
- Epic 5: Mission Presets (8 pts)

**Goal:** 5 vehicles, 3 mission types

---

### Sprint 2-3 (Week 5-9): Outputs & MC - 55 points
- Epic 6: Actionable Outputs (21 pts)
- Epic 7: Monte Carlo Pro (34 pts)

**Goal:** Production-quality outputs

---

[Continue for all sprints...]

---

## Story Template

```markdown
### Story X.Y: Title (Z points)

**As a** [role]
**I want** [capability]
**So that** [benefit]

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass

**Implementation Notes:**
[Code snippets, links, references]

**Tests Required:**
def test_feature_1()
def test_feature_2()

**Dependencies:** Story A.B, Story C.D
**Blocked By:** None
**Estimate:** Z story points
**Priority:** P0 / P1 / P2
```

---

**Status:** ✅ Epics & Stories Complete  
**Total Points:** ~370 points across 8 phases  
**Velocity Target:** 40 points/week (experienced solo dev)  
**Timeline:** 9 weeks minimum (aggressive), 24 weeks with buffer

**Next:** Start Sprint 0, Story 1.1 (Refactor Vehicle Model)
