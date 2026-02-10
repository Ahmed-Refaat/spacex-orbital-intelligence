"""
Test Request ID middleware for distributed tracing.

Observability: Request IDs enable request tracking across services.

Standards: Production observability best practices
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.middleware.request_id import RequestIDMiddleware, get_request_id
import uuid


@pytest.fixture
def app():
    """Create test app with Request ID middleware."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"request_id": get_request_id(request)}
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_generates_request_id(client):
    """Request ID must be generated for every request."""
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers
    
    # Should be valid UUID
    request_id = response.headers["X-Request-ID"]
    uuid.UUID(request_id)  # Raises ValueError if invalid


def test_preserves_client_request_id(client):
    """Client-provided X-Request-ID must be preserved."""
    client_request_id = str(uuid.uuid4())
    
    response = client.get(
        "/test",
        headers={"X-Request-ID": client_request_id}
    )
    
    assert response.headers["X-Request-ID"] == client_request_id


def test_request_id_in_response_body(client):
    """Request ID must be accessible in route handlers."""
    response = client.get("/test")
    
    body_request_id = response.json()["request_id"]
    header_request_id = response.headers["X-Request-ID"]
    
    assert body_request_id == header_request_id


def test_request_id_persists_through_errors(client):
    """Request ID must be added to response even when errors occur."""
    response = client.get("/error")
    
    # Even though endpoint raised error, header should be present
    assert "X-Request-ID" in response.headers


def test_correlation_id_matches_request_id(client):
    """X-Correlation-ID must match X-Request-ID."""
    response = client.get("/test")
    
    assert response.headers["X-Request-ID"] == response.headers["X-Correlation-ID"]


def test_unique_request_ids_for_concurrent_requests(client):
    """Each request must get a unique ID."""
    responses = [client.get("/test") for _ in range(10)]
    
    request_ids = [r.headers["X-Request-ID"] for r in responses]
    
    # All must be unique
    assert len(request_ids) == len(set(request_ids))


def test_get_request_id_helper():
    """get_request_id() helper function must work."""
    from starlette.requests import Request as StarletteRequest
    from starlette.datastructures import State
    
    # Mock request with request_id
    class MockRequest:
        state = State()
    
    request = MockRequest()
    request.state.request_id = "test-123"
    
    assert get_request_id(request) == "test-123"


def test_get_request_id_fallback():
    """get_request_id() must return 'unknown' if no ID present."""
    class MockRequest:
        state = State()
    
    request = MockRequest()
    
    assert get_request_id(request) == "unknown"
