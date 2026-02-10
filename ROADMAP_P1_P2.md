# 🗺️ ROADMAP P1/P2 - Production Hardening
**Version:** Post-P0 fixes  
**Date:** 2026-02-10  
**Status:** P0 ✅ Complete | P1/P2 📋 Pending

---

## ✅ P0 COMPLETED (2026-02-10)

### Security
- [x] Satellite ID validation (regex `^\d{1,5}$`)
- [x] Tests for injection prevention
- [x] Secrets not in Git (verified `.env` in `.gitignore`)

### Robustness
- [x] Timeout reduced: 180s → 30s
- [x] Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
- [x] Circuit breakers added to ALL external services:
  - [x] Launch Library 2 (`@circuit` on get_upcoming_launches, get_previous_launches)
  - [x] Celestrak (`@circuit` on fetch_starlink_tle, fetch_active_satellites)
  - [x] N2YO (`@circuit` on get_tle)
  - [x] SpaceX API (already protected)
- [x] Tests for circuit breaker presence

### Performance
- [x] Frontend lazy loading (Globe, Sidebar)
- [x] Manual chunk splitting (4 vendor chunks)
- [x] Bundle size: 1.2MB → ~500KB (estimated)

### Tests
- [x] test_satellite_id_validation.py (injection tests)
- [x] test_timeout_resilience.py (timeout & retry tests)
- [x] test_circuit_breakers_all_services.py (circuit breaker coverage)

**Current Score: 6.5/10** (up from 4/10)

---

## 🟠 P1 - PRODUCTION HARDENING (5 weeks)

### 1. OBSERVABILITÉ (2 weeks, $$$)

#### OpenTelemetry Tracing
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

**Objectives:**
- Request ID propagation
- Distributed tracing (API → Services → External APIs)
- Correlation IDs in all logs
- Latency tracking (p50, p95, p99)

**Implementation:**
```python
# app/main.py
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)
FastAPIInstrumentor.instrument_app(app)

# All logs get trace_id automatically
logger.info("Event", trace_id=trace.get_current_span().context.trace_id)
```

**Cost:** ~$50/month (Jaeger cloud / Honeycomb)

---

#### Sentry Error Tracking
```bash
pip install sentry-sdk
```

**Objectives:**
- Real-time error alerts
- Stack traces with context
- Performance monitoring
- Release tracking

**Implementation:**
```python
import sentry_sdk
sentry_sdk.init(
    dsn="https://xxx@sentry.io/xxx",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)
```

**Cost:** ~$26/month (Developer plan)

---

#### Request ID Middleware
```python
# app/middleware/request_id.py
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    with logger.bind(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
    return response
```

**Impact:** MTTR 30min → 5min

---

### 2. TESTS COVERAGE (3 weeks, 2 devs)

#### Target: 60% Coverage

**Critical Modules:**
- [x] `app/services/orbital_engine.py` (calculs orbitaux)
- [ ] `app/services/spice_client.py` (intégration SPICE)
- [ ] `app/core/logging_sanitizer.py` (sécurité critique)
- [ ] `app/api/websocket.py` (temps réel)

**Test Types:**

```bash
# Unit tests
pytest tests/unit/ --cov=app --cov-report=html
# Target: 60%

# Integration tests
pytest tests/integration/ -v
# API → Services → Redis/DB

# Property-based tests (orbital mechanics)
pip install hypothesis
pytest tests/property/ -v
# Test: orbital invariants (energy conservation, etc.)
```

**Example Property Test:**
```python
from hypothesis import given, strategies as st

@given(
    altitude=st.floats(min_value=200, max_value=2000),
    inclination=st.floats(min_value=0, max_value=180)
)
def test_orbital_period_invariant(altitude, inclination):
    """Orbital period depends only on semi-major axis."""
    period1 = calculate_period(altitude, inclination)
    period2 = calculate_period(altitude, inclination + 10)
    
    # Period should not change with inclination
    assert abs(period1 - period2) / period1 < 0.01
```

---

### 3. E2E TESTS (2 weeks)

```bash
pip install playwright
playwright install
```

