# 🚀 SpaceX Orbital Intelligence Platform

Real-time satellite tracking and orbital analysis platform with 3D visualization and NASA-grade astrodynamics.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-blue)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)

## ✨ Features

### 🌍 Real-Time Satellite Tracking
- Live 3D globe visualization with 30,000+ satellites
- Starlink constellation monitoring
- Interactive satellite selection and details
- Orbital trails and paths
- Search and filtering by altitude, name, or ID

### 🛰️ Orbital Analysis
- **Collision Detection** - Proximity monitoring and risk scoring
- **Ground Station Visibility** - AER (Azimuth, Elevation, Range) calculations
- **Eclipse Detection** - Solar eclipsing with ANISE precision
- **Orbital Density Analysis** - Congestion metrics per orbital shell
- **Conjunction Data** - Space-Track CDM integration

### 🚀 Launch Intelligence
- Live launch tracking and statistics
- SpaceX fleet monitoring (cores, fairings, capsules)
- Launch timeline and history
- Turnaround time analytics
- Cross-mission correlation

### 🎬 Visual Effects (IMAX Mode)
- **Constellation Flow Trails** - Flowing light trails showing satellite movement
- **Collision Visualization** - Dramatic near-miss alerts with pulsating danger zones
- **Cinematic Camera** - Automated sequences (Overview, Constellation, Conjunction, Launch)
- **Atmosphere Effects** - Glowing atmosphere, aurora borealis, city lights on night side
- **IMAX Mode** - Full Hollywood-style automated presentation (40s sequence)

*See [`VISUAL_EFFECTS_GUIDE.md`](VISUAL_EFFECTS_GUIDE.md) for complete documentation*

### 📊 Analytics & Export
- Performance metrics and monitoring
- Data export (CSV, JSON, OMM format)
- Operational insights
- Anomaly detection timeline
- Decision recommendations

### 🔬 Astrodynamics (ANISE)
- **Planetary Ephemeris** - JPL DE440s (1900-2050)
- **Sub-millisecond queries** - 0.075-0.099ms performance
- **NASA-grade precision** - Thread-safe Rust core
- **Ground stations** - 10 NASA/ESA facilities configured

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local dev)
- Node.js 20+ (for frontend dev)

### 1. Clone & Setup
```bash
git clone https://github.com/e-cesar9/spacex-orbital-intelligence.git
cd spacex-orbital-intelligence

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your settings
```

### 2. Start with Docker
```bash
docker compose up -d

# Check health
docker compose ps

# View logs
docker compose logs -f backend
```

### 3. Access Platform
- **Frontend:** http://localhost:3100
- **API Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health
- **Metrics:** http://localhost:8000/metrics

## 🛠️ Tech Stack

### Backend
- **Python 3.11** + FastAPI
- **ANISE 0.4** - NASA astrodynamics (Rust)
- **SGP4 + Skyfield** - Satellite propagation
- **Redis** - Caching & rate limiting
- **PostgreSQL** - Data persistence

### Frontend
- **React 18** + TypeScript
- **Three.js / React Three Fiber** - 3D visualization
- **TanStack Query** - Data fetching
- **Zustand** - State management
- **Tailwind CSS** - Styling

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Reverse proxy
- **Prometheus** - Metrics

## 📖 API Overview

### Satellites
```bash
GET /api/v1/satellites              # List satellites
GET /api/v1/satellites/{id}         # Satellite details
GET /api/v1/satellites/{id}/orbit   # Orbital path
```

### Analysis
```bash
GET /api/v1/analysis/collision-risk      # Risk scoring
GET /api/v1/analysis/orbital-density     # Congestion analysis
GET /api/v1/monitoring/proximity         # Proximity detection
```

### Launches
```bash
GET /api/v1/launches-live           # Live launch data
GET /api/v1/launches/statistics     # Fleet statistics
GET /api/v1/launches/timeline       # Historical timeline
```

### Ephemeris
```bash
GET /api/v1/ephemeris/{body}                    # Planetary positions
GET /api/v1/ephemeris/eclipse/{satellite_id}    # Eclipse detection
GET /api/v1/ground-stations/{station}/visibility/{satellite}  # Visibility
```

Full documentation: http://localhost:8000/docs

## 📁 Project Structure

```
spacex-orbital-intelligence/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── services/          # Business logic
│   │   ├── models/            # Data models
│   │   └── core/              # Config, metrics
│   ├── data/                  # TLE data & vehicle configs
│   ├── kernels/               # ANISE ephemeris kernels
│   └── tests/                 # Test suite
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/          # API clients
│   │   └── stores/            # State management
│   └── public/                # Static assets
└── docker-compose.yml         # Docker orchestration
```

## 🧪 Development

### Local Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Local Frontend
```bash
cd frontend
npm install
npm run dev
```

### Run Tests
```bash
cd backend
pytest tests/ -v
```

## 🔧 Configuration

### Environment Variables
See `backend/.env.example` for all available options:
- Database credentials
- Redis configuration
- API rate limits
- Data source selection (TLE providers)
- Feature flags

### Data Sources
The platform supports multiple TLE data sources:
- TLE.ivanstanojevic.me (default, no auth)
- Celestrak (optional)
- Space-Track.org (optional, requires account)

Configure in `backend/.env`:
```bash
TLE_SOURCE=ivanstanojevic  # or celestrak, spacetrack
```

## 📊 Performance

- **TLE Propagation:** 100+ satellites/frame at 60 FPS
- **ANISE Queries:** <0.1ms per calculation
- **API Response:** <100ms for satellite list (cached)
- **Database:** PostgreSQL with optimized indexes
- **Redis:** In-memory caching for hot paths

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- **ANISE** by NYX Space - High-performance astrodynamics toolkit
- **NASA NAIF SPICE** - Astrodynamics toolkit foundation
- **SpaceX** - Publicly available mission data and public launch data
- **NASA JPL** - DE440s ephemeris and planetary data
- **Space-Track.org & Open-source TLE providers** - Satellite tracking data

## 📧 Contact

- **GitHub:** [@e-cesar9](https://github.com/e-cesar9)
- **Issues:** [GitHub Issues](https://github.com/e-cesar9/spacex-orbital-intelligence/issues)

---

**Built for the space community 🌌**
