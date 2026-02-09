"""SpaceX Orbital Intelligence Platform - FastAPI Application."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog
import time

from app.core.config import get_settings
from app.core.security import limiter, get_allowed_origins, get_valid_api_key
from app.core.metrics import (
    record_request, 
    set_app_info, 
    get_metrics, 
    get_content_type,
    WEBSOCKET_CONNECTIONS,
    SATELLITES_LOADED,
    TLE_LAST_UPDATE
)
from app.services.cache import cache
from app.services.tle_service import tle_service
from app.services.spacex_api import spacex_client
from app.services.orbital_engine import orbital_engine
from app.services.spice_client import spice_client
from app.services import async_orbital_engine
from app.api import satellites, analysis, ephemeris, ground_stations, launches, websocket, ops, analytics, launches_live, cdm, export, monitoring, performance, rate_limits, launch_simulation, data_source

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()

# API version constants
API_VERSION = "1.0.0"
API_MIN_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting SpaceX Orbital Intelligence Platform")
    
    # Set Prometheus app info
    set_app_info(
        version=API_VERSION,
        environment=settings.environment if hasattr(settings, 'environment') else 'production'
    )
    
    # Connect to Redis (non-blocking)
    try:
        await asyncio.wait_for(cache.connect(), timeout=5)
    except Exception as e:
        logger.warning("Redis connection failed, running without cache", error=str(e))
    
    # Initialize SPICE client
    spice_url = settings.SPICE_URL if hasattr(settings, 'SPICE_URL') else "http://spice:3000"
    try:
        await asyncio.wait_for(spice_client.health_check(), timeout=3)
        logger.info("SPICE service available", url=spice_url)
    except Exception as e:
        logger.warning("SPICE service unavailable, using SGP4 fallback", error=str(e))
    
    # Initialize async orbital engine
    from app.services.async_orbital_engine import AsyncOrbitalEngine
    async_orbital_engine.async_orbital_engine = AsyncOrbitalEngine(
        orbital_engine=orbital_engine,
        spice_client=spice_client,
        spice_url=spice_url
    )
    logger.info("AsyncOrbitalEngine initialized")
    
    # TLE loading in background (don't block startup)
    async def load_tle_background():
        try:
            await asyncio.wait_for(tle_service.update_orbital_engine(), timeout=30)
            logger.info("TLE data loaded", count=tle_service.satellite_count)
        except Exception as e:
            logger.warning("TLE load failed, using mock data", error=str(e))
    
    # Start TLE loading in background
    asyncio.create_task(load_tle_background())
    
    # Start background TLE refresh task
    refresh_task = asyncio.create_task(tle_refresh_loop())
    
    yield
    
    # Cleanup
    refresh_task.cancel()
    try:
        await async_orbital_engine.async_orbital_engine.shutdown()
    except:
        pass
    try:
        await cache.disconnect()
    except:
        pass
    try:
        await spacex_client.close()
    except:
        pass
    logger.info("Application shutdown complete")


async def tle_refresh_loop():
    """Background task to refresh TLE data periodically."""
    while True:
        try:
            await asyncio.sleep(settings.tle_refresh_interval)
            await tle_service.update_orbital_engine()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("TLE refresh failed", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real-time orbital intelligence for SpaceX Starlink constellation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Request logging middleware with version headers and metrics
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing, add version headers, and record metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Add API version headers
    response.headers["X-API-Version"] = API_VERSION
    response.headers["X-API-Min-Version"] = API_MIN_VERSION
    
    duration = time.time() - start_time
    
    # Record Prometheus metrics (skip /metrics endpoint to avoid recursion)
    if not request.url.path.startswith("/metrics"):
        # Simplify endpoint for cardinality control
        endpoint = request.url.path.split("?")[0]
        # Group dynamic IDs
        parts = endpoint.split("/")
        if len(parts) > 3 and parts[2] == "satellites" and len(parts) > 3:
            parts[3] = "{id}"
            endpoint = "/".join(parts)
        
        record_request(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration=duration
        )
    
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    return response


# Exception handlers - Specific handlers for better error visibility
from pydantic import ValidationError

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(
        "Validation error",
        path=request.url.path,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit errors with specific logging."""
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        ip=request.client.host if request.client else "unknown"
    )
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle truly unhandled exceptions only."""
    # Don't catch HTTPException (FastAPI handles it properly)
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        logger.info(
            "HTTP exception",
            status=exc.status_code,
            detail=exc.detail,
            path=request.url.path
        )
        raise exc  # Let FastAPI handle it
    
    # Log unhandled exceptions
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(satellites.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)
app.include_router(ephemeris.router, prefix=settings.api_prefix)
app.include_router(ground_stations.router, prefix=settings.api_prefix)
app.include_router(launches.router, prefix=settings.api_prefix)
app.include_router(ops.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(launches_live.router, prefix=settings.api_prefix)
app.include_router(cdm.router, prefix=settings.api_prefix)
app.include_router(export.router, prefix=settings.api_prefix)
app.include_router(monitoring.router, prefix=settings.api_prefix)
app.include_router(performance.router, prefix=settings.api_prefix)
app.include_router(rate_limits.router, prefix=settings.api_prefix)
app.include_router(launch_simulation.router, prefix=settings.api_prefix)
app.include_router(data_source.router, prefix=settings.api_prefix)
app.include_router(websocket.router)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "satellites_loaded": tle_service.satellite_count,
        "cache_connected": cache.is_connected,
        "last_tle_update": tle_service.last_update.isoformat() if tle_service.last_update else None
    }


# Root endpoint
@app.get("/")
async def root():
    """API information."""
    return {
        "name": settings.app_name,
        "version": API_VERSION,
        "api_prefix": settings.api_prefix,
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/positions"
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Exposes metrics for:
    - HTTP request duration and counts
    - Satellite propagation performance
    - Cache hit/miss rates
    - WebSocket connections
    - Error rates
    
    **Usage:**
    ```yaml
    # prometheus.yml
    scrape_configs:
      - job_name: 'spacex-orbital'
        static_configs:
          - targets: ['localhost:8000']
    ```
    """
    from fastapi.responses import Response
    
    # Update satellite count metric
    SATELLITES_LOADED.set(tle_service.satellite_count)
    if tle_service.last_update:
        TLE_LAST_UPDATE.set(tle_service.last_update.timestamp())
    
    return Response(
        content=get_metrics(),
        media_type=get_content_type()
    )


@app.get("/api/version")
async def api_version():
    """
    API version information.
    
    **Version Strategy:**
    - URL: /api/v1/* (current)
    - Headers: X-API-Version, X-API-Min-Version
    - Breaking changes increment major version
    - New features increment minor version
    
    **Deprecation Policy:**
    - Deprecated endpoints marked in docs
    - Deprecated versions supported for 6 months
    - Sunset header added for deprecated endpoints
    """
    return {
        "current_version": API_VERSION,
        "min_supported_version": API_MIN_VERSION,
        "versions": [
            {
                "version": "1.0.0",
                "path": "/api/v1",
                "status": "current",
                "released": "2024-02-01"
            }
        ],
        "deprecation_policy": {
            "notice_period_days": 180,
            "headers": ["Sunset", "Deprecation"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
