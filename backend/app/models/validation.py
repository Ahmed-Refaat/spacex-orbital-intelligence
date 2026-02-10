"""
Input validation models for orbital calculations.

Ensures all orbital parameters are within physically valid ranges
to prevent computation errors, DoS attacks, or erroneous results.
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


class AltitudeRange(BaseModel):
    """Validate altitude parameters."""
    
    min_altitude: float = Field(
        ge=160.0,
        le=2000.0,
        description="Minimum survivable LEO altitude (km)"
    )
    max_altitude: float = Field(
        ge=160.0,
        le=35786.0,
        description="Maximum altitude up to GEO (km)"
    )
    
    @validator('max_altitude')
    def validate_altitude_range(cls, v, values):
        if 'min_altitude' in values and v < values['min_altitude']:
            raise ValueError("max_altitude must be greater than min_altitude")
        return v


class VelocityParams(BaseModel):
    """Validate velocity parameters."""
    
    velocity: float = Field(
        ge=0.0,
        le=12000.0,
        description="Velocity in m/s (up to escape velocity)"
    )
    
    @validator('velocity')
    def validate_orbital_velocity(cls, v):
        # LEO circular orbit velocity ~7,800 m/s
        # Escape velocity ~11,200 m/s
        if v > 11200 and v <= 12000:
            # Warning zone but still valid
            pass
        return v


class TimeRange(BaseModel):
    """Validate time parameters."""
    
    start_time: datetime = Field(
        description="Start time for propagation"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="End time for propagation"
    )
    
    @validator('start_time')
    def validate_start_time(cls, v):
        # Must be within reasonable range (2000-2050)
        if v.year < 2000 or v.year > 2050:
            raise ValueError("start_time must be between 2000 and 2050")
        return v
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if v is None:
            return v
        if 'start_time' in values and v < values['start_time']:
            raise ValueError("end_time must be after start_time")
        if (v - values.get('start_time')).days > 30:
            raise ValueError("time range must not exceed 30 days")
        return v


class LaunchParams(BaseModel):
    """Validate launch simulation parameters."""
    
    altitude_km: float = Field(
        ge=200.0,
        le=600.0,
        description="Target altitude (LEO range)"
    )
    
    inclination_deg: float = Field(
        ge=0.0,
        le=180.0,
        description="Orbital inclination in degrees"
    )
    
    launch_azimuth_deg: float = Field(
        ge=0.0,
        le=360.0,
        description="Launch azimuth in degrees"
    )
    
    payload_mass_kg: float = Field(
        ge=100.0,
        le=30000.0,
        description="Payload mass (kg)"
    )
    
    @validator('altitude_km')
    def validate_launch_altitude(cls, v):
        if v < 200:
            raise ValueError("Launch altitude below atmospheric re-entry threshold")
        return v
    
    @validator('payload_mass_kg')
    def validate_payload_mass(cls, v):
        # Falcon 9 max payload to LEO ~22,800 kg
        # Add margin for future vehicles
        if v > 25000:
            raise ValueError("Payload mass exceeds realistic launch vehicle capability")
        return v


class PropagationParams(BaseModel):
    """Validate orbital propagation parameters."""
    
    satellite_id: str = Field(
        min_length=1,
        max_length=50,
        description="Satellite identifier"
    )
    
    hours_ahead: int = Field(
        ge=1,
        le=168,
        description="Propagation duration in hours (max 7 days)"
    )
    
    step_minutes: int = Field(
        ge=1,
        le=60,
        description="Time step in minutes"
    )
    
    @validator('satellite_id')
    def validate_satellite_id(cls, v):
        # Prevent injection attacks
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("satellite_id contains invalid characters")
        return v
    
    @validator('hours_ahead')
    def validate_propagation_duration(cls, v):
        # Limit computation time
        if v > 168:  # 7 days
            raise ValueError("Propagation duration too long (max 7 days)")
        return v


class ConjunctionParams(BaseModel):
    """Validate conjunction analysis parameters."""
    
    primary_id: str = Field(
        min_length=1,
        max_length=50,
        description="Primary satellite identifier"
    )
    
    secondary_id: str = Field(
        min_length=1,
        max_length=50,
        description="Secondary satellite identifier"
    )
    
    threshold_km: float = Field(
        ge=0.1,
        le=100.0,
        description="Conjunction threshold in km"
    )
    
    @validator('threshold_km')
    def validate_threshold(cls, v):
        # Typical conjunction threshold: 1-5 km
        if v < 0.5:
            raise ValueError("Threshold too small (risk of false positives)")
        if v > 50:
            raise ValueError("Threshold too large (risk of missing close approaches)")
        return v
    
    @validator('secondary_id')
    def validate_different_satellites(cls, v, values):
        if 'primary_id' in values and v == values['primary_id']:
            raise ValueError("Cannot analyze conjunction of satellite with itself")
        return v
