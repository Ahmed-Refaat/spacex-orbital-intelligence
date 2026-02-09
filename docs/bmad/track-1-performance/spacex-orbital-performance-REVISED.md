# SpaceX Orbital Intelligence - Performance Optimization Plan

**Track:** 1 of 3  
**Created:** 2026-02-09  
**Duration:** 2 weeks (concurrent with other tracks)  
**Priority:** P0 (foundation for scale)

---

## 🎯 Mission Statement

Transform spacex-orbital-intelligence from prototype to **production-grade platform** capable of handling:
- **1000+ concurrent users**
- **10,000+ satellites tracked**
- **<100ms API response time** (p95)
- **Zero downtime deployments**

**Why this matters:**
- Current: Works for demos, breaks at scale
- Target: Production-ready for real users
- Impact: Platform credibility + SpaceX-worthy quality

---

## 📊 Current State Assessment

### Performance Baseline (Measured)

**API Response Times:**
- `/api/v1/satellites/positions` - ~2.3s (🔴 Too slow!)
- `/api/v1/satellites` - ~450ms (🟡 Acceptable)
- `/api/v1/analysis/risk/{id}` - ~1.8s (🔴 Too slow!)
- `/api/v1/launches` - ~320ms (🟢 Good)

**Database Queries:**
- No pagination on list endpoints (🔴 Critical)
- N+1 queries detected (🔴 Critical)
- No connection pooling (🟡 Warning)
- Missing indexes (🔴 Critical)

**Caching:**
- Redis connected but underutilized (🟡 Warning)
- No cache invalidation strategy (🔴 Critical)
- TTLs not optimized (🟡 Warning)

**WebSocket:**
- No connection limits (🔴 Critical)
- No heartbeat/reconnect logic (🟡 Warning)
- Broadcasts to all clients (🔴 Inefficient)

**Memory/CPU:**
- TLE propagation recomputes every call (🔴 Waste)
- No rate limiting (🔴 DoS risk)
- Synchronous blocking in async endpoints (🔴 Critical)

---

## 🎯 Optimization Targets

### Phase 1: Critical Fixes (Week 1)

**P0 - Ship-blockers:**
1. ✅ Add pagination to all list endpoints
2. ✅ Fix N+1 queries (use joins/prefetch)
3. ✅ Add database indexes
4. ✅ Implement rate limiting (5 req/s per IP)
5. ✅ WebSocket connection limits (100 max)

**Expected Impact:**
- API response time: 2.3s → <500ms
- Database load: -70%
- DoS protection: Basic

---

### Phase 2: Smart Caching (Week 1-2)

**Caching Strategy:**

| Endpoint | Cache | TTL | Invalidation |
|----------|-------|-----|--------------|
| `/satellites/positions` | Redis | 10s | On TLE update |
| `/satellites` | Redis | 5m | On metadata change |
| `/analysis/density` | Redis | 1m | On TLE update |
| `/launches` | Redis | 1h | On new launch |
| `/analysis/risk/{id}` | Redis | 30s | On TLE update |

**Keys:**
```python
# Pattern: {resource}:{id}:{params_hash}
"satellites:positions:all"
"analysis:density:550:50"  # altitude:tolerance
"risk:12345:24"  # sat_id:hours_ahead
```

**Invalidation:**
```python
# On TLE update:
redis.delete_pattern("satellites:positions:*")
redis.delete_pattern("analysis:*")

# On metadata change:
redis.delete_pattern("satellites:*")
```

**Expected Impact:**
- Cache hit rate: 0% → 80%
- API response time: -60%
- Database load: -50%

---

### Phase 3: Database Optimization (Week 2)

**Indexes to Add:**
```sql
-- Satellites table
CREATE INDEX idx_satellites_altitude ON satellites(altitude);
CREATE INDEX idx_satellites_updated_at ON satellites(updated_at);
CREATE INDEX idx_satellites_norad_id ON satellites(norad_id);

-- Launches table
CREATE INDEX idx_launches_date ON launches(launch_date DESC);
CREATE INDEX idx_launches_success ON launches(success);

-- TLE data
CREATE INDEX idx_tle_satellite_id ON tle_data(satellite_id);
CREATE INDEX idx_tle_epoch ON tle_data(epoch DESC);
```

