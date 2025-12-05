"""
Unit tests for current_balance.py
Tests the balance endpoint with mocked dependencies.
"""
import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId

from routes.current_balance import router


# Mock data
MOCK_USER_ID = ObjectId()
MOCK_ACCOUNT_INFO = {
    "balances": [
        {"asset": "BTC", "free": "1.50000000", "locked": "0.00000000"},
        {"asset": "USDT", "free": "10000.00000000", "locked": "500.00000000"},
        {"asset": "ETH", "free": "0.00000000", "locked": "0.00000000"},  # Should be filtered
        {"asset": "BNB", "free": "5.25000000", "locked": "1.00000000"}
    ]
}


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = MOCK_USER_ID
    user.username = "testuser@example.com"
    return user


@pytest.fixture
def mock_binance_client():
    """Create a mock Binance client."""
    client = MagicMock()
    client.get_account = MagicMock(return_value=MOCK_ACCOUNT_INFO)
    return client


class TestGetBalanceEndpoint:
    """Test cases for /balance endpoint."""

    @pytest.mark.asyncio
    async def test_get_balance_success(self, mock_user, mock_binance_client):
        """Test getting account balance successfully."""
        with patch("routes.current_balance.client", mock_binance_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            assert "balances" in result
            assert len(result["balances"]) == 3  # ETH filtered out (0 balance)
            mock_binance_client.get_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_balance_filters_zero_balances(self, mock_user, mock_binance_client):
        """Test that balances with zero free and locked amounts are filtered."""
        with patch("routes.current_balance.client", mock_binance_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            # Verify ETH is not in results
            assets = [b["asset"] for b in result["balances"]]
            assert "ETH" not in assets
            assert "BTC" in assets
            assert "USDT" in assets
            assert "BNB" in assets

    @pytest.mark.asyncio
    async def test_get_balance_correct_structure(self, mock_user, mock_binance_client):
        """Test that balance data structure is correct."""
        with patch("routes.current_balance.client", mock_binance_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            for balance in result["balances"]:
                assert "asset" in balance
                assert "free" in balance
                assert "locked" in balance
                assert isinstance(balance["free"], float)
                assert isinstance(balance["locked"], float)

    @pytest.mark.asyncio
    async def test_get_balance_converts_to_float(self, mock_user, mock_binance_client):
        """Test that balance values are converted to floats."""
        with patch("routes.current_balance.client", mock_binance_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            btc_balance = next(b for b in result["balances"] if b["asset"] == "BTC")
            assert btc_balance["free"] == 1.5
            assert btc_balance["locked"] == 0.0

    @pytest.mark.asyncio
    async def test_get_balance_includes_locked_amounts(self, mock_user, mock_binance_client):
        """Test that locked amounts are included in results."""
        with patch("routes.current_balance.client", mock_binance_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            usdt_balance = next(b for b in result["balances"] if b["asset"] == "USDT")
            assert usdt_balance["free"] == 10000.0
            assert usdt_balance["locked"] == 500.0

    @pytest.mark.asyncio
    async def test_get_balance_empty_account(self, mock_user):
        """Test getting balance when account has no balances."""
        empty_client = MagicMock()
        empty_client.get_account = MagicMock(return_value={"balances": []})
        
        with patch("routes.current_balance.client", empty_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            assert result["balances"] == []

    @pytest.mark.asyncio
    async def test_get_balance_all_zero_balances(self, mock_user):
        """Test getting balance when all balances are zero."""
        zero_client = MagicMock()
        zero_client.get_account = MagicMock(return_value={
            "balances": [
                {"asset": "BTC", "free": "0.00000000", "locked": "0.00000000"},
                {"asset": "ETH", "free": "0.00000000", "locked": "0.00000000"}
            ]
        })
        
        with patch("routes.current_balance.client", zero_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            assert result["balances"] == []

    @pytest.mark.asyncio
    async def test_get_balance_only_locked_amounts(self, mock_user):
        """Test getting balance when only locked amounts exist."""
        locked_client = MagicMock()
        locked_client.get_account = MagicMock(return_value={
            "balances": [
                {"asset": "BTC", "free": "0.00000000", "locked": "2.50000000"}
            ]
        })
        
        with patch("routes.current_balance.client", locked_client):
            from routes.current_balance import get_balance
            
            result = await get_balance(mock_user)
            
            assert len(result["balances"]) == 1
            assert result["balances"][0]["asset"] == "BTC"
            assert result["balances"][0]["free"] == 0.0
            assert result["balances"][0]["locked"] == 2.5

    @pytest.mark.asyncio
    async def test_get_balance_requires_authentication(self):
        """Test that balance endpoint requires authentication."""
        from routes.current_balance import get_balance
        import inspect
        
        sig = inspect.signature(get_balance)
        assert "current_user" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_balance_binance_api_error(self, mock_user):
        """Test handling Binance API error."""
        error_client = MagicMock()
        error_client.get_account = MagicMock(side_effect=Exception("Binance API error"))
        
        with patch("routes.current_balance.client", error_client):
            from routes.current_balance import get_balance
            
            with pytest.raises(Exception) as exc_info:
                await get_balance(mock_user)
            
            assert "Binance API error" in str(exc_info.value)
