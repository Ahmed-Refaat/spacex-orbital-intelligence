# SPICE API + OMM Integration - Product Brief

**Track:** 2 of 3  
**Created:** 2026-02-09  
**Duration:** 3 weeks  
**Priority:** P0 (accuracy foundation)

---

## 🎯 Problem Statement

**Current limitations:**
- ❌ Using simplified SGP4 only (accuracy ±1-5km)
- ❌ No high-precision ephemeris for critical analysis
- ❌ Can't export orbital data in standard formats
- ❌ Not compatible with NASA/ESA tools
- ❌ Missing planetary ephemeris for interplanetary trajectories

**Impact:**
- Platform not trusted for real mission planning
- Can't integrate with aerospace industry tools
- Mars trajectory simulation impossible (needs planetary ephemeris)
- Academic users can't cite/validate our data

---

## 💡 Solution: NASA SPICE + OMM

### What is SPICE?

**SPICE** = Spacecraft Planet Instrument C-matrix Events

NASA's **de facto standard** for space mission geometry calculations:
- High-precision planetary ephemeris (JPL DE440)
- Spacecraft trajectory data
- Instrument pointing
- Reference frame conversions
- Time system conversions

**Used by:** NASA, ESA, SpaceX, Blue Origin, every serious space mission.

**Accuracy:** <100 meters for planetary positions, <1km for spacecraft.

### What is OMM?

**OMM** = Orbit Mean-Elements Message

CCSDS standard format for orbital data exchange:
- Industry-standard XML/KVN format
- Used by Space-Track, ESA, commercial operators
- Required for collision avoidance coordination
- Enables data sharing with other platforms

---

## 🚀 Value Proposition

### For Users
1. **Trusted accuracy** - NASA-grade calculations
2. **Interoperability** - Export/import standard formats
3. **Mars missions** - Planetary ephemeris enabled
4. **Professional credibility** - Industry-standard tools

### For Platform
1. **Differentiation** - No other open platform has SPICE
2. **Academic adoption** - Citable, validated data
3. **Industry relevance** - Used in real operations
4. **Mars simulator** - Enables interplanetary trajectories

---

## 🎯 MVP Scope (3 weeks)

### P0 - Must Have

**Week 1: SPICE Integration**
- [ ] Install SpiceyPy (Python wrapper for SPICE)
- [ ] Download essential kernels (DE440, leap seconds, Earth)
- [ ] Implement high-precision position/velocity calculations
- [ ] Validate against SGP4 (should match ±1km for LEO)

**Week 2: OMM Export**
- [ ] Implement OMM XML export
- [ ] Validate against CCSDS OMM standard
- [ ] API endpoint: `GET /api/v1/satellites/{id}/omm`
- [ ] Bulk export: `GET /api/v1/satellites/omm?ids=...`

**Week 3: Integration + UI**
- [ ] Integrate SPICE into existing orbital engine
- [ ] Fallback to SGP4 if SPICE unavailable
- [ ] UI: Download OMM button
- [ ] UI: Toggle SPICE/SGP4 mode
- [ ] Documentation

---

### P1 - Nice to Have (Post-MVP)
- [ ] OMM import (upload orbital data)
- [ ] Interplanetary trajectories (Earth → Mars)
- [ ] Custom kernels upload
- [ ] SPICE event detection (eclipses, occultations)
- [ ] Frame conversions (ICRF, ITRF, etc.)

---

## 📊 Architecture

### SPICE Kernel Stack

```
┌─────────────────────────────────────────┐
│         SpiceyPy (Python)               │
│    High-level SPICE API                 │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│         CSPICE (C library)              │
│    Low-level SPICE routines             │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│         SPICE Kernels (Data)            │
│                                         │
│  • de440.bsp    - Planetary ephemeris  │
│  • naif0012.tls - Leap seconds         │
│  • pck00011.tpc - Planetary constants  │
│  • earth_latest_high_prec.bpc - Earth │
│  • satellites.bsp (user data)          │
└─────────────────────────────────────────┘
```

### Data Flow

