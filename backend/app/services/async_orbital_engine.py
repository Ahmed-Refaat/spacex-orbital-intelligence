"""Async orbital propagation engine with SPICE + SGP4 hybrid routing."""
import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass

import structlog

from .orbital_engine import OrbitalEngine, SatellitePosition
from .spice_client import SpiceClient, SpiceServiceUnavailable

logger = structlog.get_logger(__name__)

# Performance thresholds
BATCH_SIZE_THRESHOLD = 50  # Use SPICE for batch >= 50
MAX_WORKERS = 8  # ThreadPoolExecutor workers for SGP4


@dataclass
class PropagationStats:
    """Statistics for a propagation operation."""
    
    method: str  # "spice_batch", "spice_single", "sgp4_single", "sgp4_parallel"
    satellite_count: int
    duration_ms: float
    throughput_per_sec: float
    success_rate: float
    
    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "satellite_count": self.satellite_count,
            "duration_ms": round(self.duration_ms, 2),
            "throughput_per_sec": round(self.throughput_per_sec, 1),
            "success_rate": round(self.success_rate, 3)
        }


class AsyncOrbitalEngine:
    """Async orbital engine with intelligent routing (SPICE vs SGP4)."""
    
    def __init__(
        self,
        orbital_engine: OrbitalEngine,
        spice_client: Optional[SpiceClient] = None,
        spice_url: str = "http://spice:3000"
    ):
        """
        Initialize async orbital engine.
        
        Args:
            orbital_engine: Existing OrbitalEngine (SGP4)
            spice_client: Optional SpiceClient instance
            spice_url: SPICE service URL
        """
        self.orbital_engine = orbital_engine
        self.spice_client = spice_client or SpiceClient(base_url=spice_url)
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        
        # Performance tracking
        self._last_stats: Optional[PropagationStats] = None
        
        logger.info(
            "async_orbital_engine_initialized",
            spice_url=spice_url,
            max_workers=MAX_WORKERS,
            batch_threshold=BATCH_SIZE_THRESHOLD
        )
    
    async def health_check(self) -> dict:
        """Check health of both engines."""
        spice_available = await self.spice_client.health_check()
        
        return {
            "spice": {
                "available": spice_available,
                "url": self.spice_client.base_url
            },
            "sgp4": {
                "available": True,
                "satellite_count": self.orbital_engine.satellite_count
            },
            "routing": {
                "batch_threshold": BATCH_SIZE_THRESHOLD,
                "strategy": "spice_batch_sgp4_fallback"
            }
        }
    
    async def propagate_single(
        self,
        satellite_id: str,
        dt: Optional[datetime] = None,
        include_covariance: bool = False
    ) -> Optional[SatellitePosition]:
        """
        Propagate single satellite (always use SGP4 - faster for single).
        
        Args:
            satellite_id: Satellite ID
            dt: Target datetime (default: now)
            include_covariance: Include uncertainty (requires OMM via SPICE)
        
        Returns:
            SatellitePosition or None
        """
        start_time = asyncio.get_event_loop().time()
        
        # For single satellite, SGP4 is faster (no HTTP overhead)
        loop = asyncio.get_event_loop()
        position = await loop.run_in_executor(
            self.executor,
            self.orbital_engine.propagate,
            satellite_id,
            dt
        )
        
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Track stats
        self._last_stats = PropagationStats(
            method="sgp4_single",
            satellite_count=1,
            duration_ms=duration_ms,
            throughput_per_sec=1000 / duration_ms if duration_ms > 0 else 0,
            success_rate=1.0 if position else 0.0
        )
        
        logger.debug(
            "propagate_single",
            satellite_id=satellite_id,
            method="sgp4",
            duration_ms=round(duration_ms, 2),
            success=position is not None
        )
        
        return position
    
    async def propagate_batch(
        self,
        satellite_ids: List[str],
        dt: Optional[datetime] = None,
        include_covariance: bool = False
    ) -> List[Optional[SatellitePosition]]:
        """
        Propagate multiple satellites with intelligent routing.
        
        Strategy:
        - Batch >= 50: Try SPICE, fallback to SGP4 parallel
        - Batch < 50: SGP4 parallel (faster)
        
        Args:
            satellite_ids: List of satellite IDs
            dt: Target datetime (default: now)
            include_covariance: Include uncertainty
        
        Returns:
            List of SatellitePosition (None for failures)
        """
        if not satellite_ids:
            return []
        
        start_time = asyncio.get_event_loop().time()
        batch_size = len(satellite_ids)
        
        # Decision: SPICE or SGP4?
        use_spice = (
            batch_size >= BATCH_SIZE_THRESHOLD and
            self.spice_client.available
        )
        
        if use_spice:
            logger.info(
                "propagate_batch_spice",
                satellite_count=batch_size,
                threshold=BATCH_SIZE_THRESHOLD
            )
            positions = await self._propagate_via_spice(
                satellite_ids, dt, include_covariance
            )
            method = "spice_batch"
        else:
            logger.info(
                "propagate_batch_sgp4",
                satellite_count=batch_size,
                reason="below_threshold" if batch_size < BATCH_SIZE_THRESHOLD else "spice_unavailable"
            )
            positions = await self._propagate_via_sgp4_parallel(
                satellite_ids, dt
            )
            method = "sgp4_parallel"
        
        # Calculate stats
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        success_count = sum(1 for p in positions if p is not None)
        
        self._last_stats = PropagationStats(
            method=method,
            satellite_count=batch_size,
            duration_ms=duration_ms,
            throughput_per_sec=(batch_size * 1000 / duration_ms) if duration_ms > 0 else 0,
            success_rate=success_count / batch_size if batch_size > 0 else 0
        )
        
        logger.info(
            "propagate_batch_complete",
            method=method,
            satellite_count=batch_size,
            success_count=success_count,
            duration_ms=round(duration_ms, 2),
            throughput_per_sec=round(self._last_stats.throughput_per_sec, 1)
        )
        
        return positions
    
    async def _propagate_via_spice(
        self,
        satellite_ids: List[str],
        dt: Optional[datetime],
        include_covariance: bool
    ) -> List[Optional[SatellitePosition]]:
        """Propagate via SPICE API (batch mode)."""
        try:
            # For now, SPICE requires OMM-loaded satellites
            # Fallback to SGP4 if not loaded via OMM
            logger.warning(
                "spice_batch_not_implemented",
                reason="omm_only_currently",
                fallback="sgp4"
            )
            return await self._propagate_via_sgp4_parallel(satellite_ids, dt)
        
        except SpiceServiceUnavailable:
            logger.warning(
                "spice_unavailable",
                fallback="sgp4",
                satellite_count=len(satellite_ids)
            )
            return await self._propagate_via_sgp4_parallel(satellite_ids, dt)
    
    async def _propagate_via_sgp4_parallel(
        self,
        satellite_ids: List[str],
        dt: Optional[datetime]
    ) -> List[Optional[SatellitePosition]]:
        """Propagate via SGP4 in parallel using ThreadPoolExecutor."""
        loop = asyncio.get_event_loop()
        
        # Create tasks for parallel execution
        tasks = [
            loop.run_in_executor(
                self.executor,
                self.orbital_engine.propagate,
                sat_id,
                dt
            )
            for sat_id in satellite_ids
        ]
        
        # Execute in parallel
        positions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions (return None for failures)
        result = []
        for i, pos in enumerate(positions):
            if isinstance(pos, Exception):
                logger.error(
                    "sgp4_propagate_error",
                    satellite_id=satellite_ids[i],
                    error=str(pos)
                )
                result.append(None)
            else:
                result.append(pos)
        
        return result
    
    async def propagate_orbit_async(
        self,
        satellite_id: str,
        hours: int = 24,
        step_minutes: int = 5
    ) -> List[SatellitePosition]:
        """
        Generate orbital path asynchronously.
        
        Args:
            satellite_id: Satellite ID
            hours: Hours to propagate
            step_minutes: Step size in minutes
        
        Returns:
            List of positions
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self.orbital_engine.propagate_orbit,
            satellite_id,
            hours,
            step_minutes
        )
    
    async def calculate_risk_async(
        self,
        sat_id_1: str,
        sat_id_2: str,
        hours_ahead: int = 24
    ):
        """Calculate collision risk asynchronously."""
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self.orbital_engine.calculate_risk_score,
            sat_id_1,
            sat_id_2,
            hours_ahead
        )
    
    def get_last_stats(self) -> Optional[PropagationStats]:
        """Get statistics from last propagation."""
        return self._last_stats
    
    async def benchmark(
        self,
        satellite_ids: List[str],
        runs: int = 3
    ) -> dict:
        """
        Benchmark both methods for comparison.
        
        Args:
            satellite_ids: Satellites to test
            runs: Number of runs per method
        
        Returns:
            Benchmark results
        """
        batch_size = len(satellite_ids)
        
        # Benchmark SGP4 parallel
        sgp4_times = []
        for _ in range(runs):
            start = asyncio.get_event_loop().time()
            await self._propagate_via_sgp4_parallel(satellite_ids, None)
            duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            sgp4_times.append(duration_ms)
        
        sgp4_avg = sum(sgp4_times) / len(sgp4_times)
        sgp4_throughput = (batch_size * 1000) / sgp4_avg
        
        # Benchmark SPICE (if available)
        spice_avg = None
        spice_throughput = None
        spice_speedup = None
        
        if self.spice_client.available:
            spice_times = []
            for _ in range(runs):
                start = asyncio.get_event_loop().time()
                await self._propagate_via_spice(satellite_ids, None, False)
                duration_ms = (asyncio.get_event_loop().time() - start) * 1000
                spice_times.append(duration_ms)
            
            spice_avg = sum(spice_times) / len(spice_times)
            spice_throughput = (batch_size * 1000) / spice_avg
            spice_speedup = sgp4_avg / spice_avg
        
        return {
            "batch_size": batch_size,
            "runs": runs,
            "sgp4": {
                "avg_duration_ms": round(sgp4_avg, 2),
                "throughput_per_sec": round(sgp4_throughput, 1),
                "times": [round(t, 2) for t in sgp4_times]
            },
            "spice": {
                "avg_duration_ms": round(spice_avg, 2) if spice_avg else None,
                "throughput_per_sec": round(spice_throughput, 1) if spice_throughput else None,
                "speedup": round(spice_speedup, 2) if spice_speedup else None,
                "times": [round(t, 2) for t in spice_times] if spice_avg else None,
                "available": self.spice_client.available
            }
        }
    
    async def shutdown(self):
        """Shutdown executor and close connections."""
        logger.info("async_orbital_engine_shutdown")
        self.executor.shutdown(wait=True)
        await self.spice_client.close()


# Singleton instance (initialized in main.py)
async_orbital_engine: Optional[AsyncOrbitalEngine] = None


def get_async_engine() -> AsyncOrbitalEngine:
    """Get the global async engine instance."""
    if async_orbital_engine is None:
        raise RuntimeError("AsyncOrbitalEngine not initialized")
    return async_orbital_engine
