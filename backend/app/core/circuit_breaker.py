"""
Circuit breaker implementation for external service calls.

Prevents cascade failures by temporarily blocking calls to failing services.
"""
from typing import Callable, Any, Type
from datetime import datetime, timedelta
import asyncio
import httpx
from functools import wraps


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service is failing, calls are blocked immediately
    - HALF_OPEN: Testing if service recovered
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds before attempting recovery (half-open)
        expected_exception: Exception type(s) that trigger the circuit
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] | tuple[Type[Exception], ...] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> str:
        """Get current circuit state."""
        return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._state != "OPEN":
            return False
        
        if not self._last_failure_time:
            return False
        
        elapsed = datetime.now() - self._last_failure_time
        return elapsed >= self.recovery_timeout
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Raises:
            CircuitBreakerOpen: If circuit is open and recovery timeout not reached
        """
        async with self._lock:
            # Check if should attempt reset
            if self._should_attempt_reset():
                self._state = "HALF_OPEN"
                self._failure_count = 0
            
            # If open and not ready to retry, fail fast
            if self._state == "OPEN":
                raise CircuitBreakerOpen(
                    f"Circuit breaker is OPEN. "
                    f"Will retry after {self.recovery_timeout.total_seconds()}s"
                )
        
        # Try to execute
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset if we were in half-open
            async with self._lock:
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                    self._failure_count = 0
            
            return result
        
        except self.expected_exception as e:
            # Expected failure - update state
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = datetime.now()
                
                if self._failure_count >= self.failure_threshold:
                    self._state = "OPEN"
                elif self._state == "HALF_OPEN":
                    # Failed during recovery attempt
                    self._state = "OPEN"
            
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        
        return wrapper


# Pre-configured circuit breakers for common services
spice_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError)
)

spacex_api_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError)
)

launch_library_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=120,
    expected_exception=(httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError)
)

celestrak_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=300,  # 5 minutes for public service
    expected_exception=(httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError)
)
