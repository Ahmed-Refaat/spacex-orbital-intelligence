# SpaceX Orbital Intelligence API Documentation

## Overview

Real-time orbital intelligence for the SpaceX Starlink constellation. Provides satellite tracking, collision risk analysis, launch data, and orbital analytics.

**Base URL:** `http://localhost:8000/api/v1`  
**API Version:** 1.0.0  
**Authentication:** API Key (header `X-API-Key` or query param `api_key`)

---

## Quick Start

```bash
# Health check
curl http://localhost:8000/health

# Get all satellite positions
curl http://localhost:8000/api/v1/satellites/positions

# Get a specific satellite
curl http://localhost:8000/api/v1/satellites/25544

# Risk analysis
curl http://localhost:8000/api/v1/analysis/risk/25544
```

---

## Authentication

### API Key
For production deployments, an API key is required:

```bash
# Header
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/satellites

# Query parameter
curl "http://localhost:8000/api/v1/satellites?api_key=your-api-key"
```

In development mode (no API key configured), authentication is disabled.

---

## Rate Limits

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| Standard GET | 100/min | Per IP |
| Analysis (CPU-intensive) | 30/min | Per IP |
| Alerts | 20/min | Per IP |
| Deorbit simulation | 10/min | Per IP |
| OMM Upload | 10/min | Per IP |

Rate limit headers:
- `X-RateLimit-Limit`: Max requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Window reset timestamp

---

## Endpoints

### Health & Meta

#### GET /health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "satellites_loaded": 11023,
  "cache_connected": true,
  "last_tle_update": "2024-02-09T18:36:05.989123"
}
```

#### GET /api/version
Get API version information.

#### GET /metrics
Prometheus metrics endpoint for monitoring.

---

### Satellites

#### GET /satellites
List satellites with pagination.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | int | 100 | Results per page (1-1000) |
| offset | int | 0 | Pagination offset |

**Response:**
```json
{
  "total": 11023,
  "satellites": [
    {
      "satellite_id": "25544",
      "name": "ISS (ZARYA)",
      "latitude": 51.64,
      "longitude": -0.12,
      "altitude": 420.5,
      "velocity": 7.66
    }
  ]
}
```

#### GET /satellites/positions
Get current positions of all satellites.

**Response:**
```json
{
  "count": 11023,
  "timestamp": "2024-02-09T12:00:00Z",
  "positions": [
    {
      "satellite_id": "25544",
      "latitude": 51.64,
      "longitude": -0.12,
      "altitude": 420.5
    }
  ]
}
```

#### GET /satellites/{id}
Get details for a specific satellite.

**Response:**
```json
{
  "satellite_id": "25544",
  "name": "ISS (ZARYA)",
  "position": {
    "x": 4000.5,
    "y": 2000.3,
    "z": 3500.1
  },
  "velocity": {
    "vx": 5.2,
    "vy": 3.1,
    "vz": 4.8
  },
  "geographic": {
    "latitude": 51.64,
    "longitude": -0.12,
    "altitude": 420.5
  },
  "speed": 7.66
}
```

#### GET /satellites/{id}/orbit
Get orbital trajectory for visualization.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| hours | int | 24 | Hours to propagate (1-72) |
| step_minutes | int | 5 | Time step in minutes |

---

### Analysis

#### GET /analysis/risk/{satellite_id}
Calculate collision risk for a satellite.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| hours_ahead | int | 24 | Analysis window (1-72) |

**Response:**
```json
{
  "satellite_id": "25544",
  "name": "ISS (ZARYA)",
  "altitude_km": 420.5,
  "nearby_count": 15,
  "risks": [
    {
      "satellite_2": "41234",
      "min_distance_km": 5.2,
      "tca": "2024-02-09T14:30:00Z",
      "risk_score": 0.85
    }
  ]
}
```

#### GET /analysis/density
Analyze satellite density at altitude.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| altitude_km | float | 550 | Target altitude (200-2000) |
| tolerance_km | float | 50 | Altitude band (10-200) |

#### GET /analysis/hotspots
Identify orbital congestion hotspots.

#### GET /analysis/constellation/health
Starlink constellation health overview.

#### GET /analysis/alerts
Get active collision alerts.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| min_risk | float | 0.3 | Minimum risk threshold (0-1) |
| limit | int | 20 | Max alerts to return |

#### POST /analysis/simulate/deorbit
Simulate deorbit trajectory.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| satellite_id | str | required | Target satellite |
| delta_v | float | 0.1 | Deorbit burn (0.01-1.0 km/s) |

---

### Launches

#### GET /launches
Get SpaceX launch history.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | int | 20 | Results to return |
| upcoming | bool | false | Filter to upcoming launches |

#### GET /launches/cores
Get reusable booster core data.

#### GET /launches/statistics
Get fleet statistics.

#### GET /launches-live
Get live launch data from Launch Library 2.

#### GET /launches-live/next
Get next upcoming launch with countdown.

---

### WebSocket

#### WS /ws/positions
Real-time satellite position updates.

**Authentication:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/positions?token=YOUR_API_KEY');
```

**Messages received:**
```json
{
  "type": "positions",
  "count": 11023,
  "source": "tle",
  "data": [
    {"id": "25544", "lat": 51.64, "lon": -0.12, "alt": 420.5}
  ]
}
```

**Messages to send:**
```json
// Subscribe to specific satellite
{"type": "subscribe", "satellite_id": "25544"}

// Keepalive ping
{"type": "ping"}
```

---

## Error Responses

### 400 Bad Request
Invalid parameters.
```json
{
  "detail": "Invalid altitude_km: must be between 200 and 2000"
}
```

### 401 Unauthorized
Missing or invalid API key.
```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found
Resource not found.
```json
{
  "detail": "Satellite not found"
}
```

### 429 Too Many Requests
Rate limit exceeded.
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

### 500 Internal Server Error
Server error.
```json
{
  "detail": "Internal server error"
}
```

---

## Data Sources

| Source | Data | Update Frequency |
|--------|------|-----------------|
| CelesTrak | TLE orbital data | Every 6 hours |
| Space-Track | CDM conjunction data | Hourly |
| SpaceX API | Launch history | On-demand |
| Launch Library 2 | Live launch data | Real-time |

---

## SDKs & Examples

### Python
```python
import httpx

client = httpx.Client(
    base_url="http://localhost:8000",
    headers={"X-API-Key": "your-key"}
)

# Get all positions
positions = client.get("/api/v1/satellites/positions").json()

# Analyze risk
risk = client.get("/api/v1/analysis/risk/25544").json()
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8000/api/v1/satellites/positions', {
  headers: { 'X-API-Key': 'your-key' }
});
const positions = await response.json();
```

### WebSocket (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/positions?token=your-key');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'positions') {
    console.log(`Tracking ${data.count} satellites`);
  }
};
```

---

## Changelog

### v1.0.0 (2024-02-01)
- Initial release
- Satellite tracking with SGP4 propagation
- Collision risk analysis
- SpaceX launch data
- WebSocket real-time updates
- Prometheus metrics
