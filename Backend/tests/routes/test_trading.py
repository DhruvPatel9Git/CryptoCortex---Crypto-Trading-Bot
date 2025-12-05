"""
Unit tests for trading.py
Tests all trading-related endpoints with mocked dependencies.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId

from routes.trading import router, quantize_decimal, to_decimal128
from models import (
    Order, Transaction, TransactionTypeEnum, TransferRequest,
    User, Transfer, Portfolio, OrderRequest, CryptoPair,
    CreditsHistory, CreditReasonEnum, OrderTypeEnum
)


# Mock data
MOCK_USER_ID = ObjectId()
MOCK_SYMBOL = "BTCUSDT"
MOCK_QUANTITY = Decimal("0.5")
MOCK_PRICE = Decimal("50000.00")


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock(spec=User)
    user.id = MOCK_USER_ID
    user.username = "testuser@example.com"
    user.credits = Decimal("10000.00")
    user.save = AsyncMock()
    return user


@pytest.fixture
def mock_portfolio():
    """Create a mock portfolio object."""
    portfolio = MagicMock(spec=Portfolio)
    portfolio.user = MagicMock()
    portfolio.user.id = MOCK_USER_ID
    portfolio.symbol = MOCK_SYMBOL
    portfolio.quantity = Decimal("2.0")
    portfolio.avg_buy_price = MOCK_PRICE
    portfolio.save = AsyncMock()
    portfolio.delete = AsyncMock()
    return portfolio


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_quantize_decimal_default_precision(self):
        """Test quantizing decimal with default precision."""
        result = quantize_decimal(Decimal("50000.123456789"))
        assert result == Decimal("50000.12345678")

    def test_quantize_decimal_custom_precision(self):
        """Test quantizing decimal with custom precision."""
        result = quantize_decimal(Decimal("50000.123"), "0.01")
        assert result == Decimal("50000.12")

    def test_to_decimal128(self):
        """Test converting to Decimal128."""
        from bson.decimal128 import Decimal128
        result = to_decimal128(Decimal("50000.00"))
        assert isinstance(result, Decimal128)


class TestPlaceTradeEndpoint:
    """Test cases for /trade endpoint."""

    @pytest.mark.asyncio
    async def test_place_trade_buy_success(self, mock_user):
        """Test placing a buy order successfully."""
        with patch("routes.trading.process_trade_task") as mock_task:
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol=MOCK_SYMBOL,
                side="BUY",
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            result = await place_trade(request, mock_user)
            
            assert result["status"] == "success"
            assert "BUY" in result["message"]
            assert MOCK_SYMBOL in result["message"]
            mock_task.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_trade_sell_success(self, mock_user, mock_portfolio):
        """Test placing a sell order successfully with sufficient holdings."""
        with patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.trading.process_trade_task") as mock_task:
            
            mock_find.return_value = mock_portfolio
            
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol=MOCK_SYMBOL,
                side="SELL",
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            result = await place_trade(request, mock_user)
            
            assert result["status"] == "success"
            assert "SELL" in result["message"]

    @pytest.mark.asyncio
    async def test_place_trade_sell_no_holdings(self, mock_user):
        """Test sell order fails when user has no holdings."""
        with patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol=MOCK_SYMBOL,
                side="SELL",
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await place_trade(request, mock_user)
            
            assert exc_info.value.status_code == 400
            assert "don't have any holdings" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_place_trade_sell_insufficient_quantity(self, mock_user, mock_portfolio):
        """Test sell order fails with insufficient quantity."""
        mock_portfolio.quantity = Decimal("0.1")  # Less than requested
        
        with patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol=MOCK_SYMBOL,
                side="SELL",
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await place_trade(request, mock_user)
            
            assert exc_info.value.status_code == 400
            assert "Insufficient holdings" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_place_trade_limit_order(self, mock_user):
        """Test placing a limit order."""
        with patch("routes.trading.process_trade_task") as mock_task:
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol=MOCK_SYMBOL,
                side="BUY",
                order_type=OrderTypeEnum.LIMIT,
                quantity=MOCK_QUANTITY,
                price=MOCK_PRICE
            )
            
            result = await place_trade(request, mock_user)
            
            call_args = mock_task.send.call_args[0][0]
            assert call_args["order_type"] == "LIMIT"
            assert call_args["price"] == str(MOCK_PRICE)

    @pytest.mark.asyncio
    async def test_place_trade_normalizes_inputs(self, mock_user):
        """Test that trade inputs are normalized (uppercase, quantized)."""
        with patch("routes.trading.process_trade_task") as mock_task:
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol="btcusdt",
                side="buy",
                order_type=OrderTypeEnum.MARKET,
                quantity=Decimal("0.123456789")
            )
            
            await place_trade(request, mock_user)
            
            call_args = mock_task.send.call_args[0][0]
            assert call_args["symbol"] == "BTCUSDT"
            assert call_args["side"] == "BUY"
            # Quantity should be quantized
            assert len(call_args["quantity"].split('.')[-1]) <= 8

    @pytest.mark.asyncio
    async def test_place_trade_enqueues_task(self, mock_user):
        """Test that trade is enqueued as a background task."""
        with patch("routes.trading.process_trade_task") as mock_task:
            from routes.trading import place_trade
            
            request = OrderRequest(
                symbol=MOCK_SYMBOL,
                side="BUY",
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            await place_trade(request, mock_user)
            
            mock_task.send.assert_called_once()
            call_args = mock_task.send.call_args[0][0]
            assert call_args["user_id"] == str(MOCK_USER_ID)


class TestTransferEndpoint:
    """Test cases for /transfer endpoint."""

    @pytest.mark.asyncio
    async def test_transfer_success(self, mock_user, mock_portfolio):
        """Test successful transfer between users."""
        receiver = MagicMock(spec=User)
        receiver.id = ObjectId()
        receiver.username = "receiver@example.com"
        receiver.credits = Decimal("5000.00")
        receiver.save = AsyncMock()
        
        receiver_portfolio = MagicMock(spec=Portfolio)
        receiver_portfolio.quantity = Decimal("1.0")
        receiver_portfolio.save = AsyncMock()
        
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find_user, \
             patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find_portfolio, \
             patch("routes.trading.Portfolio.insert", new_callable=AsyncMock), \
             patch("routes.trading.Transfer.insert", new_callable=AsyncMock), \
             patch("routes.trading.CreditsHistory.insert_many", new_callable=AsyncMock):
            
            mock_find_user.return_value = receiver
            mock_find_portfolio.side_effect = [mock_portfolio, receiver_portfolio]
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username=receiver.username,
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            result = await transfer(request, mock_user)
            
            assert result["message"] == "Transfer successful"
            assert result["to"] == receiver.username
            assert result["symbol"] == MOCK_SYMBOL

    @pytest.mark.asyncio
    async def test_transfer_receiver_not_found(self, mock_user):
        """Test transfer fails when receiver doesn't exist."""
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username="nonexistent@example.com",
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer(request, mock_user)
            
            assert exc_info.value.status_code == 404
            assert "Receiver username not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_transfer_to_self(self, mock_user):
        """Test transfer fails when trying to transfer to self."""
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_user
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username=mock_user.username,
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer(request, mock_user)
            
            assert exc_info.value.status_code == 400
            assert "Cannot transfer to self" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_transfer_no_portfolio(self, mock_user):
        """Test transfer fails when sender has no portfolio."""
        receiver = MagicMock(spec=User)
        receiver.id = ObjectId()
        receiver.username = "receiver@example.com"
        
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find_user, \
             patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find_portfolio:
            
            mock_find_user.return_value = receiver
            mock_find_portfolio.return_value = None
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username=receiver.username,
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer(request, mock_user)
            
            assert exc_info.value.status_code == 400
            assert "Portfolio not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_transfer_insufficient_balance(self, mock_user, mock_portfolio):
        """Test transfer fails with insufficient balance."""
        mock_portfolio.quantity = Decimal("0.1")
        receiver = MagicMock(spec=User)
        receiver.id = ObjectId()
        receiver.username = "receiver@example.com"
        
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find_user, \
             patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find_portfolio:
            
            mock_find_user.return_value = receiver
            mock_find_portfolio.return_value = mock_portfolio
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username=receiver.username,
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer(request, mock_user)
            
            assert exc_info.value.status_code == 400
            assert "Insufficient balance" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_transfer_deducts_fee(self, mock_user, mock_portfolio):
        """Test that transfer deducts 1 credit fee from sender."""
        receiver = MagicMock(spec=User)
        receiver.id = ObjectId()
        receiver.username = "receiver@example.com"
        receiver.credits = Decimal("5000.00")
        receiver.save = AsyncMock()
        
        initial_credits = mock_user.credits
        
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find_user, \
             patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find_portfolio, \
             patch("routes.trading.Transfer.insert", new_callable=AsyncMock), \
             patch("routes.trading.CreditsHistory.insert_many", new_callable=AsyncMock):
            
            mock_find_user.return_value = receiver
            mock_find_portfolio.side_effect = [mock_portfolio, None]
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username=receiver.username,
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            await transfer(request, mock_user)
            
            assert mock_user.credits == initial_credits - Decimal("1")

    @pytest.mark.asyncio
    async def test_transfer_creates_receiver_portfolio(self, mock_user, mock_portfolio):
        """Test that transfer creates portfolio for receiver if not exists."""
        receiver = MagicMock(spec=User)
        receiver.id = ObjectId()
        receiver.username = "receiver@example.com"
        receiver.credits = Decimal("5000.00")
        receiver.save = AsyncMock()
        
        with patch("routes.trading.User.find_one", new_callable=AsyncMock) as mock_find_user, \
             patch("routes.trading.Portfolio.find_one", new_callable=AsyncMock) as mock_find_portfolio, \
             patch("routes.trading.Portfolio.insert", new_callable=AsyncMock) as mock_insert, \
             patch("routes.trading.Transfer.insert", new_callable=AsyncMock), \
             patch("routes.trading.CreditsHistory.insert_many", new_callable=AsyncMock):
            
            mock_find_user.return_value = receiver
            mock_find_portfolio.side_effect = [mock_portfolio, None]  # Receiver has no portfolio
            
            from routes.trading import transfer, TransferRequest
            
            request = TransferRequest(
                to_username=receiver.username,
                symbol=MOCK_SYMBOL,
                amount=Decimal("0.5")
            )
            
            await transfer(request, mock_user)
            
            mock_insert.assert_called_once()
