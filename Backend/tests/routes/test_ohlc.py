"""
Unit tests for ohlc.py
Tests all candle/OHLC data endpoints with mocked dependencies.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from bson import ObjectId

from routes.ohlc import router, VALID_INTERVALS
from models import Candle


# Mock data
MOCK_USER_ID = ObjectId()
MOCK_SYMBOL = "BTCUSDT"
MOCK_INTERVAL = "1d"


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = MOCK_USER_ID
    user.username = "testuser@example.com"
    return user


@pytest.fixture
def mock_candles():
    """Create mock candle objects."""
    now = datetime.now(timezone.utc)
    candles = []
    for i in range(5):
        candle = MagicMock(spec=Candle)
        candle.symbol = MOCK_SYMBOL
        candle.interval = MOCK_INTERVAL
        candle.candle_time = now - timedelta(days=i)
        candle.open = Decimal("50000.00") + i
        candle.high = Decimal("51000.00") + i
        candle.low = Decimal("49000.00") + i
        candle.close = Decimal("50500.00") + i
        candle.volume = Decimal("1000.00") + i
        candles.append(candle)
    return candles


class TestTriggerCandleFetchEndpoint:
    """Test cases for /fetch_historical_candles endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_candle_fetch_success_default_params(self, mock_user):
        """Test triggering candle fetch with default parameters."""
        with patch("routes.ohlc.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            from routes.ohlc import trigger_candle_fetch
            
            result = await trigger_candle_fetch(current_user=mock_user)
            
            assert "Historical candle data fetched" in result["message"]
            assert "30 days" in result["message"]
            assert "1d interval" in result["message"]
            mock_fetch.assert_called_once_with(interval="1d", days_back=30)

    @pytest.mark.asyncio
    async def test_trigger_candle_fetch_custom_params(self, mock_user):
        """Test triggering candle fetch with custom parameters."""
        with patch("routes.ohlc.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            from routes.ohlc import trigger_candle_fetch
            
            result = await trigger_candle_fetch(days_back=60, interval="1h", current_user=mock_user)
            
            assert "60 days" in result["message"]
            assert "1h interval" in result["message"]
            mock_fetch.assert_called_once_with(interval="1h", days_back=60)

    @pytest.mark.asyncio
    async def test_trigger_candle_fetch_all_valid_intervals(self, mock_user):
        """Test triggering candle fetch with all valid intervals."""
        for interval_key in VALID_INTERVALS.keys():
            with patch("routes.ohlc.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
                from routes.ohlc import trigger_candle_fetch
                
                result = await trigger_candle_fetch(interval=interval_key, current_user=mock_user)
                
                assert "Historical candle data fetched" in result["message"]
                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_candle_fetch_invalid_interval(self, mock_user):
        """Test triggering candle fetch with invalid interval."""
        from routes.ohlc import trigger_candle_fetch
        
        with pytest.raises(HTTPException) as exc_info:
            await trigger_candle_fetch(interval="INVALID", current_user=mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Invalid interval" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_trigger_candle_fetch_api_error(self, mock_user):
        """Test handling API error during candle fetch."""
        with patch("routes.ohlc.fetch_historical_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")
            
            from routes.ohlc import trigger_candle_fetch
            
            with pytest.raises(HTTPException) as exc_info:
                await trigger_candle_fetch(current_user=mock_user)
            
            assert exc_info.value.status_code == 500
            assert "Failed to fetch data" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_trigger_candle_fetch_requires_authentication(self):
        """Test that fetch endpoint requires authentication."""
        from routes.ohlc import trigger_candle_fetch
        import inspect
        
        sig = inspect.signature(trigger_candle_fetch)
        assert "current_user" in sig.parameters


class TestGetOhlcDataEndpoint:
    """Test cases for /candles/{symbol} endpoint."""

    @pytest.mark.asyncio
    async def test_get_ohlc_data_success(self, mock_candles):
        """Test getting OHLC data successfully."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles)
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query):
            from routes.ohlc import get_ohlc_data
            
            result = await get_ohlc_data(MOCK_SYMBOL)
            
            assert len(result) == 5
            assert all("symbol" in candle for candle in result)
            assert all("open" in candle for candle in result)
            assert all("high" in candle for candle in result)
            assert all("low" in candle for candle in result)
            assert all("close" in candle for candle in result)
            assert all("volume" in candle for candle in result)

    @pytest.mark.asyncio
    async def test_get_ohlc_data_symbol_case_insensitive(self, mock_candles):
        """Test that symbol search is case-insensitive."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles)
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query) as mock_find:
            from routes.ohlc import get_ohlc_data
            
            await get_ohlc_data("btcusdt")
            
            # Verify the symbol was converted to uppercase
            call_args = mock_find.call_args[0][0]
            assert call_args["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_get_ohlc_data_custom_days_back(self, mock_candles):
        """Test getting OHLC data with custom days_back parameter."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles[:3])
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query) as mock_find:
            from routes.ohlc import get_ohlc_data
            
            result = await get_ohlc_data(MOCK_SYMBOL, days_back=7)
            
            # Verify date range was applied
            call_args = mock_find.call_args[0][0]
            assert "candle_time" in call_args
            assert "$gte" in call_args["candle_time"]
            assert "$lte" in call_args["candle_time"]

    @pytest.mark.asyncio
    async def test_get_ohlc_data_sorted_by_time(self, mock_candles):
        """Test that results are sorted by candle_time."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles)
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query):
            from routes.ohlc import get_ohlc_data
            
            await get_ohlc_data(MOCK_SYMBOL)
            
            mock_query.sort.assert_called_once_with("candle_time")

    @pytest.mark.asyncio
    async def test_get_ohlc_data_no_results(self):
        """Test getting OHLC data when no candles found."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query):
            from routes.ohlc import get_ohlc_data
            
            result = await get_ohlc_data("NONEXISTENT")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_ohlc_data_correct_structure(self, mock_candles):
        """Test that OHLC data has correct structure."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles[:1])
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query):
            from routes.ohlc import get_ohlc_data
            
            result = await get_ohlc_data(MOCK_SYMBOL)
            
            candle = result[0]
            assert candle["symbol"] == MOCK_SYMBOL
            assert candle["interval"] == MOCK_INTERVAL
            assert isinstance(candle["open"], float)
            assert isinstance(candle["high"], float)
            assert isinstance(candle["low"], float)
            assert isinstance(candle["close"], float)
            assert isinstance(candle["volume"], float)

    @pytest.mark.asyncio
    async def test_get_ohlc_data_decimal_conversion(self, mock_candles):
        """Test that Decimal values are converted to floats."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles[:1])
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query):
            from routes.ohlc import get_ohlc_data
            
            result = await get_ohlc_data(MOCK_SYMBOL)
            
            candle = result[0]
            # Verify values match the mock data (converted to float)
            assert candle["open"] == 50000.0
            assert candle["high"] == 51000.0
            assert candle["low"] == 49000.0
            assert candle["close"] == 50500.0
            assert candle["volume"] == 1000.0

    @pytest.mark.asyncio
    async def test_get_ohlc_data_days_back_minimum_value(self, mock_candles):
        """Test that days_back parameter respects minimum value."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_candles)
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query):
            from routes.ohlc import get_ohlc_data
            
            # days_back has ge=1 constraint
            result = await get_ohlc_data(MOCK_SYMBOL, days_back=1)
            
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_ohlc_data_time_range_calculation(self):
        """Test that time range is calculated correctly."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.ohlc.Candle.find", return_value=mock_query) as mock_find:
            from routes.ohlc import get_ohlc_data
            
            await get_ohlc_data(MOCK_SYMBOL, days_back=10)
            
            call_args = mock_find.call_args[0][0]
            time_range = call_args["candle_time"]
            start_time = time_range["$gte"]
            end_time = time_range["$lte"]
            
            # Verify the time difference is approximately 10 days
            time_diff = (end_time - start_time).days
            assert time_diff == 10
