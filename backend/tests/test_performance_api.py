"""
Tests for Performance API endpoints.

Target: 80%+ coverage
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock

from app.main import app


client = TestClient(app)


class TestPerformanceStatsEndpoint:
    """Test GET /performance/stats endpoint."""
    
    @patch('app.api.performance.get_async_engine')
    @patch('app.api.performance.psutil')
    def test_get_stats_success(self, mock_psutil, mock_get_engine):
        """Test successful stats retrieval."""
        # Mock async engine
        mock_engine = AsyncMock()
        mock_engine.get_last_stats.return_value = None
        mock_engine.health_check = AsyncMock(return_value={
            "spice": {"available": True, "url": "http://spice:50000"},
            "sgp4": {"available": True, "satellite_count": 100},
            "routing": {"batch_threshold": 50}
        })
        mock_get_engine.return_value = mock_engine
        
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = Mock(
            percent=45.2,
            used=8 * 1024**3,  # 8GB
            total=16 * 1024**3  # 16GB
        )
        
        response = client.get("/api/v1/performance/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "health" in data
        assert "system" in data
        assert "propagation" in data
        
        # Check system metrics
        assert data["system"]["cpu_percent"] == 25.5
        assert data["system"]["memory_percent"] == 45.2
    
    def test_get_stats_error_handling(self):
        """Test error handling in stats endpoint."""
        with patch('app.api.performance.get_async_engine', side_effect=RuntimeError("Not initialized")):
            response = client.get("/api/v1/performance/stats")
            
            assert response.status_code == 500


class TestBenchmarkEndpoint:
    """Test POST /performance/benchmark endpoint."""
    
    @patch('app.api.performance.get_async_engine')
    def test_benchmark_success(self, mock_get_engine):
        """Test successful benchmark run."""
        # Mock benchmark results
        mock_engine = AsyncMock()
        mock_engine.benchmark = AsyncMock(return_value={
            "batch_size": 100,
            "runs": 3,
            "sgp4": {
                "avg_duration_ms": 280.5,
                "throughput_per_sec": 356.5,
                "times": [275.2, 282.1, 284.3]
            },
            "spice": {
                "avg_duration_ms": 50.2,
                "throughput_per_sec": 1992.0,
                "speedup": 5.59,
                "times": [48.5, 51.0, 51.0],
                "available": True
            }
        })
        mock_get_engine.return_value = mock_engine
        
        # Mock orbital_engine
        with patch('app.api.performance.orbital_engine') as mock_orbital:
            mock_orbital.satellite_ids = [f"SAT_{i:05d}" for i in range(100)]
            
            response = client.post(
                "/api/v1/performance/benchmark",
                params={"satellite_count": 100, "runs": 3}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["batch_size"] == 100
        assert data["runs"] == 3
        assert "sgp4" in data
        assert "spice" in data
        assert "recommendation" in data
        assert data["recommendation"]["method"] in ["sgp4", "spice"]
    
    def test_benchmark_validation(self):
        """Test benchmark parameter validation."""
        # Too many satellites
        response = client.post(
            "/api/v1/performance/benchmark",
            params={"satellite_count": 2000, "runs": 3}
        )
        assert response.status_code == 422  # Validation error
        
        # Too many runs
        response = client.post(
            "/api/v1/performance/benchmark",
            params={"satellite_count": 100, "runs": 20}
        )
        assert response.status_code == 422
    
    @patch('app.api.performance.get_async_engine')
    @patch('app.api.performance.orbital_engine')
    def test_benchmark_fewer_satellites_available(self, mock_orbital, mock_get_engine):
        """Test benchmark with fewer satellites than requested."""
        mock_orbital.satellite_ids = [f"SAT_{i:05d}" for i in range(50)]
        
        mock_engine = AsyncMock()
        mock_engine.benchmark = AsyncMock(return_value={
            "batch_size": 50,
            "runs": 3,
            "sgp4": {"avg_duration_ms": 140.0, "throughput_per_sec": 357.1},
            "spice": {"available": False}
        })
        mock_get_engine.return_value = mock_engine
        
        response = client.post(
            "/api/v1/performance/benchmark",
            params={"satellite_count": 100, "runs": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["batch_size"] == 50  # Adjusted to available


class TestLatencyHistoryEndpoint:
    """Test GET /performance/latency/history endpoint."""
    
    def test_latency_history_success(self):
        """Test latency history retrieval."""
        response = client.get(
            "/api/v1/performance/latency/history",
            params={"hours": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hours" in data
        assert "points" in data
        assert len(data["points"]) == 60  # 1 hour * 60 minutes
        
        # Check point structure
        point = data["points"][0]
        assert "timestamp" in point
        assert "latency_ms" in point
        assert "method" in point
    
    def test_latency_history_validation(self):
        """Test parameter validation."""
        # Too many hours
        response = client.get(
            "/api/v1/performance/latency/history",
            params={"hours": 48}
        )
        assert response.status_code == 422


class TestThroughputEndpoint:
    """Test GET /performance/throughput/current endpoint."""
    
    @patch('app.api.performance.get_async_engine')
    def test_throughput_with_stats(self, mock_get_engine):
        """Test throughput with available stats."""
        from app.services.async_orbital_engine import PropagationStats
        
        mock_engine = AsyncMock()
        mock_engine.get_last_stats.return_value = PropagationStats(
            method="sgp4_parallel",
            satellite_count=100,
            duration_ms=50.0,
            throughput_per_sec=2000.0,
            success_rate=0.98
        )
        mock_get_engine.return_value = mock_engine
        
        response = client.get("/api/v1/performance/throughput/current")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["throughput_per_sec"] == 2000.0
        assert data["method"] == "sgp4_parallel"
        assert data["satellite_count"] == 100
        assert data["success_rate"] == 0.98
    
    @patch('app.api.performance.get_async_engine')
    def test_throughput_no_stats(self, mock_get_engine):
        """Test throughput when no stats available."""
        mock_engine = AsyncMock()
        mock_engine.get_last_stats.return_value = None
        mock_get_engine.return_value = mock_engine
        
        response = client.get("/api/v1/performance/throughput/current")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["throughput_per_sec"] == 0
        assert data["method"] is None


class TestErrorsEndpoint:
    """Test GET /performance/errors/recent endpoint."""
    
    def test_errors_recent(self):
        """Test recent errors endpoint."""
        response = client.get(
            "/api/v1/performance/errors/recent",
            params={"limit": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "errors" in data
        assert "count" in data
        assert "limit" in data
    
    def test_errors_validation(self):
        """Test limit validation."""
        # Too high limit
        response = client.get(
            "/api/v1/performance/errors/recent",
            params={"limit": 200}
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestPerformanceEndpointsIntegration:
    """Integration tests for performance endpoints."""
    
    def test_stats_benchmark_flow(self):
        """Test stats → benchmark flow."""
        # Get current stats
        stats_response = client.get("/api/v1/performance/stats")
        assert stats_response.status_code == 200
        
        # Run benchmark (if satellites available)
        with patch('app.api.performance.orbital_engine') as mock_orbital:
            mock_orbital.satellite_ids = [f"SAT_{i:05d}" for i in range(100)]
            
            with patch('app.api.performance.get_async_engine') as mock_get_engine:
                mock_engine = AsyncMock()
                mock_engine.benchmark = AsyncMock(return_value={
                    "batch_size": 100,
                    "runs": 1,
                    "sgp4": {"avg_duration_ms": 100.0, "throughput_per_sec": 1000.0},
                    "spice": {"available": False}
                })
                mock_get_engine.return_value = mock_engine
                
                benchmark_response = client.post(
                    "/api/v1/performance/benchmark",
                    params={"satellite_count": 100, "runs": 1}
                )
                assert benchmark_response.status_code == 200
        
        # Get stats after benchmark
        stats_after = client.get("/api/v1/performance/stats")
        assert stats_after.status_code == 200