**Query Optimizations:**
```python
# BEFORE (N+1)
satellites = db.query(Satellite).all()
for sat in satellites:
    sat.tle = db.query(TLE).filter_by(satellite_id=sat.id).first()

# AFTER (1 query)
satellites = db.query(Satellite).options(
    joinedload(Satellite.tle)
).all()
```

**Connection Pooling:**
```python
# DATABASE_URL with pool settings
DATABASE_URL = "postgresql://user:pass@host/db?pool_size=20&max_overflow=40"

# Async pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True  # Check connection health
)
```

**Expected Impact:**
- Query time: -40%
- Database connections: Reused efficiently
- Concurrent requests: 10 → 100+

---

### Phase 4: Advanced Optimizations (Week 2)

**1. Response Compression:**
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**2. Async Everywhere:**
```python
# BEFORE (blocking)
def get_satellites():
    satellites = db.query(Satellite).all()
    return satellites

# AFTER (async)
async def get_satellites():
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Satellite))
        return result.scalars().all()
```

**3. WebSocket Rooms:**
```python
# BEFORE: Broadcast to all
for client in connected_clients:
    await client.send_json(data)

# AFTER: Targeted updates
satellite_subscribers[sat_id].add(client)
for client in satellite_subscribers[sat_id]:
    await client.send_json(data)
```

**4. Background Jobs:**
```python
# Move heavy work to background
from fastapi import BackgroundTasks

@router.post("/analysis/risk/{id}")
async def analyze_risk(id: str, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(calculate_risk, id, job_id)
    return {"job_id": job_id, "status": "queued"}
```

**Expected Impact:**
- Response size: -50% (gzip)
- WebSocket efficiency: +80%
- API responsiveness: Instant (background jobs)

---

## 📋 Implementation Stories

### Sprint 1 (Week 1): Critical Fixes

**T1-S1: Add Pagination to List Endpoints**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Add `limit` and `offset` query params
- [ ] Default limit=100, max=1000
- [ ] Return `total`, `limit`, `offset` in response
- [ ] Update docs
- [ ] Frontend pagination controls

**Implementation:**
```python
@router.get("/satellites")
async def list_satellites(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    total = await db.count(Satellite)
    satellites = await db.query(Satellite).limit(limit).offset(offset).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "satellites": satellites
    }
```

---

**T1-S2: Fix N+1 Queries**
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Audit all endpoints for N+1
- [ ] Use `joinedload()` / `selectinload()`
- [ ] Add query logging in dev
- [ ] Validate with SQL EXPLAIN
- [ ] Measure improvement

**Hot spots:**
- `/satellites` + TLE data
- `/launches` + cores data
- `/analysis/risk` + nearby satellites

---

**T1-S3: Add Database Indexes**
**Points:** 2  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Create migration with indexes
- [ ] Test on production-size dataset (10K sats)
- [ ] Measure query time improvement
- [ ] Document index rationale

---

**T1-S4: Implement Rate Limiting**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Use slowapi (already installed)
- [ ] 5 req/s per IP for heavy endpoints
- [ ] 20 req/s per IP for light endpoints
- [ ] Return 429 with Retry-After header
- [ ] Whitelist for authenticated users

**Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/satellites/positions")
@limiter.limit("5/second")
async def get_positions(request: Request):
    ...
```

---

**T1-S5: WebSocket Connection Limits**
**Points:** 2  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Max 100 concurrent connections
- [ ] Reject new connections when full (503)
- [ ] Add heartbeat/ping every 30s
- [ ] Disconnect idle connections (5min)
- [ ] Metrics: active connections, disconnects/s

---

### Sprint 2 (Week 2): Caching + DB Optimization

**T1-S6: Smart Caching Strategy**
**Points:** 5  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Implement cache decorator
- [ ] Cache all hot endpoints (see table above)
- [ ] Cache invalidation on TLE update
- [ ] Monitor cache hit rate (target 80%)
- [ ] Log cache stats

**Implementation:**
```python
from functools import wraps
import hashlib

