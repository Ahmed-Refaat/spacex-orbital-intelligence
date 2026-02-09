# Architecture - Professional Monte Carlo Launch Simulator

**Date:** 2026-02-09  
**Status:** Design → Implementation  
**Skills Applied:** code-architecture, senior-code, microservices (if needed)

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User (Browser)                        │
└────────────┬────────────────────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────────────────────┐
│                  Frontend (React)                       │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Vehicle  │  │ Mission  │  │ Results Viewer     │  │
│  │ Selector │  │ Config   │  │ (Plots, ΔV, etc.)  │  │
│  └──────────┘  └──────────┘  └────────────────────┘  │
└────────────┬───────────────────────────────────────────┘
             │ REST API (JSON)
             ↓
┌────────────────────────────────────────────────────────┐
│              Backend (FastAPI + Python)                 │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │           API Layer (FastAPI)                     │ │
│  │  /vehicles, /missions, /simulate, /export        │ │
│  └────────────┬─────────────────────────────────────┘ │
│               │                                         │
│  ┌────────────┴─────────────────────────────────────┐ │
│  │         Core Simulation Engine                    │ │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │ │
│  │  │ Physics   │  │ Monte     │  │ Validation  │ │ │
│  │  │ Engine    │  │ Carlo     │  │ Suite       │ │ │
│  │  │ (Cython)  │  │ (GPU opt) │  │ (pytest)    │ │ │
│  │  └───────────┘  └───────────┘  └─────────────┘ │ │
│  └──────────────────────────────────────────────────┘ │
│               │                                         │
│  ┌────────────┴─────────────────────────────────────┐ │
│  │            Data Layer                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │ │
│  │  │ Vehicle  │  │ Mission  │  │ Results      │  │ │
│  │  │ Database │  │ Presets  │  │ Cache        │  │ │
│  │  │ (JSON +  │  │ (JSON)   │  │ (Redis)      │  │ │
│  │  │ Postgres)│  │          │  │              │  │ │
│  │  └──────────┘  └──────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture Decisions

### AD-001: Monolithic vs Microservices

**Decision:** Start monolithic, evolve to microservices if needed

**Rationale:**
- **Monolithic for MVP (Phase 0-6):**
  - Simpler deployment (single Docker container)
  - Faster development (no inter-service communication)
  - Easier debugging (all code in one place)
  - Lower operational complexity
  
- **Microservices for Scale (Phase 7-8, optional):**
  - Separate simulation workers (can scale independently)
  - Independent deployment of UI vs compute
  - Better resource utilization (GPU workers vs API servers)

**Implementation:**
```python
# Phase 0-6: Monolithic
app/
├── api/           # FastAPI routes
├── services/      # Business logic
│   ├── physics_engine.py
│   ├── monte_carlo.py
│   └── validation.py
├── models/        # Data models
└── utils/         # Helpers

# Phase 7-8: If needed, split to microservices
services/
├── api-gateway/       # User-facing API
├── simulation-worker/ # Compute-heavy tasks
└── data-service/      # Database access
```

**Review Trigger:** If API latency >500ms or workers bottleneck

---

### AD-002: Language Choice - Python vs C++/Rust

**Decision:** Python for MVP, Cython for performance-critical code

**Rationale:**
- **Python:**
  - Fast development (weeks vs months)
  - Rich ecosystem (NumPy, SciPy, FastAPI, Plotly)
  - Easy to recruit contributors (if open source)
  
- **Cython for Hot Path:**
  - Compile physics engine to C (5-15x speedup)
  - Still Python-compatible (gradual migration)
  - No full rewrite required
  
- **Not C++/Rust:**
  - Overkill for preliminary design tool
  - Slower development
  - Harder to validate (fewer aerospace engineers know these)

**Implementation:**
```python
# Phase 0-3: Pure Python
def calculate_drag(rho, v, Cd, A):
    return 0.5 * rho * v * v * Cd * A

# Phase 4: Cython-compiled hot functions
# physics_fast.pyx
cimport numpy as np
ctypedef np.float64_t DTYPE_t

cdef DTYPE_t calculate_drag_fast(DTYPE_t rho, DTYPE_t v, DTYPE_t Cd, DTYPE_t A):
    return 0.5 * rho * v * v * Cd * A
```

