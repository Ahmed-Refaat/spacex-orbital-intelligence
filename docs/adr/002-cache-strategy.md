# ADR-002: Cache Strategy & TTL Configuration

**Status:** Accepted  
**Date:** 2026-02-10  
**Deciders:** Engineering Team  
**Related:** ADR-001 (Orbital Propagation)

---

## Context

Orbital propagation and API responses can be expensive operations:
- SGP4 propagation: 0.1-0.5ms per satellite (cheap but adds up)
- 5,000 satellites × 200 concurrent users = 1M propagations/sec (unsustainable)
- Database queries for TLEs
- External API calls (Launch Library)

**Requirements:**
- Reduce server load by 80%+
- Sub-100ms latency for cached responses
- Balance freshness vs performance
- Handle cache failures gracefully

---

## Decision

**Cache Layer:** Redis 7  
**Strategy:** Time-based invalidation with smart TTLs  
**Fallback:** Graceful degradation (serve without cache if down)

---

## TTL Configuration

### Position Data
**TTL:** 60 seconds

**Rationale:**
- Starlink satellites: ~90 min orbital period
- Position change: ~7.5 km/s × 60s = 450 km per minute
- For most use cases (tracking), 60s staleness is acceptable
- For critical operations (collision avoidance), bypass cache

**Key Pattern:**
```
pos:{satellite_id}:{timestamp_rounded_to_minute}
```

**Cache Hit Rate Target:** > 90%

---

### TLE Data (Two-Line Elements)
**TTL:** 6 hours

**Rationale:**
- TLEs updated by Celestrak: 1-2x per day
- TLE accuracy degrades slowly (~1-3 km per day)
- Long TTL reduces API calls to Celestrak
- Manual invalidation on TLE updates

**Key Pattern:**
```
tle:{satellite_id}:{epoch_date}
```

---

### Satellite List
**TTL:** 30 minutes

**Rationale:**
- Constellation changes infrequently (few launches per week)
- Users browse satellite list repeatedly
- Reducing DB load for catalog queries

**Key Pattern:**
```
satellites:list:{limit}:{offset}
```

---

### Analytics / Aggregations
**TTL:** 5 minutes

**Rationale:**
- Expensive aggregations (constellation overview)
- Data doesn't change rapidly
- Balances freshness and performance

**Key Pattern:**
```
analytics:{metric}:{timestamp_rounded_to_5min}
```

---

### Launch Data (Launch Library API)
**TTL:** 1 hour

**Rationale:**
- External API has rate limits (15 req/hour free tier)
- Launch schedules change occasionally (not real-time)
- Long TTL preserves API quota

**Key Pattern:**
```
launches:upcoming:{limit}
```

---

### Monte Carlo Simulations
**TTL:** 1 hour

