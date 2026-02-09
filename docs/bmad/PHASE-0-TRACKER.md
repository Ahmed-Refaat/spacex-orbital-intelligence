# Phase 0: Foundation - Tracker

**Duration:** Weeks 1-2 (February 10-24, 2026)  
**Goal:** Fix physics, add staging, validate Falcon 9  
**Critical:** This phase makes or breaks the entire project

---

## Week 1: Core Physics

### Day 1-2: Multi-Stage Support ⚡ PRIORITY 1

**Tasks:**
- [ ] Refactor `Vehicle` class to support `List[Stage]`
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
      engines: int
      restartable: bool = False
  
  @dataclass
  class Vehicle:
      name: str
      stages: List[Stage]
      payload_kg: float
      fairing_mass_kg: float
  ```

- [ ] Update `PhysicsEngine` to handle staging
  ```python
  def check_staging(self, state, stage):
      # Conditions for stage separation:
      # 1. Fuel depleted
      # 2. Max burn time reached
      # 3. Pre-programmed staging time
      pass
  
  def perform_staging(self, state):
      # 1. Cut off current stage engine
      # 2. Drop spent stage mass
      # 3. Optional coast phase
      # 4. Ignite next stage
      pass
  ```

- [ ] Write staging tests
  ```python
  def test_two_stage_separation():
      vehicle = create_test_vehicle_2_stages()
      result = simulate_launch(vehicle)
      assert len(result.events) >= 2  # MECO + SECO
      assert result.events[0].type == "MECO"
      assert result.events[1].type == "stage_separation"
  ```

**Expected Output:** Can simulate 2-stage vehicle

**Time Estimate:** 16 hours

---

### Day 3: Gravity Variation

**Tasks:**
- [ ] Replace constant gravity with altitude-dependent
  ```python
  def gravity(self, altitude_km: float) -> float:
      R = EARTH_RADIUS  # 6371 km
      g0 = 9.80665      # m/s² at surface
      return g0 * (R / (R + altitude_km)) ** 2
  ```

- [ ] Test against analytical solution
  ```python
  def test_gravity_decreases_with_altitude():
      g_surface = gravity(0)
      g_200km = gravity(200)
      g_400km = gravity(400)
      
      assert abs(g_surface - 9.80665) < 0.001
      assert abs(g_200km - 9.22) < 0.1  # ~6% reduction
      assert abs(g_400km - 8.70) < 0.1  # ~11% reduction
  ```

**Expected Output:** Gravity varies correctly with altitude

**Time Estimate:** 4 hours

---

### Day 4: US Standard Atmosphere

**Tasks:**
- [ ] Download US Standard Atmosphere 1976 data
  - NASA technical report: NASA-TM-X-74335
  - Or use online tables

- [ ] Create lookup table
  ```python
  # Pre-compute atmosphere at 100m intervals (0-200 km)
  altitude_grid = np.arange(0, 200, 0.1)  # km, 100m resolution
  
  atmosphere_table = {
      'altitude_km': altitude_grid,
      'temperature_K': [...],  # From US Std Atm
      'pressure_Pa': [...],
      'density_kg_m3': [...],
      'speed_of_sound_m_s': [...]
  }
  ```

- [ ] Fast lookup function
  ```python
  def atmosphere_density_fast(altitude_km):
      idx = int(altitude_km * 10)  # 100m bins
      if idx >= len(atmosphere_table['density_kg_m3']):
          return 0.0  # Space
      return atmosphere_table['density_kg_m3'][idx]
  ```

- [ ] Test against known values
  ```python
  def test_atmosphere_density():
      rho_0 = atmosphere_density_fast(0)
      rho_10 = atmosphere_density_fast(10)
      rho_100 = atmosphere_density_fast(100)
      
      assert abs(rho_0 - 1.225) < 0.01      # Sea level
      assert abs(rho_10 - 0.413) < 0.02     # 10 km
      assert abs(rho_100 - 5.6e-7) < 1e-7   # 100 km
  ```

**Expected Output:** Realistic atmospheric density profile

**Time Estimate:** 6 hours

---

### Day 5: RK4 Integration

**Tasks:**
- [ ] Implement Runge-Kutta 4th order
  ```python
  def rk4_step(state, dt, forces_func):
      """
      4th order Runge-Kutta integration step.
      
      More accurate than Euler, allows larger time steps.
      """
      k1 = forces_func(state)
      k2 = forces_func(state + 0.5 * dt * k1)
      k3 = forces_func(state + 0.5 * dt * k2)
      k4 = forces_func(state + dt * k3)
      
      return state + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
  ```

- [ ] Benchmark vs Euler
  ```python
  def benchmark_integration_methods():
      # Test case: Simple orbit
      results_euler = simulate_with_euler(dt=0.1)
      results_rk4 = simulate_with_rk4(dt=1.0)
      
      # RK4 should be more accurate even with 10x larger timestep
      assert abs(results_rk4.final_altitude - true_value) < abs(results_euler.final_altitude - true_value)
  ```

**Expected Output:** More accurate trajectory integration

**Time Estimate:** 6 hours

---

## Week 2: Falcon 9 & Validation

### Day 6: Falcon 9 Configuration

**Tasks:**
- [ ] Research Falcon 9 Block 5 parameters
  
  **Sources:**
  - SpaceX website: https://www.spacex.com/vehicles/falcon-9/
  - Wikipedia: https://en.wikipedia.org/wiki/Falcon_9
  - SpaceX user guide (PDF, public)
  - r/SpaceX wiki: https://www.reddit.com/r/spacex/wiki/
  
  **Parameters needed:**
  - First stage: dry mass, propellant mass, thrust (SL/vac), Isp (SL/vac)
  - Second stage: dry mass, propellant mass, thrust vac, Isp vac
  - Fairing mass
  - Diameter, length (for reference)

- [ ] Create vehicle config file
  ```json
  {
    "vehicle_id": "falcon9_block5",
    "name": "Falcon 9 Block 5",
    "manufacturer": "SpaceX",
    "first_flight": "2018-05-11",
    "status": "active",
    
    "stages": [
      {
        "stage_number": 1,
        "name": "First Stage (Booster)",
        "dry_mass_kg": 22200,
        "prop_mass_kg": 409500,
        "prop_type": "RP-1/LOX",
        "thrust_sl_N": 7607000,
        "thrust_vac_N": 8227000,
        "Isp_sl_s": 282,
        "Isp_vac_s": 311,
        "engines": 9,
        "engine_type": "Merlin 1D",
        "burn_time_max_s": 162,
        "restartable": false
      },
      {
        "stage_number": 2,
        "name": "Second Stage",
        "dry_mass_kg": 4000,
        "prop_mass_kg": 107500,
        "prop_type": "RP-1/LOX",
        "thrust_vac_N": 934000,
        "Isp_vac_s": 348,
        "engines": 1,
        "engine_type": "Merlin Vacuum",
        "burn_time_max_s": 397,
        "restartable": true
      }
    ],
    
    "fairing_mass_kg": 1750,
    "max_payload_leo_kg": 22800,
    "max_payload_gto_kg": 8300,
    
    "notes": "Parameters from public sources (SpaceX website, user guide)"
  }
  ```

- [ ] Load vehicle from JSON
  ```python
  def load_vehicle(vehicle_id: str) -> Vehicle:
      with open(f'data/vehicles/{vehicle_id}.json') as f:
          data = json.load(f)
      
      stages = [Stage(**s) for s in data['stages']]
      return Vehicle(
          name=data['name'],
          stages=stages,
          payload_kg=0,  # Set by mission
          fairing_mass_kg=data['fairing_mass_kg']
      )
  ```

**Expected Output:** Falcon 9 Block 5 ready to simulate

**Time Estimate:** 6 hours

---

### Day 7: ΔV Budget Calculation

**Tasks:**
- [ ] Track velocity contributions during simulation
  ```python
  @dataclass
  class DeltaVBudget:
      gravity_loss: float = 0.0
      drag_loss: float = 0.0
      steering_loss: float = 0.0
      orbital_velocity: float = 0.0
      total_delta_v: float = 0.0
      
      def update(self, dt, state, forces):
          # Gravity loss: ∫ g dt
          self.gravity_loss += state.gravity * dt
          
          # Drag loss: ∫ (D/m) dt
          self.drag_loss += (forces.drag / state.mass) * dt
          
          # Steering loss: ∫ (1 - cos(α)) × (T/m) dt
          # α = angle between thrust and velocity vector
          self.steering_loss += forces.steering_loss_component * dt
          
          # Orbital velocity: Final velocity
          self.orbital_velocity = state.velocity_total
          
          self.total_delta_v = (
              self.gravity_loss +
              self.drag_loss +
              self.steering_loss +
              self.orbital_velocity
          )
  ```

- [ ] Display in results
  ```python
  class SimulationResult:
      delta_v_budget: DeltaVBudget
      
      def summary_table(self):
          return {
              'Total ΔV Required': f"{self.delta_v_budget.total_delta_v:.0f} m/s",
              'Gravity Losses': f"{self.delta_v_budget.gravity_loss:.0f} m/s ({self.delta_v_budget.gravity_loss/self.delta_v_budget.total_delta_v*100:.1f}%)",
              'Drag Losses': f"{self.delta_v_budget.drag_loss:.0f} m/s ({self.delta_v_budget.drag_loss/self.delta_v_budget.total_delta_v*100:.1f}%)",
              'Steering Losses': f"{self.delta_v_budget.steering_loss:.0f} m/s ({self.delta_v_budget.steering_loss/self.delta_v_budget.total_delta_v*100:.1f}%)",
              'Orbital Velocity': f"{self.delta_v_budget.orbital_velocity:.0f} m/s ({self.delta_v_budget.orbital_velocity/self.delta_v_budget.total_delta_v*100:.1f}%)"
          }
  ```

**Expected Output:** Can explain where every m/s of ΔV goes

**Time Estimate:** 6 hours

---

### Day 8: Basic Trajectory Plots

**Tasks:**
- [ ] Create plotting functions
  ```python
  def plot_altitude_vs_time(trajectory):
      times = [s.time for s in trajectory]
      altitudes = [s.altitude_km for s in trajectory]
      
      fig = go.Figure()
      fig.add_trace(go.Scatter(x=times, y=altitudes, mode='lines'))
      fig.update_layout(
          title='Altitude Profile',
          xaxis_title='Time (s)',
          yaxis_title='Altitude (km)',
          template='plotly_dark'
      )
      return fig
  
  def plot_velocity_vs_time(trajectory):
      times = [s.time for s in trajectory]
      v_vert = [s.velocity_vertical_km_s for s in trajectory]
      v_horiz = [s.velocity_horizontal_km_s for s in trajectory]
      v_total = [s.velocity_total_km_s for s in trajectory]
      
      fig = go.Figure()
      fig.add_trace(go.Scatter(x=times, y=v_vert, name='Vertical'))
      fig.add_trace(go.Scatter(x=times, y=v_horiz, name='Horizontal'))
      fig.add_trace(go.Scatter(x=times, y=v_total, name='Total', line=dict(dash='dash')))
      fig.update_layout(
          title='Velocity Components',
          xaxis_title='Time (s)',
          yaxis_title='Velocity (km/s)',
          template='plotly_dark'
      )
      return fig
  ```

- [ ] Add to API response
  ```python
  @app.get("/api/v1/simulations/{sim_id}/plots")
  async def get_plots(sim_id: str):
      result = get_result(sim_id)
      
      return {
          'altitude_vs_time': plot_altitude_vs_time(result.trajectory).to_json(),
          'velocity_vs_time': plot_velocity_vs_time(result.trajectory).to_json(),
      }
  ```

**Expected Output:** Interactive trajectory plots in UI

**Time Estimate:** 6 hours

---

### Day 9: CSV Export

**Tasks:**
- [ ] Export endpoint
  ```python
  @app.get("/api/v1/simulations/{sim_id}/export/csv")
  async def export_csv(sim_id: str):
      result = get_result(sim_id)
      
      df = pd.DataFrame([
          {
              'time_s': s.time,
              'altitude_km': s.altitude_km,
              'velocity_vertical_km_s': s.velocity_vertical_km_s,
              'velocity_horizontal_km_s': s.velocity_horizontal_km_s,
              'velocity_total_km_s': s.velocity_total_km_s,
              'mass_kg': s.mass_kg,
              'thrust_N': s.thrust_N,
              'drag_N': s.drag_N,
              'pitch_deg': s.pitch_angle_deg,
              'acceleration_m_s2': s.acceleration_m_s2
          }
          for s in result.trajectory
      ])
      
      csv = df.to_csv(index=False)
      
      return Response(
          content=csv,
          media_type='text/csv',
          headers={'Content-Disposition': f'attachment; filename=trajectory_{sim_id}.csv'}
      )
  ```

**Expected Output:** Can export full trajectory data

**Time Estimate:** 2 hours

---

### Day 10: Validation Against Falcon 9 CRS-21

**Tasks:**
- [ ] Get CRS-21 reference data
  
  **Mission:** Falcon 9 Block 5, Dragon CRS-21  
  **Date:** December 6, 2020  
  **Launch Site:** Cape Canaveral LC-39A  
  **Target:** ISS (408 km, 51.6° inclination)  
  **Payload:** ~2,972 kg (Dragon + cargo)
  
  **Telemetry (from webcast):**
  - Liftoff: T+00:00
  - Max Q: T+01:10
  - MECO: T+02:35, altitude ~68 km, velocity ~2.1 km/s
  - Stage separation: T+02:38
  - Second stage ignition: T+02:45
  - Fairing separation: T+03:15
  - SECO: T+08:43, altitude ~210 km
  - Insertion orbit: 209 × 212 km, 51.6° inclination

- [ ] Run simulation
  ```python
  def test_falcon9_crs21_validation():
      vehicle = load_vehicle('falcon9_block5')
      
      mission = Mission(
          target_altitude_km=210,
          target_inclination_deg=51.6,
          launch_site='KSC_39A',  # Cape Canaveral
          payload_kg=2972
      )
      
      result = simulate_launch(vehicle, mission)
      
      # Validation criteria
      meco_event = result.get_event('MECO')
      seco_event = result.get_event('SECO')
      
      # MECO validation
      meco_alt_error = abs(meco_event.altitude - 68) / 68 * 100
      meco_vel_error = abs(meco_event.velocity - 2.1) / 2.1 * 100
      
      assert meco_alt_error < 5, f"MECO altitude error: {meco_alt_error:.1f}% (target: <5%)"
      assert meco_vel_error < 5, f"MECO velocity error: {meco_vel_error:.1f}% (target: <5%)"
      
      # SECO validation
      seco_alt_error = abs(seco_event.altitude - 210) / 210 * 100
      
      assert seco_alt_error < 5, f"SECO altitude error: {seco_alt_error:.1f}% (target: <5%)"
      
      # Orbital elements validation
      perigee_error = abs(result.orbital_elements.perigee_km - 209) / 209 * 100
      apogee_error = abs(result.orbital_elements.apogee_km - 212) / 212 * 100
      
      assert perigee_error < 5, f"Perigee error: {perigee_error:.1f}% (target: <5%)"
      assert apogee_error < 5, f"Apogee error: {apogee_error:.1f}% (target: <5%)"
      
      print("✅ VALIDATION PASSED - Falcon 9 CRS-21")
      print(f"   MECO altitude error: {meco_alt_error:.2f}%")
      print(f"   MECO velocity error: {meco_vel_error:.2f}%")
      print(f"   SECO altitude error: {seco_alt_error:.2f}%")
      print(f"   Perigee error: {perigee_error:.2f}%")
      print(f"   Apogee error: {apogee_error:.2f}%")
  ```

- [ ] Document results
  ```markdown
  # Falcon 9 CRS-21 Validation Report
  
  ## Reference Mission
  - Vehicle: Falcon 9 Block 5
  - Date: December 6, 2020
  - Payload: 2,972 kg
  - Target: ISS (408 km, 51.6°)
  
  ## Validation Results
  
  | Parameter | Target | Simulated | Error | Status |
  |-----------|--------|-----------|-------|--------|
  | MECO altitude | 68 km | [X] km | [Y]% | ✅/❌ |
  | MECO velocity | 2.1 km/s | [X] km/s | [Y]% | ✅/❌ |
  | SECO altitude | 210 km | [X] km | [Y]% | ✅/❌ |
  | Perigee | 209 km | [X] km | [Y]% | ✅/❌ |
  | Apogee | 212 km | [X] km | [Y]% | ✅/❌ |
  
  ## Overall Assessment
  
  Mean error: [X]%
  Max error: [Y]%
  
  Status: ✅ PASS / ❌ FAIL
  
  ## Notes
  - [Any observations or explanations for errors]
  ```

**Expected Output:** Validation error <5% (PASS) or document why not

**Time Estimate:** 8 hours

---

## Success Criteria for Phase 0

**MUST HAVE (Non-Negotiable):**
- [ ] Multi-stage vehicles work
- [ ] Improved physics (gravity, atmosphere, RK4)
- [ ] Falcon 9 Block 5 configured with real parameters
- [ ] Validation error vs CRS-21 < 5%
- [ ] ΔV budget breakdown
- [ ] Trajectory plots working
- [ ] CSV export functional

**NICE TO HAVE (Can defer to Phase 1):**
- Launch site effects (Earth rotation)
- 3D visualization
- More vehicles
- Advanced pitch optimization

**KILL SWITCH:**
- If validation error > 10% after debugging → Physics model is fundamentally wrong, need expert help or abort

---

## Daily Check-In Template

```markdown
## Day X - [Date]

