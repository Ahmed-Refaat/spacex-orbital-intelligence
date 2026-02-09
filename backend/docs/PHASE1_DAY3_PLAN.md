# Phase 1 Day 3 - Eclipse Detection

**Date:** 2026-02-09  
**Focus:** High-precision eclipse calculations  
**Estimate:** 2-3 hours

---

## 🎯 Goal

Implement satellite eclipse detection using ANISE.

**Eclipse = Satellite in Earth's shadow (blocked from Sun)**

**Use Cases:**
- Solar panel power management
- Thermal analysis (satellite cooling in shadow)
- Battery planning
- Orbit design (avoiding long eclipses)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│  Satellite Position (ECI)           │
│  ISS at epoch → (x, y, z)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Sun Position (ANISE)               │
│  Query from DE440s ephemeris        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Eclipse Calculation (ANISE)        │
│  - solar_eclipsing() method         │
│  - Returns: Visible/Partial/Full    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Eclipse Periods                    │
│  - Entry time                       │
│  - Exit time                        │
│  - Duration                         │
│  - Eclipse type (umbra/penumbra)    │
└─────────────────────────────────────┘
```

---

## 📋 Eclipse Types

### Umbra (Full Eclipse)
- Satellite completely in Earth's shadow
- No direct sunlight
- Solar panels produce 0% power

### Penumbra (Partial Eclipse)
- Satellite partially in Earth's shadow
- Reduced sunlight
- Solar panels at reduced power

### Visible
- Satellite in full sunlight
- Solar panels at 100% power

---

## 🧪 Test Cases

### Test 1: ISS Eclipse Detection
**Orbit:** LEO, 400km altitude
**Period:** ~90 minutes
**Eclipse:** ~36 minutes per orbit (40% of orbit)

### Test 2: GEO Satellite
**Orbit:** 35,786 km altitude
**Eclipse:** Seasonal (equinoxes only)
**Duration:** ~70 minutes max

### Test 3: Eclipse Timing
**Check:** Entry/exit times accurate to seconds
**Verify:** Duration = exit - entry

---

## 📝 Implementation Steps

### 1. ANISE Eclipse Method
```python
def detect_eclipse(
    self,
    satellite_position: Tuple[float, float, float],
    satellite_velocity: Tuple[float, float, float],
    epoch: datetime
) -> str:  # "VISIBLE" | "PARTIAL" | "FULL"
```

### 2. Eclipse Period Finder
```python
def find_eclipse_periods(
    self,
    satellite_id: str,
    start_epoch: datetime,
    duration_hours: int
) -> List[EclipsePeriod]
```

### 3. API Endpoint
```
GET /satellites/{satellite_id}/eclipses?hours_ahead=24
```

---

## ✅ Success Criteria

- [ ] Eclipse detection method working
- [ ] Eclipse type determination (visible/partial/full)
- [ ] Eclipse period finder (entry/exit times)
- [ ] API endpoint returns eclipse list
- [ ] All tests passing
- [ ] Performance: <100ms for 24h prediction

---

Starting implementation...
