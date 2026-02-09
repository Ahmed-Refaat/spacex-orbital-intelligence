# Implementation Plan - Core + ANISE + Optional OMM

**Date:** 2026-02-09  
**Status:** 🚀 GO - Approved by Rico  
**Approach:** Self-contained core (TLE+ANISE) + Optional OMM profile

---

## 🎯 Architecture Finale

```
┌─────────────────────────────────────────┐
│  Core (Always Available)                │
│  ┌───────────────────────────────┐     │
│  │ TLE/SGP4 (30K satellites)     │     │
│  │ + ANISE (planetary ephemeris) │     │
│  │ Self-contained, no external   │     │
│  └───────────────────────────────┘     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Optional: OMM Profile                  │
│  ┌───────────────────────────────┐     │
│  │ SPICE Service (docker-compose)│     │
│  │ OMM upload + covariance       │     │
│  │ Enable with --profile omm     │     │
│  └───────────────────────────────┘     │
└─────────────────────────────────────────┘
```

---

## 📅 Phase 1: Core + ANISE (4-5 jours) - CURRENT

### Day 1-2: ANISE Foundation ✅ STARTED

**Completed:**
- [x] ANISE installed (v0.9.3)
- [x] Kernels downloaded (de440s.bsp, pck08.pca)
- [x] Basic client structure
- [x] Tests skeleton

**Today - Finish:**
- [ ] Planetary ephemeris queries (Sun, Moon, Earth)
- [ ] Basic endpoint: `GET /ephemeris/{body}?epoch=...`
- [ ] Unit tests passing
- [ ] Performance benchmark

**Files:**
- `app/services/anise_client.py` (core functionality)
- `app/api/ephemeris.py` (new endpoint)
- `tests/unit/test_anise_client.py`

---

### Day 3: Ground Station AER

**Deliverables:**
- [ ] Azimuth, Elevation, Range calculations
- [ ] Ground station visibility windows
- [ ] Endpoint: `GET /ground-stations/{station}/visibility/{satellite_id}`
- [ ] Tests + documentation

**Files:**
- `app/services/anise_client.py` (add AER methods)
- `app/api/ground_stations.py` (enhance existing)

---

### Day 4: Eclipse Detection

**Deliverables:**
- [ ] High-precision eclipse calculations
- [ ] Shadow entry/exit times
- [ ] Endpoint: `GET /satellites/{id}/eclipses?hours_ahead=24`
- [ ] Visualization data for frontend

**Files:**
- `app/services/anise_client.py` (add eclipse methods)
- `app/api/analysis.py` (enhance eclipse endpoint)

---

### Day 5: Polish + Documentation

**Deliverables:**
- [ ] Benchmark ANISE vs Python (document speedup)
- [ ] README.md updated (ANISE features)
- [ ] API documentation (examples)
- [ ] Deployment guide (single container)
- [ ] Remove SPICE from default docker-compose

---

## 📅 Phase 2: Optional OMM Profile (2-3 jours) - AFTER PHASE 1

### Day 6: Docker Compose Profiles

**Deliverables:**
- [ ] Move SPICE to optional profile
- [ ] Test default deployment (no SPICE)
- [ ] Test OMM profile deployment
- [ ] Documentation: how to enable OMM

**Changes:**
```yaml
# docker-compose.yml
services:
  backend:
    # Core only
  
  spice:
    profiles: ["omm"]  # Optional
```

---

### Day 7-8: OMM Documentation + Polish

**Deliverables:**
- [ ] OMM upload documentation
- [ ] Example OMM files (ISS, TDRS)
- [ ] Architecture diagram (core vs optional)
- [ ] Contributor guide

---

## 🎯 Success Criteria Phase 1

**Must Have:**
- [x] ANISE kernels loaded
- [ ] Planetary ephemeris working (Sun, Moon, Earth)
- [ ] Ground station AER working
- [ ] Eclipse detection working
- [ ] All tests passing (>90% coverage)
- [ ] Single-container deployment works
- [ ] README documents ANISE features

**Performance:**
- [ ] Planetary queries: <50ms
- [ ] AER calculation: <10ms
- [ ] Eclipse detection: <100ms

**Quality:**
- [ ] No external service dependencies (Phase 1)
- [ ] Clean error handling
- [ ] Logging for all ANISE operations
- [ ] Graceful degradation if kernels missing

---

## 📝 Current Status

**Completed Today:**
- ✅ PRD created
- ✅ ANISE evaluation
- ✅ OMM strategic analysis
- ✅ Architecture decision (Core + Optional OMM)
- ✅ ANISE installed + kernels downloaded
- ✅ Client structure created
- ✅ Tests skeleton created

**Next: Resume Phase 1 Implementation**
- Fix ANISE client API usage (Orbit creation, etc.)
- Implement planetary ephemeris endpoint
- Get tests passing

---

## 🚀 Starting Now

**Focus:** Get planetary ephemeris working end-to-end
1. Fix `anise_client.py` API usage
2. Create `ephemeris.py` endpoint
3. Test Sun position query
4. Verify performance

**Timeline:** Rest of today (2-3 hours) + tomorrow
