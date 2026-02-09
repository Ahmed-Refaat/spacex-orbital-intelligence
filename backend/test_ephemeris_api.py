"""Quick test of ephemeris API"""
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ephemeris_health():
    response = client.get("/api/v1/ephemeris/health")
    print(f"Health: {response.status_code}")
    print(response.json())
    assert response.status_code == 200

def test_sun_position():
    response = client.get("/api/v1/ephemeris/sun?epoch=2024-01-01T12:00:00Z")
    print(f"\nSun: {response.status_code}")
    data = response.json()
    print(f"Distance: {data['distance_km']/1e6:.1f} million km")
    print(f"Computation: {data['computation_time_ms']:.3f} ms")
    assert response.status_code == 200
    assert 147e6 < data['distance_km'] < 153e6  # Earth-Sun distance range

def test_moon_position():
    response = client.get("/api/v1/ephemeris/moon?epoch=2024-01-01T12:00:00Z")
    print(f"\nMoon: {response.status_code}")
    data = response.json()
    print(f"Distance: {data['distance_km']/1e3:.1f} thousand km")
    assert response.status_code == 200
    assert 356e3 < data['distance_km'] < 406e3  # Earth-Moon distance range

if __name__ == "__main__":
    print("Testing Ephemeris API...\n")
    test_ephemeris_health()
    test_sun_position()
    test_moon_position()
    print("\n✅ ALL TESTS PASSED")
