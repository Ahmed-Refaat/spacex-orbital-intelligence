"""Satellite API endpoints."""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Request, Depends, Path
from typing import Optional, Literal
from datetime import datetime
import defusedxml.ElementTree as ET

from app.services.orbital_engine import orbital_engine
from app.services.tle_service import tle_service
from app.services.spacex_api import spacex_client
from app.services.cache import cache
from app.services.mock_satellites import mock_generator
from app.services.spice_client import spice_client, SpiceServiceUnavailable, SpiceClientError
from app.core.security import limiter, verify_api_key
from app.models.omm import OMMUploadForm
from app.models.validators import NoradIdParam, PaginationParams
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/satellites", tags=["Satellites"])


def validate_satellite_id(
    satellite_id: str = Path(
        ...,
        description="NORAD catalog number (1-99999)",
        regex=r'^\d{1,5}$'
    )
) -> str:
    """
    Validate satellite_id path parameter.
    
    Security: Prevents injection attacks and invalid inputs.
    """
    try:
        validated = NoradIdParam(value=satellite_id)
        return validated.value
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_satellites(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _auth: bool = Depends(verify_api_key)
):
    """List all tracked satellites with current positions."""
    # Ensure TLE data is loaded
    await tle_service.ensure_data_loaded()
    
    # Get all satellite IDs
    all_ids = orbital_engine.satellite_ids
    total = len(all_ids)
    
    # Paginate
    page_ids = all_ids[offset:offset + limit]
    
    # Get current positions
    satellites = []
    for sat_id in page_ids:
        pos = orbital_engine.propagate(sat_id)
        if pos:
            satellites.append({
                **pos.to_dict(),
                "name": tle_service.get_satellite_name(sat_id)
            })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "satellites": satellites
    }