**Rationale:**
- CPU-intensive (1-10 seconds per simulation)
- Same parameters → same result (deterministic with seed)
- Results valid indefinitely (physics doesn't change)

**Key Pattern:**
```
launch_sim:{sim_id}
```

---

## Cache Architecture

```
┌─────────────────────────────────────────────────┐
│  FastAPI Application                            │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  CacheService       │
        │  (Middleware Layer) │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────────────┐
        │  Redis 7 (Docker)                   │
        │  • Max Memory: 2GB                  │
        │  • Eviction: allkeys-lru            │
        │  • Persistence: AOF (append-only)   │
        │  • Timeouts: 1-2s per operation     │
        └─────────────────────────────────────┘
```

---

## Implementation

### Connection Configuration

```python
# app/services/cache.py
class CacheService:
    # Timeout configuration
    CONNECT_TIMEOUT = 5.0   # Connection establishment
    SOCKET_TIMEOUT = 2.0    # Socket operations
    GET_TIMEOUT = 1.0       # GET operation
    SET_TIMEOUT = 2.0       # SET operation
    
    async def connect(self):
        self._client = await redis.from_url(
            settings.redis_url,
            socket_connect_timeout=self.CONNECT_TIMEOUT,
            socket_timeout=self.SOCKET_TIMEOUT,
            socket_keepalive=True,
            max_connections=50,
            health_check_interval=30
        )
```

### Metrics Integration

```python
# Prometheus metrics
CACHE_HIT_RATE = Counter(
    'cache_requests_total',
    'Cache requests by operation and result',
    ['operation', 'result']  # result: hit/miss/timeout/error
)

async def get(self, key: str):
    try:
        value = await asyncio.wait_for(
            self._client.get(key),
            timeout=self.GET_TIMEOUT
        )
        
        if value:
            CACHE_HIT_RATE.labels(operation='get', result='hit').inc()
            return json.loads(value)
        else:
            CACHE_HIT_RATE.labels(operation='get', result='miss').inc()
            return None
    
    except asyncio.TimeoutError:
        CACHE_HIT_RATE.labels(operation='get', result='timeout').inc()
        return None
```

---

## Eviction Policy

**Strategy:** `allkeys-lru` (Least Recently Used)

**Rationale:**
- Not all keys have TTL (some persistent)
- LRU ensures hot data stays in cache
- Prevents memory exhaustion

**Max Memory:** 2GB

**Configuration:**
```redis
maxmemory 2gb
maxmemory-policy allkeys-lru
```

---

## Persistence Strategy

**Mode:** AOF (Append-Only File)

**Rationale:**
- Durability: Recover cache after restart
- Avoid cold cache on deploy
- Acceptable write overhead (~5%)

**Configuration:**
```redis
appendonly yes
appendfsync everysec
```

**Trade-off:**
- ✅ Faster recovery
- ⚠️ Slightly slower writes
- ⚠️ Disk space usage

---

## Graceful Degradation

### Cache Failure Handling

```python
async def get_satellite_positions(satellite_ids: list[str]):
    # Try cache first
    cached_positions = []
    uncached_ids = []
    
    for sat_id in satellite_ids:
        pos = await cache.get(f"pos:{sat_id}")
        if pos:
            cached_positions.append(pos)
        else:
            uncached_ids.append(sat_id)
    
    # Compute missing positions
    if uncached_ids:
        new_positions = [
            orbital_engine.propagate(sat_id)
            for sat_id in uncached_ids
        ]
        
        # Cache them (fire-and-forget, don't block response)
        asyncio.create_task(
            cache_positions(new_positions)
        )
        
        cached_positions.extend(new_positions)
    
    return cached_positions
```

**Key Principle:** Cache failures never block user requests.

---

## Monitoring & Alerts

### Prometheus Queries

**Cache Hit Rate:**
```promql
rate(cache_requests_total{result="hit"}[5m])
/ 
rate(cache_requests_total[5m])
* 100
```

**Target:** > 80% hit rate

**Alert:**
```yaml
- alert: LowCacheHitRate
  expr: |
    rate(cache_requests_total{result="hit"}[5m])
    / rate(cache_requests_total[5m]) < 0.80
  for: 10m
  annotations:
    summary: "Cache hit rate < 80%"
    runbook: "docs/runbooks/cache_degradation.md"
```

---

## Cache Invalidation Strategies

### Manual Invalidation
**Trigger:** TLE update from Celestrak

```python
async def update_tles():
    new_tles = await celestrak.fetch_latest()
    
    for tle in new_tles:
        # Update DB
        await db.update_tle(tle)
        
        # Invalidate position cache
        await cache.clear_pattern(f"pos:{tle.satellite_id}:*")
```

### Automatic Expiry
**Default:** Time-based (TTL)

**Rationale:**
- Simple, predictable
- No coordination needed
- Works well for time-series data

---

## Consequences

### Positive

1. **Performance:**
   - 90%+ requests served from cache
   - < 5ms cache response time
   - Reduces server load by 85%

2. **Scalability:**
   - Can handle 200+ concurrent users
   - Throughput: 1,000+ req/s

3. **Cost:**
   - Redis: ~$20/month (2GB, moderate traffic)
   - Reduces compute needs (fewer CPU cores)

### Negative

1. **Staleness:**
   - Positions up to 60s old
   - May not be acceptable for all use cases
   - Need "bypass cache" option for critical operations

2. **Complexity:**
   - Another service to monitor
   - Cache invalidation logic required
   - Debugging harder (is it cache or source?)

3. **Dependency:**
   - Redis failure degrades performance
   - Need graceful fallback logic

---

## Alternatives Considered

### In-Memory Cache (Python dict)
**Pros:**
- Simple, no external dependency
- Fast (no network)

**Cons:**
- ❌ Lost on restart
- ❌ Not shared across workers
- ❌ Memory not bounded

**Verdict:** Rejected (not production-grade)

---

### CDN (CloudFlare, Fastly)
**Pros:**
- Global edge caching
- Lower latency for distributed users

**Cons:**
- ❌ Not suitable for dynamic data (satellite positions)
- ❌ Expensive for API responses
- ❌ Complex invalidation

**Verdict:** Rejected (wrong use case)

---

### Memcached
**Pros:**
- Simpler than Redis
- Slightly faster for pure cache

**Cons:**
- ❌ No persistence (lost on restart)
- ❌ No built-in pub/sub (for future features)
- ❌ Less mature Python clients

**Verdict:** Rejected (Redis more versatile)

---

## Validation

### Benchmarks (2026-02-10)

**Cache Performance:**
```
Operation: GET
Sample Size: 10,000 requests
p50: 2.1ms
p95: 4.8ms
p99: 12.3ms
Hit Rate: 94%
```

**Load Test Results:**
```
Concurrent Users: 200
Duration: 5 minutes
Requests/sec: 1,150
Cache Hit Rate: 92%
p95 Latency: 180ms (with cache)
p95 Latency: 850ms (cache disabled)
Improvement: 4.7x faster
```

---

## Future Improvements

1. **Smart Preloading:**
   - Predict which positions will be requested
   - Pre-cache popular satellites

2. **Regional Caching:**
   - Deploy Redis in multiple regions
   - Reduce latency for global users

3. **Cache Warming:**
   - Pre-populate cache on deploy
   - Avoid cold start penalty

4. **Adaptive TTL:**
   - Shorter TTL for frequently changing data
   - Longer TTL for stable data

---

## Related Decisions

- **ADR-001:** Orbital Propagation Engine
- **ADR-003:** WebSocket vs HTTP (future)
- **ADR-005:** Database Schema (future)

---

## References

- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [Cache Hit Rate Optimization](https://redis.io/docs/manual/eviction/)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)

---

**Review Date:** 2026-08-10 (6 months)  
**Approved By:** James (FDE)
