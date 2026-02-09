"""
Ground Station Data Models.

Represents ground stations for satellite tracking and visibility calculations.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GroundStation:
    """
    Ground station location and metadata.
    
    Attributes:
        name: Station identifier (e.g., "DSS-65", "Kourou")
        latitude_deg: Latitude in degrees (-90 to +90, North positive)
        longitude_deg: Longitude in degrees (-180 to +180, East positive)
        altitude_km: Altitude above sea level in km
        min_elevation_deg: Minimum elevation angle for visibility (default 5°)
    """
    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
    min_elevation_deg: float = 5.0
    
    def __post_init__(self):
        """Validate ground station coordinates."""
        # Validate latitude
        if not -90 <= self.latitude_deg <= 90:
            raise ValueError(
                f"Latitude must be -90 to +90, got {self.latitude_deg}"
            )
        
        # Validate longitude
        if not -180 <= self.longitude_deg <= 180:
            raise ValueError(
                f"Longitude must be -180 to +180, got {self.longitude_deg}"
            )
        
        # Validate altitude (reasonable range)
        if not -1 <= self.altitude_km <= 10:
            raise ValueError(
                f"Altitude must be -1 to +10 km, got {self.altitude_km}"
            )
        
        # Validate min elevation
        if not 0 <= self.min_elevation_deg <= 90:
            raise ValueError(
                f"Min elevation must be 0-90°, got {self.min_elevation_deg}"
            )
    
    def to_dict(self) -> dict:
        """Serialize for JSON."""
        return {
            "name": self.name,
            "latitude_deg": self.latitude_deg,
            "longitude_deg": self.longitude_deg,
            "altitude_km": self.altitude_km,
            "min_elevation_deg": self.min_elevation_deg
        }


# Common ground stations (NASA DSN, ESA, etc.)
GROUND_STATIONS = {
    # NASA Deep Space Network
    "DSS-14": GroundStation("DSS-14 Goldstone", 35.426, -116.890, 0.956),
    "DSS-43": GroundStation("DSS-43 Canberra", -35.402, 148.982, 0.688),
    "DSS-63": GroundStation("DSS-63 Madrid", 40.427, -4.251, 0.835),
    "DSS-65": GroundStation("DSS-65 Madrid", 40.427, -4.251, 0.835),
    
    # ESA Ground Stations
    "Kourou": GroundStation("Kourou", 5.251, -52.805, 0.010),
    "Kiruna": GroundStation("Kiruna", 67.878, 21.063, 0.390),
    "Redu": GroundStation("Redu", 50.002, 5.146, 0.390),
    
    # Other Notable Stations
    "Houston": GroundStation("Houston JSC", 29.560, -95.091, 0.010),
    "Kennedy": GroundStation("Kennedy Space Center", 28.574, -80.651, 0.003),
    "Vandenberg": GroundStation("Vandenberg SFB", 34.632, -120.611, 0.110),
}


def get_ground_station(name: str) -> Optional[GroundStation]:
    """
    Get ground station by name.
    
    Args:
        name: Station name or identifier (case-insensitive)
    
    Returns:
        GroundStation if found, None otherwise
    """
    # Try exact match first
    if name in GROUND_STATIONS:
        return GROUND_STATIONS[name]
    
    # Try case-insensitive match
    name_upper = name.upper()
    for key, station in GROUND_STATIONS.items():
        if key.upper() == name_upper:
            return station
    
    # Try partial match
    for key, station in GROUND_STATIONS.items():
        if name.lower() in key.lower() or name.lower() in station.name.lower():
            return station
    
    return None
