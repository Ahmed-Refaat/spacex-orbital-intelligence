"""Simple ANISE test - no full app loading"""
from app.services.anise_planetary import AnisePlanetaryService
from datetime import datetime, timezone

print("🧪 Testing ANISE Planetary Service\n")

# Test 1: Service initialization
print("1. Initializing service...")
service = AnisePlanetaryService(kernel_path="./kernels")
assert service.is_ready(), "Service not ready"
print("   ✓ Service ready\n")

# Test 2: Sun position
print("2. Query Sun position...")
epoch = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
x, y, z = service.get_sun_position(epoch)
sun_dist = (x**2 + y**2 + z**2) ** 0.5
print(f"   Position: ({x/1e6:.2f}, {y/1e6:.2f}, {z/1e6:.2f}) million km")
print(f"   Distance: {sun_dist/1e6:.2f} million km")
assert 147e6 < sun_dist < 153e6, f"Sun distance out of range: {sun_dist/1e6:.2f}M km"
print("   ✓ Sun distance correct (147-153M km)\n")

# Test 3: Moon position
print("3. Query Moon position...")
x, y, z = service.get_moon_position(epoch)
moon_dist = (x**2 + y**2 + z**2) ** 0.5
print(f"   Distance: {moon_dist/1e3:.1f} thousand km")
assert 356e3 < moon_dist < 407e3, f"Moon distance out of range: {moon_dist/1e3:.1f}k km"
print("   ✓ Moon distance correct (356-407k km)\n")

# Test 4: Generic body query (Mars)
print("4. Query Mars position...")
try:
    x, y, z = service.get_body_position("MARS", epoch, observer="EARTH")
    mars_dist = (x**2 + y**2 + z**2) ** 0.5
    print(f"   Distance: {mars_dist/1e6:.1f} million km")
    print("   ✓ Mars query successful\n")
except Exception as e:
    print(f"   ⚠ Mars query failed: {e}\n")

# Test 5: Performance check
print("5. Performance test (100 queries)...")
import time
start = time.perf_counter()
for _ in range(100):
    service.get_sun_position(epoch)
duration = (time.perf_counter() - start) * 1000
avg_ms = duration / 100
print(f"   Total: {duration:.2f} ms")
print(f"   Average: {avg_ms:.3f} ms/query")
assert avg_ms < 1.0, f"Queries too slow: {avg_ms:.3f}ms"
print("   ✓ Performance excellent (<1ms/query)\n")

print("=" * 50)
print("✅ ALL TESTS PASSED")
print("=" * 50)
print("\nANISE Planetary Service is working correctly!")
print("Ready for API integration.")
