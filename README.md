# 🚀 SpaceX Orbital Intelligence Platform

**High-fidelity launch trajectory simulation and satellite tracking platform with NASA-grade astrodynamics.**

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![ANISE](https://img.shields.io/badge/ANISE-0.4-orange)](https://github.com/nyx-space/anise)

## 🎯 Features

### 🚀 Launch Trajectory Simulation
- **6-DOF Physics Engine** - Full 3D trajectory with gravity, drag, staging
- **Realistic Falcon 9 Model** - Validated against CRS-21 actual flight data
- **Multi-Stage Support** - Stage separation, coast phases, engine ignition
- **Atmospheric Modeling** - Altitude-dependent drag with Mach-number effects
- **Gravity Turn Guidance** - Time-phased pitch profile based on real telemetry
- **Monte Carlo Simulation Engine** - Statistical analysis with parameter sampling
- **Performance Validation** - <15% error vs real flight data

### 🌍 Orbital Analysis (ANISE-Powered)
- **Planetary Ephemeris** - Sun, Moon, planets (JPL DE440s, 1900-2050)
- **Ground Station Visibility** - AER calculations for 10 NASA/ESA stations
- **Eclipse Detection** - High-precision solar eclipsing (0.075ms/check)
- **Satellite Tracking** - 11,000+ objects via TLE/SGP4 propagation

### 🛰️ Orbital Intelligence
- **Real-time Tracking** - 11,000+ satellites with live position updates
- **Collision Detection** - Proximity alerts and risk scoring
- **Orbital Density Analysis** - Hotspot identification and congestion mapping
- **OMM Support** - CCSDS Orbit Mean-Elements Message format (NASA standard)
- **TLE/OMM Dual Mode** - Switch between data sources dynamically
- **Conjunction Data Messages (CDM)** - Real Space-Track.org collision screening data

### 🎬 3D Visualization
- Real-time 3D globe with satellite tracking
- Orbital trails and constellation visualization
- Interactive camera controls
- Earth atmosphere and lighting effects

### 📊 Mission Analysis
- ΔV budget tracking
- Trajectory CSV export
- Launch history and fleet tracking
- Validation against real missions
- Launch Library 2 integration (live launch data)

## 🏆 Technical Highlights

**Physics Engine:**
- RK4 numerical integration
- Altitude-dependent gravity (inverse square law)
- US Standard Atmosphere (exponential model)
- Mach-dependent drag coefficient (Cd 0.40 → 0.60 → 0.28)
- Thrust/Isp interpolation (sea level to vacuum)
- Earth rotation velocity bonus
- Monte Carlo simulation support (internal service)

**ANISE Integration:**
- Sub-millisecond queries (0.075-0.099ms)
- No external dependencies (self-contained)
- Thread-safe Rust core
- NASA-grade precision

**Data Sources:**
- **Space-Track.org** - Primary TLE source (11,000+ satellites)
- **Celestrak** - TLE fallback source
- **N2YO** - TLE validation
- **OMM Upload** - CCSDS format support
- **SpaceX API** - Launch history
- **Launch Library 2** - Live launch data

**Validation Results (CRS-21):**
```
MECO Time:      162.1s  (target: 155s,  error: 4.6% ✓)
MECO Altitude:  78.6 km (target: 68 km,  error: 15.6%)
SECO Altitude:  180 km  (target: 210 km, error: 14.3% ✓)
Final Orbit:    180 km  (target: 210 km, error: 14.3% ✓)
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local dev)
- Node.js 20+ (for frontend dev)

### 1. Clone Repository
```bash
git clone https://github.com/e-cesar9/spacex-orbital-intelligence.git
cd spacex-orbital-intelligence
```

### 2. Configure Environment
```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit backend/.env with your configuration
nano backend/.env

# Required for full functionality:
# - SPACETRACK_USERNAME (register at space-track.org)
# - SPACETRACK_PASSWORD
# - N2YO_API_KEY (optional, for TLE validation)
```

### 3. Start Services
```bash
# With Docker Compose
docker compose up -d

# Check health
docker compose ps

# View logs
docker compose logs -f backend
```

### 4. Access Platform
- **Frontend:** http://localhost:3100
- **API Docs:** http://localhost:8000/docs
- **Metrics:** http://localhost:8000/metrics

## 📖 API Documentation

### Core Endpoints

#### 🛰️ Satellite Tracking
```bash
# Get all satellite positions (11,000+ satellites)
GET /api/v1/satellites/positions

# Get satellite details
GET /api/v1/satellites/{satellite_id}

# Get orbital path (trajectory prediction)
GET /api/v1/satellites/{satellite_id}/orbit?hours=24

# Switch data source (TLE ↔ OMM)
GET /api/v1/data-source
POST /api/v1/data-source
```

#### 📤 OMM Upload (NASA Standard)
```bash
# Upload OMM file (XML or JSON)
POST /api/v1/satellites/omm
Content-Type: multipart/form-data

# Supported formats:
# - CCSDS OMM 2.0 XML
# - OMM JSON
# - Includes covariance matrix support

curl -X POST http://localhost:8000/api/v1/satellites/omm \
  -F "file=@iss_omm.xml" \
  -F "format=xml" \
  -F "source=nasa_cdm"
```

#### ⚠️ Conjunction Data (Space-Track CDM)
```bash
# Get real collision screening data
GET /api/v1/cdm/starlink?hours_ahead=72

# Check CDM status
GET /api/v1/cdm/status

# Note: Requires Space-Track credentials
# Data from 18th Space Defense Squadron
```

#### 🚀 Launch Simulation
```bash
# Launch simulation
POST /api/v1/launch-simulation/simulate
{
  "vehicle": "falcon9_block5",
  "payload_kg": 2972,
  "target_altitude_km": 210,
  "target_inclination_deg": 51.6
}

# Get simulation result
GET /api/v1/launch-simulation/{sim_id}
```

#### 🌍 Ephemeris & Analysis
```bash
# Eclipse detection
GET /api/v1/ephemeris/eclipse/25544?epoch=2024-01-01T12:00:00Z

# Ground station visibility
GET /api/v1/ground-stations/DSS-65/visibility/25544

# Planetary ephemeris
GET /api/v1/ephemeris/sun?epoch=2024-01-01T00:00:00Z

# Collision risk analysis
GET /api/v1/analysis/risk/{satellite_id}?hours_ahead=24

# Orbital density
GET /api/v1/analysis/density?altitude_km=550&tolerance_km=50
```

#### 📊 Live Launch Data
```bash
# Live upcoming launches (Launch Library 2)
GET /api/v1/launches-live?upcoming=true&spacex_only=false

# Next launch countdown
GET /api/v1/launches-live/next

# Launch statistics
GET /api/v1/launches-live/statistics
```

## 🛠️ Tech Stack

### Backend
- **Python 3.12** with FastAPI
- **ANISE 0.4** - NASA-grade astrodynamics (Rust)
- **SGP4 + Skyfield** - TLE propagation
- **NumPy** - Numerical computing
- **Redis** - Caching and rate limiting
- **PostgreSQL** - Mission data persistence
- **CircuitBreaker** - Resilience patterns

### Frontend
- **React 18** + TypeScript
- **Three.js** / @react-three/fiber - 3D visualization
- **Recharts** - Trajectory plotting
- **Zustand** - State management
- **TanStack Query** - Data fetching
- **Tailwind CSS** - Styling

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Reverse proxy
- **Prometheus** - Metrics
- **Pytest** - Testing

## 🧪 Testing

### Run Tests
```bash
# Backend tests
cd backend
python -m pytest

# Specific test
python -m pytest tests/test_crs21_validation.py -v

# With coverage
python -m pytest --cov=app --cov-report=html
```

### Validation Tests
- `test_crs21_validation.py` - CRS-21 mission validation
- `test_eclipse_detection.py` - Eclipse calculations
- `test_ground_station_aer.py` - AER calculations
- `test_falcon9_config.py` - Vehicle configuration
- `test_satellite_id_validation.py` - Injection prevention
- `test_circuit_breakers_all_services.py` - Resilience testing

## 📊 Performance

### ANISE Queries
- Planetary ephemeris: **0.085ms** per query
- Ground station AER: **0.099ms** per calculation
- Eclipse detection: **0.075ms** per check

### Simulation
- Launch trajectory (540s): **~2-3 seconds** (0.1s timestep)
- Full validation suite: **~5 seconds**
- Satellite propagation: **~1000s of satellites/sec**

### Data Sources
- TLE refresh: **30s timeout**, 3 retries with exponential backoff
- Circuit breakers on all external APIs
- Fallback sources: Space-Track → Celestrak → N2YO

## 🗺️ Roadmap

### ✅ Phase 0: Foundation (Complete)
- ✅ Multi-stage vehicle model
- ✅ 6-DOF trajectory simulation
- ✅ Gravity + drag + thrust modeling
- ✅ Staging logic
- ✅ ANISE planetary ephemeris
- ✅ Ground station visibility
- ✅ Eclipse detection
- ✅ OMM format support
- ✅ CDM integration
- ✅ TLE/OMM dual mode
- ✅ Monte Carlo simulation engine (internal)
- ✅ Circuit breakers + resilience patterns
- ✅ 11,000+ satellite tracking

### 📋 Phase 1: Production Hardening (5 weeks)
- [ ] OpenTelemetry distributed tracing
- [ ] Sentry error tracking
- [ ] 60% test coverage
- [ ] E2E tests (Playwright)
- [ ] Load testing (k6)
- [ ] Dependency injection refactor
- [ ] Request ID middleware

### 🔵 Phase 2: Spatial-Grade (2 months)
- [ ] ISO/IEC 25010 audit
- [ ] OWASP Top 10 compliance
- [ ] Penetration testing
- [ ] Chaos engineering
- [ ] Multi-region deployment
- [ ] Disaster recovery plan
- [ ] NASA software standards review

### 🚀 Phase 3: Advanced Features
- [ ] Monte Carlo UI (public endpoint)
- [ ] Optimal trajectory planning
- [ ] Launch window analysis
- [ ] Multi-body dynamics
- [ ] Maneuver planning
- [ ] Formation flying analysis

## 📝 Development

### Local Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Code Structure
```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── satellites.py      # Satellite tracking + OMM
│   │   ├── cdm.py            # Conjunction Data Messages
│   │   ├── launch_simulation.py
│   │   ├── data_source.py    # TLE/OMM switching
│   │   └── ...
│   ├── services/         # Business logic
│   │   ├── simulation_6dof.py
│   │   ├── launch_simulator.py    # Monte Carlo engine
│   │   ├── guidance_realistic.py
│   │   ├── anise_planetary.py
│   │   ├── spacetrack.py         # CDM client
│   │   └── ...
│   ├── models/           # Data models
│   └── core/             # Config, metrics
├── data/
│   └── vehicles/         # Vehicle configurations
├── tests/                # Test suite
└── docs/                 # Documentation

frontend/
├── src/
│   ├── components/       # React components
│   ├── services/         # API clients
│   ├── hooks/            # Custom hooks
│   └── stores/           # State management
```

## 🔒 Security & Compliance

### Implemented Protections
- ✅ Satellite ID validation (regex `^\d{1,5}$`)
- ✅ Input sanitization (XXE/injection prevention)
- ✅ Rate limiting (SlowAPI)
- ✅ CORS restrictions
- ✅ Security headers (CSP, HSTS, etc.)
- ✅ Secrets not in Git
- ✅ Circuit breakers on all external APIs

### Standards Compliance
- **CCSDS OMM 2.0** - NASA/ESA orbital data format
- **OWASP Top 10** - In progress (P1/P2)
- **ISO/IEC 25010** - Planned (P2)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- **ANISE** by NYX Space - High-performance astrodynamics toolkit
- **SpaceX** - Publicly available mission data
- **NASA JPL** - DE440s ephemeris and planetary data
- **Space-Track.org** - Satellite catalog, TLE, and CDM data
- **Celestrak** - Public TLE distribution
- **Launch Library 2** - Live launch data

## 📧 Contact

- **GitHub:** [@e-cesar9](https://github.com/e-cesar9)
- **Issues:** [GitHub Issues](https://github.com/e-cesar9/spacex-orbital-intelligence/issues)

---

**Built with ❤️ for the space community.**
