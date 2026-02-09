"""
Planetary Ephemeris API - ANISE-powered.

High-precision planetary positions using JPL DE440s ephemeris.
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional, Literal
import structlog

from app.services.anise_planetary import get_planetary_service

router = APIRouter(prefix="/ephemeris", tags=["Ephemeris"])
logger = structlog.get_logger(__name__)


@router.get("/health")
async def ephemeris_health():
    """Check if ANISE ephemeris service is available."""
    service = get_planetary_service()
    
    return {
        "service": "anise_ephemeris",
        "status": "ready" if service.is_ready() else "unavailable",
        "ephemeris": "JPL DE440s (1900-2050)",
        "precision": "sub-kilometer"
    }


@router.get("/{body}")
async def get_body_ephemeris(
    body: Literal["sun", "moon", "earth", "mercury", "venus", "mars", "jupiter", "saturn"],
    epoch: Optional[str] = Query(
        None,
        description="Epoch (ISO 8601 UTC). Default: now"
    ),
    observer: str = Query(
        "earth",
        description="Observer frame (earth, sun, moon, etc.)"
    )
):
    """
    Get celestial body position at specified epoch.
    
    **Powered by ANISE + JPL DE440s ephemeris**
    
    Args:
        body: Celestial body (sun, moon, earth, etc.)
        epoch: Time of query (ISO 8601 UTC) or current time
        observer: Observer reference frame
    
    Returns:
        Position vector (x, y, z) in km (J2000 inertial frame)
        + Metadata (distance, computation time)
    
    Example:
        GET /ephemeris/sun?epoch=2024-01-01T12:00:00Z&observer=earth
        
        Returns:
        {
          "body": "sun",
          "observer": "earth",
          "epoch": "2024-01-01T12:00:00+00:00",
          "position_km": {
            "x": 26344512.3,
            "y": 132789456.1,
            "z": 57561234.8
          },
          "distance_km": 147098290.5,
          "computation_time_ms": 0.234,
          "data_source": "anise/de440s",
          "precision": "sub-kilometer"
        }
    """
    service = get_planetary_service()
    
    if not service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="ANISE ephemeris service unavailable. Kernels not loaded."
        )
    
    # Parse epoch
    if epoch is None:
        query_epoch = datetime.now(timezone.utc)
    else:
        try:
            query_epoch = datetime.fromisoformat(epoch.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid epoch format: {epoch}. Use ISO 8601 (e.g., 2024-01-01T12:00:00Z)"
            )
    
    # Query position
    try:
        import time
        start = time.perf_counter()
        
        x, y, z = service.get_body_position(body, query_epoch, observer)
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Calculate distance
        distance = (x**2 + y**2 + z**2) ** 0.5
        
        logger.info(
            "ephemeris_query",
            body=body,
            observer=observer,
            epoch=query_epoch.isoformat(),
            distance_km=round(distance, 3),
            duration_ms=round(duration_ms, 3)
        )
        
        return {
            "body": body,
            "observer": observer,
            "epoch": query_epoch.isoformat(),
            "position_km": {
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(z, 3)
            },
            "distance_km": round(distance, 3),
            "computation_time_ms": round(duration_ms, 3),
            "data_source": "anise/de440s",
            "precision": "sub-kilometer",
            "frame": "J2000"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ephemeris_query_failed", error=str(e), body=body)
        raise HTTPException(
            status_code=500,
            detail=f"Ephemeris query failed: {str(e)}"
        )


@router.get("/sun/beta-angle/{satellite_id}")
async def calculate_beta_angle(
    satellite_id: str,
    epoch: Optional[str] = Query(None, description="Epoch (ISO 8601 UTC)")
):
    """
    Calculate beta angle for a satellite.
    
    Beta angle = angle between orbit plane and Sun vector.
    Important for:
    - Solar panel orientation
    - Thermal management
    - Eclipse prediction
    
    Args:
        satellite_id: NORAD catalog number
        epoch: Time of calculation (default: now)
    
    Returns:
        Beta angle in degrees + Sun vector
    
    Note: Requires satellite orbital data (TLE).
    Phase 1: Returns Sun position only (beta calc in Phase 2).
    """
    service = get_planetary_service()
    
    if not service.is_ready():
        raise HTTPException(status_code=503, detail="ANISE unavailable")
    
    # Parse epoch
    if epoch is None:
        query_epoch = datetime.now(timezone.utc)
    else:
        query_epoch = datetime.fromisoformat(epoch.replace('Z', '+00:00'))
    
    # Get Sun position
    sun_x, sun_y, sun_z = service.get_sun_position(query_epoch, observer="EARTH")
    
    return {
        "satellite_id": satellite_id,
        "epoch": query_epoch.isoformat(),
        "sun_position_km": {
            "x": round(sun_x, 3),
            "y": round(sun_y, 3),
            "z": round(sun_z, 3)
        },
        "note": "Beta angle calculation requires satellite orbit data. Coming in Phase 2.",
        "data_source": "anise/de440s"
    }