**Performance Target:** 100K Monte Carlo runs in <60s (Phase 4)

---

### AD-003: Database - PostgreSQL vs NoSQL

**Decision:** PostgreSQL for structured data, Redis for cache, JSON files for static configs

**Rationale:**
- **PostgreSQL:**
  - ACID transactions (important for user data)
  - Rich query capabilities (search simulations)
  - Mature, well-supported
  - JSONB column type (flexible for config storage)
  
- **Redis:**
  - Fast cache for simulation results (sub-ms access)
  - Pub/sub for real-time updates (future)
  - TTL for automatic cleanup
  
- **JSON Files (for vehicle/mission configs):**
  - Version-controlled with Git
  - Easy to edit and review
  - Community can contribute via PR
  - Load into database on startup

**Schema:**
```sql
-- Simulations table
CREATE TABLE simulations (
    id UUID PRIMARY KEY,
    user_id INT REFERENCES users(id),
    vehicle_id VARCHAR(50) REFERENCES vehicles(id),
    mission_config JSONB,
    parameters JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20), -- 'running', 'complete', 'failed'
    is_public BOOLEAN DEFAULT FALSE
);

-- Vehicles table (loaded from JSON)
CREATE TABLE vehicles (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    manufacturer VARCHAR(255),
    config JSONB, -- Full vehicle configuration
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users table (Phase 5+)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Data Flow:**
```
1. Vehicle configs (JSON files) → Loaded to PostgreSQL on startup
2. User runs simulation → Create record in PostgreSQL
3. Results cached in Redis (1 hour TTL)
4. User saves simulation → Update PostgreSQL
5. User shares → Generate public URL from PostgreSQL record
```

---

### AD-004: API Design - REST vs GraphQL

**Decision:** REST API for MVP, consider GraphQL later

**Rationale:**
- **REST:**
  - Simpler to implement and document
  - FastAPI has excellent OpenAPI auto-docs
  - Caching easier (HTTP standard)
  - Most users familiar with REST
  
- **GraphQL later (if needed):**
  - Better for complex queries (nested data)
  - Reduces over-fetching
  - Good for mobile clients (Phase 8+)

**Endpoints:**
```
GET    /api/v1/vehicles                 # List available vehicles
GET    /api/v1/vehicles/{id}            # Get vehicle details
GET    /api/v1/missions                 # List mission presets

POST   /api/v1/simulations              # Create simulation
GET    /api/v1/simulations/{id}         # Get results
GET    /api/v1/simulations/{id}/plots   # Get Plotly figures
GET    /api/v1/simulations/{id}/export/csv  # Export CSV

POST   /api/v1/simulations/batch        # Run multiple configs
GET    /api/v1/simulations/batch/{id}   # Get batch results

POST   /api/v1/optimize                 # Run optimization (Phase 7)
```

**Request/Response Format:**
```json
// POST /api/v1/simulations
{
  "vehicle_id": "falcon9_block5",
  "mission": {
    "type": "leo",
    "altitude_km": 400,
    "inclination_deg": 51.6
  },
  "payload_kg": 15000,
  "monte_carlo": {
    "n_runs": 10000,
    "seed": 42
  }
}

