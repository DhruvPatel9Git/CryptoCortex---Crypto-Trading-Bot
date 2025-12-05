"""
Unit tests for services/real_time_price.py
Tests WebSocket streaming functionality with mocked dependencies.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

from services.real_time_price import (
    build_stream_url,
    binance_stream,
    clients
)
from models import CryptoPair


# Mock data
MOCK_CRYPTO_PAIRS = [
    MagicMock(symbol="BTCUSDT"),
    MagicMock(symbol="ETHUSDT"),
    MagicMock(symbol="ADAUSDT")
]


@pytest.fixture
def mock_crypto_pairs():
    """Create mock crypto pairs."""
    return [
        MagicMock(symbol="BTCUSDT"),
        MagicMock(symbol="ETHUSDT"),
    ]


@pytest.fixture
def mock_websocket_message():
    """Create a mock WebSocket message."""
    return {
        "stream": "btcusdt@ticker",
        "data": {
            "e": "24hrTicker",
            "s": "BTCUSDT",
            "c": "50000.00",
            "h": "51000.00",
            "l": "49000.00"
        }
    }


class TestBuildStreamUrl:
    """Test cases for build_stream_url function."""

    @pytest.mark.asyncio
    async def test_build_stream_url_with_symbols(self, mock_crypto_pairs):
        """Test building stream URL with valid symbols."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query):
            url = await build_stream_url()
            
            assert url is not None
            assert "wss://stream.binance.com:9443/stream?streams=" in url
            assert "btcusdt@ticker" in url
            assert "ethusdt@ticker" in url

    @pytest.mark.asyncio
    async def test_build_stream_url_lowercase_conversion(self, mock_crypto_pairs):
        """Test that symbols are converted to lowercase."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query):
            url = await build_stream_url()
            
            # Ensure all symbols are lowercase in URL
            assert "BTCUSDT" not in url  # Uppercase should not appear
            assert "btcusdt@ticker" in url

    @pytest.mark.asyncio
    async def test_build_stream_url_no_symbols(self):
        """Test building stream URL when no symbols exist in database."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query):
            url = await build_stream_url()
            
            assert url is None

    @pytest.mark.asyncio
    async def test_build_stream_url_single_symbol(self):
        """Test building stream URL with a single symbol."""
        single_pair = [MagicMock(symbol="BTCUSDT")]
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=single_pair)
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query):
            url = await build_stream_url()
            
            assert url == "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker"

    @pytest.mark.asyncio
    async def test_build_stream_url_multiple_symbols(self):
        """Test building stream URL with multiple symbols joined correctly."""
        pairs = [
            MagicMock(symbol="BTCUSDT"),
            MagicMock(symbol="ETHUSDT"),
            MagicMock(symbol="ADAUSDT")
        ]
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=pairs)
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query):
            url = await build_stream_url()
            
            assert "btcusdt@ticker/ethusdt@ticker/adausdt@ticker" in url


