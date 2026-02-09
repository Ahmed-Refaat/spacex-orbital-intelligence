# PRD: ANISE Integration for SpaceX Orbital Intelligence

**Version:** 1.0  
**Date:** 2026-02-09  
**Author:** James (FDE)  
**Status:** Draft  

---

## 1. Executive Summary

### Problem Statement

SpaceX Orbital Intelligence currently uses:
- **SGP4** (Python) for TLE propagation (~10K propagations/sec)
- **SPICE** (haisamido/spice Docker) for high-performance propagation (750K/sec)

**Bottleneck:** Analysis operations (TCA calculation, ground passes, eclipse detection, frame transforms) are slow and bottleneck the system.

### Solution

Integrate **ANISE** (https://github.com/nyx-space/anise) as the **analysis engine** to complement SGP4 propagation:
- **400-500x faster** for analysis operations vs current Python implementations
- **Thread-safe** Rust core (vs SPICE global state issues)
- **TRL 9** (used by Rocket Lab, Blue Ghost lunar lander)
- **Python bindings** via `pip install anise`

### Key Metrics

| Metric | Current | Target (ANISE) | Improvement |
|--------|---------|----------------|-------------|
| TCA calculation | ~500ms | <2ms | 250x |
| Ground pass calculation | ~200ms | <1ms | 200x |
| Eclipse detection | ~300ms | <1ms | 300x |
| Frame transforms | ~100ms | <0.5ms | 200x |

### Success Criteria

1. **Performance:** Analysis operations 200x+ faster
2. **Reliability:** No regressions in existing API endpoints
3. **Maintainability:** Clean separation between propagation (SGP4) and analysis (ANISE)
4. **Production-ready:** Full test coverage, monitoring, error handling

---

## 2. Technical Context

### Current Architecture

```
TLE Data → SGP4 (Python) → Analysis (Python)
                ↓
         SPICE (Docker) → OMM/Covariance
```

**Components:**
- `orbital_engine.py` — SGP4 propagation (Python)
- `async_orbital_engine.py` — Async routing (SPICE vs SGP4)
- `spice_client.py` — SPICE API client (OMM/covariance)
- `analysis.py` — API endpoints (TCA, eclipses, ground passes)

**Limitations:**
1. Analysis operations are CPU-bound in Python
2. SPICE requires Docker container (operational overhead)
3. Global state issues with SPICE toolkit
4. No thread safety for parallel analysis

### Target Architecture

```
TLE Data → SGP4 (Python) → State Vectors → ANISE (Rust) → Analysis Results
                                              ↓
                                       TCA, Passes, Eclipses
```

**Benefits:**
- **SGP4 stays** for TLE propagation (ANISE doesn't support SPK Type 10)
- **ANISE handles** all analysis (frame transforms, event finding, TCA)
- **Clean separation** between propagation and analysis
- **Thread-safe** parallel analysis
- **No Docker** for ANISE (native Python bindings)

---

## 3. Requirements

### Functional Requirements

#### P0 (Must Have - MVP)

1. **ANISE Client Library**
   - Python client wrapping ANISE bindings
   - Load ephemeris kernels (DE440s for planets, Earth orientation)
   - Convert SGP4 state vectors → ANISE frames
   - Frame transforms (TEME → ITRF → any frame)

2. **TCA Calculation (Conjunction Analysis)**
   - Replace current Python TCA with ANISE
   - Support batch processing (N satellites vs M objects)
   - Return: TCA time, miss distance, relative velocity
   - Match existing API contract

3. **Ground Pass Calculation**
   - Replace current implementation with ANISE
   - Visibility windows from ground stations
   - Elevation, azimuth, range at each step
   - Next N passes for given station

4. **Eclipse Detection**
   - Replace current implementation with ANISE
   - Detect shadow entry/exit
   - Duration of eclipse
   - Sun angle calculations

#### P1 (Should Have)

5. **Frame Transforms**
   - TEME → ITRF (Earth-fixed)
   - ITRF → Geodetic (lat/lon/alt)
   - J2000 → GCRF
   - Custom frame support

6. **Event Finding**
   - Generic event finder (min/max altitude, latitude crossing, etc.)
   - Custom event conditions

7. **Performance Benchmarks**
   - Compare ANISE vs current Python
   - Metrics: TCA, passes, eclipses
   - Report speedup factors

#### P2 (Nice to Have)

8. **SPICE Migration Path**
   - Gradual replacement of SPICE with ANISE
   - Keep SPICE for legacy OMM support
   - Document migration strategy

9. **Advanced Analysis**
   - Orbit determination
   - Maneuver planning
   - Delta-V calculations

### Non-Functional Requirements

#### Performance

- **TCA calculation:** <2ms per pair (vs 500ms current)
- **Ground passes:** <1ms per satellite (vs 200ms current)
- **Eclipse detection:** <1ms per orbit (vs 300ms current)
- **Frame transforms:** <0.5ms per transform (vs 100ms current)

#### Reliability

- **Test coverage:** >90% for new ANISE code
- **Backward compatibility:** Existing API contracts unchanged
- **Error handling:** Graceful degradation if ANISE fails
- **Monitoring:** Log all ANISE calls with timing

#### Scalability

- **Thread safety:** Support concurrent analysis requests
- **Batch processing:** Support 1000+ satellites efficiently
- **Memory:** <100MB for ephemeris kernels

---

## 4. Architecture

### Component Design

#### 4.1 `anise_client.py`

**Purpose:** Python client for ANISE library

**Responsibilities:**
- Load ephemeris kernels (DE440s, Earth orientation)
- Convert SGP4 state vectors → ANISE frames
- Provide high-level analysis methods
- Cache kernel data

**API:**
```python
class AniseClient:
    def __init__(self, kernel_path: str = "./kernels/"):
        """Load ephemeris kernels"""
        
    async def calculate_tca(
        self,
        sat1_state: StateVector,
        sat2_state: StateVector,
        time_window_hours: int = 24
    ) -> TCAResult:
        """Calculate Time of Closest Approach"""
        
    async def find_ground_passes(
        self,
        sat_state: StateVector,
        ground_station: GroundStation,
        time_window_hours: int = 24
    ) -> List[GroundPass]:
        """Find visibility windows"""
        
    async def detect_eclipses(
        self,
        sat_state: StateVector,
        orbit_duration_hours: int = 24
    ) -> List[Eclipse]:
        """Detect shadow entry/exit"""
        
    def transform_frame(
        self,
        state: StateVector,
        from_frame: str,
        to_frame: str
    ) -> StateVector:
        """Transform between reference frames"""
```

#### 4.2 Modified `async_orbital_engine.py`

**Changes:**
- Add `anise_client: AniseClient` instance
- Route analysis requests to ANISE instead of Python
- Keep SGP4 for propagation
- Add performance tracking

**Routing Logic:**
```
Propagation Request → SGP4 (always)
Analysis Request → ANISE (if available) → Python fallback
```

#### 4.3 Modified `analysis.py` API

**Changes:**
- Replace Python analysis with ANISE calls
- Add `X-Computation-Method` header (anise vs python)
- Add timing metrics to responses
- Keep API contracts identical

**Example:**
```python
@router.get("/analysis/conjunctions/calculate")
async def calculate_conjunction(...):
    # Propagate with SGP4
    state1 = await orbital_engine.propagate(sat1_id, dt)
    state2 = await orbital_engine.propagate(sat2_id, dt)
    
    # Analyze with ANISE
    tca = await anise_client.calculate_tca(state1, state2, hours_ahead)
    
    return {
        "tca": tca.to_dict(),
        "computation_method": "anise",
        "duration_ms": tca.computation_time_ms
    }
```

### Data Flow

```
1. API Request (GET /analysis/conjunctions/calculate)
   ↓
2. Propagate with SGP4 (orbital_engine.propagate)
   → StateVector (x, y, z, vx, vy, vz, epoch)
   ↓
3. Convert to ANISE Frame (anise_client.to_anise_frame)
   → ANISE CartesianState
   ↓
4. Run Analysis (anise_client.calculate_tca)
   → TCA result (time, distance, velocity)
   ↓
5. Return JSON Response
   → {"tca_time": "...", "miss_distance_km": 12.3, ...}
```

### Deployment

**Kernel Files:**
- Store in `backend/kernels/` (gitignored)
- Download via startup script
- Required kernels:
  - `de440s.bsp` — Solar system ephemeris
  - `earth_latest_high_prec.bpc` — Earth orientation
  - `naif0012.tls` — Leap seconds

**Docker:**
- Keep SPICE container for legacy OMM
- No new containers for ANISE (native Python)

---

## 5. Implementation Plan

### Phase 1: Foundation (Week 1)

**Stories:**
1. Install ANISE Python bindings (`pip install anise`)
2. Download and configure ephemeris kernels
3. Create `anise_client.py` with basic frame conversion
4. Unit tests for frame transforms (TEME → ITRF)

**Deliverables:**
- Working ANISE client
- Kernel loading logic
- Frame transform tests passing

### Phase 2: TCA Integration (Week 1-2)

**Stories:**
5. Implement `calculate_tca()` in ANISE client
6. Replace Python TCA in `analysis.py` with ANISE
7. Add fallback to Python if ANISE fails
8. Performance benchmarks (ANISE vs Python)

**Deliverables:**
- TCA endpoint using ANISE
- Benchmark report (speedup metrics)
- Backward compatibility verified

### Phase 3: Ground Passes & Eclipses (Week 2)

**Stories:**
9. Implement `find_ground_passes()` in ANISE client
10. Implement `detect_eclipses()` in ANISE client
11. Replace endpoints in `analysis.py`
12. Add monitoring/logging for ANISE calls

**Deliverables:**
- Ground pass endpoint using ANISE
- Eclipse endpoint using ANISE
- Monitoring dashboard

### Phase 4: Optimization & Cleanup (Week 3)

**Stories:**
13. Batch TCA calculation (N×M satellites)
14. Thread-safety testing (concurrent requests)
15. Documentation (API docs, kernel setup)
16. SPICE migration plan (deprecation timeline)

**Deliverables:**
- Production-ready ANISE integration
- Complete documentation
- Migration guide for SPICE users

---

## 6. Testing Strategy

### Unit Tests

- `test_anise_client.py`:
  - Frame transforms (TEME, ITRF, J2000)
  - TCA calculation (known conjunctions)
  - Ground passes (known satellite passes)
  - Eclipse detection (known eclipse periods)

### Integration Tests

- `test_analysis_api.py`:
  - TCA endpoint with ANISE
  - Ground pass endpoint with ANISE
  - Eclipse endpoint with ANISE
  - Fallback to Python when ANISE fails

### Performance Tests

- `test_anise_benchmarks.py`:
  - TCA: ANISE vs Python (expect 200x speedup)
  - Ground passes: ANISE vs Python (expect 200x speedup)
  - Eclipses: ANISE vs Python (expect 300x speedup)

### Load Tests

- Concurrent requests (100 simultaneous TCA calculations)
- Batch processing (1000 satellites)
- Memory leak detection (long-running process)

---

## 7. Monitoring & Metrics

### Performance Metrics

- **Computation Time:**
  - Track ANISE call duration (p50, p95, p99)
  - Compare ANISE vs Python fallback
  - Alert if >10ms (regression)

- **Error Rates:**
  - ANISE failures → Python fallback
  - Track fallback frequency
  - Alert if >5% fallback rate

- **Throughput:**
  - TCA calculations per second
  - Ground pass calculations per second
  - Eclipse detections per second

### Logging

```python
logger.info(
    "anise_tca_calculation",
    satellite_1=sat1_id,
    satellite_2=sat2_id,
    tca_time=tca.time.isoformat(),
    miss_distance_km=tca.distance,
    duration_ms=tca.computation_time,
    method="anise"
)
```

### Dashboards

- **Analysis Performance:**
  - ANISE computation time (histogram)
  - Fallback rate (%)
  - Speedup factor vs Python

- **API Usage:**
  - Requests per endpoint
  - Error rates
  - Response times

---

## 8. Migration Strategy

### Phase 1: Parallel Run (Week 1-2)

- ANISE runs alongside Python
- Compare results (sanity checks)
- Log discrepancies

### Phase 2: Primary with Fallback (Week 2-3)

- ANISE becomes primary
- Python fallback on errors
- Monitor fallback rate

### Phase 3: ANISE Only (Week 4)

- Remove Python analysis code
- ANISE is sole analysis engine
- Document SPICE deprecation

### Phase 4: SPICE Sunset (Future)

- Evaluate if SPICE container still needed
- Migrate OMM handling to pure Python/ANISE
- Remove SPICE Docker dependency

---

## 9. Risks & Mitigations

### Risk 1: ANISE Kernel Loading

**Risk:** Ephemeris kernels are large (100-500MB), slow startup

**Mitigation:**
- Cache kernels on disk
- Pre-load in Docker image
- Lazy loading for optional kernels

### Risk 2: API Contract Changes

**Risk:** ANISE results differ slightly from Python (numerical precision)

**Mitigation:**
- Tolerance checks (±0.1% acceptable)
- Log discrepancies during parallel run
- Document known differences

### Risk 3: Performance Regression

**Risk:** ANISE slower than expected due to Python overhead

**Mitigation:**
- Benchmark early (Phase 1)
- Profile Python bindings overhead
- Use Rust-native batch operations

### Risk 4: Thread Safety

**Risk:** ANISE not thread-safe in Python GIL

**Mitigation:**
- Test concurrent requests
- Use process pool if needed
- Document thread safety limits

---

## 10. Success Metrics

### Launch Criteria

- [ ] All P0 requirements implemented
- [ ] Test coverage >90%
- [ ] Performance benchmarks show 200x+ speedup
- [ ] Zero regressions in existing API
- [ ] Documentation complete

### Post-Launch Metrics (30 days)

- **Performance:**
  - TCA: <2ms p95
  - Ground passes: <1ms p95
  - Eclipses: <1ms p95

- **Reliability:**
  - ANISE fallback rate: <5%
  - API error rate: <0.1%
  - Zero production incidents

- **Adoption:**
  - 100% of analysis requests use ANISE
  - SPICE usage deprecated (documented)

---

## 11. Dependencies

### External

- **ANISE Python bindings:** `pip install anise`
- **Ephemeris kernels:** DE440s, Earth orientation, leap seconds
- **SPICE (legacy):** Keep for OMM support (phase out later)

### Internal

- `orbital_engine.py` (SGP4 propagation)
- `async_orbital_engine.py` (routing)
- `analysis.py` (API endpoints)

### Team

- **Rico:** Product owner, reviews PRs
- **Christopher Rabotin (ANISE author):** Available for support
- **James (FDE):** Implementation, testing, deployment

---

## 12. Documentation

### User-Facing

- **API Docs:** Update with ANISE performance notes
- **Migration Guide:** For SPICE users
- **Kernel Setup:** Download/configure ephemeris

### Internal

- **Architecture Diagram:** SGP4 + ANISE flow
- **Runbook:** Troubleshooting ANISE issues
- **Performance Reports:** Benchmarks vs Python

---

## 13. Open Questions

1. **Kernel Distribution:** Bundle in Docker image or download at runtime?
2. **SPICE Timeline:** When to fully deprecate SPICE container?
3. **OMM Support:** Does ANISE handle OMM covariance? (investigate)
4. **Frame Conventions:** TEME vs J2000 vs GCRF - document choices

---

## Appendix A: ANISE Resources

- **GitHub:** https://github.com/nyx-space/anise
- **Docs:** https://nyxspace.com/anise/
- **Python Bindings:** https://pypi.org/project/anise/
- **Christopher Rabotin:** Available on GitHub for questions

## Appendix B: Reference Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  /analysis/conjunctions  /analysis/passes  /analysis/eclipse │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │    Async Orbital Engine             │
         │  (Routing: SGP4 + ANISE)            │
         └───────┬────────────────┬────────────┘
                 │                │
        ┌────────▼──────┐  ┌─────▼─────────────┐
        │  SGP4 Engine  │  │  ANISE Client     │
        │  (Python)     │  │  (Rust bindings)  │
        │               │  │                   │
        │ - TLE load    │  │ - TCA calc        │
        │ - Propagation │  │ - Ground passes   │
        │ - State       │  │ - Eclipses        │
        │   vectors     │  │ - Frame xforms    │
        └───────────────┘  └───────────────────┘
                                     │
                              ┌──────▼──────────┐
                              │ Ephemeris       │
                              │ Kernels         │
                              │ (DE440s, EOP)   │
                              └─────────────────┘
```

---

**End of PRD**