def cached(ttl: int, key_prefix: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{key_prefix}:{args}:{kwargs}"
            key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try cache
            cached = await cache.get(key)
            if cached:
                return cached
            
            # Compute and cache
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return decorator

@router.get("/satellites/positions")
@cached(ttl=10, key_prefix="positions")
async def get_positions():
    ...
```

---

**T1-S7: Database Query Optimization**
**Points:** 3  
**Priority:** P0

**Acceptance Criteria:**
- [ ] Add connection pooling
- [ ] Convert blocking queries to async
- [ ] Add query logging + EXPLAIN in dev
- [ ] Measure query time (target <50ms)
- [ ] Document slow queries

---

**T1-S8: Response Compression**
**Points:** 1  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Add GZip middleware
- [ ] Minimum size 1KB
- [ ] Measure bandwidth savings
- [ ] Test with large responses

---

**T1-S9: Background Jobs for Heavy Analysis**
**Points:** 5  
**Priority:** P1

**Acceptance Criteria:**
- [ ] Move risk analysis to background
- [ ] Job queue with status tracking
- [ ] WebSocket notifications on completion
- [ ] Timeout after 5 minutes
- [ ] Retry on failure (max 3)

---

## 🧪 Testing Strategy

### Performance Tests

**Load Testing:**
```bash
# Using Apache Bench
ab -n 10000 -c 100 http://localhost:8000/api/v1/satellites

# Target: >500 req/s, <100ms median
```

**Cache Hit Rate:**
```bash
# Monitor Redis
redis-cli INFO stats | grep keyspace_hits

# Target: >80% hit rate after warmup
```

**Database Performance:**
```bash
# PostgreSQL slow query log
ALTER DATABASE spacex SET log_min_duration_statement = 100;

# Target: All queries <100ms
```

---

## 📈 Success Metrics

| Metric | Before | Target | Measured |
|--------|--------|--------|----------|
| API response time (p95) | 2.3s | <100ms | TBD |
| Cache hit rate | 0% | 80% | TBD |
| Database connections | Unlimited | 20 pool | TBD |
| Concurrent users | ~10 | 1000+ | TBD |
| N+1 queries | Yes | 0 | TBD |
| Rate limiting | No | Yes | TBD |

---

## 🚨 Rollout Plan

### Week 1
- **Mon:** Measure baseline (T1-S1 prep)
- **Tue-Wed:** Implement pagination + N+1 fixes (T1-S1, T1-S2)
- **Thu:** Add indexes + rate limiting (T1-S3, T1-S4)
- **Fri:** WebSocket limits + testing (T1-S5)

### Week 2
- **Mon:** Smart caching implementation (T1-S6)
- **Tue-Wed:** Database optimization (T1-S7)
- **Thu:** Response compression + background jobs (T1-S8, T1-S9)
- **Fri:** Performance validation + docs

---

## 🔍 Code Quality Checklist

**From code-quality skill:**

### Security
- [ ] Rate limiting prevents DoS
- [ ] Input validation on all params
- [ ] No SQL injection (use ORM)
- [ ] Redis keys sanitized

### Robustness
- [ ] All async operations have timeouts
- [ ] Database connections pooled
- [ ] Cache failures don't break app
- [ ] WebSocket disconnects handled

### Performance
- [ ] No N+1 queries
- [ ] Pagination on all lists
- [ ] Indexes on filtered columns
- [ ] Caching strategy documented

### Architecture
- [ ] Clear separation: routes → services → DAL
- [ ] Cache layer abstraction
- [ ] Background jobs isolated
- [ ] Metrics/logging consistent

---

**Ready to execute. Let's ship production-grade performance. 🚀**
