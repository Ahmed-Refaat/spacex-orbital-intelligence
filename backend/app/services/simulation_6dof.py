"""
6-DOF (6 Degrees of Freedom) launch simulation.

This is the CORE of accurate trajectory prediction.

6-DOF = Full 3D state:
- Position: x, y, z (km)
- Velocity: vx, vy, vz (km/s)
- Mass: m (kg)

Integrates all physics:
- Gravity (altitude-dependent)
- Thrust (altitude-dependent, pitched)
- Drag (velocity & altitude-dependent)
- Staging (mass changes)
"""
from dataclasses import dataclass
from typing import List, Tuple
import math

from app.services.gravity import GravityModel
from app.services.thrust_profile import ThrustCalculator
from app.services.drag_model import DragModel
from app.services.integrator import RK4Integrator


# Physical constants
R_EARTH = 6371.0  # km


@dataclass
class State6DOF:
    """
    6-DOF state vector.
    
    Attributes:
        time: Time since liftoff (s)
        x: Downrange position (km, positive = east)
        y: Altitude (km, positive = up)
        z: Cross-range position (km, positive = north)
        vx: Downrange velocity (km/s)
        vy: Vertical velocity (km/s)
        vz: Cross-range velocity (km/s)
        mass: Vehicle mass (kg)
    """
    time: float
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    mass: float
    
    def altitude(self) -> float:
        """
        Calculate altitude above sea level.
        
        For small altitudes (< 1000 km), approximately equal to y.
        For precision: altitude = sqrt(x² + y² + z²) - R_earth
        
        Returns:
            Altitude (km)
        """
        # Simplified: y is altitude for small distances
        return self.y
    
    def velocity_magnitude(self) -> float:
        """
        Calculate velocity magnitude.
        
        Returns:
            Velocity magnitude (km/s)
        """
        return math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
    
    def to_list(self) -> List[float]:
        """
        Convert to list for RK4 integration.
        
        Returns:
            [x, y, z, vx, vy, vz, mass]
        """
        return [self.x, self.y, self.z, self.vx, self.vy, self.vz, self.mass]
    
    @staticmethod
    def from_list(time: float, state_list: List[float]) -> 'State6DOF':
        """
        Create State6DOF from list.
        
        Args:
            time: Current time (s)
            state_list: [x, y, z, vx, vy, vz, mass]
        
        Returns:
            State6DOF object
        """
        return State6DOF(
            time=time,
            x=state_list[0],
            y=state_list[1],
            z=state_list[2],
            vx=state_list[3],
            vy=state_list[4],
            vz=state_list[5],
            mass=state_list[6]
        )


