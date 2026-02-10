# TLE Data Source Options

**Problem:** Space-Track suspended, Celestrak timeout from VPS  
**Need:** Alternative free/open-source TLE sources

---

## 📊 Available Options

### 1. ✅ **TLE.ivanstanojevic.me** (WORKING)

**Status:** 🟢 Working from VPS  
**Auth:** ❌ None required  
**Cost:** 🟢 Free  
**API:** https://tle.ivanstanojevic.me/

**Pros:**
- No authentication required
- JSON API (easy to parse)
- Works from VPS (tested)
- Good for well-known satellites (ISS verified)

**Cons:**
- ⚠️ May not have ALL Starlink satellites
- Unknown rate limits
- Smaller dataset than Celestrak/Space-Track

**Endpoints:**
```bash
# Single satellite
GET https://tle.ivanstanojevic.me/api/tle/{norad_id}

# Search
GET https://tle.ivanstanojevic.me/api/tle?search={query}&page-size={limit}
```

**Example:**
```bash
curl "https://tle.ivanstanojevic.me/api/tle/25544"
# Returns ISS TLE in JSON
```

---

### 2. ❌ **Celestrak** (TIMEOUT)

**Status:** 🔴 Timeout from VPS  
**Issue:** VPS networking problem (not Celestrak's fault)

**Both HTTPS and HTTP timeout:**
```bash
curl https://celestrak.org/... → TIMEOUT
curl http://celestrak.org/... → TIMEOUT
```

**Possible causes:**
- VPS firewall
- IP blocked by hosting provider
- Network route issue

**Recommendation:** Contact VPS provider or use proxy

---

### 3. ❓ **N2YO.com**

**Status:** 🟡 Requires API key  
**Auth:** ✅ Required (free tier available)  
**Cost:** 🟢 Free tier (300 req/hour)  
**API:** https://www.n2yo.com/api/

**Pros:**
- Good coverage
- Multiple APIs (positions, predictions, etc.)
- Free tier available

**Cons:**
- Requires registration + API key
- Rate limits on free tier
- Need to manage key

**To use:**
1. Register at https://www.n2yo.com/api/
2. Get free API key (300 req/hour)
3. Add to `.env`: `N2YO_API_KEY=your_key`

---

### 4. ⏳ **Space-Track** (SUSPENDED)

**Status:** 🔴 Account suspended  
**Action:** Email sent (compliance report ready)  
**Timeline:** 1-2 business days for reinstatement

---

## 🎯 Recommended Strategy

### **Multi-Source Fallback** (Implemented)

```python
Try sources in order:
1. Space-Track (when reinstated) → Best coverage
2. Celestrak (if VPS network fixed) → Good coverage  
3. Ivan Stanojevic (working now) → Limited but free
4. N2YO (if registered) → Good coverage with limits
```

**Implementation:** `alternative_tle_sources.py` ✅

---

## 🚀 Immediate Action Plan

### **Option A: Use Ivan Stanojevic Now**

**Pros:** Works immediately, no auth  
**Cons:** May not have all satellites

```bash
# Test coverage
curl "https://tle.ivanstanojevic.me/api/tle/25544"  # ISS
curl "https://tle.ivanstanojevic.me/api/tle/44235"  # Starlink (test)
```

**Implementation time:** 10 minutes (integrate into `tle_service.py`)

---

### **Option B: Register N2YO + Use Multi-Source**

**Pros:** Better coverage, still free  
**Cons:** Needs registration

**Steps:**
1. Register: https://www.n2yo.com/api/
2. Get API key
3. Add to `.env`: `N2YO_API_KEY=xxx`
4. Implement N2YO client (20 minutes)
5. Use multi-source fallback

---

### **Option C: Fix VPS Network**

**Pros:** Celestrak has best free coverage  
**Cons:** Requires VPS provider support

**Actions:**
1. Check VPS firewall rules
2. Test with VPN/proxy
3. Contact hosting provider
4. Ask about Celestrak IP whitelist

---

## 📝 Current Implementation

**File:** `alternative_tle_sources.py` ✅

```python
# Ivan Stanojevic integration ready
from app.services.alternative_tle_sources import multi_source_tle

# Auto-fallback
tle = await multi_source_tle.get_tle(
    "25544",
    spacetrack_client=spacetrack,  # Try first
    celestrak_client=celestrak       # Try second
)
# Falls back to Ivan if others fail
```

---

## 🎯 RECOMMENDATION

**Immediate (today):**
1. ✅ Integrate Ivan Stanojevic (working now)
2. ⏳ Wait for Space-Track reinstatement (1-2 days)

**This week:**
1. 🔧 Debug VPS network (why Celestrak timeout?)
2. 📧 Contact VPS provider
3. 🔑 Register N2YO as backup (optional)

**Long-term:**
- Multi-source fallback ensures resilience
- Never rely on single TLE source
- Monitor all sources for availability

---

## ✅ Next Step

**Tu veux que je:**
- **A)** Intègre Ivan Stanojevic maintenant (10 min)
- **B)** Tu t'inscris sur N2YO, je l'intègre après
- **C)** On attend Space-Track + debug réseau VPS

**Recommandation:** **A** (quick win) puis **C** (long-term fix)
