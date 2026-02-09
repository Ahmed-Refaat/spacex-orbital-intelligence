"""
Tests for SPICE Client

Run with: pytest tests/test_spice_client.py -v
"""

import pytest
from datetime import datetime
import numpy as np

from app.services.spice_client import (
    SpiceClient,
    SpiceServiceUnavailable,
    SpiceClientError,
    CovarianceMatrix,
    OMMLoadResult
)


@pytest.fixture
def spice_client():
    """Create SPICE client instance."""
    return SpiceClient(base_url="http://localhost:50000")


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
        <OBJECT_NAME>TEST-SAT</OBJECT_NAME>
        <OBJECT_ID>99999</OBJECT_ID>
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


class TestCovarianceMatrix:
    """Tests for CovarianceMatrix dataclass."""
    
    def test_covariance_matrix_creation(self):
        """Test creating covariance matrix."""
        matrix = np.eye(6) * 100  # 100 m² diagonal
        cov = CovarianceMatrix(matrix=matrix)
        
        assert cov.matrix.shape == (6, 6)
        assert cov.matrix[0, 0] == 100
    
    def test_covariance_matrix_invalid_shape(self):
        """Test that invalid matrix shape raises error."""
        matrix = np.eye(5)  # Wrong shape
        
        with pytest.raises(ValueError, match="Covariance must be 6x6"):
            CovarianceMatrix(matrix=matrix)
    
    def test_position_sigma(self):
        """Test position sigma calculation."""
        matrix = np.diag([100, 200, 300, 10, 20, 30])  # m²
        cov = CovarianceMatrix(matrix=matrix)
        
        sigma = cov.position_sigma_km
        
        # sqrt(100) m = 10 m = 0.01 km
        assert abs(sigma['x'] - 0.01) < 1e-6
        # sqrt(200) m = 14.14 m = 0.01414 km
        assert abs(sigma['y'] - 0.01414) < 1e-3
        # sqrt(300) m = 17.32 m = 0.01732 km
        assert abs(sigma['z'] - 0.01732) < 1e-3
    
    def test_total_uncertainty(self):
        """Test total position uncertainty (RSS)."""
        matrix = np.diag([100, 100, 100, 0, 0, 0])  # Equal position uncertainty
        cov = CovarianceMatrix(matrix=matrix)
        
        # RSS = sqrt(100 + 100 + 100) = sqrt(300) = 17.32 m = 0.01732 km
        assert abs(cov.total_position_uncertainty_km - 0.01732) < 1e-3
    
    def test_to_dict(self):
        """Test serialization to dict."""
        matrix = np.eye(6) * 100
        cov = CovarianceMatrix(matrix=matrix)
        
        data = cov.to_dict()
        
        assert 'matrix' in data
        assert 'position_sigma_km' in data
        assert 'velocity_sigma_km_s' in data
        assert 'total_position_uncertainty_km' in data
        
        # Check matrix is list (JSON-serializable)
        assert isinstance(data['matrix'], list)
        assert len(data['matrix']) == 6
        assert len(data['matrix'][0]) == 6


class TestSpiceClient:
    """Tests for SpiceClient."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, spice_client):
        """Test client initializes correctly."""
        assert spice_client.base_url == "http://localhost:50000"
        assert spice_client.available == False  # Not checked yet
    
    @pytest.mark.asyncio
    async def test_health_check_when_service_unavailable(self, spice_client):
        """Test health check when service is not running."""
        # This will fail if SPICE is not running (expected in unit tests)
        available = await spice_client.health_check()
        
        # Either available (if SPICE running) or not (expected)
        assert isinstance(available, bool)
        assert spice_client.available == available
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="Requires SPICE service running")
    async def test_health_check_success(self, spice_client):
        """Test health check with running service."""
        available = await spice_client.health_check()
        
        assert available == True
        assert spice_client.available == True
    
    @pytest.mark.asyncio
    async def test_load_omm_when_unavailable(self, spice_client, sample_omm_xml):
        """Test load_omm raises error when service unavailable."""
        # Don't run health check - service marked unavailable
        
        with pytest.raises(SpiceServiceUnavailable):
            await spice_client.load_omm(sample_omm_xml, format='xml')
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(True, reason="Requires SPICE service running")
    async def test_load_omm_success(self, spice_client, sample_omm_xml):
        """Test loading OMM successfully."""
        await spice_client.health_check()
        
        result = await spice_client.load_omm(sample_omm_xml, format='xml')
        
        assert isinstance(result, OMMLoadResult)
        assert result.satellite_id == "99999"
        assert result.name == "TEST-SAT"
        assert isinstance(result.epoch, datetime)
    
    @pytest.mark.asyncio
    async def test_propagate_omm_when_unavailable(self, spice_client):
        """Test propagate raises error when service unavailable."""
        
        with pytest.raises(SpiceServiceUnavailable):
            await spice_client.propagate_omm(
                "99999",
                datetime.utcnow(),
                include_covariance=False
            )
    
    @pytest.mark.asyncio
    async def test_close(self, spice_client):
        """Test client closes cleanly."""
        await spice_client.close()
        # No assertion - just ensure no exception


class TestOMMLoadResult:
    """Tests for OMMLoadResult dataclass."""
    
    def test_omm_load_result_creation(self):
        """Test creating OMMLoadResult."""
        result = OMMLoadResult(
            satellite_id="12345",
            name="TEST",
            epoch=datetime(2026, 2, 9, 15, 0, 0),
            has_covariance=True,
            source="test"
        )
        
        assert result.satellite_id == "12345"
        assert result.name == "TEST"
        assert result.has_covariance == True
    
    def test_to_dict(self):
        """Test serialization."""
        result = OMMLoadResult(
            satellite_id="12345",
            name="TEST",
            epoch=datetime(2026, 2, 9, 15, 0, 0),
            has_covariance=False,
            source="test"
        )
        
        data = result.to_dict()
        
        assert data['satellite_id'] == "12345"
        assert data['name'] == "TEST"
        assert data['has_covariance'] == False
        assert isinstance(data['epoch'], str)  # ISO format


# Integration tests (require SPICE service)
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(True, reason="Requires SPICE service + sample data")
class TestSpiceIntegration:
    """Integration tests with real SPICE service."""
    
    async def test_full_omm_workflow(self, spice_client, sample_omm_xml):
        """Test complete workflow: upload OMM → propagate."""
        # Health check
        assert await spice_client.health_check()
        
        # Load OMM
        result = await spice_client.load_omm(sample_omm_xml, format='xml')
        assert result.satellite_id == "99999"
        
        # Propagate
        position, covariance = await spice_client.propagate_omm(
            result.satellite_id,
            result.epoch,
            include_covariance=False
        )
        
        assert position is not None
        assert position.satellite_id == "99999"
        # Covariance should be None (sample OMM doesn't have it)
        assert covariance is None
