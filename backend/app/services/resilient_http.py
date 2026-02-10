"""
Resilient HTTP client with circuit breaker and retry logic.

Provides production-grade robustness for external API calls:
- Circuit breaker pattern
- Exponential backoff retry
- Timeout enforcement
- Structured error logging
"""
import httpx
import asyncio
from typing import Any, Callable, Optional
from functools import wraps
import structlog

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

logger = structlog.get_logger()


class ResilientHTTPClient:
    """
    HTTP client wrapper with circuit breaker and retry logic.
    
    Usage:
        client = ResilientHTTPClient(
            name="spice",
            base_url="http://spice:3000",
            timeout=30.0,
            circuit_breaker=spice_circuit_breaker
        )
        
        response = await client.get("/health")
    """
    
    def __init__(
        self,
        name: str,
        base_url: str,
        timeout: float = 30.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        max_retries: int = 3,
        retry_on_status: tuple[int, ...] = (500, 502, 503, 504)
    ):
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(httpx.HTTPError, httpx.TimeoutException)
        )
        self.max_retries = max_retries
        self.retry_on_status = retry_on_status
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _should_retry(self, response: httpx.Response, attempt: int) -> bool:
        """Check if should retry based on response."""
        if attempt >= self.max_retries:
            return False
        
        # Retry on specific status codes
        if response.status_code in self.retry_on_status:
            return True
        
        return False
    
    def _get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.
        
        Formula: min(base * 2^attempt + jitter, max_delay)
        """
        import random
        
        base = 1.0  # Base delay in seconds
        max_delay = 30.0  # Max delay
        
        delay = min(base * (2 ** attempt), max_delay)
        
        # Add jitter (±25%)
        jitter = delay * 0.25 * random.uniform(-1, 1)
        
        return delay + jitter
    
    async def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with circuit breaker and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            httpx.HTTPError: On request failure after retries
        """
        client = await self._get_client()
        
        # Wrapper function for circuit breaker
        async def _execute():
            attempt = 0
            last_exception = None
            
            while attempt < self.max_retries:
                try:
                    logger.debug(
                        "HTTP request",
                        service=self.name,
                        method=method,
                        path=path,
                        attempt=attempt + 1,
                        max_retries=self.max_retries
                    )
                    
                    response = await client.request(method, path, **kwargs)
                    
                    # Check if should retry
                    if await self._should_retry(response, attempt):
                        delay = self._get_backoff_delay(attempt)
                        
                        logger.warning(
                            "HTTP request failed, retrying",
                            service=self.name,
                            method=method,
                            path=path,
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            retry_delay_seconds=round(delay, 2)
                        )
                        
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                    
                    # Success or non-retryable error
                    response.raise_for_status()
                    
                    logger.debug(
                        "HTTP request successful",
                        service=self.name,
                        method=method,
                        path=path,
                        status_code=response.status_code
                    )
                    
                    return response
                
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    # Network errors - always retry
                    last_exception = e
                    delay = self._get_backoff_delay(attempt)
                    
                    logger.warning(
                        "Network error, retrying",
                        service=self.name,
                        method=method,
                        path=path,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                        retry_delay_seconds=round(delay, 2)
                    )
                    
                    await asyncio.sleep(delay)
                    attempt += 1
                
                except httpx.HTTPError as e:
                    # Other HTTP errors - don't retry
                    logger.error(
                        "HTTP error",
                        service=self.name,
                        method=method,
                        path=path,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    raise
            
            # Max retries exhausted
            error_msg = f"Max retries ({self.max_retries}) exhausted"
            if last_exception:
                logger.error(
                    error_msg,
                    service=self.name,
                    method=method,
                    path=path,
                    last_error=str(last_exception)
                )
                raise last_exception
            else:
                raise httpx.HTTPError(error_msg)
        
        # Execute through circuit breaker
        try:
            return await self.circuit_breaker.call(_execute)
        except CircuitBreakerOpen as e:
            logger.error(
                "Circuit breaker is OPEN",
                service=self.name,
                method=method,
                path=path,
                error=str(e)
            )
            raise
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Execute GET request."""
        return await self.request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Execute POST request."""
        return await self.request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """Execute PUT request."""
        return await self.request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Execute DELETE request."""
        return await self.request("DELETE", path, **kwargs)


# Pre-configured clients for common services
from app.core.circuit_breaker import (
    spice_circuit_breaker,
    spacex_api_circuit_breaker,
    launch_library_circuit_breaker,
    celestrak_circuit_breaker
)

def create_spice_client(base_url: str) -> ResilientHTTPClient:
    """Create resilient SPICE service client."""
    return ResilientHTTPClient(
        name="spice",
        base_url=base_url,
        timeout=30.0,
        circuit_breaker=spice_circuit_breaker,
        max_retries=3,
        retry_on_status=(500, 502, 503, 504)
    )

def create_spacex_api_client(base_url: str) -> ResilientHTTPClient:
    """Create resilient SpaceX API client."""
    return ResilientHTTPClient(
        name="spacex_api",
        base_url=base_url,
        timeout=30.0,
        circuit_breaker=spacex_api_circuit_breaker,
        max_retries=3,
        retry_on_status=(500, 502, 503, 504, 429)  # Include rate limit
    )

def create_launch_library_client() -> ResilientHTTPClient:
    """Create resilient Launch Library API client."""
    return ResilientHTTPClient(
        name="launch_library",
        base_url="https://ll.thespacedevs.com/2.2.0",
        timeout=15.0,
        circuit_breaker=launch_library_circuit_breaker,
        max_retries=2,  # Public API - be gentle
        retry_on_status=(500, 502, 503, 504, 429)
    )
