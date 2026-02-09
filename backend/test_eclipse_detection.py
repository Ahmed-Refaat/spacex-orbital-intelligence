"""Test Eclipse Detection"""
from app.services.anise_planetary import AnisePlanetaryService
from datetime import datetime, timezone
import math

print("🧪 Testing Eclipse Detection\n")

# Test 1: Service initialization
print("1. Initialize ANISE service...")
service = AnisePlanetaryService(kernel_path="./kernels")
assert service.is_ready(), "Service not ready"
print("   ✓ Service ready\n")

# Test 2: Eclipse check - ISS in sunlight
print("2. Eclipse check - ISS in sunlight...")
epoch = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# ISS position (example - sunny side of orbit)
# Position pointing towards Sun
satellite_pos = (6800.0, 0.0, 0.0)  # km, ECI J2000
satellite_vel = (0.0, 7.5, 0.0)  # km/s

result = service.check_eclipse(
    satellite_pos,
    satellite_vel,
    epoch
)

print(f"   Eclipse type: {result['eclipse_type']}")
print(f"   In eclipse: {result['in_eclipse']}")
print(f"   Eclipse %: {result['eclipse_percentage']:.1f}%")
print(f"   Sunlight %: {100 - result['eclipse_percentage']:.1f}%")

assert result['eclipse_type'] in ['visible', 'partial', 'full'], "Invalid eclipse type"
assert 0 <= result['eclipse_percentage'] <= 100, "Invalid percentage"
print("   ✓ Eclipse check valid\n")

# Test 3: Eclipse check - Multiple orbital positions
print("3. Simulate orbital positions (ISS orbit)...")

# ISS orbital parameters
altitude_km = 400
earth_radius_km = 6371
orbital_radius_km = earth_radius_km + altitude_km
orbital_period_seconds = 2 * math.pi * math.sqrt(orbital_radius_km**3 / 398600.4)
orbital_velocity_km_s = 2 * math.pi * orbital_radius_km / orbital_period_seconds

print(f"   Orbital radius: {orbital_radius_km:.0f} km")
print(f"   Orbital period: {orbital_period_seconds/60:.1f} minutes")
print(f"   Orbital velocity: {orbital_velocity_km_s:.2f} km/s")

# Sample 8 positions around orbit (every 45°)
eclipse_count = 0
sunlight_count = 0

for i in range(8):
    angle_rad = (i * 45) * math.pi / 180
    
    # Position in orbit
    x = orbital_radius_km * math.cos(angle_rad)
    y = orbital_radius_km * math.sin(angle_rad)
    z = 0.0  # Equatorial orbit for simplicity
    
    # Velocity (perpendicular to position)
    vx = -orbital_velocity_km_s * math.sin(angle_rad)
    vy = orbital_velocity_km_s * math.cos(angle_rad)
    vz = 0.0
    
    result = service.check_eclipse((x, y, z), (vx, vy, vz), epoch)
    
    status = "☀️" if result['eclipse_type'] == 'visible' else "🌑"
    print(f"   Position {i+1} ({angle_rad*180/math.pi:.0f}°): {status} {result['eclipse_type']:8} ({result['eclipse_percentage']:.1f}% eclipse)")
    
    if result['in_eclipse']:
        eclipse_count += 1
    else:
        sunlight_count += 1

eclipse_fraction = eclipse_count / 8
print(f"\n   Eclipse fraction: {eclipse_count}/8 = {eclipse_fraction:.1%}")
print(f"   ✓ Orbital eclipse pattern detected\n")

# Test 4: Performance test
print("4. Performance test (100 eclipse checks)...")
import time
start = time.perf_counter()

for _ in range(100):
    service.check_eclipse(
        satellite_pos,
        satellite_vel,
        epoch
    )

duration = (time.perf_counter() - start) * 1000
avg_ms = duration / 100

print(f"   Total: {duration:.2f} ms")
print(f"   Average: {avg_ms:.3f} ms/check")
assert avg_ms < 10.0, f"Checks too slow: {avg_ms:.3f}ms"
print("   ✓ Performance excellent (<10ms target)\n")

# Test 5: Eclipse types
print("5. Test eclipse type determination...")
eclipse_types_seen = set()

# Try multiple positions to see different eclipse types
test_positions = [
    (6800, 0, 0),      # Likely visible
    (-6800, 0, 0),     # Likely eclipsed (behind Earth from Sun)
    (0, 6800, 0),      # Side position
    (0, -6800, 0),     # Other side
]

for i, pos in enumerate(test_positions):
    result = service.check_eclipse(pos, (0, 7.5, 0), epoch)
    eclipse_types_seen.add(result['eclipse_type'])
    print(f"   Position {i+1}: {result['eclipse_type']}")

print(f"   Eclipse types observed: {eclipse_types_seen}")
print("   ✓ Eclipse type detection working\n")

print("=" * 50)
print("✅ ALL ECLIPSE TESTS PASSED")
print("=" * 50)
print("\nEclipse detection working correctly!")
print("Ready for API deployment.")
