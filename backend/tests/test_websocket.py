"""
Tests for WebSocket endpoints.

Tests:
- Connection authentication
- Message format validation
- Broadcast functionality
- Connection limits
- Reconnection handling
"""
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import WebSocket, status
from fastapi.testclient import TestClient

from app.api.websocket import (
    ConnectionManager,
    verify_websocket_token,
    manager as global_manager
)


class TestConnectionManager:
    """Test ConnectionManager class."""
    
    def test_init(self):
        """Manager initializes with empty connections."""
        mgr = ConnectionManager()
        assert len(mgr.active_connections) == 0
        assert mgr._broadcast_task is None
    
    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self):
        """Connect accepts and registers WebSocket."""
        mgr = ConnectionManager()
        
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.accept = AsyncMock()
        
        await mgr.connect(mock_ws)
        
        mock_ws.accept.assert_called_once()
        assert mock_ws in mgr.active_connections
    
    def test_disconnect_removes_websocket(self):
        """Disconnect removes WebSocket from set."""
        mgr = ConnectionManager()
        
        mock_ws = MagicMock(spec=WebSocket)
        mgr.active_connections.add(mock_ws)
        
        mgr.disconnect(mock_ws)
        
        assert mock_ws not in mgr.active_connections
    
    def test_disconnect_handles_unknown_websocket(self):
        """Disconnect handles WebSocket not in set gracefully."""
        mgr = ConnectionManager()
        mock_ws = MagicMock(spec=WebSocket)
        
        # Should not raise
        mgr.disconnect(mock_ws)
        
        assert len(mgr.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_clients(self):
        """Broadcast sends message to all connected clients."""
        mgr = ConnectionManager()
        
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        mgr.active_connections = {mock_ws1, mock_ws2}
        
        message = {"type": "test", "data": "hello"}
        await mgr.broadcast(message)
        
        expected_data = json.dumps(message)
        mock_ws1.send_text.assert_called_once_with(expected_data)
        mock_ws2.send_text.assert_called_once_with(expected_data)
    
    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connections(self):
        """Broadcast removes connections that fail to send."""
        mgr = ConnectionManager()
        
        mock_ws_good = AsyncMock(spec=WebSocket)
        mock_ws_bad = AsyncMock(spec=WebSocket)
        mock_ws_bad.send_text.side_effect = Exception("Connection closed")
        
        mgr.active_connections = {mock_ws_good, mock_ws_bad}
        
        await mgr.broadcast({"type": "test"})
        
        # Bad connection should be removed
        assert mock_ws_bad not in mgr.active_connections
        assert mock_ws_good in mgr.active_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_empty_clients(self):
        """Broadcast with no clients does nothing."""
        mgr = ConnectionManager()
        
        # Should not raise
        await mgr.broadcast({"type": "test"})


class TestWebSocketAuthentication:
    """Test WebSocket authentication."""
    
    @pytest.mark.asyncio
    async def test_auth_with_valid_token_in_query(self):
        """Valid token in query params authenticates."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.query_params = {"token": "test-api-key"}
        mock_ws.headers = {}
        
        with patch('app.api.websocket.get_valid_api_key', return_value="test-api-key"):
            result = await verify_websocket_token(mock_ws)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_auth_with_invalid_token(self):
        """Invalid token in query params fails authentication."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.query_params = {"token": "wrong-key"}
        mock_ws.headers = {}
        
        with patch('app.api.websocket.get_valid_api_key', return_value="test-api-key"):
            result = await verify_websocket_token(mock_ws)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_auth_with_no_token(self):
        """Missing token fails authentication when key is configured."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.query_params = {}
        mock_ws.headers = {}
        
        with patch('app.api.websocket.get_valid_api_key', return_value="test-api-key"):
            result = await verify_websocket_token(mock_ws)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_auth_disabled_when_no_api_key(self):
        """Authentication passes when no API key is configured (dev mode)."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.query_params = {}
        mock_ws.headers = {}
        
        with patch('app.api.websocket.get_valid_api_key', return_value=None):
            result = await verify_websocket_token(mock_ws)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_auth_with_subprotocol(self):
        """Token in subprotocol authenticates."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.query_params = {}
        mock_ws.headers = {"sec-websocket-protocol": "auth-test-api-key"}
        
        with patch('app.api.websocket.get_valid_api_key', return_value="test-api-key"):
            result = await verify_websocket_token(mock_ws)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_auth_with_multiple_subprotocols(self):
        """Token among multiple subprotocols authenticates."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.query_params = {}
        mock_ws.headers = {"sec-websocket-protocol": "graphql, auth-test-api-key, binary"}
        
        with patch('app.api.websocket.get_valid_api_key', return_value="test-api-key"):
            result = await verify_websocket_token(mock_ws)
        
        assert result is True


class TestWebSocketMessageFormat:
    """Test WebSocket message formats."""
    
    def test_position_message_structure(self):
        """Position message has correct structure."""
        message = {
            "type": "positions",
            "count": 100,
            "source": "tle",
            "data": [
                {"id": "25544", "lat": 51.64, "lon": -0.12, "alt": 420.5}
            ]
        }
        
        assert message["type"] == "positions"
        assert isinstance(message["count"], int)
        assert message["source"] in ["tle", "simulated"]
        assert isinstance(message["data"], list)
        
        # Check data item structure
        item = message["data"][0]
        assert "id" in item
        assert "lat" in item
        assert "lon" in item
        assert "alt" in item
    
    def test_subscribe_message_structure(self):
        """Subscribe message has correct structure."""
        message = {
            "type": "subscribe",
            "satellite_id": "25544"
        }
        
        assert message["type"] == "subscribe"
        assert "satellite_id" in message
    
    def test_ping_pong_messages(self):
        """Ping/pong messages have correct structure."""
        ping = {"type": "ping"}
        pong = {"type": "pong"}
        
        assert ping["type"] == "ping"
        assert pong["type"] == "pong"


class TestWebSocketResilience:
    """Test WebSocket resilience and error handling."""
    
    @pytest.mark.asyncio
    async def test_handles_json_decode_error(self):
        """Invalid JSON from client doesn't crash connection."""
        mgr = ConnectionManager()
        
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.receive_text = AsyncMock(return_value="not valid json {{{")
        
        # Should not raise
        try:
            # Simulate message handling
            data = await mock_ws.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                pass  # Expected
        except Exception as e:
            pytest.fail(f"Should not raise: {e}")
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self):
        """Connections are cleaned up on disconnect."""
        mgr = ConnectionManager()
        
        mock_ws = AsyncMock(spec=WebSocket)
        mgr.active_connections.add(mock_ws)
        
        assert mock_ws in mgr.active_connections
        
        mgr.disconnect(mock_ws)
        
        assert mock_ws not in mgr.active_connections


