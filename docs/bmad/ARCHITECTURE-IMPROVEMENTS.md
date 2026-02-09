# Architecture - Quality Improvements

**Sprint:** Quality & Security Hardening  
**Scope:** 10 technical improvements (P0+P1)

---

## Overview

```
┌─────────────────────────────────────────────────┐
│                  FRONTEND (React)                │
│  ┌──────────────────────────────────────────┐  │
│  │  Error Boundary (NEW)                    │  │
│  │  ├─ Globe.tsx (ref-based controls)       │  │
│  │  ├─ API Service (batched + validated)    │  │
│  │  └─ Lazy-loaded tabs                     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                        ↓ HTTPS
┌─────────────────────────────────────────────────┐
│              BACKEND (FastAPI)                   │
│  ┌──────────────────────────────────────────┐  │
│  │  Exception Handlers (specific)           │  │
│  │  API Key Validator (mandatory in prod)   │  │
│  │  Input Validation (Pydantic models)      │  │
│  │  Circuit Breaker (external calls)        │  │
│  │  Prefixed Cache Keys                     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 1. Frontend Waterfalls → Batch API Calls

**Problem:** Sequential API calls block rendering

**Current:**
```tsx
const positions = await getAllPositions()  // Wait
const health = await getHealth()           // Wait
const launches = await getLaunches()        // Wait
```

**Solution:** Parallel fetch + React Query batching

```tsx
// api.ts - New batch endpoint wrapper
export async function getInitialData() {
  const [positions, health, launches] = await Promise.all([
    getAllPositions(),
    getHealth(),
    getLaunches(20, false)
  ])
  return { positions, health, launches }
}

// App.tsx - Use React Query
const { data, isLoading } = useQuery({
  queryKey: ['initial-data'],
  queryFn: getInitialData,
  staleTime: 30000
})
```

**Impact:** Reduce initial load from 1200ms → 400ms (3x faster)

---

## 2. Global Mutation → useRef Pattern

**Problem:** `window.__orbitControls` breaks React principles

**Current:**
```tsx
window.__orbitControls = controls  // ❌ Global mutation
```

**Solution:** React ref + custom hook

```tsx
// hooks/useOrbitControls.ts
export function useOrbitControls() {
  const controlsRef = useRef<OrbitControls>(null)
  
  const zoom = useCallback((delta: number) => {
    if (!controlsRef.current) return
    const camera = controlsRef.current.object
    const currentDistance = camera.position.length()
    const newDistance = Math.max(8, Math.min(50, currentDistance + delta))
    camera.position.setLength(newDistance)
    controlsRef.current.update()
  }, [])
  
  return { controlsRef, zoom }
}

// Globe.tsx
const { controlsRef, zoom } = useOrbitControls()
<OrbitControls ref={controlsRef} ... />
```

**Impact:** Type-safe, testable, React-idiomatic

---

## 3. Exception Handler → Specific Handlers

**Problem:** `@app.exception_handler(Exception)` catches everything

**Current:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**Solution:** Specific handlers per exception type

```python
# main.py - Specific handlers
from fastapi import HTTPException
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded

