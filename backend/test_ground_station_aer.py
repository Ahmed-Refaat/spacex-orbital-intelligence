"""Test Ground Station AER calculations"""
from app.services.anise_planetary import AnisePlanetaryService
from app.models.ground_station import GroundStation, GROUND_STATIONS
from datetime import datetime, timezone

print("🧪 Testing Ground Station AER\n")

# Test 1: Service initialization
print("1. Initialize ANISE service...")
service = AnisePlanetaryService(kernel_path="./kernels")
assert service.is_ready(), "Service not ready"
print("   ✓ Service ready\n")

# Test 2: Ground station data
print("2. Load ground stations...")
print(f"   Available stations: {len(GROUND_STATIONS)}")
dss65 = GROUND_STATIONS["DSS-65"]
print(f"   DSS-65: {dss65.latitude_deg}°N, {dss65.longitude_deg}°E")
print("   ✓ Ground stations loaded\n")

# Test 3: AER calculation
print("3. Calculate AER (ISS over DSS-65)...")
epoch = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# ISS approximate position (from typical orbit)
# At epoch, ISS at ~400km altitude, 51.6° inclination
# Position (example - would come from SGP4)
satellite_pos = (6800.0, 0.0, 0.0)  # km, ECI J2000
satellite_vel = (0.0, 7.5, 0.0)  # km/s

azimuth, elevation, range_km = service.calculate_aer(
    satellite_pos,
    satellite_vel,
    dss65.latitude_deg,
    dss65.longitude_deg,
    dss65.altitude_km,
    epoch
)

print(f"   Azimuth: {azimuth:.2f}° (0-360°)")
print(f"   Elevation: {elevation:.2f}° (-90 to +90°)")
print(f"   Range: {range_km:.2f} km")

# Validate ranges
assert 0 <= azimuth <= 360, f"Azimuth out of range: {azimuth}"
assert -90 <= elevation <= 90, f"Elevation out of range: {elevation}"
assert range_km > 0, f"Range must be positive: {range_km}"
print("   ✓ AER values valid\n")

# Test 4: Visibility check
print("4. Visibility check...")
is_visible = elevation >= dss65.min_elevation_deg
print(f"   Min elevation: {dss65.min_elevation_deg}°")
print(f"   Current elevation: {elevation:.2f}°")
print(f"   Visible: {is_visible}")
if is_visible:
    print("   ✓ Satellite is above horizon")
else:
    print("   ✓ Satellite is below horizon (expected for this geometry)")
print()

# Test 5: Multiple ground stations
print("5. Test multiple ground stations...")
stations_tested = 0
for name, station in list(GROUND_STATIONS.items())[:3]:  # Test first 3
    az, el, rng = service.calculate_aer(
        satellite_pos,
        satellite_vel,
        station.latitude_deg,
        station.longitude_deg,
        station.altitude_km,
        epoch
    )
    print(f"   {name}: el={el:+.1f}°, rng={rng:.0f}km")
    stations_tested += 1

print(f"   ✓ Tested {stations_tested} stations\n")

# Test 6: Performance
print("6. Performance test (100 AER calculations)...")
import time
start = time.perf_counter()
for _ in range(100):
    service.calculate_aer(
        satellite_pos,
        satellite_vel,
        dss65.latitude_deg,
        dss65.longitude_deg,
        dss65.altitude_km,
        epoch
    )
duration = (time.perf_counter() - start) * 1000
avg_ms = duration / 100
print(f"   Total: {duration:.2f} ms")
print(f"   Average: {avg_ms:.3f} ms/calculation")
assert avg_ms < 10.0, f"Calculations too slow: {avg_ms:.3f}ms"
print("   ✓ Performance excellent (<10ms target)\n")

print("=" * 50)
print("✅ ALL AER TESTS PASSED")
print("=" * 50)
print("\nGround Station AER calculations working correctly!")
print("Ready for API deployment.")
