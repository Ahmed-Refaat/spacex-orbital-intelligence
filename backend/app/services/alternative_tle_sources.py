"""
Alternative TLE sources when primary sources fail.

Free/Open Source TLE APIs (no auth required):
1. TLE.ivanstanojevic.me - Free, no auth, JSON API
2. Celestrak (via proxy if needed)
3. Space-Track (primary, auth required)
"""
import httpx
from typing import Optional
import structlog

logger = structlog.get_logger()


class IvanStanojevicTLESource:
    """
    TLE API by Ivan Stanojevic - Free, no authentication required.
    
    API: https://tle.ivanstanojevic.me/
    Format: JSON (Hydra format)
    Rate Limits: Unknown, be respectful
    Coverage: Good for well-known satellites (ISS, etc.)
    
    Note: May not have all Starlink satellites.
    """
    
    BASE_URL = "https://tle.ivanstanojevic.me/api/tle"
    
    @staticmethod
    async def get_tle_by_norad(norad_id: str) -> Optional[dict]:
        """
        Get TLE for a single satellite by NORAD ID.
        
        Args:
            norad_id: NORAD catalog number
            
        Returns:
            Dict with 'name', 'line1', 'line2' or None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(f"{IvanStanojevicTLESource.BASE_URL}/{norad_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        'name': data.get('name', f'SAT-{norad_id}'),
                        'line1': data.get('line1', ''),
                        'line2': data.get('line2', '')
                    }
                
                logger.warning(
                    "Ivan Stanojevic TLE fetch failed",
                    norad_id=norad_id,
                    status_code=response.status_code
                )
                return None
                
        except Exception as e:
            logger.error(
                "Ivan Stanojevic TLE error",
                norad_id=norad_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    @staticmethod
    async def search_satellites(query: str, page_size: int = 100) -> list[dict]:
        """
        Search satellites by name.
        
        Args:
            query: Search query (e.g., "ISS", "STARLINK")
            page_size: Results per page
            
        Returns:
            List of dicts with TLE data
        """
        try:
            params = {
                'search': query,
                'page-size': min(page_size, 1000)  # API limit
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    IvanStanojevicTLESource.BASE_URL,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    members = data.get('hydra:member', [])
                    
                    results = []
                    for item in members:
                        norad_id = str(item.get('satelliteId', ''))
                        if norad_id:
                            results.append({
                                'norad_id': norad_id,
                                'name': item.get('name', f'SAT-{norad_id}'),
                                'line1': item.get('line1', ''),
                                'line2': item.get('line2', '')
                            })
                    
                    logger.info(
                        "Ivan Stanojevic search successful",
                        query=query,
                        count=len(results)
                    )
                    return results
                
                logger.warning(
                    "Ivan Stanojevic search failed",
                    query=query,
                    status_code=response.status_code
                )
                return []
                
        except Exception as e:
            logger.error(
                "Ivan Stanojevic search error",
                query=query,
                error=str(e),
                error_type=type(e).__name__
            )
            return []


class MultiSourceTLEFallback:
    """
    Multi-source TLE fallback with automatic failover.
    
    Tries sources in order:
    1. Space-Track (requires auth, best coverage)
    2. Celestrak (public, good coverage)
    3. Ivan Stanojevic (public, limited coverage)
    
    Usage:
        fallback = MultiSourceTLEFallback()
        tle = await fallback.get_tle("25544")
    """
    
    def __init__(self):
        self.ivan = IvanStanojevicTLESource()
    
    async def get_tle(
        self,
        norad_id: str,
        spacetrack_client=None,
        celestrak_client=None
    ) -> Optional[tuple[str, str, str]]:
        """
        Get TLE with automatic fallback.
        
        Args:
            norad_id: NORAD catalog number
            spacetrack_client: Optional SpaceTrackClient instance
            celestrak_client: Optional CelestrakFallback instance
            
        Returns:
            Tuple of (name, line1, line2) or None
        """
        # Try Space-Track first (if available and not suspended)
        if spacetrack_client and spacetrack_client.is_configured:
            try:
                tle_data = await spacetrack_client.get_tle(norad_id)
                if tle_data:
                    logger.info("TLE from Space-Track", norad_id=norad_id)
                    return (
                        tle_data.get('OBJECT_NAME', f'SAT-{norad_id}'),
                        tle_data.get('TLE_LINE1', ''),
                        tle_data.get('TLE_LINE2', '')
                    )
            except Exception as e:
                logger.warning(
                    "Space-Track failed, trying fallback",
                    norad_id=norad_id,
                    error=str(e)
                )
        
        # Try Celestrak (if available)
        if celestrak_client:
            try:
                # Celestrak doesn't have single-satellite fetch
                # This would need to be implemented differently
                pass
            except Exception as e:
                logger.warning(
                    "Celestrak failed, trying fallback",
                    norad_id=norad_id,
                    error=str(e)
                )
        
        # Try Ivan Stanojevic as last resort
        try:
            tle_data = await self.ivan.get_tle_by_norad(norad_id)
            if tle_data:
                logger.info("TLE from Ivan Stanojevic", norad_id=norad_id)
                return (
                    tle_data['name'],
                    tle_data['line1'],
                    tle_data['line2']
                )
        except Exception as e:
            logger.error(
                "All TLE sources failed",
                norad_id=norad_id,
                error=str(e)
            )
        
        return None


# Global instance
multi_source_tle = MultiSourceTLEFallback()
