"""Launch Library 2 API client for up-to-date launch data."""
import httpx
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

# Launch Library 2 - Free tier (15 requests/hour)
# Docs: https://thespacedevs.com/llapi

BASE_URL = "https://ll.thespacedevs.com/2.2.0"


@dataclass
class LL2Launch:
    """Launch from Launch Library 2."""
    id: str
    name: str
    status: str
    net: datetime  # No Earlier Than
    window_start: Optional[datetime]
    window_end: Optional[datetime]
    rocket_name: str
    rocket_family: str
    pad_name: str
    pad_location: str
    pad_lat: Optional[float]
    pad_lon: Optional[float]
    mission_name: Optional[str]
    mission_type: Optional[str]
    mission_description: Optional[str]
    webcast_live: Optional[str]
    image: Optional[str]
    agency: str
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "date_utc": self.net.isoformat(),
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "rocket": {
                "name": self.rocket_name,
                "family": self.rocket_family
            },
            "pad": {
                "name": self.pad_name,
                "location": self.pad_location,
                "latitude": self.pad_lat,
                "longitude": self.pad_lon
            },
            "mission": {
                "name": self.mission_name,
                "type": self.mission_type,
                "description": self.mission_description
            },
            "webcast": self.webcast_live,
            "image": self.image,
            "agency": self.agency
        }


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return None