// Response
{
  "sim_id": "abc123",
  "status": "complete",
  "success_rate": 0.952,
  "delta_v_budget": {...},
  "orbital_elements": {...},
  "plots": {...}
}
```

---

### AD-005: Frontend - React vs Vue/Svelte

**Decision:** Stick with React (already used)

**Rationale:**
- **React:**
  - Already implemented in current codebase
  - Large ecosystem (Plotly, React Query, etc.)
  - Team familiar with it
  - Good performance with proper optimization
  
- **Libraries:**
  - **React Query:** Server state management, caching
  - **Plotly:** Interactive plots (aerospace standard)
  - **Tailwind CSS:** Rapid UI development
  - **Zustand:** Client state (simpler than Redux)

**Component Structure:**
```
src/
├── pages/
│   ├── HomePage.tsx           # Landing + quick start
│   ├── SimulatePage.tsx       # Main simulation UI
│   ├── ResultsPage.tsx        # Results viewer
│   └── LibraryPage.tsx        # Saved simulations
├── components/
│   ├── VehicleSelector/
│   ├── MissionConfig/
│   ├── MonteCarloConfig/
│   ├── TrajectoryPlot/
│   └── DeltaVTable/
├── hooks/
│   ├── useSimulation.ts       # Simulation API calls
│   └── useVehicles.ts         # Vehicle data
└── stores/
    └── simulationStore.ts     # Global state
```

---

### AD-006: Testing Strategy

**Decision:** TDD with pytest, 85%+ coverage enforced

**Test Pyramid:**
```
         ╱╲
        ╱  ╲   E2E (10%)
       ╱────╲  - Full workflow tests
      ╱      ╲
     ╱────────╲ Integration (30%)
    ╱          ╲ - API tests, validation tests
   ╱────────────╲
  ╱              ╲ Unit (60%)
 ╱────────────────╲ - Physics functions, math
```

**Test Categories:**

**1. Unit Tests (Fast, Many):**
```python
# test_physics.py
def test_gravity_decreases_with_altitude():
    g_0 = gravity(0)
    g_200 = gravity(200)
    assert g_0 > g_200
    assert abs(g_200 - 9.22) < 0.1  # Expected value

def test_tsiolkovsky_equation():
    # Analytical test
    delta_v = rocket_equation(Isp=300, mass_ratio=10)
    expected = 300 * 9.81 * np.log(10)
    assert abs(delta_v - expected) < 1.0
```

**2. Integration Tests (Medium Speed, Some):**
```python
# test_validation.py
def test_falcon9_crs21_validation():
    """Validate against real Falcon 9 CRS-21 flight."""
    vehicle = load_vehicle('falcon9_block5')
    mission = Mission(altitude=210, inclination=51.6, payload=2972)
    
    result = simulate_launch(vehicle, mission)
    
    # Real flight data
    assert abs(result.meco.altitude - 68) / 68 < 0.05  # <5% error
    assert abs(result.meco.velocity - 2.1) / 2.1 < 0.05
    assert abs(result.seco.altitude - 210) / 210 < 0.05

# test_api.py
@pytest.mark.asyncio
async def test_simulation_api_endpoint():
    response = await client.post("/api/v1/simulations", json={
        "vehicle_id": "falcon9_block5",
        "mission": {"type": "leo", "altitude_km": 400},
        "payload_kg": 15000
    })
    assert response.status_code == 200
    assert "sim_id" in response.json()
```

**3. E2E Tests (Slow, Few):**
```python
# test_e2e.py (Playwright)
def test_full_workflow(page):
    """User can run a simulation end-to-end."""
    page.goto("http://localhost:3000")
    
    # Select vehicle
    page.click('text=Falcon 9 Block 5')
    
    # Configure mission
    page.fill('input[name="payload"]', '15000')
    
    # Run simulation
    page.click('button:has-text("Run Simulation")')
    
    # Wait for results
    page.wait_for_selector('text=Success Rate')
    
    # Export CSV
    page.click('button:has-text("Export CSV")')
    # Assert download occurred
```

**CI/CD Pipeline:**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml --cov-fail-under=85
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Coverage Requirement:** 85% minimum (enforced by CI)

---

### AD-007: Deployment Strategy

**Decision:** Docker + Simple VPS for MVP, Kubernetes for scale

**Phase 0-6 (MVP): Simple Deployment**
```
Current state (already deployed):
- Single VPS (OVH/DigitalOcean)
- Docker Compose
- Nginx reverse proxy
- Let's Encrypt SSL
- Manual deployment (git pull + docker compose up)

Good enough for MVP (1-50 users)
```

**Phase 7-8 (Scale): Kubernetes**
```
Deploy to:
- Google Kubernetes Engine (GKE)
- Or AWS EKS
- Or DigitalOcean Kubernetes

