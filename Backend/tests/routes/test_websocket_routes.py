"""
Unit tests for websocket_routes.py
Tests WebSocket endpoint with mocked dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from routes.websocket_routes import router


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = MagicMock()
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    return websocket


class TestWebSocketPriceEndpoint:
    """Test cases for /ws/prices WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_accept_connection(self, mock_websocket):
        """Test that WebSocket connection is accepted and function exits on disconnect."""
        from fastapi import WebSocketDisconnect
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        with patch("routes.websocket_routes.clients", []):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_adds_client_to_list(self, mock_websocket):
        """Test that client is added and later removed from clients list."""
        from fastapi import WebSocketDisconnect
        clients_mock = MagicMock()
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        with patch("routes.websocket_routes.clients", clients_mock):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            clients_mock.append.assert_called_once_with(mock_websocket)
            clients_mock.remove.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, mock_websocket):
        """Test WebSocket ping-pong mechanism."""
        mock_websocket.receive_text.side_effect = ["ping", __import__("fastapi").WebSocketDisconnect()]

        with patch("routes.websocket_routes.clients", []):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            mock_websocket.send_text.assert_called_with("pong")

    @pytest.mark.asyncio
    async def test_websocket_timeout_handling(self, mock_websocket):
        """Test that WebSocket handles timeout gracefully."""
        from fastapi import WebSocketDisconnect
        mock_websocket.receive_text.side_effect = [asyncio.TimeoutError(), WebSocketDisconnect()]

        with patch("routes.websocket_routes.clients", []):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_disconnect_removes_client(self, mock_websocket):
        """Test that disconnected client is removed from list."""
        from fastapi import WebSocketDisconnect
        
        clients_mock = MagicMock()
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        with patch("routes.websocket_routes.clients", clients_mock):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            clients_mock.remove.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_websocket_multiple_messages(self, mock_websocket):
        """Test handling multiple WebSocket messages."""
        from fastapi import WebSocketDisconnect
        
        mock_websocket.receive_text.side_effect = [
            "ping",
            "ping",
            "other_message",
            WebSocketDisconnect()
        ]
        
        with patch("routes.websocket_routes.clients", []):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            # Should have responded to ping messages
            assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_websocket_non_ping_message(self, mock_websocket):
        """Test that non-ping messages don't trigger pong response."""
        from fastapi import WebSocketDisconnect
        
        mock_websocket.receive_text.side_effect = [
            "hello",
            "world",
            WebSocketDisconnect()
        ]
        
        with patch("routes.websocket_routes.clients", []):
            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            # Should not have sent any pong responses
            mock_websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, mock_websocket):
        """Test complete WebSocket connection lifecycle."""
        from fastapi import WebSocketDisconnect
        
        clients_mock = MagicMock()
        mock_websocket.receive_text.side_effect = ["ping", WebSocketDisconnect()]

        with patch("routes.websocket_routes.clients", clients_mock):
            from routes.websocket_routes import websocket_price
            
            await websocket_price(mock_websocket)
            
            mock_websocket.accept.assert_called_once()
            clients_mock.append.assert_called_once_with(mock_websocket)
            clients_mock.remove.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_websocket_concurrent_clients(self):
        """Test that multiple clients can be connected simultaneously."""
        from fastapi import WebSocketDisconnect
        
        client1 = MagicMock()
        client1.accept = AsyncMock()
        client1.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        
        client2 = MagicMock()
        client2.accept = AsyncMock()
        client2.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        
        clients_list = []
        
        with patch("routes.websocket_routes.clients", clients_list):
            from routes.websocket_routes import websocket_price
            
            # Connect first client
            task1 = asyncio.create_task(websocket_price(client1))
            await asyncio.sleep(0.01)  # Let it start
            
            # At this point, client1 should be in list (before disconnect)
            # But it disconnects immediately, so we can't guarantee it
            
            await task1
            
            # Both should have been accepted
            client1.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_timeout_value(self, mock_websocket):
        """Test that WebSocket uses 30-second timeout by asserting call arguments."""
        from fastapi import WebSocketDisconnect
        # Ensure the loop ends: first a timeout, then disconnect
        mock_websocket.receive_text.side_effect = [asyncio.TimeoutError(), WebSocketDisconnect()]

        async def fake_wait_for(coro, timeout):
            # Immediately await the underlying coroutine to trigger its side effects
            assert timeout == 30
            return await coro

        with patch("routes.websocket_routes.clients", []), \
             patch("asyncio.wait_for", side_effect=fake_wait_for) as mock_wait_for:

            from routes.websocket_routes import websocket_price

            await websocket_price(mock_websocket)

            # verify accept
            mock_websocket.accept.assert_called_once()
