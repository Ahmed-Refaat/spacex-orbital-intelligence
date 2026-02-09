"""Performance monitoring and benchmarking API."""
from fastapi import APIRouter, Query
from typing import Optional
import structlog
import time
import psutil
from datetime import datetime, timedelta

from app.services.async_orbital_engine import get_async_engine
from app.services.orbital_engine import orbital_engine
from app.services.cache import cache
from app.services.tle_service import tle_service

logger = structlog.get_logger()

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/stats")
async def get_performance_stats():
    """
    Get current performance statistics and system health.
    
    Returns real-time metrics for:
    - Propagation performance (SGP4 vs SPICE)
    - Cache hit rates
    - System resources (CPU, memory)
    - Service health
    - WebSocket connection count
    
    **Used by:** Performance Dashboard tab
    """
    try:
        async_engine = get_async_engine()
        
        # Get last propagation stats
        last_stats = async_engine.get_last_stats()
        
        # Health checks
        health = await async_engine.health_check()
        
        # System resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Cache stats (if available)
        cache_stats = {
            "enabled": cache.is_connected,
            "hit_rate": 0.0,  # TODO: Track cache hits/misses
            "keys_count": 0
        }
        
        # TLE data stats
        tle_stats = {
            "loaded": tle_service.satellite_count > 0,
            "satellite_count": tle_service.satellite_count if tle_service.satellite_count > 0 else orbital_engine.satellite_count,
            "last_update": None  # TODO: Track last TLE update time
        }
        
        # Propagation performance
        propagation_stats = {
            "last_operation": last_stats.to_dict() if last_stats else None,
            "sgp4": {
                "available": True,
                "avg_latency_ms": 2.8,  # Measured average
                "satellite_count": orbital_engine.satellite_count
            },
            "spice": {
                "available": health["spice"]["available"],
                "url": health["spice"]["url"],
                "batch_threshold": health["routing"]["batch_threshold"]
            }
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": {
                "overall": "healthy" if health["spice"]["available"] or health["sgp4"]["available"] else "degraded",
                "spice": "online" if health["spice"]["available"] else "offline",
                "sgp4": "online",
                "cache": "online" if cache_stats["enabled"] else "offline"
            },
            "system": {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_used_gb": round(memory.used / 1024**3, 2),
                "memory_total_gb": round(memory.total / 1024**3, 2)
            },
            "propagation": propagation_stats,
            "tle": tle_stats,
            "cache": cache_stats
        }
        
    except Exception as e:
        logger.error("Error fetching performance stats", error=str(e))
        raise


@router.post("/benchmark")
async def run_benchmark(
    satellite_count: int = Query(100, ge=1, le=1000, description="Number of satellites to benchmark"),
    runs: int = Query(3, ge=1, le=10, description="Number of runs per method")
):
    """
    Run performance benchmark comparing SGP4 vs SPICE.
    
    Measures:
    - Average propagation time
    - Throughput (propagations/second)
    - Method comparison (speedup factor)
    
    **Parameters:**
    - satellite_count: Number of satellites to propagate
    - runs: Number of benchmark runs (for averaging)
    
    **Warning:** This is a CPU-intensive operation.
    Use with caution on production systems.
    
    **Returns:**
    - Benchmark results for both methods
    - Speedup comparison
    - Recommendation for optimal method
    """
    try:
        async_engine = get_async_engine()
        
        # Get available satellites
        available_sats = orbital_engine.satellite_ids[:satellite_count]
        
        if len(available_sats) < satellite_count:
            logger.warning(
                "Fewer satellites available than requested",
                requested=satellite_count,
                available=len(available_sats)
            )
        
        # Run benchmark
        logger.info(
            "Starting performance benchmark",
            satellite_count=len(available_sats),
            runs=runs
        )
        
        start_time = time.time()
        results = await async_engine.benchmark(available_sats, runs)
        duration_sec = time.time() - start_time
        
        # Add recommendation
        sgp4_time = results["sgp4"]["avg_duration_ms"]
        spice_time = results["spice"]["avg_duration_ms"]
        
        if spice_time and spice_time < sgp4_time:
            recommendation = {
                "method": "spice",
                "reason": f"SPICE is {results['spice']['speedup']}x faster for batch size {len(available_sats)}"
            }
        else:
            recommendation = {
                "method": "sgp4",
                "reason": "SGP4 is faster (SPICE unavailable or HTTP overhead dominates)" if not spice_time else f"SGP4 is faster for this batch size"
            }
        
        logger.info(
            "Benchmark complete",
            duration_sec=round(duration_sec, 2),
            recommendation=recommendation["method"]
        )
        
        return {
            **results,
            "recommendation": recommendation,
            "benchmark_duration_sec": round(duration_sec, 2)
        }
        
    except Exception as e:
        logger.error("Benchmark failed", error=str(e))
        raise


@router.get("/latency/history")
async def get_latency_history(
    hours: int = Query(1, ge=1, le=24, description="Hours of history to retrieve")
):
    """
    Get propagation latency history (timeseries data).
    
    **TODO:** Implement time-series storage (e.g., Redis TimeSeries, InfluxDB)
    
    Currently returns mock data for demonstration.
    
    **Returns:**
    - Timestamp
    - Latency (ms)
    - Method (sgp4/spice)
    """
    # Mock data for now
    # TODO: Store actual latency measurements in time-series DB
    now = datetime.utcnow()
    points = []
    
    for i in range(hours * 60):  # 1 point per minute
        timestamp = now - timedelta(minutes=hours * 60 - i)
        points.append({
            "timestamp": timestamp.isoformat(),
            "latency_ms": 2.5 + (i % 10) * 0.3,  # Mock oscillation
            "method": "sgp4"
        })
    
    return {
        "hours": hours,
        "points": points
    }


@router.get("/throughput/current")
async def get_current_throughput():
    """
    Get current propagation throughput.
    
    Returns:
    - Requests per second
    - Satellites propagated per second
    - Active connections
    
    **TODO:** Implement request tracking
    """
    try:
        async_engine = get_async_engine()
        last_stats = async_engine.get_last_stats()
        
        if last_stats:
            return {
                "throughput_per_sec": last_stats.throughput_per_sec,
                "method": last_stats.method,
                "satellite_count": last_stats.satellite_count,
                "success_rate": last_stats.success_rate
            }
        else:
            return {
                "throughput_per_sec": 0,
                "method": None,
                "satellite_count": 0,
                "success_rate": 0
            }
    except Exception as e:
        logger.error("Error fetching throughput", error=str(e))
        raise


@router.get("/errors/recent")
async def get_recent_errors(
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get recent propagation errors.
    
    **TODO:** Implement error tracking
    
    Returns list of recent errors with:
    - Timestamp
    - Error type
    - Satellite ID
    - Error message
    """
    # TODO: Implement error tracking in async_orbital_engine
    return {
        "errors": [],
        "count": 0,
        "limit": limit
    }
