# Load Testing Suite

Performance validation for SpaceX Orbital Intelligence Platform using k6.

## Prerequisites

```bash
# macOS
brew install k6

# Linux
sudo apt install k6

# Docker
docker pull grafana/k6
```

## Test Suites

### 1. Smoke Test (CI/CD)
**Purpose:** Fast sanity check for every PR  
**Duration:** 30 seconds  
**Load:** 10 concurrent users  
**Thresholds:** p95 < 1s, error rate < 1%

```bash
k6 run tests/load/smoke.js
```

**When to run:**
- Every PR in CI/CD
- Before deploying to staging
- After infrastructure changes

---

### 2. Sustained Load Test
**Purpose:** Validate production capacity  
**Duration:** 7.5 minutes (30s warmup + 2m ramp + 5m sustained + 30s ramp-down)  
**Load:** 200 concurrent users  
**Thresholds:** p95 < 500ms, error rate < 1%

```bash
k6 run tests/load/sustained.js
```

**When to run:**
- Weekly performance regression test
- Before major releases
- After performance optimizations

**Endpoints tested:**
- `/health` - Health check
- `/api/v1/satellites` - List satellites
- `/api/v1/satellites/positions` - Get positions (CRITICAL)
- `/api/v1/analytics/constellation-overview` - Analytics
- `/api/v1/simulation/launch` - Monte Carlo (10% of users)

---

### 3. Spike Test
**Purpose:** Stress test for traffic bursts  
**Duration:** 4.5 minutes  
**Load:** 100 → 1000 → 100 VUs  
**Thresholds:** p95 < 2s, error rate < 5%

```bash
k6 run tests/load/spike.js
```

**When to run:**
- Before launch events (high traffic expected)
- Quarterly resilience testing
- After scaling infrastructure

---

## Test Environment

**Recommended:**
```bash
# Set custom base URL
export BASE_URL=https://staging.spacex.ericcesar.com
k6 run tests/load/sustained.js
```

**Default:** `https://spacex.ericcesar.com` (production)

---

## Interpreting Results

### Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| p50 latency | < 100ms | ✅ |
| p95 latency | < 500ms | ✅ |
| p99 latency | < 1000ms | ✅ |
| Throughput | > 1000 req/s | ✅ |
| Error rate | < 0.1% | ✅ |

### Failure Indicators

**High Latency (p95 > 500ms):**
- Possible bottleneck in orbital propagation
- Database query optimization needed
- Consider caching positions (60s TTL)

**High Error Rate (> 1%):**
- Check logs: `docker logs spacex-orbital-backend`
- Look for timeout errors
- Check database connection pool

**Low Throughput (<1000 req/s):**
- CPU-bound (profile with py-spy)
- Database locks
- Network bandwidth

---

## CI/CD Integration

### GitHub Actions

**File:** `.github/workflows/performance.yml`

```yaml
name: Performance Smoke Test

on:
  pull_request:
    branches: [main]

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6
      
      - name: Run smoke test
        run: k6 run tests/load/smoke.js --out json=smoke-results.json
        env:
          BASE_URL: https://staging.spacex.ericcesar.com
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: k6-results
          path: smoke-results.json
```

---

## Scheduled Tests

**Weekly sustained load test:**

```bash
# crontab
0 2 * * 1 cd /home/clawd/prod/spacex-orbital-intelligence && k6 run tests/load/sustained.js --out json=/var/log/k6/weekly-$(date +\%Y-\%m-\%d).json
```

---

## Profiling During Load Test

**Recommended workflow:**

```bash
# Terminal 1: Start load test
k6 run tests/load/sustained.js

# Terminal 2: Profile backend (60s sample)
docker exec spacex-orbital-backend py-spy record -o profile.svg --pid 1 --duration 60

# Analyze profile.svg to identify bottlenecks
```

---

## Grafana Dashboard

Import `grafana/dashboards/load-testing.json` to visualize:
- HTTP request duration (p50/p95/p99)
- Throughput (req/s)
- Error rate
- WebSocket connections
- Cache hit rate

---

## Troubleshooting

### Test Fails Immediately

**Error:** `ECONNREFUSED`

```bash
# Check if backend is running
curl https://spacex.ericcesar.com/health

# Check Docker
docker ps | grep spacex-orbital-backend
```

### High Latency Only During Test

**Cause:** Cold cache

```bash
# Pre-warm cache before test
curl https://spacex.ericcesar.com/api/v1/satellites?limit=100
sleep 2
k6 run tests/load/sustained.js
```

### Rate Limit Hit (429 errors)

**Fix:** Increase rate limit for load testing

```python
# app/core/security.py
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/minute"]  # Increase for load testing
)
```

---

## Performance Baseline (2026-02-10)

**Environment:** AWS EC2 t3.medium (2 vCPU, 4GB RAM)  
**Test:** Sustained load (200 VUs, 5min)

| Metric | Value |
|--------|-------|
| p50 latency | TBD |
| p95 latency | TBD |
| p99 latency | TBD |
| Throughput | TBD |
| Error rate | TBD |

**Run your first test to establish baseline!**

```bash
k6 run tests/load/sustained.js
```

Then update this README with actual numbers.

---

## Next Steps

1. ✅ Run smoke test locally
2. ⬜ Run sustained load test
3. ⬜ Document baseline metrics
4. ⬜ Add to CI/CD
5. ⬜ Schedule weekly tests
6. ⬜ Create Grafana dashboard
