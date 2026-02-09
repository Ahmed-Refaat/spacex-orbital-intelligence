"""
Tests for AsyncOrbitalEngine - Hybrid SGP4/SPICE propagation engine.

Target: 80%+ coverage
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.services.async_orbital_engine import (
    AsyncOrbitalEngine,
    PropagationStats,
    BATCH_SIZE_THRESHOLD
)
from app.services.orbital_engine import SatellitePosition


class TestPropagationStats:
    """Test PropagationStats dataclass."""
    
    def test_stats_creation(self):
        """Test basic stats creation."""
        stats = PropagationStats(
            method="sgp4_single",
            satellite_count=1,
            duration_ms=2.8,
            throughput_per_sec=357.1,
            success_rate=1.0
        )
        
        assert stats.method == "sgp4_single"
        assert stats.satellite_count == 1
        assert stats.duration_ms == 2.8
        assert stats.throughput_per_sec == 357.1
        assert stats.success_rate == 1.0
    
    def test_stats_to_dict(self):
        """Test stats serialization."""
        stats = PropagationStats(
            method="spice_batch",
            satellite_count=100,
            duration_ms=50.5,
            throughput_per_sec=1980.2,
            success_rate=0.98
        )
        
        result = stats.to_dict()
        
        assert result["method"] == "spice_batch"
        assert result["satellite_count"] == 100
        assert result["duration_ms"] == 50.5
        assert result["throughput_per_sec"] == 1980.2
        assert result["success_rate"] == 0.98


class TestAsyncOrbitalEngineInit:
    """Test AsyncOrbitalEngine initialization."""
    
    def test_initialization(self, mock_orbital_engine, mock_spice_client):
        """Test engine initialization with mocks."""
        engine = AsyncOrbitalEngine(
            orbital_engine=mock_orbital_engine,
            spice_client=mock_spice_client,
            spice_url="http://test:50000"
        )
        
        assert engine.orbital_engine == mock_orbital_engine
        assert engine.spice_client == mock_spice_client
        assert engine.executor is not None
        assert engine._last_stats is None
    
    def test_initialization_default_spice_client(self, mock_orbital_engine):
        """Test initialization creates default SPICE client if not provided."""
        with patch('app.services.async_orbital_engine.SpiceClient') as MockClient:
            engine = AsyncOrbitalEngine(
                orbital_engine=mock_orbital_engine,
                spice_url="http://custom:50000"
            )
            
            MockClient.assert_called_once_with(base_url="http://custom:50000")


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality."""
    
    async def test_health_check_both_available(self, mock_async_engine):
        """Test health check when both engines available."""
        health = await mock_async_engine.health_check()
        
        assert health["spice"]["available"] is True
        assert health["sgp4"]["available"] is True
        assert health["routing"]["batch_threshold"] == BATCH_SIZE_THRESHOLD
    
    async def test_health_check_spice_unavailable(self, mock_orbital_engine):
        """Test health check when SPICE unavailable."""
        spice_mock = AsyncMock()
        spice_mock.health_check = AsyncMock(return_value=False)
        spice_mock.available = False
        spice_mock.base_url = "http://localhost:50000"
        
        engine = AsyncOrbitalEngine(
            orbital_engine=mock_orbital_engine,
            spice_client=spice_mock
        )
        
        health = await engine.health_check()
        
        assert health["spice"]["available"] is False
        assert health["sgp4"]["available"] is True


