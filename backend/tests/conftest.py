"""
Shared pytest fixtures for spacex-orbital-intelligence tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, MagicMock

# Fixtures auto-imported by pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=False)
    return redis_mock


@pytest.fixture
def mock_spice_client():
    """Mock SPICE client for testing."""
    from app.services.spice_client import SpiceClient, OMMLoadResult, CovarianceMatrix
    from datetime import datetime
    import numpy as np
    
    client = AsyncMock(spec=SpiceClient)
    client.available = True
    client.base_url = "http://localhost:50000"
    
    # Mock health_check
    async def mock_health():
        return True
    client.health_check = AsyncMock(side_effect=mock_health)
    
    # Mock load_omm
    async def mock_load_omm(content, format='xml', validate=True):
        return OMMLoadResult(
            satellite_id="25544",
            name="ISS (ZARYA)",
            epoch=datetime(2026, 2, 9, 15, 0, 0),
            has_covariance=False,
            source="test"
        )
    client.load_omm = AsyncMock(side_effect=mock_load_omm)
    
    # Mock propagate_omm
    async def mock_propagate_omm(sat_id, epoch, include_covariance=False):
        from app.services.orbital_engine import SatellitePosition
        position = SatellitePosition(
            satellite_id=sat_id,
            timestamp=epoch,
            x=6678.137, y=0.0, z=0.0,
            vx=0.0, vy=7.612, vz=0.0,
            latitude=0.0,
            longitude=0.0,
            altitude=407.5,
            velocity=7.612
        )
        covariance = None
        if include_covariance:
            matrix = np.eye(6) * 100  # Mock covariance
            covariance = CovarianceMatrix(matrix=matrix)
        return position, covariance
    
    client.propagate_omm = AsyncMock(side_effect=mock_propagate_omm)
    
    # Mock close
    client.close = AsyncMock()
    
    return client


@pytest.fixture
def mock_orbital_engine():
    """Mock OrbitalEngine for testing."""
    from app.services.orbital_engine import OrbitalEngine, SatellitePosition
    from datetime import datetime
    
    engine = Mock(spec=OrbitalEngine)
    engine.satellite_count = 100
    engine.satellite_ids = [f"SAT_{i:05d}" for i in range(100)]
    
    def mock_propagate(sat_id, dt=None):
        if dt is None:
            dt = datetime.utcnow()
        return SatellitePosition(
            satellite_id=sat_id,
            timestamp=dt,
            x=6678.137, y=0.0, z=0.0,
            vx=0.0, vy=7.612, vz=0.0,
            latitude=0.0,
            longitude=0.0,
            altitude=407.5,
            velocity=7.612
        )
    
    engine.propagate = Mock(side_effect=mock_propagate)
    
    return engine


@pytest.fixture
async def mock_async_engine(mock_orbital_engine, mock_spice_client):
    """Mock AsyncOrbitalEngine for testing."""
    from app.services.async_orbital_engine import AsyncOrbitalEngine
    
    engine = AsyncOrbitalEngine(
        orbital_engine=mock_orbital_engine,
        spice_client=mock_spice_client,
        spice_url="http://localhost:50000"
    )
    
    yield engine
    
    # Cleanup
    await engine.shutdown()


@pytest.fixture
def sample_omm_xml():
    """Sample OMM XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<omm xmlns="http://ccsds.org/schema/omm/1.0">
  <header>
    <CREATION_DATE>2026-02-09T15:00:00Z</CREATION_DATE>
    <ORIGINATOR>TEST</ORIGINATOR>
  </header>
  <body>
    <segment>
      <metadata>
        <OBJECT_NAME>ISS (ZARYA)</OBJECT_NAME>
        <OBJECT_ID>25544</OBJECT_ID>
        <CENTER_NAME>EARTH</CENTER_NAME>
        <REF_FRAME>TEME</REF_FRAME>
        <TIME_SYSTEM>UTC</TIME_SYSTEM>
      </metadata>
      <data>
        <meanElements>
          <EPOCH>2026-02-09T15:00:00.000Z</EPOCH>
          <SEMI_MAJOR_AXIS unit="km">6778.137</SEMI_MAJOR_AXIS>
          <ECCENTRICITY>0.0001</ECCENTRICITY>
          <INCLINATION unit="deg">51.6</INCLINATION>
          <RA_OF_ASC_NODE unit="deg">120.5</RA_OF_ASC_NODE>
          <ARG_OF_PERICENTER unit="deg">90.0</ARG_OF_PERICENTER>
          <MEAN_ANOMALY unit="deg">180.0</MEAN_ANOMALY>
        </meanElements>
      </data>
    </segment>
  </body>
</omm>"""


@pytest.fixture
def sample_malicious_xml():
    """Malicious XML with XXE attack for security testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<omm>
  <data>&xxe;</data>
</omm>"""


@pytest.fixture
def sample_xml_bomb():
    """XML bomb (billion laughs attack) for security testing."""
    return """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<omm>
  <data>&lol3;</data>
</omm>"""
