import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from decimal import Decimal
from bson.decimal128 import Decimal128

from fetch_binance import fetch_cryptoPair


def test_to_decimal128_with_none_returns_none():
    assert fetch_cryptoPair.to_decimal128(None) is None


def test_to_decimal128_with_decimal128_passes_through():
    val = Decimal128("1.234")
    res = fetch_cryptoPair.to_decimal128(val)
    assert res is val


def test_to_decimal128_converts_decimal_and_str():
    res1 = fetch_cryptoPair.to_decimal128(Decimal("2.5"))
    assert isinstance(res1, Decimal128)

    res2 = fetch_cryptoPair.to_decimal128("3.75")
    assert isinstance(res2, Decimal128)


@patch("fetch_binance.fetch_cryptoPair.binance_client")
@patch("fetch_binance.fetch_cryptoPair.CryptoPair")
@pytest.mark.asyncio
async def test_fetch_and_store_inserts_new_and_updates_existing(mock_crypto_class, mock_client):
    """fetch_and_store_binance_symbols should insert new docs and update existing ones."""
    # Build fake exchange info with a mix of symbols
    exchange_info = {
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "isSpotTradingAllowed": True,
             "baseAsset": "BTC", "quoteAsset": "USDT",
             "filters": [{"filterType": "LOT_SIZE", "minQty": "0.001", "stepSize": "0.001"}, {"filterType": "PRICE_FILTER", "tickSize": "0.01"}]},
            {"symbol": "ABCETH", "status": "TRADING", "isSpotTradingAllowed": True, "baseAsset": "ABC", "quoteAsset": "ETH", "filters": []},  # not USDT, skipped
            {"symbol": "XZYUSDT", "status": "BREAK", "isSpotTradingAllowed": True, "baseAsset": "XZY", "quoteAsset": "USDT", "filters": []}  # not trading, skipped
        ]
    }

    mock_client.get_exchange_info.return_value = exchange_info
    mock_client.get_symbol_ticker.side_effect = lambda symbol: {"price": "50000"} if symbol == "BTCUSDT" else {}

    # No existing doc for BTCUSDT
    mock_crypto_class.find_one = AsyncMock(return_value=None)

    mock_instance = MagicMock()
    mock_instance.insert = AsyncMock()
    mock_crypto_class.return_value = mock_instance

    await fetch_cryptoPair.fetch_and_store_binance_symbols()

    # Should have attempted to insert the BTCUSDT document
    mock_instance.insert.assert_called_once()


@patch("fetch_binance.fetch_cryptoPair.binance_client")
@patch("fetch_binance.fetch_cryptoPair.CryptoPair")
@pytest.mark.asyncio
async def test_fetch_and_store_updates_existing_doc(mock_crypto_class, mock_client):
    """If a CryptoPair exists, it should call set/update on it."""
    exchange_info = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING", "isSpotTradingAllowed": True,
                                    "baseAsset": "BTC", "quoteAsset": "USDT", "filters": []}]}
    mock_client.get_exchange_info.return_value = exchange_info
    mock_client.get_symbol_ticker.return_value = {"price": "42000"}

    existing = MagicMock()
    existing.set = AsyncMock()

    mock_crypto_class.find_one = AsyncMock(return_value=existing)

    await fetch_cryptoPair.fetch_and_store_binance_symbols()

    existing.set.assert_called_once()