class TestBinanceStream:
    """Test cases for binance_stream function."""

    @pytest.mark.asyncio
    async def test_binance_stream_connects_successfully(self, mock_crypto_pairs):
        """Test that binance_stream establishes connection successfully."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        mock_websocket = MagicMock()
        # First recv() raises exception to break the inner loop and trigger reconnect
        # Second exception breaks the outer while True loop
        mock_websocket.recv = AsyncMock(side_effect=Exception("Test exception"))
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query), \
             patch("services.real_time_price.websockets.connect") as mock_connect, \
             patch("services.real_time_price.build_stream_url", new_callable=AsyncMock) as mock_build_url, \
             patch("services.real_time_price.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_build_url.return_value = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker"
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)
            
            # Make sleep raise CancelledError to break the outer loop after first iteration
            mock_sleep.side_effect = asyncio.CancelledError
            
            try:
                await binance_stream()
            except asyncio.CancelledError:
                pass
            
            # Verify URL was built and connection was attempted
            mock_build_url.assert_called()
            mock_connect.assert_called_once_with("wss://stream.binance.com:9443/stream?streams=btcusdt@ticker")

    @pytest.mark.asyncio
    async def test_binance_stream_sends_message_to_clients(self, mock_crypto_pairs, mock_websocket_message):
        """Test that messages are sent to connected clients."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        mock_client = MagicMock()
        mock_client.send_text = AsyncMock()
        
        # Temporarily add mock client to the module-level clients list
        from services import real_time_price
        original_clients = real_time_price.clients.copy()
        real_time_price.clients.clear()
        real_time_price.clients.append(mock_client)
        
        mock_websocket = MagicMock()
        mock_websocket.recv = AsyncMock(side_effect=[
            json.dumps(mock_websocket_message),
            asyncio.CancelledError
        ])
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query), \
             patch("services.real_time_price.websockets.connect") as mock_connect, \
             patch("services.real_time_price.build_stream_url", new_callable=AsyncMock) as mock_build_url, \
             patch("services.real_time_price.asyncio.sleep", new_callable=AsyncMock):
            
            mock_build_url.return_value = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker"
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)
            
            try:
                await binance_stream()
            except asyncio.CancelledError:
                pass
            
            # Verify client received message
            mock_client.send_text.assert_called()
        
        # Restore original clients list
        real_time_price.clients.clear()
        real_time_price.clients.extend(original_clients)

    @pytest.mark.asyncio
    async def test_binance_stream_removes_failed_client(self, mock_crypto_pairs, mock_websocket_message):
        """Test that clients are removed when send fails."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        mock_client = MagicMock()
        mock_client.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        
        from services import real_time_price
        original_clients = real_time_price.clients.copy()
        real_time_price.clients.clear()
        real_time_price.clients.append(mock_client)
        
        mock_websocket = MagicMock()
        mock_websocket.recv = AsyncMock(side_effect=[
            json.dumps(mock_websocket_message),
            asyncio.CancelledError
        ])
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query), \
             patch("services.real_time_price.websockets.connect") as mock_connect, \
             patch("services.real_time_price.build_stream_url", new_callable=AsyncMock) as mock_build_url, \
             patch("services.real_time_price.asyncio.sleep", new_callable=AsyncMock):
            
            mock_build_url.return_value = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker"
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)
            
            try:
                await binance_stream()
            except asyncio.CancelledError:
                pass
            
            # Client should be removed after error
            assert mock_client not in real_time_price.clients
        
        real_time_price.clients.clear()
        real_time_price.clients.extend(original_clients)

    @pytest.mark.asyncio
    async def test_binance_stream_retries_on_no_symbols(self):
        """Test that stream retries when no symbols are found."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query), \
             patch("services.real_time_price.build_stream_url", new_callable=AsyncMock) as mock_build_url, \
             patch("services.real_time_price.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_build_url.return_value = None
            mock_sleep.side_effect = asyncio.CancelledError
            
            try:
                await binance_stream()
            except asyncio.CancelledError:
                pass
            
            mock_sleep.assert_called_with(30)

    @pytest.mark.asyncio
    async def test_binance_stream_reconnects_on_error(self, mock_crypto_pairs):
        """Test that stream reconnects after connection error."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query), \
             patch("services.real_time_price.websockets.connect") as mock_connect, \
             patch("services.real_time_price.build_stream_url", new_callable=AsyncMock) as mock_build_url, \
             patch("services.real_time_price.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_build_url.return_value = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker"
            mock_connect.side_effect = [
                Exception("Connection failed"),
                asyncio.CancelledError
            ]
            mock_sleep.side_effect = asyncio.CancelledError
            
            try:
                await binance_stream()
            except asyncio.CancelledError:
                pass
            
            mock_sleep.assert_called_with(10)

    @pytest.mark.asyncio
    async def test_binance_stream_handles_message_without_data(self, mock_crypto_pairs):
        """Test that stream ignores messages without 'data' field."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        mock_client = MagicMock()
        mock_client.send_text = AsyncMock()
        
        from services import real_time_price
        original_clients = real_time_price.clients.copy()
        real_time_price.clients.clear()
        real_time_price.clients.append(mock_client)
        
        message_without_data = {"stream": "btcusdt@ticker"}
        
        mock_websocket = MagicMock()
        mock_websocket.recv = AsyncMock(side_effect=[
            json.dumps(message_without_data),
            asyncio.CancelledError
        ])
        
        with patch("services.real_time_price.CryptoPair.find_all", return_value=mock_query), \
             patch("services.real_time_price.websockets.connect") as mock_connect, \
             patch("services.real_time_price.build_stream_url", new_callable=AsyncMock) as mock_build_url, \
             patch("services.real_time_price.asyncio.sleep", new_callable=AsyncMock):
            
            mock_build_url.return_value = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker"
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__ = AsyncMock(return_value=False)
            
            try:
                await binance_stream()
            except asyncio.CancelledError:
                pass
            
            # Client should not receive message
            mock_client.send_text.assert_not_called()
        
        real_time_price.clients.clear()
        real_time_price.clients.extend(original_clients)
