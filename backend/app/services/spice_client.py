"""
SPICE API Client - OMM Input Support

Integrates with SPICE service (haisamido/spice) for:
- OMM parsing (XML/JSON)
- High-performance SGP4 propagation
- Covariance matrix handling
- Batch processing

Architecture:
    Backend FastAPI → SpiceClient → SPICE Service (Docker)
"""

import httpx
import numpy as np
from circuitbreaker import circuit
from typing import Optional, Tuple, List, Literal
from datetime import datetime
from dataclasses import dataclass
import structlog
from circuitbreaker import circuit

from app.core.rate_limiter import spice_rate_limiter

logger = structlog.get_logger()


@dataclass
class OMMLoadResult:
    """Result from OMM loading."""
    satellite_id: str
    name: str
    epoch: datetime
    has_covariance: bool
    source: str
    
    def to_dict(self) -> dict:
        return {
            "satellite_id": self.satellite_id,
            "name": self.name,
            "epoch": self.epoch.isoformat(),
            "has_covariance": self.has_covariance,
            "source": self.source
        }


@dataclass
class CovarianceMatrix:
    """6x6 covariance matrix for position/velocity uncertainty."""
    matrix: np.ndarray  # 6x6 array
    
    def __post_init__(self):
        """Validate matrix shape."""
        if self.matrix.shape != (6, 6):
            raise ValueError(f"Covariance must be 6x6, got {self.matrix.shape}")
    
    @property
    def position_sigma_km(self) -> dict:
        """Position uncertainty (1-sigma) in km."""
        return {
            "x": np.sqrt(self.matrix[0, 0]) / 1000,  # m to km
            "y": np.sqrt(self.matrix[1, 1]) / 1000,
            "z": np.sqrt(self.matrix[2, 2]) / 1000
        }
    
    @property
    def velocity_sigma_km_s(self) -> dict:
        """Velocity uncertainty (1-sigma) in km/s."""
        return {
            "vx": np.sqrt(self.matrix[3, 3]) / 1000,
            "vy": np.sqrt(self.matrix[4, 4]) / 1000,
            "vz": np.sqrt(self.matrix[5, 5]) / 1000
        }
    
    @property
    def total_position_uncertainty_km(self) -> float:
        """Total position uncertainty (RSS of x, y, z)."""
        return np.sqrt(
            self.matrix[0, 0] + self.matrix[1, 1] + self.matrix[2, 2]
        ) / 1000
    
    def to_dict(self) -> dict:
        """Serialize for JSON."""
        return {
            "matrix": self.matrix.tolist(),
            "position_sigma_km": self.position_sigma_km,
            "velocity_sigma_km_s": self.velocity_sigma_km_s,
            "total_position_uncertainty_km": self.total_position_uncertainty_km
        }


class SpiceClientError(Exception):
    """Base exception for SPICE client errors."""
    pass


class SpiceServiceUnavailable(SpiceClientError):
    """SPICE service is not available."""
    pass