Benefits:
- Auto-scaling (workers scale with load)
- Zero-downtime deployments
- Better resource utilization
- GPU node pools (for Monte Carlo)

Structure:
├── api (deployment)      # REST API servers
├── workers (deployment)  # Simulation workers
│   ├── CPU workers       # Standard simulations
│   └── GPU workers       # Large Monte Carlo
├── redis (statefulset)   # Cache
└── postgres (statefulset) # Database
```

**Deployment Pipeline (Phase 8):**
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t gcr.io/project/app:${{ github.sha }} .
      - name: Push to registry
        run: docker push gcr.io/project/app:${{ github.sha }}
      - name: Deploy to GKE
        run: kubectl set image deployment/app app=gcr.io/project/app:${{ github.sha }}
```

---

### AD-008: Observability & Monitoring

**Decision:** Structured logging + Prometheus + Sentry

**Logging (Structured):**
```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "simulation_started",
    sim_id=sim_id,
    vehicle="falcon9",
    payload_kg=15000
)

logger.info(
    "simulation_complete",
    sim_id=sim_id,
    success_rate=0.95,
    runtime_s=2.3
)
```

**Metrics (Prometheus):**
```python
from prometheus_client import Counter, Histogram

simulation_count = Counter('simulations_total', 'Total simulations run')
simulation_duration = Histogram('simulation_duration_seconds', 'Simulation runtime')

with simulation_duration.time():
    result = run_simulation()
    simulation_count.inc()
```

**Error Tracking (Sentry):**
```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://...",
    traces_sample_rate=1.0
)

# Automatically captures exceptions
```

**Dashboard (Grafana):**
```
Metrics to track:
- Simulations per day
- Average runtime
- Success rate
- Error rate by type
- API latency (p50, p95, p99)
- Database connection pool
- Cache hit rate
```

---

## Data Model

### Vehicle Configuration
```json
{
  "vehicle_id": "falcon9_block5",
  "name": "Falcon 9 Block 5",
  "manufacturer": "SpaceX",
  
  "stages": [
    {
      "stage_number": 1,
      "dry_mass_kg": 22200,
      "prop_mass_kg": 409500,
      "thrust_sl_N": 7607000,
      "thrust_vac_N": 8227000,
      "Isp_sl_s": 282,
      "Isp_vac_s": 311,
      "engines": 9,
      "burn_time_max_s": 162
    },
    {
      "stage_number": 2,
      "dry_mass_kg": 4000,
      "prop_mass_kg": 107500,
      "thrust_vac_N": 934000,
      "Isp_vac_s": 348,
      "engines": 1,
      "burn_time_max_s": 397
    }
  ],
  
  "fairing_mass_kg": 1750,
  "max_payload_leo_kg": 22800
}
```

### Mission Configuration
```json
{
  "mission_id": "iss_rendezvous",
  "name": "ISS Rendezvous",
  "target_orbit": {
    "altitude_km": 408,
    "inclination_deg": 51.6,
    "orbit_type": "circular"
  },
  "launch_site": "KSC_39A",
  "available_azimuths": [37, 57]
}
```

### Simulation Result
```json
{
  "sim_id": "abc123",
  "status": "complete",
  "timestamp": "2026-02-10T10:30:00Z",
  
  "vehicle": "falcon9_block5",
  "mission": {...},
  "payload_kg": 15000,
  
  "success": true,
  "delta_v_budget": {
    "total": 9400,
    "gravity_loss": 1534,
    "drag_loss": 135,
    "steering_loss": 89,
    "orbital_velocity": 7800
  },
  
  "orbital_elements": {
    "semi_major_axis_km": 6779,
    "eccentricity": 0.0012,
    "inclination_deg": 51.63,
    "perigee_km": 407.2,
    "apogee_km": 412.8,
    "period_min": 92.7
  },
  
  "events": [
    {"type": "liftoff", "time": 0, "altitude": 0},
    {"type": "max_q", "time": 70, "altitude": 12.3},
    {"type": "meco", "time": 155, "altitude": 68.2, "velocity": 2.1},
    {"type": "separation", "time": 158},
    {"type": "seco", "time": 523, "altitude": 210, "velocity": 7.8}
  ],
  
  "monte_carlo": {
    "n_runs": 10000,
    "success_rate": 0.952,
    "confidence_intervals": {
      "50%": {"altitude": 408.2, "velocity": 7.803},
      "95%": {"altitude": 405.1, "velocity": 7.789},
      "99%": {"altitude": 402.3, "velocity": 7.775}
    },
    "failure_modes": {
      "fuel_depletion": 320,
      "insufficient_velocity": 160
    }
  },
  
  "trajectory": [
    {"time": 0, "altitude": 0, "velocity": 0, ...},
    {"time": 0.1, "altitude": 0.001, "velocity": 0.008, ...},
    ...
  ]
}
```

