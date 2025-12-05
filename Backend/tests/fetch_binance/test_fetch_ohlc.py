import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from fetch_binance import fetch_ohlc


@pytest.mark.asyncio
async def test_fetch_historical_data_inserts_new_candles_and_updates_tracker():
    """fetch_historical_data should fetch klines, insert candles and update tracker."""
    pair = MagicMock()
    pair.symbol = "BTCUSDT"

    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=[pair])

    # Prepare sample klines
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    klines = [
        [now_ts - 86400000, "40000", "41000", "39000", "40500", "1000"],
        [now_ts, "40500", "42000", "40000", "41500", "500"]
    ]

    with patch("fetch_binance.fetch_ohlc.CryptoPair.find_all", return_value=mock_query), \
         patch("fetch_binance.fetch_ohlc.Candle") as mock_candle_class, \
         patch("fetch_binance.fetch_ohlc.CandleSyncTracker") as mock_tracker_class, \
         patch("fetch_binance.fetch_ohlc.client") as mock_client:

        mock_client.get_historical_klines.return_value = klines
        # Create simple candle objects so .candle_time is available for max()
        class DummyCandle:
            def __init__(self, candle_time):
                self.candle_time = candle_time

        def candle_side_effect(*args, **kwargs):
            return DummyCandle(kwargs.get("candle_time"))

        mock_candle_class.side_effect = candle_side_effect
        mock_candle_class.insert_many = AsyncMock()
        mock_tracker_class.find_one = AsyncMock(return_value=None)
        mock_tracker_class.return_value.insert = AsyncMock()

        await fetch_ohlc.fetch_historical_data()

        mock_client.get_historical_klines.assert_called()
        mock_candle_class.insert_many.assert_called_once()
        mock_tracker_class.return_value.insert.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_historical_data_handles_exceptions():
    """If the Binance client raises, the function should catch and not raise."""
    pair = MagicMock()
    pair.symbol = "BTCUSDT"
    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=[pair])

    with patch("fetch_binance.fetch_ohlc.CryptoPair.find_all", return_value=mock_query), \
         patch("fetch_binance.fetch_ohlc.CandleSyncTracker") as mock_tracker_class, \
         patch("fetch_binance.fetch_ohlc.client") as mock_client:

        mock_tracker_class.find_one = AsyncMock(return_value=None)
        mock_client.get_historical_klines.side_effect = Exception("API error")

        # Should not raise
        await fetch_ohlc.fetch_historical_data()

        mock_client.get_historical_klines.assert_called()