class EquationsOfMotion:
    """
    Equations of motion for 6-DOF simulation.
    
    Calculates accelerations from forces:
    - Gravity: F_g = -m × g × r̂
    - Thrust: F_t = T × thrust_direction
    - Drag: F_d = -0.5 × ρ × v² × Cd × A × v̂
    
    Total: a = (F_g + F_t + F_d) / m
    """
    
    def __init__(self):
        self.gravity_model = GravityModel()
        self.thrust_calc = ThrustCalculator()
        self.drag_model = DragModel()
    
    def gravity_acceleration(self, state: State6DOF) -> List[float]:
        """
        Calculate gravity acceleration.
        
        Gravity points toward Earth center.
        For small altitudes, approximately straight down (-y direction).
        
        Args:
            state: Current state
        
        Returns:
            [ax, ay, az] in km/s²
        """
        g = self.gravity_model.gravity_at_altitude(state.altitude())
        
        # Convert to km/s²
        g_km_s2 = g / 1000.0
        
        # Simplified: gravity points down (-y)
        # (For precision, would normalize position vector)
        return [0.0, -g_km_s2, 0.0]
    
    def thrust_acceleration(
        self,
        state: State6DOF,
        thrust_N: float,
        pitch_deg: float
    ) -> List[float]:
        """
        Calculate thrust acceleration.
        
        Thrust direction determined by pitch angle:
        - pitch = 90° → vertical (pure +y)
        - pitch = 0° → horizontal (pure +x)
        
        Args:
            state: Current state
            thrust_N: Thrust force (Newtons)
            pitch_deg: Pitch angle (degrees, 90 = vertical)
        
        Returns:
            [ax, ay, az] in km/s²
        """
        # Thrust acceleration magnitude (m/s²)
        a_mag = thrust_N / state.mass
        
        # Convert pitch to radians
        pitch_rad = math.radians(pitch_deg)
        
        # Decompose into x (horizontal) and y (vertical)
        ax = a_mag * math.cos(pitch_rad)  # Horizontal component
        ay = a_mag * math.sin(pitch_rad)  # Vertical component
        az = 0.0  # No cross-range (for now)
        
        # Convert to km/s²
        return [ax / 1000.0, ay / 1000.0, az / 1000.0]
    
    def drag_acceleration(
        self,
        state: State6DOF,
        Cd: float,
        area_m2: float
    ) -> List[float]:
        """
        Calculate drag acceleration.
        
        Drag opposes velocity vector.
        
        Args:
            state: Current state
            Cd: Drag coefficient
            area_m2: Reference area (m²)
        
        Returns:
            [ax, ay, az] in km/s²
        """
        # Velocity in m/s
        velocity_m_s = state.velocity_magnitude() * 1000.0
        
        if velocity_m_s < 1.0:
            # No drag at very low velocity
            return [0.0, 0.0, 0.0]
        
        # Drag acceleration magnitude
        a_drag_mag = self.drag_model.drag_acceleration(
            velocity_m_s=velocity_m_s,
            altitude_km=state.altitude(),
            mass_kg=state.mass,
            Cd=Cd,
            area_m2=area_m2
        )
        
        # Drag opposes velocity
        # Unit velocity vector
        v_mag = state.velocity_magnitude()
        v_hat = [state.vx / v_mag, state.vy / v_mag, state.vz / v_mag]
        
        # Drag acceleration = magnitude × (-velocity direction)
        # Note: a_drag_mag is already negative from drag_model
        ax = a_drag_mag * v_hat[0] / 1000.0  # Convert to km/s²
        ay = a_drag_mag * v_hat[1] / 1000.0
        az = a_drag_mag * v_hat[2] / 1000.0
        
        return [ax, ay, az]
    
    def total_acceleration(
        self,
        state: State6DOF,
        thrust_N: float,
        pitch_deg: float,
        Cd: float,
        area_m2: float
    ) -> List[float]:
        """
        Calculate total acceleration.
        
        Total = gravity + thrust + drag
        
        Args:
            state: Current state
            thrust_N: Thrust (N)
            pitch_deg: Pitch angle (degrees)
            Cd: Drag coefficient
            area_m2: Reference area (m²)
        
        Returns:
            [ax, ay, az] in km/s²
        """
        a_grav = self.gravity_acceleration(state)
        a_thrust = self.thrust_acceleration(state, thrust_N, pitch_deg)
        a_drag = self.drag_acceleration(state, Cd, area_m2)
        
        # Sum all accelerations
        ax = a_grav[0] + a_thrust[0] + a_drag[0]
        ay = a_grav[1] + a_thrust[1] + a_drag[1]
        az = a_grav[2] + a_thrust[2] + a_drag[2]
        
        return [ax, ay, az]


