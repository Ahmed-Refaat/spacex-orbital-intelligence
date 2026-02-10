# Space-Track.org API Compliance Report

**Date:** February 10, 2026  
**Account:** e.cesar.pro@gmail.com  
**Project:** SpaceX Orbital Intelligence Platform

## Suspension Acknowledgement

We acknowledge the suspension of our account due to violations of Space-Track.org API usage policy. We take full responsibility for:

1. **Unnecessary login/logout cycles** — Logging in on every API request instead of reusing the 2-hour session
2. **Repeated GP ephemerides access** — Accessing the same GP data multiple times within an hour

We have immediately **disabled all automated scripts** and implemented comprehensive fixes.

---

## Root Cause Analysis

### Problem 1: No Session Reuse
**Old behavior:**
- Each service (`spacetrack.py`, `tle_service.py`) authenticated independently
- No tracking of session validity (2h lifetime)
- Potential login on every request

**Cause:** Decentralized authentication without session lifecycle management

### Problem 2: No GP Data Caching
**Old behavior:**
- No Redis caching for GP ephemerides
- Same TLE/OMM data fetched multiple times per hour
- Violated "access GP data no more than once per hour" rule

**Cause:** Missing cache layer for GP queries

---

## Implemented Solution

### 1. Centralized Session Manager

**New file:** `backend/app/services/spacetrack_session.py`

**Key features:**
```python
class SpaceTrackSessionManager:
    """
    Singleton session manager ensuring compliance:
    - One session shared across all services
    - Auto-refresh every 1h50min (before 2h expiry)
    - Redis caching of GP ephemerides (min 1h)
    """
```

**Behavior:**
- **Session lifetime:** 1h50min before refresh (safe margin before 2h expiry)
- **Session tracking:** Timestamp-based validation
- **No logout:** Session naturally expires after 2h of inactivity
- **Shared cookies:** All services use the same authenticated session

### 2. Redis Caching for GP Data

**Cache TTLs:**
- **GP ephemerides (TLE/OMM):** 3600 seconds (1 hour) minimum
- **Satellite catalog:** 86400 seconds (24 hours) — rarely changes
- **CDM (conjunction data):** 300 seconds (5 minutes) — time-sensitive

**Cache key generation:**
```python
def _get_cache_key(self, query_path: str) -> str:
    query_hash = hashlib.md5(query_path.encode()).hexdigest()
    return f"spacetrack:gp:{query_hash}"
```

**Result:**
- Same GP query → cache hit for 1+ hour
- No redundant API calls for identical data
- Full compliance with "max 1 access per hour" rule

### 3. Updated Services

**Modified files:**
- `backend/app/services/spacetrack.py` — Now uses `session_manager.get()`
- `backend/app/services/tle_service.py` — Now uses `session_manager.get()`

**All GP queries now cached:**
- `get_tle()` → 1h cache
- `get_omm()` → 1h cache
- `get_omm_starlink()` → 1h cache
- `get_satellite_catalog()` → 24h cache

---

## Mitigation Plan

### Immediate Actions (Completed ✅)

1. ✅ **Disabled all automated scripts**
2. ✅ **Implemented centralized session manager**
3. ✅ **Added Redis caching for GP data (1h+ TTL)**
4. ✅ **Removed all login/logout cycles**
5. ✅ **Replaced per-request auth with session reuse**

### API Usage Schedule (After Reinstatement)

**TLE/OMM Data (GP class):**
- **URL:** `/basicspacedata/query/class/gp/...`
- **Frequency:** Maximum once per hour per unique query
- **Cached:** Yes, 1 hour minimum via Redis
- **Typical queries:**
  - Starlink constellation: Once per hour
  - Station satellites: Once per hour
  - Individual TLE lookups: Cached for 1 hour

**Conjunction Data (CDM class):**
- **URL:** `/basicspacedata/query/class/cdm_public/...`
- **Frequency:** Every 5 minutes (time-sensitive safety data)
- **Cached:** Yes, 5 minutes via Redis
- **Justification:** CDM data is critical for collision avoidance monitoring

**Satellite Catalog (satcat class):**
- **URL:** `/basicspacedata/query/class/satcat/...`
- **Frequency:** Once per 24 hours (static data)
- **Cached:** Yes, 24 hours via Redis

### Session Management

- **Login frequency:** Maximum once per 2 hours
- **Typical behavior:** Once every 1h50min to stay ahead of expiry
- **Session reuse:** All requests within 2h window reuse the same session
- **No logout:** Sessions expire naturally after 2h inactivity

### Expected Request Volume

**Per Hour (typical):**
- **Logins:** 1 (every ~2h)
- **GP queries (TLE/OMM):** 2-3 unique queries (cached for 1h)
- **CDM queries:** 12 (every 5 min, time-sensitive)
- **Catalog queries:** 0-1 (cached for 24h)

**Total:** ~15-20 requests/hour (well below 300/hour limit)

---

## Testing & Validation

### Pre-Deployment Checks

**Session reuse verification:**
```bash
# Check session manager status
curl http://localhost:8000/api/v1/system/spacetrack-status

# Expected output:
{
  "authenticated": true,
  "session_age_seconds": 1200,
  "session_remaining_seconds": 5400,
  "session_valid_until": "2026-02-10T13:45:00Z"
}
```

**Cache verification:**
```bash
# Redis cache inspection
redis-cli KEYS "spacetrack:gp:*"
redis-cli TTL "spacetrack:gp:<hash>"
# Expected: TTL >= 3600 seconds
```

### Monitoring

**Metrics tracked:**
- Session age and validity
- Cache hit/miss ratio
- API request count per endpoint
- Rate limit headroom

**Logging:**
- All Space-Track API calls logged with cache status
- Session refresh events logged
- Cache hits explicitly logged

---

## Code Review Summary

### Before (Violations)

```python
# spacetrack.py - WRONG
async def get_omm(self):
    # Login on EVERY call
    await self._authenticate()
    response = await client.get(query)  # No caching
    return response.text
```

```python
# tle_service.py - WRONG
async def fetch_tle_data(self):
    async with httpx.AsyncClient() as client:
        # Login on EVERY call
        await self._authenticate(client)
        response = await client.get(query)  # No caching
```

### After (Compliant)

```python
# spacetrack.py - CORRECT
async def get_omm(self):
    # Uses shared session (auto-managed)
    # Cached for 1h minimum
    response = await self.session.get(query, cache_ttl=3600)
    return response.text
```

```python
# tle_service.py - CORRECT
async def fetch_tle_data(self):
    # Uses shared session (auto-managed)
    # Cached for 1h minimum
    response = await self.session.get(query, cache_ttl=3600)
```

---

## Commitment to Compliance

We commit to:

1. **Never access GP data more than once per hour** for identical queries
2. **Reuse sessions** for the full 2-hour validity window
3. **Monitor API usage** via built-in metrics and logging
4. **Respect rate limits** (30/min, 300/hour)
5. **Immediate notification** if any anomaly is detected

We request reinstatement of our account and confirm that all automated processes are currently disabled pending your approval.

---

## Contact Information

**Account:** e.cesar.pro@gmail.com  
**Project:** SpaceX Orbital Intelligence Platform  
**Repository:** https://github.com/e-cesar9/spacex-orbital-intelligence

We appreciate Space-Track.org's services and are committed to responsible API usage.

Thank you for your consideration.

**Sincerely,**  
Eric Cesar  
Developer, SpaceX Orbital Intelligence Platform
