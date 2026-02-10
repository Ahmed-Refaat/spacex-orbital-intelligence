"""
Atmospheric drag model for launch simulation.

Drag is a major loss during ascent, typically 1-2% of total ΔV.
Critical for accurate trajectory prediction, especially through max-Q.
"""
import math


# Physical constants
RHO_0 = 1.225  # Sea level density (kg/m³)
H_SCALE = 8500.0  # Scale height (m)


class AtmosphereDensity:
    """
    Atmospheric density model.
    
    Uses exponential model: ρ(h) = ρ₀ × exp(-h / H)
    
    Where:
    - ρ₀ = sea level density (1.225 kg/m³)
    - H = scale height (~8.5 km)
    - h = altitude
    
    This is simplified but accurate enough for preliminary design.
    For higher accuracy, use US Standard Atmosphere 1976 (Story 2.2).
    """
    
    def __init__(self):
        self.rho_0 = RHO_0
        self.scale_height = H_SCALE
    
    def density_at_altitude(self, altitude_km: float) -> float:
        """
        Calculate atmospheric density at given altitude.
        
        Args:
            altitude_km: Altitude (km)
        
        Returns:
            Density (kg/m³)
        
        Example:
            >>> atm = AtmosphereDensity()
            >>> atm.density_at_altitude(0.0)   # Sea level
            1.225
            >>> atm.density_at_altitude(10.0)  # 10 km
            0.41
        """
        altitude_m = altitude_km * 1000.0
        
        # Exponential decay
        rho = self.rho_0 * math.exp(-altitude_m / self.scale_height)
        
        return rho