class SpiceClient:
    """
    Client for SPICE API service.
    
    Features:
    - OMM parsing (XML/JSON)
    - High-performance propagation (750K/s)
    - Covariance matrix handling
    - Circuit breaker for resilience
    - Automatic fallback to SGP4
    
    Example:
        >>> client = SpiceClient("http://spice:3000")
        >>> await client.health_check()
        True
        >>> result = await client.load_omm(omm_xml_content, format='xml')
        >>> position, cov = await client.propagate_omm("25544", datetime.utcnow())
    """
    
    def __init__(
        self,
        base_url: str = "http://spice:3000",
        timeout: float = 30.0
    ):
        """
        Initialize SPICE client.
        
        Args:
            base_url: SPICE service URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.available = False
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )
        
        logger.info("SpiceClient initialized", base_url=base_url)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        logger.info("SpiceClient closed")
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="spice_health_check")
    async def health_check(self) -> bool:
        """
        Check if SPICE service is available.
        
        Rate limited to max 1 check per 30 seconds to avoid API abuse.
        Circuit breaker protects against cascade failures.
        Opens after 5 consecutive failures, recovers after 60s.
        
        Returns:
            True if service is healthy
        """
        # Rate limiting: Use cached result if available
        if not spice_rate_limiter.health_check.can_call():
            cached_result = spice_rate_limiter.health_check.get_cached()
            if cached_result is not None:
                logger.debug("SPICE health check: using cached result")
                self.available = cached_result
                return cached_result
        
        # Make actual call
        try:
            response = await self.client.get("/api/spice/sgp4/health")
            self.available = response.status_code == 200
            
            # Cache the result
            spice_rate_limiter.health_check.record_call(self.available)
            
            if self.available:
                logger.debug("SPICE health check passed")
            else:
                logger.warning(
                    "SPICE health check failed",
                    status_code=response.status_code
                )
            
            return self.available
            
        except Exception as e:
            self.available = False
            logger.warning("SPICE health check error", error=str(e))
            # Cache the failure result too
            spice_rate_limiter.health_check.record_call(False)
            return False
    
    @circuit(failure_threshold=3, recovery_timeout=30, name="spice_load_omm")
    async def load_omm(
        self,
        omm_content: str,
        format: Literal['xml', 'json'] = 'xml',
        validate: bool = True
    ) -> OMMLoadResult:
        """
        Load OMM into SPICE engine.
        
        Rate limited to 5 uploads per minute to avoid API abuse.
        
        Args:
            omm_content: OMM XML or JSON string
            format: 'xml' or 'json'
            validate: Validate against CCSDS schema
        
        Returns:
            OMMLoadResult with satellite metadata
        
        Raises:
            SpiceServiceUnavailable: Service not available
            SpiceClientError: Loading failed or rate limited
        """
        # Check rate limit
        if not spice_rate_limiter.omm_load.can_call():
            stats = spice_rate_limiter.omm_load.get_stats()
            logger.warning(
                "SPICE OMM load rate limited",
                calls_last_minute=stats["calls_last_minute"],
                max_allowed=stats["max_calls_per_minute"]
            )
            raise SpiceClientError(
                f"Rate limit exceeded: {stats['calls_last_minute']}/{stats['max_calls_per_minute']} "
                "uploads per minute. Please wait before uploading again."
            )
        
        if not self.available:
            raise SpiceServiceUnavailable(
                "SPICE service unavailable. Run health_check() first."
            )
        
        payload = {
            "format": format,
            "omm": omm_content,
            "validate": validate
        }
        
        try:
            response = await self.client.post(
                "/api/spice/omm/load",
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(
                    "SPICE OMM load failed",
                    status_code=response.status_code,
                    error=error_detail
                )
                raise SpiceClientError(f"OMM load failed: {error_detail}")
            
            data = response.json()
            
            result = OMMLoadResult(
                satellite_id=data["satellite_id"],
                name=data.get("name", "Unknown"),
                epoch=datetime.fromisoformat(data["epoch"]),
                has_covariance=data.get("has_covariance", False),
                source=data.get("source", "omm")
            )
            
            # Record successful call for rate limiting
            spice_rate_limiter.omm_load.record_call(result)
            
            logger.info(
                "OMM loaded into SPICE",
                satellite_id=result.satellite_id,
                has_covariance=result.has_covariance
            )
            
            return result
            
        except httpx.HTTPError as e:
            logger.error("SPICE HTTP error", error=str(e))
            raise SpiceClientError(f"HTTP error: {str(e)}")
    
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    async def propagate_omm(
        self,
        satellite_id: str,
        epoch: datetime,
        include_covariance: bool = True
    ) -> Tuple['SatellitePosition', Optional[CovarianceMatrix]]:
        """
        Propagate satellite loaded from OMM.
        
        Circuit breaker protection:
        - Opens after 5 consecutive failures
        - Stays open for 60 seconds
        
        Args:
            satellite_id: Satellite ID (NORAD catalog number)
            epoch: Propagation epoch
            include_covariance: Include uncertainty if available
        
        Returns:
            (position, covariance) tuple
            covariance is None if not available or not requested
        
        Raises:
            SpiceServiceUnavailable: Service not available
            SpiceClientError: Propagation failed
        """
        if not self.available:
            raise SpiceServiceUnavailable("SPICE service unavailable")
        
        payload = {
            "satellite_id": satellite_id,
            "epoch": epoch.isoformat(),
            "include_covariance": include_covariance
        }
        
        try:
            response = await self.client.post(
                "/api/spice/omm/propagate",
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(
                    "SPICE propagation failed",
                    satellite_id=satellite_id,
                    error=error_detail
                )
                raise SpiceClientError(f"Propagation failed: {error_detail}")
            
            data = response.json()
            
            # Import here to avoid circular dependency
            from app.services.orbital_engine import SatellitePosition
            
            # Parse position
            position = SatellitePosition(
                satellite_id=satellite_id,
                timestamp=epoch,
                x=data["position"]["x"],
                y=data["position"]["y"],
                z=data["position"]["z"],
                vx=data["velocity"]["vx"],
                vy=data["velocity"]["vy"],
                vz=data["velocity"]["vz"],
                latitude=data["geographic"]["latitude"],
                longitude=data["geographic"]["longitude"],
                altitude=data["geographic"]["altitude"],
                velocity=data["speed"]
            )
            
            # Parse covariance if present
            covariance = None
            if include_covariance and "covariance" in data:
                covariance = CovarianceMatrix(
                    matrix=np.array(data["covariance"])
                )
            
            return position, covariance
            
        except httpx.HTTPError as e:
            logger.error("SPICE HTTP error", error=str(e))
            raise SpiceClientError(f"HTTP error: {str(e)}")
    
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    async def batch_propagate(
        self,
        satellite_ids: List[str],
        epoch: datetime,
        include_covariance: bool = False
    ) -> List[Tuple['SatellitePosition', Optional[CovarianceMatrix]]]:
        """
        Batch propagate multiple satellites.
        
        High-performance batch processing (750K propagations/second).
        
        Circuit breaker protection:
        - Opens after 5 consecutive failures
        - Stays open for 60 seconds
        
        Args:
            satellite_ids: List of satellite IDs
            epoch: Propagation epoch
            include_covariance: Include uncertainty
        
        Returns:
            List of (position, covariance) tuples
        """
        if not self.available:
            raise SpiceServiceUnavailable("SPICE service unavailable")
        
        payload = {
            "satellite_ids": satellite_ids,
            "epoch": epoch.isoformat(),
            "include_covariance": include_covariance
        }
        
        try:
            response = await self.client.post(
                "/api/spice/batch/propagate",
                json=payload
            )
            
            if response.status_code != 200:
                raise SpiceClientError(f"Batch propagation failed: {response.text}")
            
            data = response.json()
            
            from app.services.orbital_engine import SatellitePosition
            
            results = []
            for item in data["results"]:
                position = SatellitePosition(
                    satellite_id=item["satellite_id"],
                    timestamp=epoch,
                    x=item["position"]["x"],
                    y=item["position"]["y"],
                    z=item["position"]["z"],
                    vx=item["velocity"]["vx"],
                    vy=item["velocity"]["vy"],
                    vz=item["velocity"]["vz"],
                    latitude=item["geographic"]["latitude"],
                    longitude=item["geographic"]["longitude"],
                    altitude=item["geographic"]["altitude"],
                    velocity=item["speed"]
                )
                
                covariance = None
                if include_covariance and "covariance" in item:
                    covariance = CovarianceMatrix(
                        matrix=np.array(item["covariance"])
                    )
                
                results.append((position, covariance))
            
            logger.info(
                "SPICE batch propagation complete",
                count=len(results),
                duration_ms=data.get("duration_ms")
            )
            
            return results
            
        except httpx.HTTPError as e:
            logger.error("SPICE batch HTTP error", error=str(e))
            raise SpiceClientError(f"HTTP error: {str(e)}")


# Global instance
spice_client = SpiceClient()