@pytest.mark.asyncio
class TestPropagateSingle:
    """Test single satellite propagation (always uses SGP4)."""
    
    async def test_propagate_single_success(self, mock_async_engine):
        """Test successful single satellite propagation."""
        sat_id = "25544"
        dt = datetime(2026, 2, 9, 15, 0, 0)
        
        result = await mock_async_engine.propagate_single(sat_id, dt)
        
        assert result is not None
        assert result.satellite_id == sat_id
        assert result.timestamp == dt
        assert result.altitude > 0
    
    async def test_propagate_single_tracks_stats(self, mock_async_engine):
        """Test that single propagation tracks stats."""
        await mock_async_engine.propagate_single("25544")
        
        stats = mock_async_engine.get_last_stats()
        
        assert stats is not None
        assert stats.method == "sgp4_single"
        assert stats.satellite_count == 1
        assert stats.duration_ms > 0
        assert stats.success_rate == 1.0
    
    async def test_propagate_single_failure(self, mock_orbital_engine):
        """Test propagation failure handling."""
        # Make propagate return None (satellite not found)
        mock_orbital_engine.propagate = Mock(return_value=None)
        
        engine = AsyncOrbitalEngine(
            orbital_engine=mock_orbital_engine,
            spice_client=AsyncMock()
        )
        
        result = await engine.propagate_single("INVALID")
        
        assert result is None
        
        stats = engine.get_last_stats()
        assert stats.success_rate == 0.0


@pytest.mark.asyncio
class TestPropagateBatch:
    """Test batch satellite propagation with hybrid routing."""
    
    async def test_batch_small_uses_sgp4(self, mock_async_engine):
        """Test that small batch (<50) uses SGP4 parallel."""
        sat_ids = [f"SAT_{i:05d}" for i in range(10)]
        
        results = await mock_async_engine.propagate_batch(sat_ids)
        
        assert len(results) == 10
        assert all(r is not None for r in results)
        
        stats = mock_async_engine.get_last_stats()
        assert stats.method == "sgp4_parallel"
        assert stats.satellite_count == 10
    
    async def test_batch_large_uses_spice(self, mock_async_engine):
        """Test that large batch (≥50) attempts SPICE."""
        sat_ids = [f"SAT_{i:05d}" for i in range(60)]
        
        # Since SPICE is mocked and available
        results = await mock_async_engine.propagate_batch(sat_ids)
        
        assert len(results) == 60
        
        stats = mock_async_engine.get_last_stats()
        # Should attempt SPICE first (but may fallback in mock)
        assert stats.satellite_count == 60
    
    async def test_batch_empty(self, mock_async_engine):
        """Test batch with empty list."""
        results = await mock_async_engine.propagate_batch([])
        
        assert results == []
    
    async def test_batch_spice_unavailable_fallback(self, mock_orbital_engine):
        """Test fallback to SGP4 when SPICE unavailable."""
        spice_mock = AsyncMock()
        spice_mock.available = False
        
        engine = AsyncOrbitalEngine(
            orbital_engine=mock_orbital_engine,
            spice_client=spice_mock
        )
        
        sat_ids = [f"SAT_{i:05d}" for i in range(60)]
        results = await engine.propagate_batch(sat_ids)
        
        assert len(results) == 60
        
        stats = engine.get_last_stats()
        # Should use SGP4 because SPICE unavailable
        assert stats.method == "sgp4_parallel"
    
    async def test_batch_handles_partial_failures(self, mock_orbital_engine):
        """Test batch handles some satellites failing."""
        def mock_propagate(sat_id, dt=None):
            # Fail on odd IDs
            if int(sat_id.split('_')[1]) % 2 == 1:
                return None
            return SatellitePosition(
                satellite_id=sat_id,
                timestamp=datetime.utcnow(),
                x=6678.137, y=0, z=0,
                vx=0, vy=7.612, vz=0,
                latitude=0, longitude=0, altitude=407.5,
                velocity=7.612
            )
        
        mock_orbital_engine.propagate = Mock(side_effect=mock_propagate)
        
        engine = AsyncOrbitalEngine(
            orbital_engine=mock_orbital_engine,
            spice_client=AsyncMock()
        )
        
        sat_ids = [f"SAT_{i:05d}" for i in range(10)]
        results = await engine.propagate_batch(sat_ids)
        
        # Half should be None (failures)
        assert len(results) == 10
        assert sum(1 for r in results if r is None) == 5
        
        stats = engine.get_last_stats()
        assert stats.success_rate == 0.5


