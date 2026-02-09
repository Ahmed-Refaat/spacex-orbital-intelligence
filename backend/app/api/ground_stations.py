"""
Ground Station Visibility API - ANISE-powered AER calculations.

Provides Azimuth, Elevation, Range calculations for satellite visibility
from ground stations.
"""
from fastapi import APIRouter, HTTPException, Query, Path
from datetime import datetime, timezone
from typing import Optional, List
import structlog

from app.models.ground_station import GroundStation, GROUND_STATIONS, get_ground_station
from app.services.anise_planetary import get_planetary_service
from app.services.orbital_engine import orbital_engine

router = APIRouter(prefix="/ground-stations", tags=["Ground Stations"])
logger = structlog.get_logger(__name__)


@router.get("/")
async def list_ground_stations():
    """
    List all available ground stations.
    
    Returns:
        List of ground stations with coordinates
    
    Example:
        GET /ground-stations/
    """
    return {
        "count": len(GROUND_STATIONS),
        "stations": [
            {
                "id": key,
                **station.to_dict()
            }
            for key, station in GROUND_STATIONS.items()
        ]
    }


@router.get("/{station_name}")
async def get_station_info(
    station_name: str = Path(..., description="Station name or ID (e.g., DSS-65, Houston)")
):
    """
    Get information about a specific ground station.
    
    Args:
        station_name: Station identifier
    
    Returns:
        Station details (lat, lon, altitude, etc.)
    """
    station = get_ground_station(station_name)
    
    if not station:
        available = ", ".join(GROUND_STATIONS.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Ground station '{station_name}' not found. Available: {available}"
        )
    
    return station.to_dict()


@router.get("/{station_name}/visibility/{satellite_id}")
async def get_satellite_visibility(
    station_name: str = Path(..., description="Station name (e.g., DSS-65)"),
    satellite_id: str = Path(..., description="Satellite NORAD ID (e.g., 25544)"),
    epoch: Optional[str] = Query(None, description="Epoch (ISO 8601 UTC), default: now")
):
    """
    Calculate satellite visibility from ground station (AER).
    
    **Powered by ANISE + SPICE** for high-precision calculations.
    
    Args:
        station_name: Ground station identifier
        satellite_id: NORAD catalog number
        epoch: Time of calculation (ISO 8601 UTC)
    
    Returns:
        Azimuth, Elevation, Range, Visibility status
    
    Example:
        GET /ground-stations/DSS-65/visibility/25544?epoch=2024-01-01T12:00:00Z
        
        Returns:
        {
          "station": "DSS-65",
          "satellite_id": "25544",
          "epoch": "2024-01-01T12:00:00+00:00",
          "azimuth_deg": 93.62,
          "elevation_deg": -40.67,
          "range_km": 8928.60,
          "is_visible": false,
          "visibility_reason": "Below horizon (elevation < 5°)",
          "computation_time_ms": 0.234,
          "data_source": "anise/sgp4"
        }
    """
    # Get ground station
    station = get_ground_station(station_name)
    if not station:
        raise HTTPException(
            status_code=404,
            detail=f"Ground station '{station_name}' not found"
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
                detail=f"Invalid epoch format: {epoch}. Use ISO 8601"
            )
    
    # Get satellite position (SGP4 propagation)
    satellite_pos = orbital_engine.propagate(satellite_id, query_epoch)
    if not satellite_pos:
        raise HTTPException(
            status_code=404,
            detail=f"Satellite {satellite_id} not found or TLE unavailable"
        )
    
    # Calculate AER using ANISE
    try:
        import time
        start = time.perf_counter()
        
        anise_service = get_planetary_service()
        
        if not anise_service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="ANISE service unavailable. High-precision AER requires ANISE."
            )
        
        # Extract position/velocity from SGP4 result
        sat_pos = (satellite_pos.x, satellite_pos.y, satellite_pos.z)
        sat_vel = (satellite_pos.vx, satellite_pos.vy, satellite_pos.vz)
        
        azimuth, elevation, range_km = anise_service.calculate_aer(
            sat_pos,
            sat_vel,
            station.latitude_deg,
            station.longitude_deg,
            station.altitude_km,
            query_epoch
        )
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Determine visibility
        is_visible = elevation >= station.min_elevation_deg
        
        if is_visible:
            visibility_reason = f"Above horizon (elevation ≥ {station.min_elevation_deg}°)"
        else:
            visibility_reason = f"Below horizon (elevation < {station.min_elevation_deg}°)"
        
        logger.info(
            "aer_query",
            station=station_name,
            satellite_id=satellite_id,
            azimuth=round(azimuth, 2),
            elevation=round(elevation, 2),
            range_km=round(range_km, 2),
            visible=is_visible,
            duration_ms=round(duration_ms, 3)
        )
        
        return {
            "station": {
                "name": station.name,
                "latitude_deg": station.latitude_deg,
                "longitude_deg": station.longitude_deg,
                "altitude_km": station.altitude_km,
                "min_elevation_deg": station.min_elevation_deg
            },
            "satellite_id": satellite_id,
            "satellite_name": satellite_pos.satellite_id,  # From TLE
            "epoch": query_epoch.isoformat(),
            "aer": {
                "azimuth_deg": round(azimuth, 2),
                "elevation_deg": round(elevation, 2),
                "range_km": round(range_km, 2)
            },
            "is_visible": is_visible,
            "visibility_reason": visibility_reason,
            "computation_time_ms": round(duration_ms, 3),
            "data_source": "anise+sgp4",
            "satellite_altitude_km": round(satellite_pos.altitude, 2)
        }
    
    except Exception as e:
        logger.error(
            "aer_calculation_failed",
            error=str(e),
            station=station_name,
            satellite_id=satellite_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"AER calculation failed: {str(e)}"
        )