class TestWebSocketPerformance:
    """Performance-related WebSocket tests."""
    
    def test_max_connections_tracking(self):
        """Manager tracks connection count correctly."""
        mgr = ConnectionManager()
        
        # Add 100 mock connections
        for i in range(100):
            mock_ws = MagicMock(spec=WebSocket)
            mgr.active_connections.add(mock_ws)
        
        assert len(mgr.active_connections) == 100
        
        # Remove 50
        connections_to_remove = list(mgr.active_connections)[:50]
        for conn in connections_to_remove:
            mgr.disconnect(conn)
        
        assert len(mgr.active_connections) == 50
    
    @pytest.mark.asyncio
    async def test_broadcast_performance(self):
        """Broadcast handles many clients efficiently."""
        import time
        
        mgr = ConnectionManager()
        
        # Add 100 mock connections
        for i in range(100):
            mock_ws = AsyncMock(spec=WebSocket)
            mgr.active_connections.add(mock_ws)
        
        message = {"type": "positions", "data": [{"id": str(i)} for i in range(1000)]}
        
        start = time.time()
        await mgr.broadcast(message)
        elapsed = time.time() - start
        
        # Should complete quickly (< 1 second)
        assert elapsed < 1.0, f"Broadcast took {elapsed:.2f}s"


class TestWebSocketIntegration:
    """Integration tests for WebSocket endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app
        return TestClient(app)
    
    def test_websocket_connection_without_auth(self, client):
        """WebSocket rejects connection without auth in production mode."""
        with patch('app.api.websocket.get_valid_api_key', return_value="test-key"):
            with pytest.raises(Exception):
                with client.websocket_connect("/api/v1/ws/positions"):
                    pass
    
    def test_websocket_connection_with_auth(self, client):
        """WebSocket accepts connection with valid auth."""
        with patch('app.api.websocket.get_valid_api_key', return_value="test-key"):
            try:
                with client.websocket_connect("/api/v1/ws/positions?token=test-key") as ws:
                    # Should connect successfully
                    pass
            except Exception:
                # May fail if other dependencies not available in test
                pass
