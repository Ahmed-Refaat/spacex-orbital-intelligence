# ANISE Pre-Implementation Evaluation

**Date:** 2026-02-09  
**Evaluator:** James (FDE)  
**Status:** ✅ CLEARED FOR IMPLEMENTATION

---

## 📦 Issue 1: Kernel Distribution

### Question
Bundle kernels in Docker image vs download at runtime?

### Investigation Results

**Kernel Sizes:**
- `de440s.bsp` (short-term, 1900-2050): **31.2 MB** (verified: 32,726,016 bytes)
- `pck08.pca` (planetary constants): ~5 MB (est.)
- `earth_latest_high_prec.bpc` (Earth orientation): ~10-20 MB (est.)
- **Total:** ~50-60 MB

**Options:**

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Bundle in Docker** | ✅ Reliable (no download fail)<br>✅ Faster startup<br>✅ Offline-capable | ❌ Larger image size (+50MB) | ⭐ **PREFERRED** |
| **Download at runtime** | ✅ Smaller image<br>✅ Auto-update kernels | ❌ Slow startup (31MB download)<br>❌ Network dependency<br>❌ Can fail | Backup only |

### Decision

**✅ Bundle kernels in Docker image**

**Rationale:**
1. 50-60MB increase is acceptable (total backend image ~500MB → ~560MB)
2. Production reliability > image size
3. Startup time critical (avoid 10-30s kernel download)
4. Kernels rarely change (DE440s valid until 2050)

**Implementation:**
```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

# Download kernels during build
RUN mkdir -p /app/kernels && \
    curl -o /app/kernels/de440s.bsp http://public-data.nyxspace.com/anise/de440s.bsp && \
    curl -o /app/kernels/pck08.pca http://public-data.nyxspace.com/anise/v0.7/pck08.pca && \
    curl -o /app/kernels/earth_latest_high_prec.bpc http://public-data.nyxspace.com/anise/earth_latest_high_prec.bpc

COPY . /app
RUN pip install -r requirements.txt
```

**Fallback:** If kernel missing, download on first run + cache to disk.

---

## 🛰️ Issue 2: OMM Covariance Support

### Question
Does ANISE support OMM covariance matrices?

### Investigation Results

**ANISE Capabilities:**
- ✅ **Orbit ephemeris** (SPK/BSP files)
- ✅ **Frame transforms** (PCK, BPC)
- ✅ **Time conversions** (all scales)
- ✅ **Rigid body transformations** (rotations + translations)
- ❌ **OMM parsing** — NOT MENTIONED in docs
- ❌ **Covariance propagation** — NOT MENTIONED in docs

**SPK Type Support:**
- ✅ Type 1, 2, 3: Planetary ephemerides
- ✅ Type 9, 13: Spacecraft trajectories (numerical integration)
- ❌ **Type 10: TLE/SGP4** — **EXPLICITLY NOT SUPPORTED**

> "Type 10: Space Command TLE — ✅ SPICE | ❌ ANISE | Please don't use TLEs, a punch-card format (no joke)"

### Findings

**OMM Support:** ❌ **NO**
- ANISE does NOT parse OMM files
- ANISE does NOT handle covariance matrices
- ANISE expects SPK ephemeris data (Types 1-3, 9, 13)

**TLE/SGP4:** ❌ **NO**
- ANISE explicitly does NOT support SPK Type 10 (TLE format)
- This is by design (ANISE philosophy: "don't use punch-card formats")

### Impact on Architecture

**Current Plan:**
```
TLE → SGP4 (Python) → State Vector → ANISE (Analysis)
```

**✅ This is CORRECT and NECESSARY**

ANISE is **NOT** a replacement for SGP4 propagation. It's an **analysis engine** that works on state vectors.

**Covariance Handling:**
- Keep SPICE client for OMM covariance (if needed)
- ANISE does **not** propagate covariance
- Python fallback for covariance-aware TCA calculations

### Decision

**✅ Keep SPICE for OMM Support**

**Rationale:**
1. ANISE cannot parse OMM → SPICE remains necessary
2. ANISE cannot propagate covariance → SPICE handles uncertainty
3. ANISE excels at **deterministic analysis** (TCA, passes, eclipses)
4. Hybrid approach: SPICE (OMM) + ANISE (analysis) + SGP4 (TLE)

**Updated Architecture:**
```
┌─────────────────────────────────────────┐
│         Input Data Sources              │
│  TLE Files         OMM Files (XML/JSON) │
└─────┬──────────────────┬────────────────┘
      │                  │
      ▼                  ▼
  SGP4 Engine      SPICE Client
  (Python)         (Docker/API)
      │                  │
      └──────┬───────────┘
             │
             ▼
       State Vectors
       (x, y, z, vx, vy, vz)
             │
             ▼
       ANISE Client
       (Rust/Python)
             │
       ┌─────┴──────┐
       ▼            ▼
    Analysis    Frame Transforms
    (TCA, etc.) (TEME→ITRF, etc.)
```

