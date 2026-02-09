# Phase 1 Day 2 - Ground Station AER

**Date:** 2026-02-09  
**Focus:** Azimuth, Elevation, Range calculations  
**Estimate:** 3-4 hours

---

## 🎯 Goal

Implement ground station visibility calculations using ANISE.

**Use Cases:**
- Ground station operators need to know when satellites are visible
- Antenna pointing angles (azimuth, elevation)
- Link budget calculations (range)
- Pass prediction (AOS/LOS times)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│  Ground Station (lat, lon, alt)    │
│  DSS-65 Madrid: 40.427°N, 4.251°W  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Satellite Position (TLE/SGP4)      │
│  ISS at epoch → (x, y, z) ECI       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ANISE Frame Transform              │
│  ECI → ECEF (Earth-fixed)           │
│  ECEF → Topocentric (station frame) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  AER Calculation                    │
│  Azimuth: 0-360° (North = 0°)       │
│  Elevation: -90 to +90° (horizon=0°)│
│  Range: distance in km              │
└─────────────────────────────────────┘
```

---

## 📋 Implementation Steps

### 1. Ground Station Data Structure
```python
@dataclass
class GroundStation:
    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
```

### 2. ANISE AER Method
```python
def calculate_aer(
    self,
    satellite_position: Tuple[float, float, float],  # ECI
    ground_station: GroundStation,
    epoch: datetime
) -> Tuple[float, float, float]:  # (az, el, range)
```

### 3. API Endpoint
```
GET /ground-stations/{station_name}/visibility/{satellite_id}
```

### 4. Tests
- Known satellite passes (ISS over Houston)
- Azimuth/Elevation ranges (0-360°, -90 to +90°)
- Range calculation accuracy

---

## 🧪 Test Cases

### Test 1: DSS-65 Visibility
**Station:** DSS-65 Madrid (40.427°N, 4.251°W)  
**Satellite:** ISS (25544)  
**Epoch:** 2024-01-01 12:00 UTC  
**Expected:** Valid AER values

### Test 2: Azimuth Range
**Check:** 0° ≤ azimuth ≤ 360°

### Test 3: Elevation Range
**Check:** -90° ≤ elevation ≤ +90°

### Test 4: Visibility Threshold
**Rule:** elevation > 5° = visible

---

## 📝 Files to Create/Modify

### Create:
- `app/models/ground_station.py` (data structures)
- `tests/test_ground_station_aer.py` (tests)

### Modify:
- `app/services/anise_planetary.py` (add AER method)
- `app/api/ground_stations.py` (enhance endpoint)

---

## ✅ Success Criteria

- [ ] Ground station data structure defined
- [ ] AER calculation method working
- [ ] API endpoint returns valid AER
- [ ] All tests passing (azimuth, elevation, range)
- [ ] Performance: <10ms per calculation

---

Starting implementation now...
