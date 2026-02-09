"""
Data Source Management API - Switch between TLE and OMM formats.
"""
from fastapi import APIRouter, HTTPException
from typing import Literal, Optional
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/data-source", tags=["Configuration"])

# Global state for data source preference
_current_source: Literal["tle", "omm"] = "tle"


class DataSourceConfig(BaseModel):
    """Data source configuration."""
    source: Literal["tle", "omm"]
    auto_refresh: bool = True
    refresh_interval_seconds: int = 3600


class DataSourceStatus(BaseModel):
    """Current data source status."""
    current_source: Literal["tle", "omm"]
    available_sources: list[str]
    satellite_count: int
    last_update: str
    auto_refresh: bool


@router.get("", response_model=DataSourceStatus)
async def get_data_source_status():
    """
    Get current data source configuration.
    
    **Returns:**
    - current_source: "tle" or "omm"
    - available_sources: List of available data sources
    - satellite_count: Number of loaded satellites
    - last_update: ISO timestamp of last data refresh
    - auto_refresh: Whether auto-refresh is enabled
    """
    from app.services.tle_service import tle_service
    from app.services.orbital_engine import orbital_engine
    from datetime import datetime, timezone
    
    return DataSourceStatus(
        current_source=_current_source,
        available_sources=["tle", "omm"],
        satellite_count=orbital_engine.satellite_count,
        last_update=datetime.now(timezone.utc).isoformat(),
        auto_refresh=True
    )


@router.post("", response_model=DataSourceStatus)
async def set_data_source(config: DataSourceConfig):
    """
    Switch between TLE and OMM data sources.
    
    **TLE (Two-Line Elements):**
    - Classic format from Space-Track.org
    - Simple orbital elements
    - Fast propagation
    - ~9,000+ objects in catalog
    
    **OMM (Orbit Mean-Elements Message):**
    - CCSDS standard format from Space-Track GP class
    - Includes covariance matrices (when available)
    - Higher accuracy propagation
    - Used by NASA, ESA, SpaceX
    - Auto-fetched from Space-Track or uploaded manually
    
    **Example:**
    ```json
    {
      "source": "tle",
      "auto_refresh": true,
      "refresh_interval_seconds": 3600
    }
    ```
    """
    global _current_source
    from app.services.tle_service import tle_service
    from app.services.orbital_engine import orbital_engine
    
    if config.source == "tle":
        # Load TLE data from Space-Track
        logger.info("Switching to TLE data source")
        _current_source = "tle"
        
        # Force reload TLE data
        await tle_service.ensure_data_loaded()
        
        logger.info(
            "TLE data loaded",
            satellite_count=orbital_engine.satellite_count
        )
        
    elif config.source == "omm":
        # Switch to OMM data source
        logger.info("Switching to OMM data source")
        _current_source = "omm"
        
        # Note: OMM data can be fetched from Space-Track or uploaded manually
        logger.info(
            "OMM mode active - use GET /data-source/omm/fetch to download from Space-Track"
        )
    
    return await get_data_source_status()


@router.get("/omm/fetch")
async def fetch_omm_from_spacetrack(
    object_name: Optional[str] = None,
    format: Literal["xml", "json"] = "json",
    limit: int = 1000
):
    """
    Fetch OMM data directly from Space-Track.org.
    
    **Parameters:**
    - object_name: Filter by satellite name (e.g., "STARLINK" for all Starlink sats)
    - format: "xml" (CCSDS OMM) or "json"
    - limit: Maximum number of satellites to fetch
    
    **Examples:**
    ```bash
    # Get all active satellites (up to 1000)
    GET /data-source/omm/fetch?format=json&limit=1000
    
    # Get only Starlink satellites
    GET /data-source/omm/fetch?object_name=STARLINK&limit=5000
    
    # Get OMM XML format
    GET /data-source/omm/fetch?format=xml
    ```
    
    **Returns:**
    OMM data in requested format (XML or JSON)
    """
    from app.services.spacetrack import spacetrack_client
    
    if not spacetrack_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Space-Track credentials not configured"
        )
    
    logger.info(
        "Fetching OMM from Space-Track",
        object_name=object_name,
        format=format,
        limit=limit
    )
    
    try:
        if object_name:
            # Fetch specific satellite(s) by name
            from httpx import AsyncClient
            client = await spacetrack_client._get_client()
            
            if not await spacetrack_client._authenticate():
                raise HTTPException(
                    status_code=503,
                    detail="Failed to authenticate with Space-Track"
                )
            
            query = (
                f"/basicspacedata/query/class/gp"
                f"/OBJECT_NAME/~~{object_name}"
                f"/EPOCH/>now-7"
                f"/orderby/NORAD_CAT_ID,EPOCH desc"
                f"/limit/{limit}"
                f"/format/{format}"
            )
            
            response = await client.get(query, cookies=spacetrack_client._cookies)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Space-Track query failed"
                )
            
            omm_data = response.text
        else:
            # Fetch all active satellites
            omm_data = await spacetrack_client.get_omm(
                format=format,
                limit=limit
            )
        
        if not omm_data:
            raise HTTPException(
                status_code=404,
                detail="No OMM data found"
            )
        
        logger.info(
            "OMM data fetched",
            size_bytes=len(omm_data)
        )
        
        # Return raw OMM data
        from fastapi.responses import PlainTextResponse
        
        content_type = "application/xml" if format == "xml" else "application/json"
        
        return PlainTextResponse(
            content=omm_data,
            media_type=content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OMM fetch failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch OMM data: {str(e)}"
        )


def get_current_source() -> Literal["tle", "omm"]:
    """Get current active data source."""
    return _current_source