**Migration Strategy:**
- Phase 1-3: ANISE for deterministic analysis (no covariance)
- Phase 4: Evaluate if SPICE OMM still needed (rare use case?)
- Future: Consider contributing OMM support to ANISE (OSS)

---

## 🔢 Issue 3: Numerical Precision

### Question
Will ANISE results differ from Python implementations?

### Investigation Results

**ANISE vs SPICE Precision:**
- **Translations:** Machine precision (2e-16) — **BETTER than SPICE**
- **Rotations:** <2 arcsec pointing error, <1 arcsec angle error
- **Root Cause of Differences:** SPICE uses floats, ANISE uses integers (hifitime)

> "The PCK data comes from the IAU Reports... expressed in centuries past the J2000 reference epoch. ANISE uses Hifitime for time conversions. Hifitime's reliance solely on integers for all time computations eliminates the risk of rounding errors. In contrast, SPICE utilizes floating-point values, which introduces rounding errors in calculations like centuries past J2000. Consequently, you might observe a discrepancy of up to 1 millidegree in rotation angles between SPICE and ANISE. However, this difference is a testament to ANISE's superior precision."

**ANISE is MORE accurate than SPICE/Python due to integer time handling.**

### Expected Differences

**ANISE vs Current Python:**
- **TCA calculations:** Likely ±0.01-0.1 km difference (acceptable)
- **Frame transforms:** <1 millidegree rotation difference
- **Eclipse timing:** ±1 second difference (negligible)
- **Ground passes:** ±0.1° elevation difference

**Cause:** Python uses simplified models, ANISE uses high-fidelity ephemeris + integer time.

### Decision

**✅ Tolerate Small Differences (ANISE is MORE accurate)**

**Validation Strategy:**
1. **Parallel run** (Phase 1-2): Log ANISE vs Python results
2. **Tolerance checks:**
   - TCA miss distance: ±1% acceptable
   - Eclipse times: ±5 seconds acceptable
   - Ground pass elevation: ±0.5° acceptable
3. **Document differences** in API response:
   ```json
   {
     "tca_time": "2026-02-10T14:23:15Z",
     "miss_distance_km": 12.345,
     "computation_method": "anise",
     "note": "ANISE uses high-fidelity ephemeris and integer time (more accurate than Python)"
   }
   ```
4. **Regression tests:** Compare ANISE against SPICE (gold standard), not Python

**Known Acceptable Differences:**
- ✅ ANISE more accurate due to integer time
- ✅ ANISE uses JPL ephemeris (DE440s) vs Python approximations
- ⚠️ Large differences (>5%) indicate bug — investigate

**Monitoring:**
```python
logger.warning(
    "anise_python_discrepancy",
    anise_result=anise_tca,
    python_result=python_tca,
    diff_percent=abs(anise_tca - python_tca) / python_tca * 100,
    threshold_percent=5.0
)
```

---

## 📊 Summary & Recommendations

### Issue 1: Kernel Distribution
**Status:** ✅ **RESOLVED**  
**Decision:** Bundle in Docker (+50MB acceptable)  
**Action:** Add kernel download to Dockerfile

### Issue 2: OMM Covariance
**Status:** ⚠️ **CLARIFIED**  
**Decision:** Keep SPICE for OMM, ANISE for analysis  
**Action:** Update PRD architecture diagram  
**Impact:** ANISE complements SGP4/SPICE, doesn't replace

### Issue 3: Numerical Precision
**Status:** ✅ **RESOLVED**  
**Decision:** ANISE is MORE accurate (integer time)  
**Action:** Log differences during parallel run, document in API

---

## 🚦 Implementation Readiness

### Blockers: NONE ✅

All issues clarified. Ready to proceed with Phase 1.

### Risk Adjustments

| Risk | Original | Updated | Mitigation |
|------|----------|---------|------------|
| Kernel loading | Medium | **LOW** | Bundle in Docker |
| OMM support | High | **ACCEPTED** | Keep SPICE container |
| Precision issues | Medium | **LOW** | ANISE more accurate |

### Updated Success Criteria

1. ✅ Performance: 200x+ speedup (unchanged)
2. ✅ Reliability: No regressions (unchanged)
3. ⚠️ **NEW:** Document ANISE vs Python differences in API
4. ⚠️ **NEW:** Keep SPICE for OMM (don't deprecate yet)

---

## 🚀 Phase 1 Kickoff: APPROVED

**Cleared to start:**
1. Install `anise` Python bindings
2. Download kernels to `backend/kernels/`
3. Create `anise_client.py`
4. First frame transform test

**Confidence Level:** 95% ✅

**Remaining Unknowns:**
- Python bindings performance overhead (will benchmark in Phase 1)
- Thread safety in Python GIL (will test in Phase 3)

---

**Evaluation Complete.** Rico: GO or adjust? 💰
