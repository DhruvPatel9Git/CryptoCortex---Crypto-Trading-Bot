"""
Unit tests for cryptoPair.py
Tests all crypto pair-related endpoints with mocked dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from routes.cryptoPair import router
from models import CryptoPair


# Mock data
MOCK_SYMBOL = "BTCUSDT"
MOCK_BASE_ASSET = "BTC"


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = ObjectId()
    user.username = "testuser@example.com"
    return user


@pytest.fixture
def mock_crypto_pairs():
    """Create mock crypto pair objects."""
    pairs = []
    for i, symbol in enumerate(["BTCUSDT", "ETHUSDT", "ADAUSDT"]):
        pair = MagicMock(spec=CryptoPair)
        pair.symbol = symbol
        pair.base_asset = symbol[:-4]  # Remove 'USDT'
        pairs.append(pair)
    return pairs


class TestSyncBinanceSymbolsEndpoint:
    """Test cases for /sync_binance_symbols endpoint."""

    @pytest.mark.asyncio
    async def test_sync_binance_symbols_success(self, mock_user):
        """Test syncing Binance symbols successfully."""
        with patch("routes.cryptoPair.fetch_and_store_binance_symbols", new_callable=AsyncMock) as mock_fetch:
            from routes.cryptoPair import sync_binance_symbols
            
            result = await sync_binance_symbols(mock_user)
            
            assert result["status"] == "sync complete"
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_binance_symbols_requires_authentication(self):
        """Test that sync endpoint requires authentication."""
        # This test verifies the Depends(get_current_user) is present
        from routes.cryptoPair import sync_binance_symbols
        import inspect
        
        sig = inspect.signature(sync_binance_symbols)
        assert "current_user" in sig.parameters


class TestGetCryptosEndpoint:
    """Test cases for /cryptos endpoint."""

    @pytest.mark.asyncio
    async def test_get_cryptos_success_default_params(self, mock_crypto_pairs):
        """Test getting cryptos with default parameters."""
        mock_query = MagicMock()
        mock_query.skip = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        mock_query.count = AsyncMock(return_value=len(mock_crypto_pairs))
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import get_cryptos
            
            result = await get_cryptos()
            
            assert "items" in result
            assert "total" in result
            assert len(result["items"]) == 3
            assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_get_cryptos_with_pagination(self, mock_crypto_pairs):
        """Test getting cryptos with pagination parameters."""
        mock_query = MagicMock()
        mock_query.skip = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs[:2])
        mock_query.count = AsyncMock(return_value=len(mock_crypto_pairs))
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import get_cryptos
            
            result = await get_cryptos(skip=0, limit=2)
            
            mock_query.skip.assert_called_once_with(0)
            mock_query.limit.assert_called_once_with(2)
            assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_cryptos_with_search_symbol(self, mock_crypto_pairs):
        """Test searching cryptos by symbol."""
        btc_pairs = [p for p in mock_crypto_pairs if "BTC" in p.symbol]
        mock_query = MagicMock()
        mock_query.skip = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=btc_pairs)
        mock_query.count = AsyncMock(return_value=len(btc_pairs))
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query) as mock_find:
            from routes.cryptoPair import get_cryptos
            
            result = await get_cryptos(search="BTC")
            
            # Verify regex search was applied
            call_args = mock_find.call_args[0][0]
            assert "$or" in call_args
            assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_cryptos_with_search_base_asset(self, mock_crypto_pairs):
        """Test searching cryptos by base asset."""
        eth_pairs = [p for p in mock_crypto_pairs if "ETH" in p.base_asset]
        mock_query = MagicMock()
        mock_query.skip = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=eth_pairs)
        mock_query.count = AsyncMock(return_value=len(eth_pairs))
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import get_cryptos
            
            result = await get_cryptos(search="ETH")
            
            assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_cryptos_empty_results(self):
        """Test getting cryptos when no results found."""
        mock_query = MagicMock()
        mock_query.skip = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])
        mock_query.count = AsyncMock(return_value=0)
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import get_cryptos
            
            result = await get_cryptos(search="NONEXISTENT")
            
            assert result["items"] == []
            assert result["total"] == 0


class TestSearchCryptosEndpoint:
    """Test cases for /cryptos/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_cryptos_success(self, mock_crypto_pairs):
        """Test searching cryptos successfully."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import search_cryptos
            
            result = await search_cryptos(query="BTC")
            
            assert len(result) == 3
            assert all("symbol" in item and "base_asset" in item for item in result)

    @pytest.mark.asyncio
    async def test_search_cryptos_case_insensitive(self, mock_crypto_pairs):
        """Test that search is case-insensitive."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query) as mock_find:
            from routes.cryptoPair import search_cryptos
            
            await search_cryptos(query="btc")
            
            # Verify regex with case-insensitive option was used
            call_args = mock_find.call_args[0][0]
            assert "$or" in call_args
            for condition in call_args["$or"]:
                for field, regex in condition.items():
                    assert regex["$options"] == "i"

    @pytest.mark.asyncio
    async def test_search_cryptos_empty_results(self):
        """Test searching cryptos with no results."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import search_cryptos
            
            result = await search_cryptos(query="NONEXISTENT")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_search_cryptos_returns_correct_structure(self, mock_crypto_pairs):
        """Test that search returns correct data structure."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs[:1])
        
        with patch("routes.cryptoPair.CryptoPair.find", return_value=mock_query):
            from routes.cryptoPair import search_cryptos
            
            result = await search_cryptos(query="BTC")
            
            assert len(result) == 1
            assert result[0]["symbol"] == "BTCUSDT"
            assert result[0]["base_asset"] == "BTC"


class TestGetAllCryptosEndpoint:
    """Test cases for /cryptos/all endpoint."""

    @pytest.mark.asyncio
    async def test_get_all_cryptos_success(self, mock_crypto_pairs):
        """Test getting all crypto symbols successfully."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("routes.cryptoPair.CryptoPair.find_all", return_value=mock_query):
            from routes.cryptoPair import get_all_cryptos
            
            result = await get_all_cryptos()
            
            assert len(result) == 3
            assert result == ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

    @pytest.mark.asyncio
    async def test_get_all_cryptos_empty(self):
        """Test getting all cryptos when database is empty."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.cryptoPair.CryptoPair.find_all", return_value=mock_query):
            from routes.cryptoPair import get_all_cryptos
            
            result = await get_all_cryptos()
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_all_cryptos_returns_only_symbols(self, mock_crypto_pairs):
        """Test that only symbols are returned, not full objects."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_crypto_pairs)
        
        with patch("routes.cryptoPair.CryptoPair.find_all", return_value=mock_query):
            from routes.cryptoPair import get_all_cryptos
            
            result = await get_all_cryptos()
            
            # Verify all items are strings, not objects
            assert all(isinstance(symbol, str) for symbol in result)
