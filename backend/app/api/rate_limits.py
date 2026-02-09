"""
Rate Limiting Monitoring API

Provides visibility into API usage and rate limiting status.
"""
from fastapi import APIRouter
import structlog

from app.core.rate_limiter import spice_rate_limiter

logger = structlog.get_logger()

router = APIRouter(prefix="/rate-limits", tags=["Rate Limits"])


@router.get("/spice")
async def get_spice_rate_limits():
    """
    Get current SPICE API rate limiting status.
    
    Shows:
    - Health check usage (max 1 per 30s)
    - OMM upload usage (max 5 per minute)
    - Propagation usage (max 100 per minute)
    
    **Use case:** Monitoring, debugging rate limit errors
    
    **Returns:**
    - can_call_now: Whether API call is allowed
    - calls_last_minute: Number of recent calls
    - cache_remaining_sec: Seconds until cache expires
    """
    stats = spice_rate_limiter.get_all_stats()
    
    return {
        "service": "SPICE API",
        "limits": stats,
        "notes": {
            "health_check": "Cached for 30s to avoid excessive polling",
            "omm_load": "Limited to 5/min to prevent API abuse",
            "propagate": "Limited to 100/min for batch operations"
        },
        "recommendations": {
            "health_check": "Use cached results from /performance/stats",
            "omm_load": "Upload once, query multiple times",
            "propagate": "Use batch operations (≥50 sats) for efficiency"
        }
    }


@router.get("/status")
async def get_overall_status():
    """
    Get overall rate limiting health status.
    
    **Returns:**
    - status: "ok" or "throttled"
    - throttled_apis: List of rate-limited APIs
    """
    stats = spice_rate_limiter.get_all_stats()
    
    throttled = []
    for name, limiter_stats in stats.items():
        if not limiter_stats["can_call_now"]:
            throttled.append({
                "api": name,
                "reason": "rate_limited" if limiter_stats["calls_last_minute"] >= limiter_stats["max_calls_per_minute"] else "cached",
                "retry_after_sec": limiter_stats.get("cache_remaining_sec", 0)
            })
    
    return {
        "status": "ok" if not throttled else "throttled",
        "throttled_count": len(throttled),
        "throttled_apis": throttled,
        "total_apis_monitored": len(stats)
    }
