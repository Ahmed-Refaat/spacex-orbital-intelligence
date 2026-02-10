"""
Realistic Falcon 9 Guidance Law

Based on actual Falcon 9 telemetry and launch videos.

Key characteristics:
1. Vertical flight: 0-15 seconds
2. Pitch kickover: 15-30 seconds (very gradual, 2-3°)
3. Gravity turn: 30-150 seconds (follows prograde vector)
4. Final approach: 150+ seconds (shallow pitch to horizontal)

Falcon 9 is VERY conservative early in flight (thick atmosphere).
Aggressive pitch-over happens after passing Max-Q (~70-80 seconds).
"""
from typing import Tuple
import math


class Falcon9GuidanceLaw:
    """
    Realistic Falcon 9 pitch profile based on telemetry.
    
    Profile stages:
    - 0-15s: Vertical ascent
    - 15-20s: Initial kickover (87-85° pitch)
    - 20-60s: Conservative pitch (85-75° pitch) 
    - 60-90s: Post-Max-Q aggressive turn (75-55° pitch)
    - 90-150s: Stage 1 completion (55-30° pitch)
    - 150-300s: Stage 2 gravity turn (30-10° pitch)
    - 300+s: Final circularization (10-0° pitch)
    
    Based on CRS-21 and similar Falcon 9 ISS missions.
    """
    
    def __init__(
        self,
        target_altitude_km: float = 210.0,
        target_inclination_deg: float = 51.6
    ):
        """
        Initialize guidance law.
        
        Args:
            target_altitude_km: Target orbit altitude
            target_inclination_deg: Target orbit inclination
        """
        self.target_altitude = target_altitude_km
        self.target_inclination = target_inclination_deg
        
        # Flight phases (time breakpoints in seconds)
        self.t_vertical_flight = 13.0      # Pure vertical (balanced)
        self.t_initial_kickover = 19.0     # Start pitch
        self.t_max_q = 69.0                # Max aerodynamic pressure
        self.t_post_max_q = 88.0           # Post Max-Q turn
        self.t_meco = 150.0                # ~MECO time
        self.t_gravity_turn_end = 320.0    # End of major turning
        
        # Pitch angles at key points (degrees from horizontal)
        # 90° = vertical, 0° = horizontal
        # CALIBRATED FOR CRS-21 VALIDATION
        self.pitch_liftoff = 90.0
        self.pitch_kickover_start = 82.5   # Balanced kickover
        self.pitch_max_q = 66.0            # Balanced pre-Max-Q
        self.pitch_post_max_q = 46.0       # Balanced turn
        self.pitch_meco = 26.5             # Balanced pitch at MECO
        self.pitch_final = 0.0             # Horizontal
    
    def get_pitch_angle(
        self,
        time: float,
        altitude: float,
        velocity: float,
        stage: int = 1
    ) -> float:
        """
        Calculate desired pitch angle.
        
        Args:
            time: Time since liftoff (seconds)
            altitude: Current altitude (km)
            velocity: Current velocity magnitude (km/s)
            stage: Current stage (1 or 2)
        
        Returns:
            Pitch angle in degrees (90 = vertical, 0 = horizontal)
        """
        # Stage 1: Conservative profile
        if stage == 1 or time < self.t_meco:
            return self._stage1_pitch(time, altitude, velocity)
        
        # Stage 2: More aggressive profile
        else:
            return self._stage2_pitch(time, altitude, velocity)
    
    def _stage1_pitch(self, time: float, altitude: float, velocity: float) -> float:
        """Stage 1 pitch profile (0-150s)."""
        
        # Phase 1: Vertical flight (0-15s)
        if time < self.t_vertical_flight:
            return self.pitch_liftoff
        
        # Phase 2: Initial kickover (15-20s) - very gentle
        elif time < self.t_initial_kickover:
            progress = (time - self.t_vertical_flight) / (self.t_initial_kickover - self.t_vertical_flight)
            return self._interpolate(
                self.pitch_liftoff,
                self.pitch_kickover_start,
                progress
            )
        
        # Phase 3: Pre-Max-Q (20-70s) - still conservative
        elif time < self.t_max_q:
            progress = (time - self.t_initial_kickover) / (self.t_max_q - self.t_initial_kickover)
            return self._interpolate(
                self.pitch_kickover_start,
                self.pitch_max_q,
                progress ** 0.7  # Slightly faster turn
            )
        
        # Phase 4: Post-Max-Q (70-90s) - more aggressive
        elif time < self.t_post_max_q:
            progress = (time - self.t_max_q) / (self.t_post_max_q - self.t_max_q)
            return self._interpolate(
                self.pitch_max_q,
                self.pitch_post_max_q,
                progress ** 1.2  # Faster turn after Max-Q
            )
        
        # Phase 5: Approaching MECO (90-150s) - aggressive turn
        elif time < self.t_meco:
            progress = (time - self.t_post_max_q) / (self.t_meco - self.t_post_max_q)
            return self._interpolate(
                self.pitch_post_max_q,
                self.pitch_meco,
                progress ** 1.5  # Even faster turn near MECO
            )
        
        # Fallback
        return self.pitch_meco
    
    def _stage2_pitch(self, time: float, altitude: float, velocity: float) -> float:
        """Stage 2 pitch profile (150-540s) - altitude-focused."""
        
        # Continue from Stage 1 pitch at MECO
        if time < self.t_meco + 10:
            # Brief coast/transition
            return self.pitch_meco
        
        # Phase 6: STAY VERTICAL to gain altitude (150-350s)
        # Stage 2 needs to climb first, turn later
        elif time < 350.0:
            progress = (time - self.t_meco) / (350.0 - self.t_meco)
            # Very conservative - stay above 20° for altitude
            return self._interpolate(
                self.pitch_meco,
                25.0,  # Still quite vertical
                progress ** 0.6  # Very slow turn
            )
        
        # Phase 7: Gradual turn (350-480s)
        elif time < 480.0:
            progress = (time - 350.0) / 130.0
            return self._interpolate(
                25.0,
                10.0,  # Start approaching horizontal
                progress ** 1.2
            )
        
        # Phase 8: Final circularization (480-540s)
        else:
            # Final approach to horizontal
            progress = min(1.0, (time - 480.0) / 60.0)
            return self._interpolate(
                10.0,
                self.pitch_final,
                progress ** 1.8
            )
    
    def _interpolate(self, start: float, end: float, progress: float) -> float:
        """Linear interpolation with clamping."""
        progress = max(0.0, min(1.0, progress))
        return start + (end - start) * progress
    
    def get_azimuth(self, latitude_deg: float) -> float:
        """
        Calculate launch azimuth for target inclination.
        
        Args:
            latitude_deg: Launch site latitude
        
        Returns:
            Launch azimuth (degrees from North)
        """
        # Simplified azimuth calculation
        # Real Falcon 9 uses optimized trajectory
        
        lat_rad = math.radians(latitude_deg)
        inc_rad = math.radians(self.target_inclination)
        
        # Check if inclination is achievable
        if abs(self.target_inclination) < abs(latitude_deg):
            # Can't reach inclination lower than launch latitude
            # Use minimum energy trajectory
            return 90.0 if self.target_inclination > 0 else 270.0
        
        # Calculate azimuth
        sin_az = math.cos(inc_rad) / math.cos(lat_rad)
        sin_az = max(-1.0, min(1.0, sin_az))  # Clamp
        
        azimuth = math.degrees(math.asin(sin_az))
        
        # Adjust for northbound vs southbound
        if self.target_inclination > 0:
            # Northbound
            if latitude_deg > 0:
                azimuth = azimuth  # Northeast
            else:
                azimuth = 180.0 - azimuth  # Northwest
        else:
            # Southbound
            if latitude_deg > 0:
                azimuth = 180.0 - azimuth  # Southeast
            else:
                azimuth = azimuth  # Southwest
        
        return azimuth


def test_guidance_profile():
    """Test pitch profile at key times."""
    guidance = Falcon9GuidanceLaw(target_altitude_km=210, target_inclination_deg=51.6)
    
    test_times = [0, 10, 15, 20, 40, 70, 90, 120, 150, 200, 300, 400, 500]
    
    print("Falcon 9 Pitch Profile (CRS-21-like mission)")
    print("=" * 60)
    print(f"{'Time (s)':>10} | {'Pitch (°)':>10} | Phase")
    print("-" * 60)
    
    for t in test_times:
        stage = 1 if t < 150 else 2
        pitch = guidance.get_pitch_angle(t, altitude=0, velocity=0, stage=stage)
        
        # Determine phase
        if t < 15:
            phase = "Vertical"
        elif t < 70:
            phase = "Pre-Max-Q"
        elif t < 90:
            phase = "Post-Max-Q"
        elif t < 150:
            phase = "Pre-MECO"
        elif t < 300:
            phase = "Gravity Turn"
        else:
            phase = "Circularization"
        
        print(f"{t:10.0f} | {pitch:10.1f} | {phase}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_guidance_profile()
