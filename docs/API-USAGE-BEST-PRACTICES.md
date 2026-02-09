# 🎯 API Usage - Best Practices & Professional Guidelines

**Date:** 2026-02-09  
**Audience:** Developers, DevOps, API consumers  
**Goal:** Prevent API abuse, ensure professional usage

---

## TL;DR - Quick Rules

✅ **DO:**
- Cache results locally (5-60 seconds)
- Use batch operations for multiple satellites (≥50)
- Monitor rate limits via `/rate-limits/spice`
- Handle 429 (rate limited) responses gracefully

❌ **DON'T:**
- Poll health checks every second
- Upload same OMM multiple times
- Query same satellite position repeatedly without caching
- Ignore rate limit errors (429)

---

## Rate Limits Overview

| API Endpoint | Limit | Cache Duration | Notes |
|--------------|-------|----------------|-------|
| **SPICE Health Check** | 1 per 30s | 30s | Cached automatically |
| **OMM Upload** | 5 per minute | No cache | Each upload unique |
| **Propagation** | 100 per minute | No cache | Batch counts as 1 |
| **Performance Stats** | Unlimited | 5s recommended | Uses cached health |

---

## 1. Health Checks ✅

### ❌ WRONG - Polling Too Frequently

```python
# BAD: Polling every 5 seconds from frontend
setInterval(async () => {
    const health = await fetch('/api/v1/performance/stats')
    // This triggers SPICE health check!
}, 5000)  # ← 12 checks per minute! Over limit!
```

**Problem:**
- SPICE health check rate limit: **1 per 30 seconds**
- Frontend auto-refresh: **5 seconds**
- Result: Rate limit exceeded after 6 refreshes

---

### ✅ CORRECT - Use Cached Results

**Backend (Already Implemented):**
```python
# backend/app/services/spice_client.py
async def health_check(self) -> bool:
    # Automatically uses 30s cache
    if not spice_rate_limiter.health_check.can_call():
        cached = spice_rate_limiter.health_check.get_cached()
        return cached  # ← Returns cached result
    
    # Only makes real call if cache expired
    response = await self.client.get("/health")
    spice_rate_limiter.health_check.record_call(result)
    return result
```

**Frontend (Already Safe):**
```typescript
// frontend/src/components/Sidebar/PerformanceTab.tsx
useQuery({
    queryKey: ['performance-stats'],
    queryFn: async () => {
        const res = await fetch('/api/v1/performance/stats')
        return res.json()
    },
    refetchInterval: 5000  // ← Safe! Backend caches for 30s
})
```

**Why It Works:**
- Frontend polls every 5s ✅
- Backend caches health check for 30s ✅
- SPICE only called once per 30s ✅
- No rate limit exceeded ✅

---

## 2. OMM Uploads ✅

### ❌ WRONG - Uploading Same File Multiple Times

```python
# BAD: Retry loop without backoff
for i in range(10):
    try:
        response = await upload_omm(file)
    except Exception:
        continue  # ← Immediate retry! Spams API!
```

**Problem:**
- OMM upload limit: **5 per minute**
- Loop retries 10 times immediately
- Result: Rate limit exceeded after 5th attempt

---

### ✅ CORRECT - Upload Once, Query Many Times

```python
# GOOD: Upload once, cache result
satellite_id = await upload_omm_once(file)

# Query position multiple times (cached)
for _ in range(100):
    position = await get_position(satellite_id)
    # Backend caches position for 5 seconds
```

**Best Practice:**
```python
async def upload_omm_with_retry(file, max_retries=3):
    """Professional retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await upload_omm(file)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt * 10  # 10s, 20s, 40s
                logger.info(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                raise
```

---

## 3. Propagation Queries ✅

### ❌ WRONG - Sequential Single Queries

```python
# BAD: 100 individual API calls
satellites = ["SAT_00001", "SAT_00002", ..., "SAT_00100"]

for sat_id in satellites:
    position = await get_position(sat_id)  # ← 100 API calls!
```

**Problem:**
- 100 individual calls
- Each call ~3ms + HTTP overhead
- Total time: ~500ms
- API stress: High

---

### ✅ CORRECT - Batch Operations

```python
# GOOD: 1 batch API call
satellites = ["SAT_00001", "SAT_00002", ..., "SAT_00100"]

# Backend automatically routes to SPICE batch (threshold ≥50)
positions = await propagate_batch(satellites)  # ← 1 API call!
```

**Performance:**
- 1 batch call instead of 100 ✅
- Total time: ~50ms (10x faster)
- API stress: Minimal ✅

**When to Batch:**
- ≥50 satellites → SPICE batch mode
- <50 satellites → SGP4 parallel (still batched internally)

---

## 4. Caching Strategy 💾

### Application-Level Caching

**Position Queries:**
```python
# Backend caches positions for 5 seconds
cache_key = f"satellite:position:{sat_id}"
ttl = 5  # seconds

# First query: Cache miss, compute position
position = await get_position("25544")  # ~3ms

# Second query within 5s: Cache hit
position = await get_position("25544")  # <0.1ms (from Redis)
```

**Orbit Paths:**
```python
# Backend caches orbits for 5 minutes
cache_key = f"satellite:orbit:{sat_id}:{hours}:{step}"
ttl = 300  # 5 minutes

# Orbit rarely changes, safe to cache longer
```

**Recommendations:**
| Data Type | Cache Duration | Rationale |
|-----------|----------------|-----------|
| Health Check | 30s | Service status changes slowly |
| Position | 5s | Satellites move fast |
| Orbit Path | 5 minutes | Predictable trajectory |
| Metadata | 24 hours | Static data |

---