---

## Security Considerations

### Input Validation
```python
from pydantic import BaseModel, Field, validator

class SimulationRequest(BaseModel):
    vehicle_id: str = Field(..., regex=r'^[a-z0-9_]+$')  # No injection
    payload_kg: float = Field(..., ge=0, le=100000)     # Reasonable limits
    
    @validator('vehicle_id')
    def vehicle_must_exist(cls, v):
        if v not in KNOWN_VEHICLES:
            raise ValueError(f'Unknown vehicle: {v}')
        return v
```

### Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=lambda: request.client.host)

@app.post("/api/v1/simulations")
@limiter.limit("10/minute")  # 10 simulations per minute per IP
async def create_simulation(...):
    ...
```

### Authentication (Phase 5+)
```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/api/v1/simulations")
async def create_simulation(
    token: str = Depends(oauth2_scheme),
    ...
):
    user = verify_token(token)
    # Check user quota, permissions, etc.
```

### Secrets Management
```python
# Never commit secrets!
# Use environment variables or secret manager

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
```

---

## Performance Targets

| Metric | Phase 0-3 (MVP) | Phase 4-6 (Optimized) | Phase 7-8 (Production) |
|--------|-----------------|---------------------|----------------------|
| Single simulation | <5s | <2s | <1s |
| 1,000 Monte Carlo | 3-5s | <1s | <0.5s |
| 10,000 Monte Carlo | 30-50s | 3-5s | <3s |
| 100,000 Monte Carlo | N/A | 30-60s | <30s |
| API latency (p95) | <500ms | <200ms | <100ms |
| Database queries | <100ms | <50ms | <20ms |
| Frontend load | <3s | <2s | <1s |

---

## Migration Path

### Phase 0-3: Current Architecture (Good Enough)
- Monolithic app
- Pure Python
- Docker Compose
- Manual deployment

### Phase 4-6: Optimized
- Still monolithic
- Cython for physics
- Maybe GPU support
- Same deployment

### Phase 7-8: If Scale Needed
- Microservices (optional)
- Kubernetes
- Auto-scaling
- CI/CD pipeline

---

## Decision Log

| ID | Decision | Date | Status | Review |
|----|----------|------|--------|--------|
| AD-001 | Monolithic MVP | 2026-02-09 | ✅ Approved | Week 16 |
| AD-002 | Python + Cython | 2026-02-09 | ✅ Approved | Week 10 |
| AD-003 | PostgreSQL | 2026-02-09 | ✅ Approved | Week 9 |
| AD-004 | REST API | 2026-02-09 | ✅ Approved | Week 16 |
| AD-005 | React | 2026-02-09 | ✅ Approved | - |
| AD-006 | TDD + 85% coverage | 2026-02-09 | ✅ Approved | Every PR |
| AD-007 | Docker → K8s | 2026-02-09 | ✅ Approved | Week 20 |
| AD-008 | Prometheus + Sentry | 2026-02-09 | ✅ Approved | Week 12 |

---

**Status:** ✅ Architecture Complete  
**Next:** Epics & Stories (03-epics-stories.md)  
**Skills Applied:** code-architecture, senior-code, tdd  
**Review:** Architecture decisions can be challenged at phase gates