class GravityTurnGuidance:
    """
    Gravity turn guidance law.
    
    Flight profile:
    1. Vertical flight (first 15-20 seconds)
    2. Small pitch kickover (5-10 degrees)
    3. Gravity turn (let gravity naturally curve trajectory)
    4. Coast to horizontal insertion
    
    This is a SIMPLIFIED guidance law for preliminary design.
    Real rockets use optimal guidance (PEG, etc.).
    """
    
    def __init__(
        self,
        vertical_flight_duration: float = 20.0,
        pitch_kickover_angle: float = 5.0
    ):
        """
        Initialize guidance law.
        
        Args:
            vertical_flight_duration: How long to fly straight up (seconds)
            pitch_kickover_angle: How much to pitch over after vertical (degrees)
        """
        self.vertical_duration = vertical_flight_duration
        self.kickover_angle = pitch_kickover_angle
    
    def pitch_angle(
        self,
        time: float,
        velocity: float,
        altitude: float
    ) -> float:
        """
        Calculate desired pitch angle.
        
        Args:
            time: Time since liftoff (s)
            velocity: Velocity magnitude (km/s)
            altitude: Altitude (km)
        
        Returns:
            Pitch angle (degrees, 90 = vertical, 0 = horizontal)
        """
        # Phase 1: Vertical flight
        if time < self.vertical_duration:
            return 90.0
        
        # Phase 2: Kickover
        if time < self.vertical_duration + 5.0:
            # Linearly pitch over
            t_kickover = time - self.vertical_duration
            pitch = 90.0 - (self.kickover_angle * t_kickover / 5.0)
            return pitch
        
        # Phase 3: Gravity turn
        # Pitch decreases with velocity (simplified)
        # Real guidance: align thrust with velocity vector + small correction
        
        # Target: horizontal (0°) at orbital velocity (~7.8 km/s)
        # Faster pitch-over for realistic trajectory
        v_orbital = 7.8  # km/s
        pitch_min = 0.0
        pitch_max = 90.0 - self.kickover_angle
        
        # Pitch as function of velocity (non-linear for faster turn)
        if velocity < 0.1:
            pitch = pitch_max
        elif velocity >= v_orbital:
            pitch = pitch_min
        else:
            # Quadratic interpolation (pitches faster early on)
            ratio = velocity / v_orbital
            pitch = pitch_max * (1 - ratio) ** 1.5  # Power 1.5 for faster turn
        
        return max(0.0, pitch)


class Simulation6DOF:
    """
    6-DOF simulation integrator.
    
    Integrates equations of motion using RK4.
    
    Methods:
        step(): Advance simulation by one timestep
        simulate(): Run full simulation
    """
    
    def __init__(self):
        self.eom = EquationsOfMotion()
        self.integrator = RK4Integrator()
    
    def step(
        self,
        state: State6DOF,
        thrust_N: float,
        pitch_deg: float,
        Cd: float,
        area_m2: float,
        dt: float
    ) -> State6DOF:
        """
        Advance simulation by one timestep using RK4.
        
        Args:
            state: Current state
            thrust_N: Thrust (N)
            pitch_deg: Pitch angle (degrees)
            Cd: Drag coefficient
            area_m2: Reference area (m²)
            dt: Timestep (seconds)
        
        Returns:
            New state after dt
        """
        # Define derivative function for RK4
        def derivative(state_list, t):
            # Unpack state
            x, y, z, vx, vy, vz, mass = state_list
            state_temp = State6DOF(t, x, y, z, vx, vy, vz, mass)
            
            # Get accelerations
            a = self.eom.total_acceleration(state_temp, thrust_N, pitch_deg, Cd, area_m2)
            
            # Derivatives
            dx_dt = vx
            dy_dt = vy
            dz_dt = vz
            dvx_dt = a[0]
            dvy_dt = a[1]
            dvz_dt = a[2]
            dm_dt = 0.0  # Mass change handled separately (staging)
            
            return [dx_dt, dy_dt, dz_dt, dvx_dt, dvy_dt, dvz_dt, dm_dt]
        
        # Integrate with RK4
        state_list = state.to_list()
        new_state_list = self.integrator.step(derivative, state_list, state.time, dt)
        
        # Convert back to State6DOF
        new_state = State6DOF.from_list(state.time + dt, new_state_list)
        
        return new_state