```
┌────────────────────────────────────────────────┐
│           User Request                         │
│  "Get satellite position at 2026-02-10 12:00"  │
└───────────────────┬────────────────────────────┘
                    │
┌───────────────────┴────────────────────────────┐
│        Orbital Engine (Enhanced)               │
│                                                │
│  ┌──────────────┐      ┌──────────────────┐  │
│  │ SPICE Mode   │  OR  │  SGP4 Mode       │  │
│  │ (High-prec)  │      │  (Fast, fallback)│  │
│  └──────────────┘      └──────────────────┘  │
└───────────────────┬────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────┴──────┐       ┌────────┴───────┐
│ SPICE Kernel │       │  TLE Data      │
│ (.bsp files) │       │  (CelesTrak)   │
└──────────────┘       └────────────────┘
```

### OMM Export Pipeline

```
Satellite Object (DB)
        ↓
Extract Orbital Elements
        ↓
Convert to OMM Format (XML/KVN)
        ↓
Validate against CCSDS Schema
        ↓
Return to User
```

---

## 🔧 Technical Specifications

### SPICE Kernels Required (MVP)

| Kernel | Type | Size | Purpose |
|--------|------|------|---------|
| `de440.bsp` | SPK | 3 GB | Planetary ephemeris (JPL DE440) |
| `naif0012.tls` | LSK | 5 KB | Leap seconds table |
| `pck00011.tpc` | PCK | 100 KB | Planetary constants |
| `earth_latest_high_prec.bpc` | PCK | 50 MB | Earth orientation |

**Total:** ~3.1 GB (one-time download)

**Storage:** `/data/spice/kernels/`

**Update frequency:**
- Leap seconds: Yearly
- Earth orientation: Monthly
- Planetary ephemeris: Every 5-10 years

---

### OMM Format (CCSDS Standard)

**XML Example:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<omm xmlns="http://ccsds.org/schema/omm/1.0">
  <header>
    <CREATION_DATE>2026-02-09T14:00:00Z</CREATION_DATE>
    <ORIGINATOR>SpaceX Orbital Intelligence</ORIGINATOR>
  </header>
  <body>
    <segment>
      <metadata>
        <OBJECT_NAME>STARLINK-1234</OBJECT_NAME>
        <OBJECT_ID>2020-001A</OBJECT_ID>
        <CENTER_NAME>EARTH</CENTER_NAME>
        <REF_FRAME>TEME</REF_FRAME>
        <TIME_SYSTEM>UTC</TIME_SYSTEM>
      </metadata>
      <data>
        <meanElements>
          <EPOCH>2026-02-09T14:00:00.000Z</EPOCH>
          <MEAN_MOTION>15.54</MEAN_MOTION>
          <ECCENTRICITY>0.0001</ECCENTRICITY>
          <INCLINATION>53.0</INCLINATION>
          <RA_OF_ASC_NODE>120.5</RA_OF_ASC_NODE>
          <ARG_OF_PERICENTER>90.0</ARG_OF_PERICENTER>
          <MEAN_ANOMALY>180.0</MEAN_ANOMALY>
        </meanElements>
      </data>
    </segment>
  </body>
</omm>
```

**KVN Example (Key-Value Notation):**
```
CCSDS_OMM_VERS = 2.0
CREATION_DATE = 2026-02-09T14:00:00Z
ORIGINATOR = SpaceX Orbital Intelligence
OBJECT_NAME = STARLINK-1234
OBJECT_ID = 2020-001A
CENTER_NAME = EARTH
REF_FRAME = TEME
TIME_SYSTEM = UTC
EPOCH = 2026-02-09T14:00:00.000Z
MEAN_MOTION = 15.54
ECCENTRICITY = 0.0001
INCLINATION = 53.0
RA_OF_ASC_NODE = 120.5
ARG_OF_PERICENTER = 90.0
MEAN_ANOMALY = 180.0
```

---

## 📋 Implementation Stories

### Sprint 1 (Week 1): SPICE Foundation

**T2-S1: Install SpiceyPy + Download Kernels**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Install `spiceypy` via pip
- [ ] Download DE440, leap seconds, Earth orientation
- [ ] Store in `/data/spice/kernels/`
- [ ] Load kernels in `OrbitalEngine.__init__()`
- [ ] Test basic SPICE call (Earth position)

**Implementation:**
```python
import spiceypy as spice

# Load kernels
spice.furnsh('/data/spice/kernels/de440.bsp')
spice.furnsh('/data/spice/kernels/naif0012.tls')
spice.furnsh('/data/spice/kernels/pck00011.tpc')

