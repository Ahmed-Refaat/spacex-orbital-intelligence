"""
OMM Upload API endpoint.

Add this to satellites.py at the end of the file.
"""

@router.post("/omm")
@limiter.limit("10/minute")
async def upload_omm(
    request: Request,
    file: UploadFile = File(..., description="OMM file (XML or JSON)"),
    format: Literal['xml', 'json'] = Form('xml', description="OMM format"),
    source: str = Form("user_upload", description="Data source identifier")
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
    
    # Basic format validation
    if format == 'xml':
        if not omm_content.strip().startswith('<?xml'):
            raise HTTPException(
                status_code=400,
                detail="Invalid XML: Must start with <?xml declaration"
            )
        if '<omm' not in omm_content.lower():
            raise HTTPException(
                status_code=400,
                detail="Invalid OMM XML: Missing <omm> root element"
            )
    elif format == 'json':
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
        result = await spice_client.load_omm(omm_content, format=format, validate=True)
        
        # Store metadata in cache for future reference
        metadata = {
            "satellite_id": result.satellite_id,
            "name": result.name,
            "epoch": result.epoch.isoformat(),
            "source": source,
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
            source=source,
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
    satellite_id: str,
    epoch: Optional[datetime] = Query(None, description="Propagation epoch (default: now)"),
    include_covariance: bool = Query(False, description="Include uncertainty ellipsoid")
):
    """
    Get satellite position with optional uncertainty information.
    
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