**Critical User Flows:**
1. Load page → See globe → Select satellite → View details
2. WebSocket connection → Real-time updates
3. Search satellite → Filter by altitude → Select
4. Launch tab → View upcoming → Click details

**Example:**
```python
# tests/e2e/test_satellite_selection.py
async def test_user_can_select_satellite(page):
    await page.goto("https://spacex.ericcesar.com")
    
    # Wait for globe to load
    await page.wait_for_selector(".canvas-container")
    
    # Open sidebar
    await page.click("[data-testid='sidebar-toggle']")
    
    # Search for satellite
    await page.fill("[data-testid='satellite-search']", "44000")
    await page.click("[data-testid='satellite-44000']")
    
    # Verify details panel
    details = await page.text_content("[data-testid='satellite-details']")
    assert "STARLINK-1000" in details
```

---

### 4. ARCHITECTURE REFACTOR (3 weeks, breaking changes)

#### Dependency Injection Container

```bash
pip install dependency-injector
```

**Before (coupled):**
```python
class OrbitalEngine:
    def __init__(self):
        self.redis = redis.Redis()  # ❌ Direct dependency
```

**After (DI):**
```python
class OrbitalEngine:
    def __init__(self, cache: CacheInterface):
        self.cache = cache  # ✅ Interface injection

# container.py
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    cache = providers.Singleton(
        RedisCache,
        url=config.redis_url
    )
    
    orbital_engine = providers.Factory(
        OrbitalEngine,
        cache=cache
    )
```

**Benefits:**
- Testable without Redis
- Swappable implementations
- Clear dependencies

---

#### Domain Layer Isolation

```
app/
├── domain/           # ✨ NEW
│   ├── models/      # Pure domain objects
│   ├── services/    # Business logic
│   └── interfaces/  # Contracts
├── infrastructure/   # Redis, HTTP, DB
└── api/             # FastAPI routes
```

**Principle:** Domain never depends on infrastructure

---

### 5. LOAD TESTING (1 week)

```bash
# k6 scenarios
k6 run tests/load/sustained.js --vus 100 --duration 10m
k6 run tests/load/spike.js --vus 1000 --duration 1m
```

**Objectives:**
- WebSocket: 1000 concurrent connections
- API: 500 req/s sustained
- TLE update: <30s under load
- No memory leaks

**Metrics:**
- Response time p95 < 200ms
- Error rate < 0.1%
- CPU < 80% under load

---

## 🔵 P2 - SPATIAL-GRADE (2 months)

### 1. COMPLIANCE & SECURITY (4 weeks, external audit)

#### ISO/IEC 25010 Audit
- Quality model compliance
- Security characteristics
- Reliability assessment

**Cost:** ~$5k-10k (external auditor)

---

#### OWASP Top 10 Full Scan
```bash
# ZAP (OWASP) automated scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://spacex.ericcesar.com
```

**Manual Tests:**
- [ ] Injection (SQL, NoSQL, Command)
- [ ] Broken Authentication
- [ ] Sensitive Data Exposure
- [ ] XML External Entities (XXE)
- [ ] Broken Access Control
- [ ] Security Misconfiguration
- [ ] XSS
- [ ] Insecure Deserialization
- [ ] Components with Known Vulnerabilities
- [ ] Insufficient Logging & Monitoring

---

#### Penetration Testing
**Cost:** ~$10k-20k (professional firm)

**Scope:**
- Network scanning
- Vulnerability exploitation
- Social engineering (phishing test)
- Report + remediation plan

---

### 2. CHAOS ENGINEERING (2 weeks)

```python
# tests/chaos/test_resilience.py
import chaos_toolkit

async def test_circuit_breaker_under_chaos():
    """Kill external service, verify circuit breaker opens."""
    # Simulate Celestrak down
    with chaos.kill_service("celestrak"):
        # Should fail fast (not hang)
        with pytest.raises(CircuitBreakerError):
            await tle_service.fetch_celestrak()
```

**Scenarios:**
- Kill Redis → Graceful degradation
- Kill PostgreSQL → Read-only mode
- Slow external API → Timeout handling
- Network partition → Fallback sources

---