@router.get("/positions")
async def get_all_positions():
    """Get current positions of all satellites (optimized for 3D visualization)."""
    cache_key = "satellites:positions:all"
    
    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Check if TLE data already loaded (don't wait for fetch)
    positions = []
    if orbital_engine.satellite_count > 0:
        positions = orbital_engine.get_all_positions()
    
    # Use mock data if no TLE data available (fast path)
    if not positions:
        mock_positions = mock_generator.get_all_positions()
        result = {
            "count": len(mock_positions),
            "source": "simulated",
            "positions": mock_positions
        }
    else:
        # Compact format for visualization
        result = {
            "count": len(positions),
            "source": "tle",
            "positions": [
                {
                    "id": p.satellite_id,
                    "lat": round(p.latitude, 4),
                    "lon": round(p.longitude, 4),
                    "alt": round(p.altitude, 2),
                    "v": round(p.velocity, 3)
                }
                for p in positions
            ]
        }
    
    # Cache for 5 seconds
    await cache.set(cache_key, result, ttl=5)
    
    return result


@router.get("/{satellite_id}")
async def get_satellite(
    satellite_id: str = Depends(validate_satellite_id)
):
    """
    Get detailed information for a specific satellite.
    
    Args:
        satellite_id: NORAD catalog number (validated, 1-99999)
        
    Security: Input validated to prevent injection attacks.
    """
    await tle_service.ensure_data_loaded()
    
    pos = orbital_engine.propagate(satellite_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    tle = tle_service.get_tle(satellite_id)
    
    return {
        **pos.to_dict(),
        "name": tle_service.get_satellite_name(satellite_id),
        "tle": {
            "line1": tle[0] if tle else None,
            "line2": tle[1] if tle else None
        }
    }


@router.get("/{satellite_id}/orbit")
async def get_satellite_orbit(
    satellite_id: str = Depends(validate_satellite_id),
    hours: int = Query(24, ge=1, le=168),
    step_minutes: int = Query(5, ge=1, le=60)
):
    """
    Get orbital path for visualization.
    
    Security: Input validated to prevent injection attacks.
    """
    cache_key = f"satellites:orbit:{satellite_id}:{hours}:{step_minutes}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Try TLE data first
    try:
        await tle_service.ensure_data_loaded()
        positions = orbital_engine.propagate_orbit(satellite_id, hours, step_minutes)
    except Exception:
        positions = []
    
    if positions:
        result = {
            "satellite_id": satellite_id,
            "name": tle_service.get_satellite_name(satellite_id),
            "hours": hours,
            "step_minutes": step_minutes,
            "points": len(positions),
            "source": "tle",
            "orbit": [
                {
                    "t": p.timestamp.isoformat(),
                    "lat": round(p.latitude, 4),
                    "lon": round(p.longitude, 4),
                    "alt": round(p.altitude, 2)
                }
                for p in positions
            ]
        }
    else:
        # Fall back to mock data
        steps = (hours * 60) // step_minutes
        path = mock_generator.get_orbit_path(satellite_id, hours, steps)
        if not path:
            raise HTTPException(status_code=404, detail="Satellite not found")
        
        result = {
            "satellite_id": satellite_id,
            "name": satellite_id,
            "hours": hours,
            "step_minutes": step_minutes,
            "points": len(path),
            "source": "simulated",
            "orbit": path
        }
    
    # Cache for 5 minutes
    await cache.set(cache_key, result, ttl=300)
    
    return result


@router.get("/starlink/metadata")
async def get_starlink_metadata(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get Starlink satellite metadata from SpaceX API."""
    cache_key = f"starlink:metadata:{limit}:{offset}"
    
    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    satellites = await spacex_client.get_starlink_satellites(limit, offset)
    
    result = {
        "count": len(satellites),
        "limit": limit,
        "offset": offset,
        "satellites": [s.to_dict() for s in satellites]
    }
    
    # Cache for 10 minutes
    await cache.set(cache_key, result, ttl=600)
    
    return result


@router.post("/omm")
@limiter.limit("10/minute")
async def upload_omm(
    request: Request,
    file: UploadFile = File(..., description="OMM file (XML or JSON)"),
    form_data: OMMUploadForm = Depends()
):
    """
    Upload satellite orbital data in OMM (Orbit Mean-Elements Message) format.
    
    **Supported formats:**
    - OMM XML (CCSDS 2.0)
    - OMM JSON
    
    **Features:**
    - Parses OMM via SPICE API
    - Extracts covariance matrix (if present)
    - Validates against CCSDS schema
    - Stores metadata for future queries
    
    **NASA Compliance:**
    - CCSDS OMM 2.0 standard
    - Used by NASA, ESA, SpaceX, commercial operators
    - Enables high-accuracy propagation with uncertainty tracking
    
    **Rate limit:** 10 uploads per minute per IP
    
    **Returns:**
    - satellite_id: NORAD catalog number
    - name: Satellite name
    - epoch: Data epoch
    - has_covariance: Whether covariance matrix is included
    - source: Data source
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/satellites/omm \\
      -F "file=@iss_omm.xml" \\
      -F "format=xml" \\
      -F "source=nasa_cdm"
    ```
    """
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_size / 1024 / 1024}MB"
        )
    
    # Decode content
    try:
        omm_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded text"
        )
    
    # Security: Sanitize XML to prevent XXE attacks
    if form_data.format == 'xml':
        try:
            # Parse with defusedxml (forbids DTD and entities)
            tree = ET.fromstring(
                omm_content.encode('utf-8'),
                forbid_dtd=True,
                forbid_entities=True,
                forbid_external=True
            )
            # Validate it's an OMM document
            if tree.tag.lower().endswith('omm') or 'omm' in tree.tag.lower():
                # Convert back to string after sanitization
                omm_content = ET.tostring(tree, encoding='utf-8').decode('utf-8')
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid OMM XML: Missing <omm> root element"
                )
        except ET.ParseError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid XML: {str(e)}"
            )
        except Exception as e:
            logger.error("XML parsing error", error=str(e))
            raise HTTPException(
                status_code=400,
                detail="Invalid XML format"
            )
    elif form_data.format == 'json':
        # Basic JSON validation
        if not (omm_content.strip().startswith('{') or omm_content.strip().startswith('[')):
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON: Must start with { or ["
            )
    
    # Check SPICE service availability
    if not await spice_client.health_check():
        logger.error("SPICE service unavailable for OMM upload")
        raise HTTPException(
            status_code=503,
            detail="SPICE service unavailable. OMM processing requires SPICE. "
                   "Please ensure SPICE service is running (docker-compose up spice)"
        )
    
    try:
        # Load OMM into SPICE
        result = await spice_client.load_omm(omm_content, format=form_data.format, validate=True)
        
        # Store metadata in cache for future reference
        metadata = {
            "satellite_id": result.satellite_id,
            "name": result.name,
            "epoch": result.epoch.isoformat(),
            "source": form_data.source,
            "format": "omm",
            "has_covariance": result.has_covariance,
            "uploaded_at": datetime.utcnow().isoformat(),
            "omm_content_preview": omm_content[:500]  # First 500 chars for reference
        }
        
        cache_key = f"satellite:metadata:{result.satellite_id}"
        await cache.set(cache_key, metadata, ttl=86400)  # 24 hours
        
        logger.info(
            "OMM uploaded successfully",
            satellite_id=result.satellite_id,
            source=form_data.source,
            has_covariance=result.has_covariance,
            file_size_kb=len(content) / 1024
        )
        
        return {
            "status": "success",
            "message": "OMM loaded successfully into SPICE engine",
            **result.to_dict()
        }
        
    except SpiceServiceUnavailable as e:
        logger.error("SPICE service unavailable during upload", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"SPICE service unavailable: {str(e)}"
        )
    
    except SpiceClientError as e:
        logger.error("SPICE client error during OMM upload", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"OMM processing failed: {str(e)}"
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error during OMM upload",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during OMM processing: {str(e)}"
        )


@router.get("/{satellite_id}/position")
async def get_satellite_position_with_uncertainty(
    satellite_id: str = Depends(validate_satellite_id),
    epoch: Optional[datetime] = Query(None, description="Propagation epoch (default: now)"),
    include_covariance: bool = Query(False, description="Include uncertainty ellipsoid")
):
    """
    Get satellite position with optional uncertainty information.
    
    Security: Input validated to prevent injection attacks.
    
    If satellite was loaded from OMM with covariance matrix,
    optionally includes position/velocity uncertainty (1-sigma).
    
    **Parameters:**
    - satellite_id: NORAD catalog number
    - epoch: Propagation time (ISO 8601) or current time
    - include_covariance: Include uncertainty data
    
    **Returns:**
    - position: x, y, z (ECI frame, km)
    - velocity: vx, vy, vz (km/s)
    - geographic: latitude, longitude, altitude
    - uncertainty: (if requested and available)
      - position_sigma_km: 1-sigma uncertainty in x, y, z
      - total_position_uncertainty_km: RSS of position uncertainties
      - covariance_matrix: Full 6x6 matrix
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/v1/satellites/25544/position?include_covariance=true"
    ```
    """
    if epoch is None:
        epoch = datetime.utcnow()
    
    # Check if satellite was loaded from OMM
    metadata = await cache.get(f"satellite:metadata:{satellite_id}")
    
    if metadata and metadata.get("format") == "omm":
        # Satellite loaded from OMM - use SPICE if available
        try:
            if await spice_client.health_check():
                position, covariance = await spice_client.propagate_omm(
                    satellite_id,
                    epoch,
                    include_covariance=(include_covariance and metadata.get("has_covariance", False))
                )
                
                response = position.to_dict()
                response["data_source"] = "omm_via_spice"
                
                # Add covariance if present
                if covariance is not None:
                    response["uncertainty"] = covariance.to_dict()
                
                return response
            else:
                logger.warning(
                    "SPICE unavailable, falling back to SGP4",
                    satellite_id=satellite_id
                )
        except Exception as e:
            logger.warning(
                "SPICE propagation failed, falling back to SGP4",
                satellite_id=satellite_id,
                error=str(e)
            )
    
    # Fallback: Standard SGP4 propagation (no covariance)
    position = orbital_engine.propagate(satellite_id, epoch)
    if not position:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    response = position.to_dict()
    response["data_source"] = "tle_sgp4"
    
    if include_covariance:
        response["uncertainty"] = None
        response["uncertainty_note"] = "Covariance not available for TLE-based propagation. Upload OMM with covariance matrix."
    
    return response