## 5. Error Handling 🔧

### Rate Limit Errors (429)

**Response:**
```json
{
    "detail": "Rate limit exceeded: 6/5 uploads per minute. Please wait before uploading again."
}
```

**How to Handle:**
```python
try:
    result = await upload_omm(file)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        # Parse retry-after header (if available)
        retry_after = int(e.response.headers.get("Retry-After", 60))
        
        logger.warning(f"Rate limited. Retry after {retry_after}s")
        await asyncio.sleep(retry_after)
        
        # Retry once
        result = await upload_omm(file)
    else:
        raise
```

**Frontend (User-Friendly):**
```typescript
try {
    await uploadOMM(file)
} catch (error) {
    if (error.status === 429) {
        toast.error("Upload limit reached. Please wait 1 minute and try again.")
    } else {
        toast.error("Upload failed. Please try again.")
    }
}
```

---

## 6. Monitoring Your Usage 📊

### Check Current Rate Limits

**Endpoint:** `GET /api/v1/rate-limits/spice`

```bash
curl http://localhost:8000/api/v1/rate-limits/spice
```

**Response:**
```json
{
    "service": "SPICE API",
    "limits": {
        "health_check": {
            "can_call_now": false,
            "cache_remaining_sec": 15.3,
            "calls_last_minute": 2,
            "max_calls_per_minute": 2
        },
        "omm_load": {
            "can_call_now": true,
            "calls_last_minute": 2,
            "max_calls_per_minute": 5
        }
    }
}
```

**Interpretation:**
- `can_call_now: false` → Use cached result or wait
- `cache_remaining_sec: 15.3` → Wait 15s for fresh data
- `calls_last_minute: 2` → Used 2 out of 5 quota

---

### Overall Status

**Endpoint:** `GET /api/v1/rate-limits/status`

```bash
curl http://localhost:8000/api/v1/rate-limits/status
```

**Response:**
```json
{
    "status": "ok",
    "throttled_count": 0,
    "throttled_apis": [],
    "total_apis_monitored": 3
}
```

**Status Values:**
- `ok` → All APIs available
- `throttled` → Some APIs rate limited

---

## 7. Production Checklist ✅

**Before Deploying:**
- [ ] Cache configured (Redis running)
- [ ] Rate limits tested (load test with k6)
- [ ] Error handling implemented (429 responses)
- [ ] Monitoring enabled (`/rate-limits/status`)
- [ ] Retry logic with exponential backoff
- [ ] Health checks NOT polled <30s interval
- [ ] Batch operations used for ≥50 satellites

**Monitoring:**
- [ ] Dashboard shows rate limit status
- [ ] Alerts on rate limit exceeded (>10% requests)
- [ ] Logs include rate limit violations
- [ ] Metrics track API call frequency

---

## 8. Common Mistakes & Fixes 🔧

### Mistake 1: Polling Health Too Fast

```typescript
// ❌ BAD
setInterval(checkHealth, 1000)  // Every 1 second!

// ✅ GOOD
setInterval(checkHealth, 30000)  // Every 30 seconds (matches cache)
```

---

### Mistake 2: No Retry Backoff

```python
# ❌ BAD
for _ in range(10):
    try:
        upload()
    except:
        pass  # Immediate retry!

# ✅ GOOD
async def upload_with_backoff():
    for attempt in range(3):
        try:
            return await upload()
        except RateLimitError:
            await asyncio.sleep(2 ** attempt * 10)  # 10s, 20s, 40s
```

---

### Mistake 3: Ignoring Cache

```python
# ❌ BAD
for i in range(100):
    position = await get_position("25544")  # 100 queries!

# ✅ GOOD
position = await get_position("25544")  # 1 query, cached
for i in range(100):
    use_cached_position(position)  # Reuse
```

---

## 9. Rate Limit Budget Calculator

**Example Scenario:**
- Users: 10 concurrent
- Each user: Performance dashboard open (refreshes every 5s)
- Duration: 1 minute

**Calculation:**
```
Health checks per user: 12 per minute (every 5s)
Total health checks: 10 users × 12 = 120 per minute

Actual SPICE calls: 2 per minute (cached for 30s)
```

**Result:** ✅ **Safe** (2 calls << 120 limit)

**Without Caching:**
```
SPICE calls without cache: 120 per minute
Rate limit: 2 per minute
Result: ❌ FAIL after 10 seconds
```

---

## 10. Advanced: Circuit Breaker Status

**Endpoint:** `GET /api/v1/health` (includes circuit breaker state)

**Response:**
```json
{
    "status": "healthy",
    "circuit_breakers": {
        "spice_health_check": "closed",  // Normal
        "spice_load_omm": "closed",      // Normal
        "spice_propagate": "open"        // OPEN = Failing!
    }
}
```

**Circuit Breaker States:**
- `closed` → Normal operation ✅
- `open` → Too many failures, blocked for recovery ⏸️
- `half_open` → Testing if recovered 🔄

---

## Summary

**Key Takeaways:**
1. **Cache aggressively** (30s health, 5s positions, 5min orbits)
2. **Batch operations** (≥50 satellites)
3. **Retry with backoff** (exponential: 10s, 20s, 40s)
4. **Monitor rate limits** (`/rate-limits/spice`)
5. **Handle 429 errors** gracefully

**Result:**
- ✅ Professional API usage
- ✅ No service overload
- ✅ Optimal performance
- ✅ Happy users

---

**Questions?**  
Check `/rate-limits/spice` endpoint for real-time usage stats.

**Violations?**  
Review logs for `rate_limiter_throttled` warnings.

**Need Higher Limits?**  
Deploy additional SPICE instances and load balance.
