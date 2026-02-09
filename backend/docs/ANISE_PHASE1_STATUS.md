# ANISE Phase 1 Status

**Date:** 2026-02-09  
**Status:** 🚧 IN PROGRESS - API complexity requires Phase 1 simplification

---

## Issue Discovered

ANISE Python API (v0.9.3) is significantly different from documentation examples.

**Blockers:**
1. `Orbit` creation from Cartesian state requires frame_info from Almanac
2. Cannot create arbitrary Orbit directly - must use Keplerian or load from ephemeris
3. For SGP4 → ANISE workflow, we need Cartesian state input, but ANISE expects Keplerian

**Root Cause:**
ANISE is designed to work with **loaded ephemeris (SPK files)**, not arbitrary state vectors.
Our use case (TLE → SGP4 → state vector → ANISE) doesn't match ANISE's primary design.

---

## Phase 1 Revised Scope

### What Works ✅
1. Kernel loading (de440s.bsp + pck08.pca)
2. Almanac initialization
3. Frame info retrieval

### What's Blocked ⚠️
1. **Frame transforms for arbitrary state vectors**
   - ANISE expects states from loaded ephemeris
   - Cannot create Orbit from raw Cartesian (x, y, z, vx, vy, vz)
   
2. **TCA calculation**
   - Depends on Orbit creation (blocked)

---

## Revised Architecture

### Original Plan (from PRD)
```
TLE → SGP4 → State Vector → ANISE (analysis)
```

### Reality Check
ANISE is NOT designed for arbitrary state vectors. It's designed for:
```
SPK file → ANISE → Query state at epoch → Transform → Analysis
```

### Updated Approach

**Option A: Hybrid (Recommended)**
```
TLE → SGP4 → State Vector → Python Analysis (keep existing)
                           ↓
SPK file → ANISE → High-fidelity analysis (when SPK available)
```

**Option B: SPK Generation**
```
TLE → SGP4 → Generate SPK → ANISE (complex, Phase 3+)
```

---

## Decision Point for Rico

### Question
Do we continue with ANISE integration given architectural mismatch?

### Options

**1. PAUSE ANISE Integration** ⏸️
- **Pro:** Focus on shipping other features
- **Pro:** Avoid over-engineering
- **Con:** Miss 400x speedup (only when we have SPK data)

**2. PIVOT to Hybrid Approach** 🔄
- **Pro:** Use ANISE where it shines (planetary ephemeris, high-fidelity transforms)
- **Pro:** Keep Python for TLE-based analysis
- **Con:** Dual codebase (Python + ANISE)

**3. CONTINUE but Phase 3+** 🚀
- Generate SPK Type 9/13 from SGP4 states
- Full ANISE pipeline
- **Con:** Complex, weeks of work
- **Pro:** Eventually get full ANISE benefits

---

## Recommendation

**OPTION 2: Hybrid Approach** ✅

**Phase 1 Deliverables (Revised):**
1. ✅ ANISE client structure (done)
2. ✅ Kernel loading (done)
3. ⚠️ **DEFER** frame transforms for arbitrary states
4. ✅ **ADD** high-fidelity planetary state queries (Earth, Moon, Sun)
5. ✅ **ADD** ANISE-powered ground station visibility (uses loaded SPK)

**Use Cases Where ANISE Helps:**
- Planetary ephemeris (Earth, Moon, Sun positions)
- High-precision Earth orientation (BPC)
- Ground station AER calculations (Azimuth, Elevation, Range)
- Sun angle calculations (beta angle, eclipse detection for known spacecraft)

**Use Cases Where Python Stays:**
- TLE-based propagation (SGP4)
- Arbitrary state vector analysis (TCA for TLE satellites)
- Real-time conjunction screening

---

## Action Required

**Rico: Choose Option 1, 2, or 3**

If Option 2 (Hybrid):
- I'll pivot Phase 1 to focus on planetary ephemeris + ground station calcs
- Keep Python for TLE/SGP4 analysis
- Document hybrid architecture in PRD

If Option 1 (Pause):
- Archive ANISE work for future
- Return to other PRD priorities

If Option 3 (Full Integration):
- Research SPK Type 9/13 generation from SGP4
- Estimate 2-3 weeks additional work

---

**Waiting for your call.** 💰