@app.exception_handler(ValidationError)
async def validation_handler(request, exc):
    logger.warning("Validation error", errors=exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    # Let FastAPI handle it, but log it
    logger.info("HTTP exception", status=exc.status_code, detail=exc.detail)
    raise exc

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Only truly unhandled exceptions
    logger.error("Unhandled exception", 
                 error=str(exc), 
                 type=type(exc).__name__,
                 path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**Impact:** Better error visibility, proper HTTP status codes

---

## 4. API Key → Mandatory in Production

**Problem:** If `SPACEX_API_KEY` not set, generates random key

**Current:**
```python
if not key:
    key = secrets.token_urlsafe(32)  # ❌ Nobody knows this key
```

**Solution:** Fail fast in production

```python
# core/security.py
def get_api_key() -> str:
    key = os.environ.get("SPACEX_API_KEY")
    env = os.environ.get("ENV", "development")
    
    if not key:
        if env == "production":
            raise RuntimeError(
                "SPACEX_API_KEY must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        # Dev only: generate temporary key
        key = secrets.token_urlsafe(32)
        logger.warning(f"[DEV] Using temporary API key: {key}")
    
    return key
```

**Impact:** No silent security degradation in prod

---

## 5. Error Boundaries → Catch React Crashes

**Problem:** Three.js crash kills entire app

**Solution:** Error Boundary component

```tsx
// components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: any) {
    console.error('React Error Boundary caught:', error, info)
    // Optional: Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex items-center justify-center h-screen bg-spacex-dark">
          <div className="text-center glass p-8 rounded-xl">
            <h2 className="text-2xl font-bold text-red-400 mb-4">
              Visualization Error
            </h2>
            <p className="text-gray-400 mb-4">
              The 3D globe encountered an error
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

// App.tsx - Wrap critical components
<ErrorBoundary>
  <Globe />
</ErrorBoundary>
```

**Impact:** Graceful degradation, better UX

---

## 6. Runtime Validation → Zod Schemas

**Problem:** TypeScript types don't validate at runtime

**Solution:** Zod validation on API responses

```tsx
// types/schemas.ts (NEW)
import { z } from 'zod'

export const SatellitePositionSchema = z.object({
  id: z.string(),
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
  alt: z.number().min(0),
  v: z.number().min(0)
})

export const PositionsResponseSchema = z.object({
  count: z.number(),
  source: z.enum(['tle', 'simulated']),
  positions: z.array(SatellitePositionSchema)
})

// api.ts - Validate responses
export async function getAllPositions() {
  const data = await fetchJson<unknown>(`${API_BASE}/satellites/positions`)
  return PositionsResponseSchema.parse(data)  // Throws if invalid
}
```

**Dependencies:** `zod@^3.22.0`

**Impact:** Catch API contract violations early

---

## 7. Form Input Validation → Pydantic Models

**Problem:** `source` field unlimited, no sanitization

**Current:**
```python
source: str = Form("user_upload")  # ❌ No limits
```

**Solution:** Pydantic model with constraints

```python
# models/omm.py (NEW)
from pydantic import BaseModel, Field, validator
from typing import Literal

class OMMUploadForm(BaseModel):
    format: Literal['xml', 'json']
    source: str = Field(
        default="user_upload",
        max_length=100,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Data source identifier (alphanumeric + _ - only)"
    )
    
    @validator('source')
    def sanitize_source(cls, v):
        # Additional sanitization
        return v.strip().lower()

# api/satellites.py
from app.models.omm import OMMUploadForm

@router.post("/omm")
async def upload_omm(
    request: Request,
    file: UploadFile = File(...),
    form: OMMUploadForm = Depends()
):
    # form.source is now validated
    ...
```

**Impact:** SQL injection + XSS prevention

---

## 8. Bundle Size → Code Splitting

**Problem:** Initial bundle ~500KB (recharts + three.js)

**Solution:** Lazy load non-critical tabs

```tsx
// components/Sidebar/Sidebar.tsx
import { lazy, Suspense } from 'react'

// Eager load (always visible)
import { SatellitesTab } from './SatellitesTab'

// Lazy load (conditional)
const LaunchesTab = lazy(() => import('./LaunchesTab'))
const AnalysisTab = lazy(() => import('./AnalysisTab'))
const OpsTab = lazy(() => import('./OpsTab'))
const PerformanceTab = lazy(() => import('./PerformanceTab'))
const InsightsTab = lazy(() => import('./InsightsTab'))
const SimulationTab = lazy(() => import('./SimulationTab'))

// Render
<Suspense fallback={<TabSkeleton />}>
  {activeTab === 'launches' && <LaunchesTab />}
  {activeTab === 'analysis' && <AnalysisTab />}
  {/* ... */}
</Suspense>
```

**Vite config:**
```ts
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'three': ['three', '@react-three/fiber', '@react-three/drei'],
          'charts': ['recharts'],
          'vendor': ['react', 'react-dom', 'zustand']
        }
      }
    }
  }
})
```

**Impact:** Initial bundle: 500KB → <200KB

---

## 9. Cache Keys → Prefixed

**Problem:** Cache key collision risk across services

**Current:**
```python
cache_key = "satellites:positions:all"  # ❌ No namespace
```

**Solution:** Centralized prefix

```python
# core/config.py
class Settings(BaseSettings):
    cache_prefix: str = "spacex_orbital:"
    # ...

# services/cache.py
class CacheService:
    def _make_key(self, key: str) -> str:
        return f"{settings.cache_prefix}{key}"
    
    async def get(self, key: str):
        return await self.redis.get(self._make_key(key))
    
    async def set(self, key: str, value, ttl: int):
        return await self.redis.set(self._make_key(key), value, ex=ttl)

# api/satellites.py
cache_key = "satellites:positions:all"  # Becomes "spacex_orbital:satellites:positions:all"
```

**Impact:** Safe multi-service Redis usage

---

## 10. Circuit Breaker → External Calls

**Problem:** Circuit breaker imported but not used

**Solution:** Wrap external API calls

```python
# services/spacex_api.py
from circuitbreaker import circuit

class SpaceXClient:
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    async def get_starlink_satellites(self, limit: int, offset: int):
        """Fetch with circuit breaker protection."""
        response = await self.client.get(
            f"{self.base_url}/starlink",
            params={"limit": limit, "offset": offset},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

# services/tle_service.py
class TLEService:
    @circuit(failure_threshold=3, recovery_timeout=120)
    async def fetch_celestrak(self):
        """Fetch TLE with circuit breaker."""
        response = await httpx.get(CELESTRAK_URL, timeout=30)
        response.raise_for_status()
        return response.text
```

**Impact:** Prevent cascade failures when external APIs down

---

## Testing Strategy

### Backend
- Unit tests for new validators
- Integration tests for circuit breaker
- Security tests for API key enforcement

### Frontend
- Test Error Boundary with simulated crashes
- Test lazy loading
- Test batched API calls

### E2E
- Lighthouse performance test (target >85)
- Bundle size check (target <300KB)
- Error handling flow

---

## Deployment Plan

1. **Backend deploy** (zero-downtime)
   - Deploy new backend with `ENV=production`
   - Set `SPACEX_API_KEY` in production `.env`
   - Restart services

2. **Frontend deploy**
   - Build with code splitting
   - Deploy to Nginx
   - Monitor bundle size

3. **Monitoring**
   - Watch error logs for unhandled exceptions
   - Check Redis key prefixes
   - Verify circuit breaker triggers

---

## Dependencies Added

```json
// Frontend package.json
{
  "dependencies": {
    "zod": "^3.22.4"
  }
}
```

```txt
# Backend requirements.txt (already present)
circuitbreaker==1.4.0  # Now actively used
```

---

## Rollback Plan

If issues after deploy:
1. Frontend: Revert Nginx to previous build
2. Backend: Revert Docker image to previous tag
3. Database: No schema changes (safe)

**Estimated rollback time:** <5 minutes
