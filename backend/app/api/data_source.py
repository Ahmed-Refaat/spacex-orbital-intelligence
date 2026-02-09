"""
Data Source Management API - Switch between TLE and OMM formats.
"""
from fastapi import APIRouter, HTTPException
from typing import Literal
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
    - CCSDS standard format
    - Includes covariance matrices
    - Higher accuracy propagation
    - Used by NASA, ESA, SpaceX
    - Must be uploaded via /satellites/omm endpoint
    
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
        
        # Note: OMM data must be uploaded via /satellites/omm endpoint
        logger.warning(
            "OMM mode active - upload OMM files via POST /satellites/omm"
        )
    
    return await get_data_source_status()


def get_current_source() -> Literal["tle", "omm"]:
    """Get current active data source."""
    return _current_source
