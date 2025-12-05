import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from bson.decimal128 import Decimal128

from fetch_binance import background_jobs


def test_decimal128_to_decimal_converts_decimal128():
    d128 = Decimal128("12.34")
    res = background_jobs.decimal128_to_decimal(d128)
    assert isinstance(res, Decimal)
    assert str(res) == str(d128.to_decimal())


def test_decimal128_to_decimal_returns_decimal_for_other_values():
    res = background_jobs.decimal128_to_decimal("5.5")
    assert isinstance(res, Decimal)
    assert str(res) == "5.5"


@patch("fetch_binance.background_jobs.Order")
@patch("fetch_binance.background_jobs.client")
@patch("fetch_binance.background_jobs.Transaction")
@patch("fetch_binance.background_jobs.CreditsHistory")
@patch("fetch_binance.background_jobs.update_or_create_portfolio")
@patch("fetch_binance.background_jobs.update_portfolio_on_sell")
@pytest.mark.asyncio
async def test_settle_filled_limit_orders_handles_buy_and_records_transactions(
    mock_update_sell, mock_update_buy, mock_credits, mock_transaction, mock_client, mock_order_class
):
    """When Binance reports a filled order with fills, transactions are created and portfolio updated."""
    # Prepare one order
    order = MagicMock()
    order.id = "ord1"
    order.symbol = "BTCUSDT"
    order.order_id = 123
    order.side = "BUY"
    order.quantity = Decimal128("0.1")
    order.price = Decimal128("40000")
    order.fetch_link = AsyncMock()
    order.save = AsyncMock()

    # User associated with order
    user = MagicMock()
    user.id = "user1"
    user.credits = Decimal128("100000")
    user.save = AsyncMock()

    order.user = user

    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=[order])
    mock_order_class.find.return_value = mock_query

    # Binance returns a filled order with fills
    binance_order = {
        "status": "FILLED",
        "fills": [{"qty": "0.1", "price": "40000"}]
    }
    mock_client.get_order.return_value = binance_order

    # Patch inserts
    mock_transaction.insert = AsyncMock()
    mock_credits.insert = AsyncMock()

    await background_jobs.settle_filled_limit_orders()

    # Ensure transaction insert was called
    assert mock_transaction.insert.await_count >= 1
    mock_update_buy.assert_called_once()
    order.save.assert_called_once()
    user.save.assert_called_once()


@patch("fetch_binance.background_jobs.Order")
@patch("fetch_binance.background_jobs.client")
@pytest.mark.asyncio
async def test_settle_filled_limit_orders_skips_if_insufficient_credits(mock_client, mock_order_class):
    """If user doesn't have enough credits, settlement should be skipped for BUY."""
    order = MagicMock()
    order.id = "ord2"
    order.symbol = "BTCUSDT"
    order.order_id = 456
    order.side = "BUY"
    order.quantity = Decimal128("1")
    order.price = Decimal128("50000")
    order.fetch_link = AsyncMock()
    order.save = AsyncMock()

    user = MagicMock()
    user.id = "user2"
    user.credits = Decimal128("10")  # insufficient
    user.save = AsyncMock()
    order.user = user

    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=[order])
    mock_order_class.find.return_value = mock_query

    binance_order = {"status": "FILLED", "fills": [{"qty": "1", "price": "50000"}]}
    mock_client.get_order.return_value = binance_order

    # Ensure function runs without raising and does not mark order FILLED
    await background_jobs.settle_filled_limit_orders()

    # If credits insufficient, order.status should not be set to FILLED
    assert order.status != "FILLED"