# Test: Get Earth position at J2000
et = spice.str2et('2000-01-01T12:00:00')
pos, _ = spice.spkpos('EARTH', et, 'J2000', 'NONE', 'SOLAR SYSTEM BARYCENTER')
print(f"Earth position: {pos}")
```

---

**T2-S2: High-Precision Position Calculation**
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Implement `spice_propagate(satellite_id, epoch)`
- [ ] Convert TLE → state vector → SPICE-compatible
- [ ] Return position/velocity in ICRF frame
- [ ] Validate: SPICE vs SGP4 (should match ±1km for LEO)
- [ ] Handle kernel errors gracefully

**Implementation:**
```python
class OrbitalEngine:
    def spice_propagate(
        self, 
        satellite_id: str, 
        epoch: datetime
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Propagate satellite using SPICE (high-precision).
        
        Returns:
            (position_km, velocity_km_s) in ICRF frame
        """
        # Convert epoch to ephemeris time
        et = spice.str2et(epoch.isoformat())
        
        # Get state (requires satellite loaded as SPICE object)
        # For MVP, we convert TLE -> state vector -> propagate
        # In P1, we can create custom .bsp kernels
        
        # Fallback to SGP4 if SPICE unavailable
        try:
            state, _ = spice.spkezr(satellite_id, et, 'J2000', 'NONE', 'EARTH')
            pos = state[:3]
            vel = state[3:]
            return pos, vel
        except Exception as e:
            logger.warning(f"SPICE failed, falling back to SGP4: {e}")
            return self.sgp4_propagate(satellite_id, epoch)
```

---

**T2-S3: Validate SPICE Accuracy**
**Points:** 2  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Compare SPICE vs SGP4 for 100 satellites
- [ ] Measure position error (RMS)
- [ ] Target: <1km for LEO, <5km for MEO
- [ ] Document validation results
- [ ] Add regression test

---

### Sprint 2 (Week 2): OMM Export

**T2-S4: OMM Data Model**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Define `OMMData` Pydantic model
- [ ] Convert TLE → OMM mean elements
- [ ] Validate required fields per CCSDS
- [ ] Unit tests for conversion

**Implementation:**
```python
from pydantic import BaseModel
from datetime import datetime

class OMMData(BaseModel):
    """Orbit Mean-Elements Message (CCSDS OMM 2.0)."""
    
    # Metadata
    object_name: str
    object_id: str  # NORAD ID
    center_name: str = "EARTH"
    ref_frame: str = "TEME"  # True Equator Mean Equinox
    time_system: str = "UTC"
    
    # Mean elements
    epoch: datetime
    mean_motion: float  # rev/day
    eccentricity: float
    inclination: float  # degrees
    ra_of_asc_node: float  # degrees
    arg_of_pericenter: float  # degrees
    mean_anomaly: float  # degrees
    
    # Optional
    bstar: Optional[float] = None  # Drag term
    mean_motion_dot: Optional[float] = None
    mean_motion_ddot: Optional[float] = None
    
    def to_xml(self) -> str:
        """Export as OMM XML."""
        # Implementation in T2-S5
        pass
    
    def to_kvn(self) -> str:
        """Export as OMM KVN."""
        # Implementation in T2-S5
        pass
```

---

**T2-S5: OMM XML/KVN Export**
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Implement `to_xml()` method
- [ ] Implement `to_kvn()` method
- [ ] Validate against CCSDS schema
- [ ] Handle edge cases (missing fields)
- [ ] Unit tests with known-good OMM files

**Validation:**
```bash
# Use CCSDS schema validator
xmllint --schema omm-2.0.xsd output.xml
```

---

**T2-S6: OMM API Endpoints**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] `GET /api/v1/satellites/{id}/omm` - Single satellite
- [ ] Query param: `format=xml|kvn`
- [ ] `GET /api/v1/satellites/omm?ids=123,456` - Bulk export
- [ ] Rate limiting: 10 req/min
- [ ] OpenAPI docs updated

**Implementation:**
```python
@router.get("/satellites/{satellite_id}/omm")
async def export_omm(
    satellite_id: str,
    format: Literal['xml', 'kvn'] = Query('xml')
):
    """
    Export satellite orbital data in OMM format.
    
    Supports CCSDS OMM 2.0 standard.
    """
    # Get TLE data
    tle = await tle_service.get_tle(satellite_id)
    
    # Convert to OMM
    omm = OMMData(
        object_name=tle_service.get_satellite_name(satellite_id),
        object_id=satellite_id,
        epoch=tle.epoch,
        mean_motion=tle.mean_motion,
        eccentricity=tle.eccentricity,
        inclination=tle.inclination,
        ra_of_asc_node=tle.raan,
        arg_of_pericenter=tle.arg_perigee,
        mean_anomaly=tle.mean_anomaly,
        bstar=tle.bstar
    )
    
    # Export
    if format == 'xml':
        return Response(
            content=omm.to_xml(),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename={satellite_id}.omm.xml"}
        )
    else:
        return Response(
            content=omm.to_kvn(),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={satellite_id}.omm.kvn"}
        )
```

---

### Sprint 3 (Week 3): Integration + UI

**T2-S7: Dual-Mode Orbital Engine**
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] `OrbitalEngine.propagate()` tries SPICE, falls back to SGP4
- [ ] Config flag: `USE_SPICE=true|false`
- [ ] Logging: Which mode was used
- [ ] Benchmarks: SPICE vs SGP4 performance
- [ ] Documentation on when to use each

---

**T2-S8: Frontend OMM Download**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Satellite detail page: "Download OMM" button
- [ ] Format selector (XML/KVN)
- [ ] Bulk download: Select multiple satellites
- [ ] Toast notification on download
- [ ] Loading state

**UI Mockup:**
```tsx
<SatelliteDetail satellite={satellite}>
  <div className="flex gap-2">
    <button onClick={downloadOMM('xml')}>
      Download OMM (XML)
    </button>
    <button onClick={downloadOMM('kvn')}>
      Download OMM (KVN)
    </button>
  </div>
</SatelliteDetail>
```

---

**T2-S9: SPICE/SGP4 Toggle + Docs**
**Points:** 2  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Settings page: Toggle SPICE/SGP4
- [ ] Indicator in UI showing which mode
- [ ] Help text explaining difference
- [ ] Documentation: SPICE integration guide
- [ ] API docs: OMM format examples

---

## 🧪 Testing Strategy

### SPICE Validation Tests
```python
def test_spice_vs_sgp4_accuracy():
    """Test SPICE accuracy vs SGP4."""
    satellite_ids = get_test_satellites(n=100)
    epoch = datetime(2026, 2, 9, 12, 0, 0)
    
    for sat_id in satellite_ids:
        pos_spice, _ = engine.spice_propagate(sat_id, epoch)
        pos_sgp4, _ = engine.sgp4_propagate(sat_id, epoch)
        
        error = np.linalg.norm(pos_spice - pos_sgp4)
        
        # For LEO, error should be <5km
        assert error < 5.0, f"{sat_id}: error {error:.1f} km > 5km"
```

### OMM Validation Tests
```python
def test_omm_xml_validates():
    """Test OMM XML validates against CCSDS schema."""
    tle = get_test_tle()
    omm = OMMData.from_tle(tle)
    xml = omm.to_xml()
    
    # Validate with xmllint
    result = subprocess.run(
        ['xmllint', '--schema', 'omm-2.0.xsd', '-'],
        input=xml.encode(),
        capture_output=True
    )
    
    assert result.returncode == 0, "XML validation failed"
```

---

## 📈 Success Metrics

| Metric | Target | Measured |
|--------|--------|----------|
| SPICE accuracy (LEO) | <1km RMS | TBD |
| SPICE accuracy (MEO) | <5km RMS | TBD |
| OMM export compliance | 100% valid | TBD |
| SPICE propagation time | <10ms | TBD |
| Kernel loading time | <5s on startup | TBD |

---

## 🚨 Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| SPICE kernels too large (3GB) | Download on first use, not in Docker image |
| SPICE slower than SGP4 | Cache results, use SGP4 for UI, SPICE for analysis |
| Kernel updates required | Auto-check monthly, manual fallback |
| OMM standard complex | Use reference implementation, validate rigorously |

---

**Ready to bring NASA-grade accuracy to the platform. 🚀**
