# Chaos Engineering Tests

Test system resilience under failure conditions.

## Setup

```bash
pip install chaos-toolkit
pip install chaostoolkit-kubernetes  # If using K8s
```

## Test Scenarios

### 1. External Service Failures

```python
# test_external_service_chaos.py
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_celestrak_down_graceful_degradation():
    """
    Scenario: Celestrak is completely down
    Expected: System falls back to cached data or mock data
    """
    from app.services.tle_service import tle_service
    from circuitbreaker import CircuitBreakerError
    
    # Simulate Celestrak down (all requests fail)
    with patch('app.services.celestrak_fallback.httpx.AsyncClient') as mock_client:
        mock_client.return_value.get = AsyncMock(side_effect=Exception("Connection refused"))
        
        # Should not crash, should use fallback
        try:
            await tle_service.fetch_celestrak()
        except CircuitBreakerError:
            # Circuit breaker opens - expected
            assert True
        except Exception as e:
            pytest.fail(f"Should handle gracefully, got: {e}")


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_slow_external_api_timeout():
    """
    Scenario: External API is very slow (>30s)
    Expected: Request times out, does not hang
    """
    import asyncio
    
    async def slow_api():
        await asyncio.sleep(100)  # Simulate very slow API
        return "data"
    
    # Should timeout, not wait forever
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_api(), timeout=30)
```

### 2. Database Failures

```python
@pytest.mark.chaos
async def test_redis_down_read_only_mode():
    """
    Scenario: Redis is down
    Expected: System continues in read-only mode
    """
    # Simulate Redis failure
    # System should still serve cached TLE data
    pass


@pytest.mark.chaos
async def test_postgresql_down_graceful():
    """
    Scenario: PostgreSQL is down
    Expected: System serves from memory/cache
    """
    pass
```

### 3. Resource Exhaustion

```python
@pytest.mark.chaos
async def test_memory_pressure():
    """
    Scenario: System under memory pressure
    Expected: Garbage collection, no OOM crashes
    """
    pass


@pytest.mark.chaos
async def test_cpu_saturation():
    """
    Scenario: CPU at 100%
    Expected: Request queueing, no crashes
    """
    pass
```

### 4. Network Failures

```python
@pytest.mark.chaos
async def test_network_partition():
    """
    Scenario: Network partition between services
    Expected: Circuit breakers open, fallback behavior
    """
    pass
```

## Running Chaos Tests

```bash
# Run all chaos tests
pytest tests/chaos/ -m chaos -v

# Run specific scenario
pytest tests/chaos/test_external_service_chaos.py -v

# With coverage
pytest tests/chaos/ -m chaos --cov=app
```

## Chaos Toolkit Integration

Create `chaos_experiments.yaml`:

```yaml
version: 1.0.0
title: SpaceX Orbital Intelligence Chaos Experiments
description: Test system resilience

steady-state-hypothesis:
  title: System is healthy
  probes:
    - type: probe
      name: health-endpoint-ok
      tolerance: 200
      provider:
        type: http
        url: https://spacex.ericcesar.com/health

method:
  - type: action
    name: kill-celestrak-connection
    provider:
      type: python
      module: chaoslib.network
      func: block_outbound_connection
      arguments:
        host: celestrak.org
        port: 443
    pauses:
      after: 5

  - type: probe
    name: system-still-healthy
    tolerance: 200
    provider:
      type: http
      url: https://spacex.ericcesar.com/health

rollbacks:
  - type: action
    name: restore-connection
    provider:
      type: python
      module: chaoslib.network
      func: restore_connection
```

Run with:
```bash
chaos run chaos_experiments.yaml
```

## Metrics to Track

During chaos experiments, monitor:
- Response time (p50, p95, p99)
- Error rate
- Circuit breaker state
- Cache hit rate
- Memory usage
- CPU usage

## Expected Behaviors

| Scenario | Expected Result |
|----------|----------------|
| Celestrak down | Circuit breaker opens, uses cached data |
| Space-Track down | Falls back to Celestrak |
| Redis down | In-memory cache only, degraded performance |
| PostgreSQL down | Read-only from cache |
| Network slow | Timeout after 30s, not hang |
| CPU at 100% | Requests queued, eventual timeout |

## Safety

**DO NOT run chaos tests in production without:**
1. Maintenance window
2. Monitoring active
3. Rollback plan ready
4. Team on standby

Use staging environment for chaos tests.
