"""
Thrust and Isp interpolation with altitude.

Story 1.3: Thrust Profile
Realistic thrust/Isp variation from sea level to vacuum.
"""
import math
from app.models.vehicle import Stage


# Physical constants
G0 = 9.80665  # Standard gravity (m/s²)
P0 = 101325.0  # Sea level pressure (Pa)
H_SCALE = 8500.0  # Scale height (m), simplified


class AtmosphereModel:
    """
    Atmospheric pressure model.
    
    Uses simplified barometric formula:
    P(h) = P0 * exp(-h / H)
    
    Where:
    - P0 = sea level pressure (101325 Pa)
    - H = scale height (~8500 m)
    - h = altitude (m)
    
    This is a simplified model. For higher accuracy, use US Standard
    Atmosphere 1976 (Story 2.2).
    """
    
    def __init__(self):
        self.p0 = P0
        self.scale_height = H_SCALE
    
    def pressure_at_altitude(self, altitude_km: float) -> float:
        """
        Calculate atmospheric pressure at given altitude.
        
        Args:
            altitude_km: Altitude (kilometers)
        
        Returns:
            Pressure (Pascals)
        """
        altitude_m = altitude_km * 1000.0
        
        # Barometric formula
        pressure = self.p0 * math.exp(-altitude_m / self.scale_height)
        
        return pressure


class ThrustCalculator:
    """
    Calculate effective thrust and Isp based on altitude.
    
    Rocket engine performance varies with atmospheric pressure:
    - At sea level: Lower thrust, lower Isp (back pressure from atmosphere)
    - In vacuum: Higher thrust, higher Isp (no back pressure)
    
    This class interpolates between sea level and vacuum values based
    on atmospheric pressure.
    
    Interpolation method: Linear interpolation based on pressure ratio.
    
    For upper stages (thrust_sl_N = 0), always uses vacuum values.
    """
    
    def __init__(self):
        self.atmosphere = AtmosphereModel()
        
        # Pressure thresholds for interpolation
        self.p_sea_level = P0  # 101325 Pa
        self.p_vacuum = 100.0  # <100 Pa considered vacuum (~50 km)
    
    def effective_thrust(self, stage: Stage, altitude_km: float) -> float:
        """
        Calculate effective thrust at given altitude.
        
        Args:
            stage: Stage with thrust_sl_N and thrust_vac_N
            altitude_km: Current altitude (km)
        
        Returns:
            Effective thrust (Newtons)
        """
        # Upper stage: no sea level rating
        if stage.thrust_sl_N == 0:
            return stage.thrust_vac_N
        
        # Get atmospheric pressure
        pressure = self.atmosphere.pressure_at_altitude(altitude_km)
        
        # Interpolate between sea level and vacuum
        thrust = self._interpolate(
            pressure,
            stage.thrust_sl_N,
            stage.thrust_vac_N
        )
        
        return thrust
    
    def effective_isp(self, stage: Stage, altitude_km: float) -> float:
        """
        Calculate effective specific impulse at given altitude.
        
        Args:
            stage: Stage with Isp_sl_s and Isp_vac_s
            altitude_km: Current altitude (km)
        
        Returns:
            Effective Isp (seconds)
        """
        # Upper stage: no sea level rating
        if stage.Isp_sl_s == 0:
            return stage.Isp_vac_s
        
        # Get atmospheric pressure
        pressure = self.atmosphere.pressure_at_altitude(altitude_km)
        
        # Interpolate between sea level and vacuum
        isp = self._interpolate(
            pressure,
            stage.Isp_sl_s,
            stage.Isp_vac_s
        )
        
        return isp
    
    def mass_flow_rate(self, stage: Stage, altitude_km: float) -> float:
        """
        Calculate propellant mass flow rate.
        
        From rocket equation: mdot = Thrust / (Isp * g0)
        
        Args:
            stage: Stage configuration
            altitude_km: Current altitude (km)
        
        Returns:
            Mass flow rate (kg/s)
        """
        thrust = self.effective_thrust(stage, altitude_km)
        isp = self.effective_isp(stage, altitude_km)
        
        mdot = thrust / (isp * G0)
        
        return mdot
    
    def _interpolate(
        self,
        pressure: float,
        value_sl: float,
        value_vac: float
    ) -> float:
        """
        Linear interpolation between sea level and vacuum values.
        
        Interpolation factor based on pressure:
        - At P >= P_SL: factor = 0 (use sea level value)
        - At P <= P_VAC: factor = 1 (use vacuum value)
        - Between: linear interpolation
        
        Args:
            pressure: Current atmospheric pressure (Pa)
            value_sl: Value at sea level
            value_vac: Value in vacuum
        
        Returns:
            Interpolated value
        """
        # Clamp pressure to valid range
        if pressure >= self.p_sea_level:
            return value_sl
        
        if pressure <= self.p_vacuum:
            return value_vac
        
        # Linear interpolation factor (0 to 1)
        # factor = 0 at sea level, 1 at vacuum
        factor = 1.0 - (pressure - self.p_vacuum) / (self.p_sea_level - self.p_vacuum)
        
        # Interpolate
        value = value_sl + factor * (value_vac - value_sl)
        
        return value
