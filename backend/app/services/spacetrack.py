"""
Space-Track.org API client for real conjunction data (CDM).

Space-Track is the authoritative source for:
- Conjunction Data Messages (CDM) from 18th Space Defense Squadron
- Official TLE data
- Satellite catalog
- Decay predictions

Register for free at: https://www.space-track.org/auth/createAccount

COMPLIANCE: Uses centralized session manager to comply with Space-Track API policy.
"""
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from dataclasses import dataclass
import os

from app.core.config import get_settings
from app.services.spacetrack_session import session_manager

BASE_URL = "https://www.space-track.org"


@dataclass
class SatelliteCatalogEntry:
    """Enriched satellite information from catalog."""
    norad_id: str
    name: str
    object_type: str
    country: str
    launch_date: Optional[str] = None
    decay_date: Optional[str] = None
    owner: Optional[str] = None
    purpose: Optional[str] = None
    perigee_km: Optional[float] = None
    apogee_km: Optional[float] = None
    inclination_deg: Optional[float] = None


@dataclass
class CDMAlert:
    """Conjunction Data Message from Space-Track."""
    cdm_id: str
    created: datetime
    tca: datetime  # Time of Closest Approach
    miss_distance_km: float
    probability: float
    
    sat1_name: str
    sat1_norad: str
    sat1_type: str  # PAYLOAD, DEBRIS, ROCKET BODY
    
    sat2_name: str
    sat2_norad: str
    sat2_type: str
    
    relative_speed_km_s: float
    
    # Risk classification
    emergency: bool  # Pc > 1e-4 or miss < 1km
    
    # Enriched catalog data (optional)
    sat1_catalog: Optional[SatelliteCatalogEntry] = None
    sat2_catalog: Optional[SatelliteCatalogEntry] = None
    
    def to_dict(self) -> dict:
        result = {
            "cdm_id": self.cdm_id,
            "created": self.created.isoformat(),
            "tca": self.tca.isoformat(),
            "miss_distance_km": self.miss_distance_km,
            "probability": self.probability,
            "satellite_1": {
                "name": self.sat1_name,
                "norad_id": self.sat1_norad,
                "type": self.sat1_type
            },
            "satellite_2": {
                "name": self.sat2_name,
                "norad_id": self.sat2_norad,
                "type": self.sat2_type
            },
            "relative_speed_km_s": self.relative_speed_km_s,
            "emergency": self.emergency,
            "risk_level": self._calculate_risk_level()
        }
        
        # Add enriched catalog data if available
        if self.sat1_catalog:
            result["satellite_1"]["catalog"] = {
                "country": self.sat1_catalog.country,
                "owner": self.sat1_catalog.owner,
                "purpose": self.sat1_catalog.purpose,
                "launch_date": self.sat1_catalog.launch_date,
                "orbit": {
                    "perigee_km": self.sat1_catalog.perigee_km,
                    "apogee_km": self.sat1_catalog.apogee_km,
                    "inclination_deg": self.sat1_catalog.inclination_deg
                }
            }
        
        if self.sat2_catalog:
            result["satellite_2"]["catalog"] = {
                "country": self.sat2_catalog.country,
                "owner": self.sat2_catalog.owner,
                "purpose": self.sat2_catalog.purpose,
                "launch_date": self.sat2_catalog.launch_date,
                "orbit": {
                    "perigee_km": self.sat2_catalog.perigee_km,
                    "apogee_km": self.sat2_catalog.apogee_km,
                    "inclination_deg": self.sat2_catalog.inclination_deg
                }
            }
        
        return result
    
    def _calculate_risk_level(self) -> str:
        if self.emergency or self.probability > 1e-3:
            return "CRITICAL"
        elif self.probability > 1e-4:
            return "HIGH"
        elif self.probability > 1e-5:
            return "MEDIUM"
        return "LOW"