### 3. DISASTER RECOVERY (3 weeks)

#### Multi-Region Deployment
```yaml
# docker-compose.prod.yml
services:
  backend-us-east:
    deploy:
      replicas: 3
  backend-eu-west:
    deploy:
      replicas: 3
```

#### Data Replication
- PostgreSQL: Primary + 2 replicas
- Redis: Cluster mode (3 masters, 3 replicas)
- TLE cache: Multi-region sync

#### Backup Strategy
```bash
# Daily backups
0 2 * * * pg_dump spacex_orbital | gzip > backup-$(date +\%Y\%m\%d).sql.gz

# Retention: 30 days
# Test restore monthly
```

#### RTO/RPO Targets
- RTO (Recovery Time Objective): < 15 minutes
- RPO (Recovery Point Objective): < 5 minutes

---

### 4. NASA SOFTWARE STANDARDS REVIEW (4 weeks)

#### NPR 7150.2D Compliance
- Software Engineering Requirements
- Software Safety Critical classification
- IV&V (Independent Verification & Validation)

**Deliverables:**
- Software Requirements Specification (SRS)
- Software Design Document (SDD)
- Software Test Plan (STP)
- Hazard Analysis Report
- V&V Report

---

### 5. DOCUMENTATION (2 weeks)

#### Architecture Decision Records (ADR)
```markdown
# ADR-001: Use SGP4 for orbit propagation

## Status
Accepted

## Context
Need fast, accurate orbit propagation for 2000+ satellites.

## Decision
Use SGP4 algorithm with SPICE fallback.

## Consequences
+ Fast (1000s of propagations/sec)
+ Industry standard
- Less accurate than numerical integration
```

#### Runbooks
- [x] Incident: High latency
- [ ] Incident: Circuit breaker open
- [ ] Incident: TLE update failed
- [ ] Incident: WebSocket disconnects
- [ ] Deployment: Blue-green deployment
- [ ] Deployment: Rollback procedure

#### API Contracts (OpenAPI strict mode)
```yaml
# openapi.yaml
paths:
  /api/v1/satellites/{satellite_id}:
    get:
      parameters:
        - name: satellite_id
          schema:
            type: string
            pattern: '^\d{1,5}$'  # ✅ STRICT
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SatelliteDetail'
```

---

## 📊 TIMELINE & RESOURCES

| Phase | Duration | Team | Cost | Status |
|-------|----------|------|------|--------|
| **P0** | 2 weeks | 1 dev | $0 | ✅ Done |
| **P1** | 5 weeks | 2 devs | ~$100/mo | 📋 TODO |
| **P2** | 2 months | 2 devs + external | ~$20k | 📋 TODO |

**Total:** ~3.5 months, ~$20k + salaries

---

## 🎯 DECISION POINTS

Rico, voici les décisions à prendre:

### Immediate (P1 start)
1. **Observabilité:** Quel budget pour Sentry/OpenTelemetry? (~$80/mo)
2. **Tests:** Allouer 2 devs pendant 3 semaines pour coverage 60%?
3. **E2E:** Setup Playwright ou attendre?

### Mid-term (P2 planning)
1. **Audit externe:** Budget $15-30k pour compliance/pentest?
2. **Multi-region:** Worth it maintenant ou attendre scale?
3. **NASA standards:** Requis pour ton use case?

### Quick Wins (can do now)
1. **Observabilité basique:** Request ID middleware (1 jour)
2. **Tests prioritaires:** Orbital engine coverage (1 semaine)
3. **Load testing baseline:** k6 smoke tests (2 jours)

---

## 📈 EXPECTED OUTCOMES

### After P1 (5 weeks)
- **Score:** 6.5/10 → 8/10
- **Coverage:** 15% → 60%
- **MTTR:** 30min → 5min
- **Observability:** Full tracing + error tracking

### After P2 (3.5 months total)
- **Score:** 8/10 → 9/10
- **Status:** Spatial-grade ✅
- **Compliance:** ISO/IEC 25010, OWASP Top 10
- **Reliability:** 99.9% uptime

---

**Next Step:** Prioriser P1 tasks et allouer ressources 💪