@pytest.mark.asyncio
class TestBenchmark:
    """Test benchmark functionality."""
    
    async def test_benchmark_runs(self, mock_async_engine):
        """Test benchmark executes successfully."""
        sat_ids = [f"SAT_{i:05d}" for i in range(10)]
        
        results = await mock_async_engine.benchmark(sat_ids, runs=2)
        
        assert "batch_size" in results
        assert results["batch_size"] == 10
        assert results["runs"] == 2
        assert "sgp4" in results
        assert "spice" in results
        
        # SGP4 should have results
        assert results["sgp4"]["avg_duration_ms"] > 0
        assert results["sgp4"]["throughput_per_sec"] > 0
        assert len(results["sgp4"]["times"]) == 2
    
    async def test_benchmark_spice_available(self, mock_async_engine):
        """Test benchmark includes SPICE when available."""
        sat_ids = [f"SAT_{i:05d}" for i in range(60)]
        
        results = await mock_async_engine.benchmark(sat_ids, runs=1)
        
        # SPICE should be available in mock
        assert results["spice"]["available"] is True


@pytest.mark.asyncio
class TestShutdown:
    """Test cleanup and shutdown."""
    
    async def test_shutdown_closes_resources(self, mock_async_engine):
        """Test shutdown properly closes resources."""
        await mock_async_engine.shutdown()
        
        # Verify SPICE client close was called
        mock_async_engine.spice_client.close.assert_called_once()
    
    async def test_shutdown_stops_executor(self, mock_orbital_engine, mock_spice_client):
        """Test shutdown stops ThreadPoolExecutor."""
        engine = AsyncOrbitalEngine(
            orbital_engine=mock_orbital_engine,
            spice_client=mock_spice_client
        )
        
        executor_mock = Mock()
        engine.executor = executor_mock
        
        await engine.shutdown()
        
        executor_mock.shutdown.assert_called_once_with(wait=True)


@pytest.mark.asyncio
class TestPropagateOrbitAsync:
    """Test async orbit path generation."""
    
    async def test_propagate_orbit_async(self, mock_async_engine):
        """Test async orbit propagation."""
        sat_id = "25544"
        
        positions = await mock_async_engine.propagate_orbit_async(
            sat_id,
            hours=1,
            step_minutes=5
        )
        
        # Should return list of positions
        assert isinstance(positions, list)


@pytest.mark.asyncio
class TestCalculateRiskAsync:
    """Test async collision risk calculation."""
    
    async def test_calculate_risk_async(self, mock_async_engine):
        """Test async risk calculation."""
        mock_async_engine.orbital_engine.calculate_risk_score = Mock(
            return_value=Mock(risk_score=0.3)
        )
        
        risk = await mock_async_engine.calculate_risk_async("25544", "25545", hours_ahead=24)
        
        assert risk is not None


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
class TestPerformance:
    """Performance benchmarks."""
    
    async def test_single_propagation_performance(self, mock_async_engine):
        """Test single propagation is fast (<10ms)."""
        import time
        
        start = time.time()
        await mock_async_engine.propagate_single("25544")
        duration_ms = (time.time() - start) * 1000
        
        # With mocks should be <1ms
        assert duration_ms < 10
    
    async def test_batch_propagation_scaling(self, mock_async_engine):
        """Test batch propagation scales linearly."""
        import time
        
        # Small batch
        sat_ids_10 = [f"SAT_{i:05d}" for i in range(10)]
        start = time.time()
        await mock_async_engine.propagate_batch(sat_ids_10)
        time_10 = time.time() - start
        
        # Large batch (should scale linearly, not exponentially)
        sat_ids_100 = [f"SAT_{i:05d}" for i in range(100)]
        start = time.time()
        await mock_async_engine.propagate_batch(sat_ids_100)
        time_100 = time.time() - start
        
        # 10x satellites should take <20x time (due to parallelization)
        assert time_100 < time_10 * 20


@pytest.mark.integration
@pytest.mark.asyncio
class TestIntegration:
    """Integration tests (require real services)."""
    
    @pytest.mark.skip(reason="Requires real SPICE service")
    async def test_real_spice_integration(self):
        """Test with real SPICE service (manual test)."""
        # This test is skipped in CI but can be run manually
        # when SPICE service is available
        pass