class SpaceTrackClient:
    """
    Client for Space-Track.org API.
    
    Uses centralized session manager for compliance with API usage policy:
    - Session reuse (2h validity, refresh at 1h50min)
    - GP data caching (minimum 1h)
    - No unnecessary login/logout cycles
    
    Rate limits: 30 requests per minute, 300 per hour
    """
    
    def __init__(self):
        self.settings = get_settings()
        # Use centralized session manager
        self.session = session_manager
    
    @property
    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.settings.spacetrack_username and self.settings.spacetrack_password)
    
    async def close(self):
        """Close is handled by session manager lifecycle."""
        pass
    
    async def get_cdm_for_starlink(
        self,
        hours_ahead: int = 72,
        min_probability: float = 1e-7
    ) -> list[CDMAlert]:
        """
        Get Conjunction Data Messages involving Starlink satellites.
        
        Args:
            hours_ahead: Look ahead window in hours
            min_probability: Minimum collision probability
        """
        if not self.is_configured:
            return []
        
        # Query CDM data for Starlink
        # CDM class: https://www.space-track.org/basicspacedata/modeldef/class/cdm_public
        # NOTE: CDM data is time-sensitive, no caching (short TTL)
        
        tca_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tca_end = (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d")
        
        try:
            # Query format for Space-Track
            query = (
                f"/basicspacedata/query/class/cdm_public"
                f"/TCA/{tca_start}--{tca_end}"
                f"/SAT1_NAME/~~STARLINK"  # Contains STARLINK
                f"/orderby/TCA asc"
                f"/limit/100"
                f"/format/json"
            )
            
            # CDM data changes frequently, use short cache (5 min)
            response = await self.session.get(query, cache_ttl=300)
            
            if not response or response.status_code != 200:
                print(f"Space-Track CDM query failed: {response.status_code if response else 'No response'}")
                return []
            
            data = response.json()
            alerts = []
            
            for item in data:
                try:
                    prob = float(item.get("PC", 0) or 0)
                    if prob < min_probability:
                        continue
                    
                    miss_km = float(item.get("MISS_DISTANCE", 0) or 0) / 1000  # m to km
                    
                    alert = CDMAlert(
                        cdm_id=item.get("CDM_ID", ""),
                        created=self._parse_datetime(item.get("CREATED")),
                        tca=self._parse_datetime(item.get("TCA")),
                        miss_distance_km=miss_km,
                        probability=prob,
                        sat1_name=item.get("SAT1_NAME", "Unknown"),
                        sat1_norad=item.get("SAT1_NORAD_CAT_ID", ""),
                        sat1_type=item.get("SAT1_OBJECT_TYPE", "UNKNOWN"),
                        sat2_name=item.get("SAT2_NAME", "Unknown"),
                        sat2_norad=item.get("SAT2_NORAD_CAT_ID", ""),
                        sat2_type=item.get("SAT2_OBJECT_TYPE", "UNKNOWN"),
                        relative_speed_km_s=float(item.get("RELATIVE_SPEED", 0) or 0) / 1000,
                        emergency=(prob > 1e-4 or miss_km < 1.0)
                    )
                    alerts.append(alert)
                    
                except Exception as e:
                    print(f"Error parsing CDM: {e}")
                    continue
            
            return alerts
            
        except Exception as e:
            print(f"Space-Track CDM error: {e}")
            return []
    
    async def get_all_cdm(
        self,
        hours_ahead: int = 72,
        limit: int = 50
    ) -> list[CDMAlert]:
        """Get all CDM alerts (not just Starlink)."""
        if not self.is_configured:
            return []
        
        tca_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tca_end = (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d")
        
        try:
            query = (
                f"/basicspacedata/query/class/cdm_public"
                f"/TCA/{tca_start}--{tca_end}"
                f"/orderby/PC desc"  # Highest probability first
                f"/limit/{limit}"
                f"/format/json"
            )
            
            # CDM data changes frequently, use short cache (5 min)
            response = await self.session.get(query, cache_ttl=300)
            
            if not response or response.status_code != 200:
                return []
            
            data = response.json()
            alerts = []
            
            for item in data:
                try:
                    prob = float(item.get("PC", 0) or 0)
                    miss_km = float(item.get("MISS_DISTANCE", 0) or 0) / 1000
                    
                    alert = CDMAlert(
                        cdm_id=item.get("CDM_ID", ""),
                        created=self._parse_datetime(item.get("CREATED")),
                        tca=self._parse_datetime(item.get("TCA")),
                        miss_distance_km=miss_km,
                        probability=prob,
                        sat1_name=item.get("SAT1_NAME", "Unknown"),
                        sat1_norad=item.get("SAT1_NORAD_CAT_ID", ""),
                        sat1_type=item.get("SAT1_OBJECT_TYPE", "UNKNOWN"),
                        sat2_name=item.get("SAT2_NAME", "Unknown"),
                        sat2_norad=item.get("SAT2_NORAD_CAT_ID", ""),
                        sat2_type=item.get("SAT2_OBJECT_TYPE", "UNKNOWN"),
                        relative_speed_km_s=float(item.get("RELATIVE_SPEED", 0) or 0) / 1000,
                        emergency=(prob > 1e-4 or miss_km < 1.0)
                    )
                    alerts.append(alert)
                    
                except Exception:
                    continue
            
            return alerts
            
        except Exception as e:
            print(f"Space-Track error: {e}")
            return []
    
    async def get_tle(self, norad_id: str) -> Optional[dict]:
        """Get latest TLE for a satellite."""
        if not self.is_configured:
            return None
        
        try:
            query = (
                f"/basicspacedata/query/class/tle_latest"
                f"/NORAD_CAT_ID/{norad_id}"
                f"/orderby/EPOCH desc"
                f"/limit/1"
                f"/format/json"
            )
            
            # TLE data is GP data - MUST cache for minimum 1 hour
            response = await self.session.get(query, cache_ttl=3600)
            
            if response and response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            
            return None
            
        except Exception:
            return None
    
    async def get_omm(
        self, 
        norad_id: Optional[str] = None,
        format: Literal["xml", "json"] = "json",
        limit: int = 100
    ) -> Optional[str]:
        """
        Get OMM (Orbit Mean-Elements Message) data from Space-Track.
        
        Args:
            norad_id: Specific NORAD ID, or None for all active satellites
            format: "xml" for OMM XML (CCSDS), "json" for JSON format
            limit: Maximum number of records to return
            
        Returns:
            OMM data as string (XML or JSON)
            
        Space-Track GP class documentation:
        https://www.space-track.org/basicspacedata/modeldef/class/gp
        
        COMPLIANCE: GP data is cached for minimum 1 hour per Space-Track policy.
        """
        if not self.is_configured:
            return None
        
        try:
            # Build query for GP (General Perturbations) class
            # GP class contains OMM-format orbital elements
            if norad_id:
                query = (
                    f"/basicspacedata/query/class/gp"
                    f"/NORAD_CAT_ID/{norad_id}"
                    f"/orderby/EPOCH desc"
                    f"/limit/1"
                    f"/format/{format}"
                )
            else:
                # Get all active satellites (latest epoch only)
                query = (
                    f"/basicspacedata/query/class/gp"
                    f"/EPOCH/>now-7"  # Last 7 days
                    f"/orderby/NORAD_CAT_ID,EPOCH desc"
                    f"/limit/{limit}"
                    f"/format/{format}"
                )
            
            # CRITICAL: GP ephemerides MUST be cached for minimum 1 hour
            response = await self.session.get(query, cache_ttl=3600)
            
            if response and response.status_code == 200:
                return response.text
            
            return None
            
        except Exception as e:
            print(f"OMM fetch error: {e}")
            return None
    
    async def get_omm_starlink(
        self,
        format: Literal["xml", "json"] = "json",
        limit: int = 1000
    ) -> Optional[str]:
        """
        Get OMM data for all Starlink satellites.
        
        Args:
            format: "xml" or "json"
            limit: Max number of satellites (default 1000)
            
        Returns:
            OMM data as string
            
        COMPLIANCE: GP data is cached for minimum 1 hour per Space-Track policy.
        """
        if not self.is_configured:
            return None
        
        try:
            query = (
                f"/basicspacedata/query/class/gp"
                f"/OBJECT_NAME/~~STARLINK"  # Contains STARLINK
                f"/EPOCH/>now-7"  # Last 7 days
                f"/orderby/NORAD_CAT_ID,EPOCH desc"
                f"/limit/{limit}"
                f"/format/{format}"
            )
            
            # CRITICAL: GP ephemerides MUST be cached for minimum 1 hour
            response = await self.session.get(query, cache_ttl=3600)
            
            if response and response.status_code == 200:
                return response.text
            
            return None
            
        except Exception as e:
            print(f"Starlink OMM fetch error: {e}")
            return None
    
    async def get_satellite_catalog(self, norad_ids: list[str]) -> dict[str, SatelliteCatalogEntry]:
        """
        Fetch satellite catalog entries for given NORAD IDs.
        
        Returns a dict mapping NORAD ID to catalog entry.
        
        NOTE: Catalog data changes infrequently, cached for 24 hours.
        """
        if not self.is_configured or not norad_ids:
            return {}
        
        result = {}
        
        try:
            # Query satcat for multiple IDs at once
            ids_str = ",".join(norad_ids[:50])  # Limit to 50 at a time
            
            query = (
                f"/basicspacedata/query/class/satcat"
                f"/NORAD_CAT_ID/{ids_str}"
                f"/format/json"
            )
            
            # Catalog data rarely changes - cache for 24 hours
            response = await self.session.get(query, cache_ttl=86400)
            
            if response and response.status_code == 200:
                data = response.json()
                
                for item in data:
                    norad = item.get("NORAD_CAT_ID", "")
                    if norad:
                        result[norad] = SatelliteCatalogEntry(
                            norad_id=norad,
                            name=item.get("SATNAME", "Unknown"),
                            object_type=item.get("OBJECT_TYPE", "UNKNOWN"),
                            country=item.get("COUNTRY", "UNKNOWN"),
                            launch_date=item.get("LAUNCH", None),
                            decay_date=item.get("DECAY", None),
                            owner=item.get("OWNER", None),
                            purpose=self._get_purpose(item.get("SATNAME", "")),
                            perigee_km=float(item.get("PERIGEE", 0) or 0),
                            apogee_km=float(item.get("APOGEE", 0) or 0),
                            inclination_deg=float(item.get("INCLINATION", 0) or 0)
                        )
        
        except Exception as e:
            print(f"Catalog fetch error: {e}")
        
        return result
    
    def _get_purpose(self, name: str) -> str:
        """Infer satellite purpose from name."""
        name_upper = name.upper()
        if "STARLINK" in name_upper:
            return "Internet/Communications"
        elif "COSMOS" in name_upper or "KOSMOS" in name_upper:
            return "Military/Government"
        elif "ISS" in name_upper:
            return "Space Station"
        elif "GPS" in name_upper or "NAVSTAR" in name_upper:
            return "Navigation"
        elif "WEATHER" in name_upper or "NOAA" in name_upper or "METEO" in name_upper:
            return "Weather"
        elif any(x in name_upper for x in ["DEB", "R/B", "DEBRIS"]):
            return "Debris"
        else:
            return "Unknown"
    
    async def get_cdm_enriched(
        self,
        hours_ahead: int = 72,
        limit: int = 50
    ) -> list[CDMAlert]:
        """
        Get CDM alerts enriched with satellite catalog data.
        
        This cross-references CDM data with the satellite catalog
        to provide additional context about involved objects.
        """
        # First get basic CDM alerts
        alerts = await self.get_all_cdm(hours_ahead=hours_ahead, limit=limit)
        
        if not alerts:
            return alerts
        
        # Collect all unique NORAD IDs
        norad_ids = set()
        for alert in alerts:
            if alert.sat1_norad:
                norad_ids.add(alert.sat1_norad)
            if alert.sat2_norad:
                norad_ids.add(alert.sat2_norad)
        
        # Fetch catalog data
        catalog = await self.get_satellite_catalog(list(norad_ids))
        
        # Enrich alerts
        for alert in alerts:
            if alert.sat1_norad in catalog:
                alert.sat1_catalog = catalog[alert.sat1_norad]
            if alert.sat2_norad in catalog:
                alert.sat2_catalog = catalog[alert.sat2_norad]
        
        return alerts
    
    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        """Parse Space-Track datetime format."""
        if not dt_str:
            return datetime.now(timezone.utc)
        try:
            # Space-Track uses format: 2024-01-15 12:30:45
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except:
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except:
                return datetime.now(timezone.utc)


# Global client instance
spacetrack_client = SpaceTrackClient()
