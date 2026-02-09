"""
Test suite for ANISE client - TDD approach.

Following TDD:
1. RED: Write failing test
2. GREEN: Minimal implementation
3. REFACTOR: Clean up

Test Priority:
- P0: Frame transforms (TEME → ITRF)
- P1: TCA calculation
- P2: Ground passes
- P3: Eclipse detection
"""
import pytest
from datetime import datetime, timezone
from dataclasses import dataclass
import numpy as np


@dataclass
class StateVector:
    """Satellite state vector (position + velocity)."""
    x: float  # km
    y: float  # km
    z: float  # km
    vx: float  # km/s
    vy: float  # km/s
    vz: float  # km/s
    epoch: datetime
    frame: str  # "TEME", "ITRF93", "J2000", etc.


@dataclass
class TCAResult:
    """Time of Closest Approach result."""
    tca_time: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    computation_time_ms: float


# ============================================================================
# Test Suite: AniseClient Foundation
# ============================================================================

class TestAniseClientInit:
    """Test ANISE client initialization and kernel loading."""
    
    def test_client_init_without_kernels(self):
        """RED: Client should initialize but warn about missing kernels."""
        from app.services.anise_client import AniseClient
        
        # This should work but log warning
        client = AniseClient(kernel_path="./kernels")
        assert client is not None
        assert not client.is_ready()  # No kernels loaded yet
    
    def test_client_loads_kernels_when_available(self):
        """GREEN: Client should load kernels if present."""
        from app.services.anise_client import AniseClient
        
        # Will implement kernel auto-download later
        client = AniseClient(kernel_path="./kernels")
        
        # For now, just check it doesn't crash
        assert client.kernel_path == "./kernels"


class TestFrameTransforms:
    """Test frame transformations (TEME → ITRF, etc.)."""
    
    @pytest.fixture
    def sample_state_teme(self):
        """Sample satellite state in TEME frame."""
        return StateVector(
            x=6800.0,  # km
            y=1200.0,
            z=3400.0,
            vx=2.5,  # km/s
            vy=-5.2,
            vz=3.1,
            epoch=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            frame="TEME"
        )
    
    def test_transform_teme_to_itrf_basic(self, sample_state_teme):
        """RED: Transform TEME → ITRF93 frame."""
        from app.services.anise_client import AniseClient
        
        client = AniseClient(kernel_path="./kernels")
        
        # This will fail initially - no implementation yet
        result = client.transform_frame(
            state=sample_state_teme,
            target_frame="ITRF93"
        )
        
        # Check result is StateVector
        assert isinstance(result, StateVector)
        assert result.frame == "ITRF93"
        
        # Position should be different (rotation applied)
        assert result.x != sample_state_teme.x
        assert result.y != sample_state_teme.y
        assert result.z != sample_state_teme.z
        
        # Magnitude should be preserved (rigid body transform)
        original_mag = np.sqrt(
            sample_state_teme.x**2 + 
            sample_state_teme.y**2 + 
            sample_state_teme.z**2
        )
        result_mag = np.sqrt(
            result.x**2 + result.y**2 + result.z**2
        )
        assert abs(original_mag - result_mag) < 0.001  # <1m precision
    
    def test_transform_preserves_epoch(self, sample_state_teme):
        """Epoch should remain unchanged during transform."""
        from app.services.anise_client import AniseClient
        
        client = AniseClient(kernel_path="./kernels")
        result = client.transform_frame(sample_state_teme, "ITRF93")
        
        assert result.epoch == sample_state_teme.epoch
    
    def test_transform_invalid_frame_raises_error(self, sample_state_teme):
        """Should raise ValueError for unknown frames."""
        from app.services.anise_client import AniseClient, AniseFrameError
        
        client = AniseClient(kernel_path="./kernels")
        
        with pytest.raises(AniseFrameError, match="Unknown frame: INVALID"):
            client.transform_frame(sample_state_teme, "INVALID")


class TestTCACalculation:
    """Test Time of Closest Approach (conjunction analysis)."""
    
    @pytest.fixture
    def state1(self):
        """First satellite state."""
        return StateVector(
            x=6800.0, y=0.0, z=0.0,
            vx=0.0, vy=7.5, vz=0.0,
            epoch=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            frame="J2000"
        )
    
    @pytest.fixture
    def state2(self):
        """Second satellite state (close pass)."""
        return StateVector(
            x=6802.0, y=10.0, z=5.0,  # 12km away initially
            vx=0.0, vy=7.48, vz=0.0,  # Slightly slower
            epoch=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            frame="J2000"
        )
    
    def test_calculate_tca_basic(self, state1, state2):
        """RED: Calculate TCA between two satellites."""
        from app.services.anise_client import AniseClient
        
        client = AniseClient(kernel_path="./kernels")
        
        tca = client.calculate_tca(
            state1=state1,
            state2=state2,
            time_window_hours=24
        )
        
        assert isinstance(tca, TCAResult)
        assert tca.miss_distance_km > 0
        assert tca.miss_distance_km < 100  # Should be close
        assert tca.tca_time >= state1.epoch
        assert tca.computation_time_ms > 0
    
    def test_tca_identical_orbits_returns_zero(self, state1):
        """TCA of satellite with itself should be 0km."""
        from app.services.anise_client import AniseClient
        
        client = AniseClient(kernel_path="./kernels")
        
        tca = client.calculate_tca(state1, state1, time_window_hours=24)
        
        assert tca.miss_distance_km < 0.001  # Numerical precision


class TestPerformance:
    """Performance benchmarks (ANISE vs Python baseline)."""
    
    def test_transform_performance(self, benchmark, sample_state_teme):
        """Benchmark frame transform performance."""
        from app.services.anise_client import AniseClient
        
        client = AniseClient(kernel_path="./kernels")
        
        # Benchmark: should be <1ms
        result = benchmark(
            client.transform_frame,
            sample_state_teme,
            "ITRF93"
        )
        
        # Verify result is correct
        assert result.frame == "ITRF93"
    
    @pytest.fixture
    def sample_state_teme(self):
        """Sample state for benchmarking."""
        return StateVector(
            x=6800.0, y=1200.0, z=3400.0,
            vx=2.5, vy=-5.2, vz=3.1,
            epoch=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            frame="TEME"
        )


# ============================================================================
# Test Configuration
# ============================================================================

@pytest.fixture(scope="session")
def ensure_kernels_downloaded():
    """Download kernels before running tests."""
    import os
    from pathlib import Path
    
    kernel_dir = Path(__file__).parent.parent.parent / "kernels"
    kernel_dir.mkdir(exist_ok=True)
    
    # Check if kernels exist
    required_kernels = [
        "de440s.bsp",
        "pck08.pca",
    ]
    
    for kernel in required_kernels:
        kernel_path = kernel_dir / kernel
        if not kernel_path.exists():
            pytest.skip(f"Kernel {kernel} not found. Run: make download-kernels")
    
    return kernel_dir


# Mark all tests to use kernel fixture
pytestmark = pytest.mark.usefixtures("ensure_kernels_downloaded")