### Completed Today:
- [x] Task 1
- [x] Task 2

### Blockers:
- Issue with X (need to research Y)

### Tomorrow:
- [ ] Task 3
- [ ] Task 4

### Notes:
- Thing I learned
- Thing that surprised me
- Question to ask user/expert
```

---

## Phase 0 Completion Checklist

When all tasks done, run this final checklist:

**Code Quality:**
- [ ] All tests passing (`pytest`)
- [ ] No critical bugs
- [ ] Code formatted (`black`, `prettier`)
- [ ] Types checked (`mypy`)
- [ ] Git commits clean

**Validation:**
- [ ] Falcon 9 CRS-21 error < 5%
- [ ] Validation report written
- [ ] Results documented

**Documentation:**
- [ ] Physics model explained
- [ ] Falcon 9 config documented
- [ ] API endpoints documented
- [ ] User guide started

**Demo:**
- [ ] Can show working simulation in <2 minutes
- [ ] Plots look professional
- [ ] Results are credible

**Decision:**
- [ ] Validation PASSED → Continue to Phase 1 ✅
- [ ] Validation MARGINAL → Debug and retry 🔄
- [ ] Validation FAILED → Abort or pivot ❌

---

**Phase 0 Status:** Not started  
**Start Date:** February 10, 2026  
**Target Completion:** February 24, 2026  
**Owner:** Rico + James

**Next Action:** Start Day 1 tasks tomorrow morning (implement staging support).