class LaunchLibrary2Client:
    """
    Client for Launch Library 2 API with timeout protection.
    
    Features:
    - Explicit timeouts on all requests
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - Structured logging
    """
    
    # Timeout configuration (seconds)
    CONNECT_TIMEOUT = 5.0   # Connection establishment
    READ_TIMEOUT = 30.0     # Reading response (API can be slow)
    WRITE_TIMEOUT = 5.0     # Writing request
    POOL_TIMEOUT = 1.0      # Connection pool acquisition
    
    # Retry configuration
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 0.5    # 0.5s, 1s, 2s
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = httpx.Timeout(
            connect=self.CONNECT_TIMEOUT,
            read=self.READ_TIMEOUT,
            write=self.WRITE_TIMEOUT,
            pool=self.POOL_TIMEOUT
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client with proper timeout configuration.
        
        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=self._timeout,
                headers={"User-Agent": "SpaceX-Orbital-Intelligence/1.0"},
                follow_redirects=True,
                max_redirects=3
            )
        return self._client
    
    async def close(self):
        """Close HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic and timeout protection.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            **kwargs: Additional arguments for httpx (params, headers, etc.)
        
        Returns:
            httpx.Response
        
        Raises:
            httpx.HTTPStatusError: On HTTP error after retries
            httpx.TimeoutException: On timeout after retries
            httpx.RequestError: On other request errors after retries
        """
        import asyncio
        import structlog
        
        logger = structlog.get_logger()
        client = await self._get_client()
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            
            except httpx.TimeoutException as e:
                logger.warning(
                    "Launch Library timeout",
                    attempt=attempt + 1,
                    max_retries=self.MAX_RETRIES,
                    path=path,
                    timeout_config=str(self._timeout)
                )
                
                if attempt == self.MAX_RETRIES - 1:
                    # Last attempt failed
                    raise
                
                # Exponential backoff
                await asyncio.sleep(self.BACKOFF_FACTOR * (2 ** attempt))
            
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    logger.error(
                        "Launch Library client error",
                        status_code=e.response.status_code,
                        path=path
                    )
                    raise
                
                # Retry on 5xx errors (server errors)
                logger.warning(
                    "Launch Library server error",
                    attempt=attempt + 1,
                    status_code=e.response.status_code,
                    path=path
                )
                
                if attempt == self.MAX_RETRIES - 1:
                    raise
                
                await asyncio.sleep(self.BACKOFF_FACTOR * (2 ** attempt))
            
            except httpx.RequestError as e:
                logger.warning(
                    "Launch Library request error",
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                    path=path
                )
                
                if attempt == self.MAX_RETRIES - 1:
                    raise
                
                await asyncio.sleep(self.BACKOFF_FACTOR * (2 ** attempt))
        
        # Should never reach here
        raise RuntimeError("Retry loop completed without return or raise")
    
    async def get_upcoming_launches(
        self,
        limit: int = 20,
        agency: Optional[str] = None  # "SpaceX" to filter
    ) -> list[LL2Launch]:
        """
        Get upcoming launches with retry and timeout protection.
        
        Args:
            limit: Maximum number of launches to return (default: 20)
            agency: Filter by agency name (e.g., "SpaceX")
        
        Returns:
            List of LL2Launch objects
        
        Raises:
            httpx.HTTPError: On API error after retries
        """
        params = {
            "limit": limit,
            "ordering": "net",
            "mode": "detailed"
        }
        
        if agency:
            params["lsp__name__icontains"] = agency
        
        # Use retry logic
        response = await self._request_with_retry(
            "GET",
            "/launch/upcoming/",
            params=params
        )
        
        data = response.json()
        launches = []
        
        for item in data.get("results", []):
            try:
                launch = self._parse_launch(item)
                if launch:
                    launches.append(launch)
            except Exception as e:
                print(f"Error parsing launch: {e}")
                continue
        
        return launches
    
    async def get_previous_launches(
        self,
        limit: int = 20,
        agency: Optional[str] = None
    ) -> list[LL2Launch]:
        """Get past launches."""
        client = await self._get_client()
        
        params = {
            "limit": limit,
            "ordering": "-net",  # Descending
            "mode": "detailed"
        }
        
        if agency:
            params["lsp__name__icontains"] = agency
        
        response = await client.get("/launch/previous/", params=params)
        response.raise_for_status()
        
        data = response.json()
        launches = []
        
        for item in data.get("results", []):
            try:
                launch = self._parse_launch(item)
                if launch:
                    launches.append(launch)
            except Exception as e:
                continue
        
        return launches
    
    async def get_spacex_launches(self, limit: int = 30, upcoming: bool = True) -> list[LL2Launch]:
        """Get SpaceX launches specifically."""
        if upcoming:
            return await self.get_upcoming_launches(limit=limit, agency="SpaceX")
        else:
            return await self.get_previous_launches(limit=limit, agency="SpaceX")
    
    def _parse_launch(self, item: dict) -> Optional[LL2Launch]:
        """Parse launch item from API response."""
        rocket = item.get("rocket", {}).get("configuration", {})
        pad = item.get("pad", {})
        location = pad.get("location", {})
        mission = item.get("mission") or {}
        lsp = item.get("launch_service_provider", {})
        status = item.get("status", {})
        
        # Get video URL
        vid_urls = item.get("vidURLs", [])
        webcast = vid_urls[0].get("url") if vid_urls else None
        
        return LL2Launch(
            id=item.get("id", ""),
            name=item.get("name", "Unknown"),
            status=status.get("abbrev", "Unknown"),
            net=parse_datetime(item.get("net")) or datetime.now(timezone.utc),
            window_start=parse_datetime(item.get("window_start")),
            window_end=parse_datetime(item.get("window_end")),
            rocket_name=rocket.get("full_name", "Unknown"),
            rocket_family=rocket.get("family", {}).get("name", "Unknown") if isinstance(rocket.get("family"), dict) else rocket.get("family", "Unknown"),
            pad_name=pad.get("name", "Unknown"),
            pad_location=location.get("name", "Unknown"),
            pad_lat=pad.get("latitude"),
            pad_lon=pad.get("longitude"),
            mission_name=mission.get("name"),
            mission_type=mission.get("type", {}).get("name") if isinstance(mission.get("type"), dict) else mission.get("type"),
            mission_description=mission.get("description"),
            webcast_live=webcast,
            image=item.get("image"),
            agency=lsp.get("name", "Unknown")
        )


# Global client instance
ll2_client = LaunchLibrary2Client()
