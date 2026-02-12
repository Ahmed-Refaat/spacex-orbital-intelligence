"""
Request ID middleware for distributed tracing.

Adds unique request ID to every request:
- Generates UUID for each request
- Propagates through logs (via structlog context)
- Returns in response headers (X-Request-ID)
- Enables request tracking across services

Standards: Production observability best practices
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to every request.
    
    Features:
    - UUID generation for each request
    - Context propagation through logs
    - Response header injection
    - Existing X-Request-ID header preservation
    
    Usage:
        app.add_middleware(RequestIDMiddleware)
    
    Headers:
        X-Request-ID: Request ID (generated or from client)
        X-Correlation-ID: Same as X-Request-ID (for compatibility)
    """
    
    REQUEST_ID_HEADER = "X-Request-ID"
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with request ID.
        
        Flow:
        1. Check for existing X-Request-ID header (client-provided)
        2. Generate new UUID if not present
        3. Store in request.state for access in route handlers
        4. Bind to structlog context (appears in all logs)
        5. Add to response headers
        """
        # Get or generate request ID
        request_id = request.headers.get(self.REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Bind to structlog context for automatic inclusion in logs
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )
        
        try:
            # Log request start
            logger.info(
                "Request started",
                client=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
            # Process request
            try:
                response: Response = await call_next(request)
                
                # Log request complete
                logger.info(
                    "Request completed",
                    status_code=response.status_code
                )
                
            except Exception as e:
                # Log errors with request context
                logger.error(
                    "Request failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
            
            # Add request ID to response headers
            response.headers[self.REQUEST_ID_HEADER] = request_id
            response.headers[self.CORRELATION_ID_HEADER] = request_id
            
            return response
        finally:
            # Clean up contextvars
            structlog.contextvars.clear_contextvars()


def get_request_id(request: Request) -> str:
    """
    Get request ID from current request.
    
    Usage in route handlers:
        @app.get("/api/example")
        async def example(request: Request):
            request_id = get_request_id(request)
            logger.info("Processing", request_id=request_id)
    
    Args:
        request: FastAPI/Starlette Request object
    
    Returns:
        Request ID string (UUID)
    """
    return getattr(request.state, "request_id", "unknown")
