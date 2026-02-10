"""
Prometheus metrics for SpaceX Orbital Intelligence Platform.

Exposes metrics at /metrics endpoint for Prometheus scraping.

Key metrics:
- HTTP request duration and counts
- Satellite propagation performance
- Cache hit/miss rates
- WebSocket connections
- Error rates
"""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)
import time
from functools import wraps


# ============================================================================
# HTTP Metrics
# ============================================================================

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint']
)


# ============================================================================
# Orbital Engine Metrics
# ============================================================================

PROPAGATION_DURATION = Histogram(
    'orbital_propagation_duration_seconds',
    'Satellite propagation calculation duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

PROPAGATION_COUNT = Counter(
    'orbital_propagation_total',
    'Total satellite propagations',
    ['operation', 'success']
)

SATELLITES_LOADED = Gauge(
    'satellites_loaded',
    'Number of satellites currently loaded in orbital engine'
)

TLE_LAST_UPDATE = Gauge(
    'tle_last_update_timestamp',
    'Unix timestamp of last TLE data update'
)


# ============================================================================
# Cache Metrics
# ============================================================================

CACHE_HITS = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

CACHE_HIT_RATE = Counter(
    'cache_requests_total',
    'Cache requests by operation and result',
    ['operation', 'result']  # result: hit/miss/timeout/error/disconnected
)

CACHE_SIZE = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)


# ============================================================================
# WebSocket Metrics
# ============================================================================

WEBSOCKET_CONNECTIONS = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections'
)

WEBSOCKET_MESSAGES_SENT = Counter(
    'websocket_messages_sent_total',
    'Total WebSocket messages sent'
)

WEBSOCKET_CONNECTIONS_TOTAL = Counter(
    'websocket_connections_total',
    'Total WebSocket connection attempts',
    ['status']  # 'connected', 'rejected', 'error'
)


# ============================================================================
# Risk Analysis Metrics
# ============================================================================

RISK_CALCULATIONS = Counter(
    'risk_calculations_total',
    'Total risk calculations performed'
)

RISK_ALERTS_GENERATED = Counter(
    'risk_alerts_generated_total',
    'Total collision risk alerts generated',
    ['severity']  # 'high', 'medium', 'low'
)

CONJUNCTION_CHECKS = Counter(
    'conjunction_checks_total',
    'Total conjunction checks performed'
)


# ============================================================================
# System Metrics
# ============================================================================

APP_INFO = Info(
    'spacex_orbital_app',
    'Application information'
)

STARTUP_TIME = Gauge(
    'app_startup_timestamp',
    'Unix timestamp when the application started'
)


# ============================================================================
# Helper Functions
# ============================================================================

def record_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    HTTP_REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).observe(duration)
    
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()


def track_propagation(operation: str):
    """Decorator to track propagation timing."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                PROPAGATION_COUNT.labels(operation=operation, success='true').inc()
                return result
            except Exception as e:
                PROPAGATION_COUNT.labels(operation=operation, success='false').inc()
                raise
            finally:
                PROPAGATION_DURATION.labels(operation=operation).observe(
                    time.time() - start
                )
        return wrapper
    return decorator


def set_app_info(version: str, environment: str):
    """Set application info metrics."""
    APP_INFO.info({
        'version': version,
        'environment': environment,
        'name': 'spacex-orbital-intelligence'
    })
    STARTUP_TIME.set(time.time())


def get_metrics():
    """Generate Prometheus metrics output."""
    return generate_latest(REGISTRY)


def get_content_type():
    """Get Prometheus content type."""
    return CONTENT_TYPE_LATEST