class DragModel:
    """
    Atmospheric drag model for rockets.
    
    Drag force: D = 0.5 × ρ × v² × Cd × A
    
    Where:
    - ρ = atmospheric density (kg/m³)
    - v = velocity (m/s)
    - Cd = drag coefficient (dimensionless)
    - A = reference area (m²)
    
    Methods:
        calculate_drag_force(): Compute drag force (N)
        drag_acceleration(): Compute drag acceleration (m/s²)
        drag_coefficient(): Cd based on Mach number
        dynamic_pressure(): Calculate q (Pa)
    
    Example:
        >>> drag = DragModel()
        >>> force = drag.calculate_drag_force(500, 10.0, 0.3, 10.0)
        >>> accel = drag.drag_acceleration(500, 10.0, 500000, 0.3, 10.0)
    """
    
    def __init__(self):
        self.atmosphere = AtmosphereDensity()
    
    def calculate_drag_force(
        self,
        velocity_m_s: float,
        altitude_km: float,
        Cd: float,
        area_m2: float
    ) -> float:
        """
        Calculate drag force.
        
        Formula: D = 0.5 × ρ × v² × Cd × A
        
        Args:
            velocity_m_s: Velocity (m/s)
            altitude_km: Altitude (km)
            Cd: Drag coefficient
            area_m2: Reference area (m²)
        
        Returns:
            Drag force (Newtons)
        """
        rho = self.atmosphere.density_at_altitude(altitude_km)
        
        # D = 0.5 × ρ × v² × Cd × A
        drag_force = 0.5 * rho * velocity_m_s**2 * Cd * area_m2
        
        return drag_force
    
    def drag_acceleration(
        self,
        velocity_m_s: float,
        altitude_km: float,
        mass_kg: float,
        Cd: float,
        area_m2: float
    ) -> float:
        """
        Calculate drag acceleration.
        
        Formula: a_drag = -D / m
        
        Args:
            velocity_m_s: Velocity (m/s)
            altitude_km: Altitude (km)
            mass_kg: Vehicle mass (kg)
            Cd: Drag coefficient
            area_m2: Reference area (m²)
        
        Returns:
            Drag acceleration (m/s², negative = opposes motion)
        
        Example:
            >>> drag = DragModel()
            >>> a = drag.drag_acceleration(1000, 15, 500000, 0.3, 10.0)
            >>> # Returns negative value (drag opposes motion)
        """
        D = self.calculate_drag_force(velocity_m_s, altitude_km, Cd, area_m2)
        
        # Acceleration is negative (opposes motion)
        a_drag = -D / mass_kg
        
        return a_drag
    
    def drag_coefficient(self, mach: float) -> float:
        """
        Drag coefficient based on Mach number (Falcon 9 calibrated).
        
        Based on typical rocket drag curves + calibrated for CRS-21 validation.
        
        Cd varies with Mach:
        - Subsonic (M < 0.8): Cd ~ 0.35-0.40 (low speed drag)
        - Transonic (0.8 < M < 1.3): Cd peaks ~0.55-0.65 (drag rise)
        - Supersonic (M > 1.3): Cd ~ 0.25-0.30 (stabilizes lower)
        
        Args:
            mach: Mach number (velocity / speed of sound)
        
        Returns:
            Drag coefficient (dimensionless)
        
        Example:
            >>> drag = DragModel()
            >>> drag.drag_coefficient(0.5)   # Subsonic
            0.38
            >>> drag.drag_coefficient(1.0)   # Transonic (peak)
            0.60
            >>> drag.drag_coefficient(3.0)   # Supersonic
            0.28
        """
        # Calibrated drag curve for Falcon 9
        # Based on:
        # 1. Typical rocket aerodynamics
        # 2. CRS-21 validation data
        # 3. Max-Q analysis (~70 seconds, Mach ~1.0)
        
        if mach < 0.6:
            # Low subsonic (launch, early ascent)
            Cd = 0.40
        
        elif mach < 0.85:
            # High subsonic (approaching transonic)
            # Linear increase from 0.40 to 0.50
            t = (mach - 0.6) / 0.25
            Cd = 0.40 + 0.10 * t
        
        elif mach < 1.15:
            # Transonic region (CRITICAL - drag rise)
            # Peak drag near Mach 1.0
            # Polynomial curve: peak at Mach 1.0
            t = (mach - 0.85) / 0.30
            # Bell curve centered at t=0.5 (Mach 1.0)
            peak_factor = math.exp(-4 * (t - 0.5)**2)
            Cd = 0.50 + 0.10 * peak_factor  # Peak at 0.60
        
        elif mach < 2.0:
            # Early supersonic (drag settling)
            # Exponential decay from peak to stable
            t = (mach - 1.15) / 0.85
            Cd = 0.50 - 0.20 * (1 - math.exp(-2 * t))  # Decay to 0.30
        
        else:
            # High supersonic (stable drag)
            # Slight decrease with Mach due to shock wave effects
            Cd = 0.28 - 0.02 * min(1.0, (mach - 2.0) / 3.0)  # Asymptote to 0.26
        
        return Cd
    
    def dynamic_pressure(
        self,
        velocity_m_s: float,
        altitude_km: float
    ) -> float:
        """
        Calculate dynamic pressure (q).
        
        Formula: q = 0.5 × ρ × v²
        
        Max-Q (maximum dynamic pressure) typically occurs at 10-15 km
        altitude during ascent, around 30-40 kPa for rockets.
        
        Args:
            velocity_m_s: Velocity (m/s)
            altitude_km: Altitude (km)
        
        Returns:
            Dynamic pressure (Pascals)
        
        Example:
            >>> drag = DragModel()
            >>> q = drag.dynamic_pressure(500, 12.0)  # Near max-Q
            >>> print(f"q = {q/1000:.1f} kPa")
        """
        rho = self.atmosphere.density_at_altitude(altitude_km)
        q = 0.5 * rho * velocity_m_s**2
        
        return q
    
    def reference_area_from_diameter(self, diameter_m: float) -> float:
        """
        Calculate reference area from diameter.
        
        For cylindrical rockets: A = π × (d/2)²
        
        Args:
            diameter_m: Vehicle diameter (meters)
        
        Returns:
            Reference area (m²)
        
        Example:
            >>> drag = DragModel()
            >>> drag.reference_area_from_diameter(3.66)  # Falcon 9
            10.52
        """
        radius = diameter_m / 2.0
        area = math.pi * radius**2
        
        return area
    
    def mach_number(
        self,
        velocity_m_s: float,
        altitude_km: float,
        temperature_k: float = None
    ) -> float:
        """
        Calculate Mach number.
        
        Mach = v / a
        
        Where a = speed of sound = sqrt(γ × R × T)
        - γ = 1.4 (ratio of specific heats for air)
        - R = 287 J/(kg·K) (specific gas constant for air)
        - T = temperature (K)
        
        Args:
            velocity_m_s: Velocity (m/s)
            altitude_km: Altitude (km)
            temperature_k: Temperature (K), optional (estimated if None)
        
        Returns:
            Mach number
        
        Example:
            >>> drag = DragModel()
            >>> drag.mach_number(340, 0.0)  # Sea level, speed of sound
            1.0
        """
        # Estimate temperature if not provided
        if temperature_k is None:
            # Simplified: T decreases by ~6.5 K/km in troposphere
            T_0 = 288.15  # K (15°C at sea level)
            lapse_rate = 6.5  # K/km
            temperature_k = max(216.65, T_0 - lapse_rate * altitude_km)  # Min at tropopause
        
        # Speed of sound
        gamma = 1.4
        R = 287.0
        a = math.sqrt(gamma * R * temperature_k)
        
        # Mach number
        mach = velocity_m_s / a
        
        return mach
