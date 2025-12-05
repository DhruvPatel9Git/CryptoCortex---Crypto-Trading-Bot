"""
Unit tests for cart.py
Tests all cart-related endpoints with mocked dependencies.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId

from routes.cart import router
from models import (
    Cart, CartItemEmbed, StatusEnum, OrderStatusEnum, Order,
    Transaction, TransactionTypeEnum, Portfolio, OrderTypeEnum,
    CreditsHistory, CreditReasonEnum
)


# Mock data
MOCK_USER_ID = ObjectId()
MOCK_SYMBOL = "BTCUSDT"
MOCK_QUANTITY = Decimal("0.5")
MOCK_PRICE = Decimal("50000.00")


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = MOCK_USER_ID
    user.username = "testuser@example.com"
    user.credits = Decimal("10000.00")
    user.save = AsyncMock()
    return user


@pytest.fixture
def mock_cart(mock_user):
    """Create a mock cart object."""
    cart = MagicMock(spec=Cart)
    cart.id = ObjectId()
    cart.user = mock_user
    cart.status = StatusEnum.active
    cart.items = []
    cart.created_at = datetime.now(timezone.utc)
    cart.updated_at = datetime.now(timezone.utc)
    cart.save = AsyncMock()
    cart.insert = AsyncMock(return_value=cart)
    return cart


@pytest.fixture
def mock_binance_client():
    """Create a mock Binance client."""
    client = MagicMock()
    client.get_symbol_ticker = MagicMock(return_value={"price": "50000.00"})
    client.create_order = MagicMock(return_value={
        "orderId": 12345,
        "status": "FILLED",
        "fills": [{
            "qty": "0.5",
            "price": "50000.00"
        }]
    })
    return client


class TestAddToCartEndpoint:
    """Test cases for /cart/add endpoint."""

    @pytest.mark.asyncio
    async def test_add_to_cart_success_market_order(self, mock_user, mock_cart, mock_binance_client):
        """Test adding a market order item to cart successfully."""
        with patch("routes.cart.client", mock_binance_client), \
             patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart

            from routes.cart import add_to_cart, AddToCartRequest
            request = AddToCartRequest(
                symbol=MOCK_SYMBOL,
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            result = await add_to_cart(request, mock_user)
            
            assert result["message"] == "Item added to cart (or quantity updated)"
            assert "unit_price" in result
            assert "total_price" in result
            mock_cart.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_cart_success_limit_order(self, mock_user, mock_cart):
        """Test adding a limit order item to cart successfully."""
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart
            
            from routes.cart import add_to_cart, AddToCartRequest
            request = AddToCartRequest(
                symbol=MOCK_SYMBOL,
                order_type=OrderTypeEnum.LIMIT,
                quantity=MOCK_QUANTITY,
                price=MOCK_PRICE
            )
            
            result = await add_to_cart(request, mock_user)
            
            assert "total_price" in result
            assert len(mock_cart.items) == 1

    @pytest.mark.asyncio
    async def test_add_to_cart_creates_new_cart(self, mock_user, mock_cart, mock_binance_client):
        """Test creating a new cart when none exists."""
        with patch("routes.cart.client", mock_binance_client), \
             patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.cart.Cart.insert", new_callable=AsyncMock) as mock_insert:
            mock_find.return_value = None  # No existing cart

            from routes.cart import add_to_cart, AddToCartRequest
            request = AddToCartRequest(
                symbol=MOCK_SYMBOL,
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            result = await add_to_cart(request, mock_user)
            
            assert result["message"] == "Item added to cart (or quantity updated)"
            mock_insert.assert_awaited()

    @pytest.mark.asyncio
    async def test_add_to_cart_updates_existing_item(self, mock_user, mock_cart, mock_binance_client):
        """Test updating quantity of existing cart item."""
        existing_item = MagicMock(spec=CartItemEmbed)
        existing_item.symbol = MOCK_SYMBOL
        existing_item.order_type = OrderTypeEnum.MARKET
        existing_item.quantity = MOCK_QUANTITY
        existing_item.price = Decimal("25000.00")
        mock_cart.items = [existing_item]
        
        with patch("routes.cart.client", mock_binance_client), \
             patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            
            mock_find.return_value = mock_cart
            
            from routes.cart import add_to_cart, AddToCartRequest
            request = AddToCartRequest(
                symbol=MOCK_SYMBOL,
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            result = await add_to_cart(request, mock_user)
            
            assert existing_item.quantity == MOCK_QUANTITY * 2

    @pytest.mark.asyncio
    async def test_add_to_cart_binance_error(self, mock_user, mock_cart, mock_binance_client):
        """Test handling Binance API error."""
        mock_binance_client.get_symbol_ticker.side_effect = Exception("Binance API error")
        
        with patch("routes.cart.client", mock_binance_client), \
             patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            
            mock_find.return_value = mock_cart
            
            from routes.cart import add_to_cart, AddToCartRequest
            request = AddToCartRequest(
                symbol="INVALID",
                order_type=OrderTypeEnum.MARKET,
                quantity=MOCK_QUANTITY
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await add_to_cart(request, mock_user)
            
            assert exc_info.value.status_code == 400
            assert "Could not fetch market price" in exc_info.value.detail


class TestViewCartEndpoint:
    """Test cases for /cart/view endpoint."""

    @pytest.mark.asyncio
    async def test_view_cart_success(self, mock_user, mock_cart):
        """Test viewing cart successfully."""
        cart_item = MagicMock(spec=CartItemEmbed)
        cart_item.symbol = MOCK_SYMBOL
        cart_item.order_type = OrderTypeEnum.MARKET
        cart_item.quantity = MOCK_QUANTITY
        cart_item.price = MOCK_PRICE
        mock_cart.items = [cart_item]
        
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart
            
            from routes.cart import view_cart
            result = await view_cart(mock_user)
            
            assert "cart_id" in result
            assert "items" in result
            assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_view_cart_not_found(self, mock_user):
        """Test viewing cart when no active cart exists."""
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            from routes.cart import view_cart
            
            with pytest.raises(HTTPException) as exc_info:
                await view_cart(mock_user)
            
            assert exc_info.value.status_code == 404
            assert "Active cart not found" in exc_info.value.detail


class TestClearCartEndpoint:
    """Test cases for /cart/clear endpoint."""

    @pytest.mark.asyncio
    async def test_clear_cart_success(self, mock_user, mock_cart):
        """Test clearing cart successfully."""
        mock_cart.items = [MagicMock(), MagicMock()]
        
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart
            
            from routes.cart import clear_cart
            result = await clear_cart(mock_user)
            
            assert result["message"] == "Cart cleared"
            assert len(mock_cart.items) == 0
            mock_cart.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cart_not_found(self, mock_user):
        """Test clearing cart when no active cart exists."""
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            from routes.cart import clear_cart
            
            with pytest.raises(HTTPException) as exc_info:
                await clear_cart(mock_user)
            
            assert exc_info.value.status_code == 404


class TestRemoveItemFromCartEndpoint:
    """Test cases for /cart/remove endpoint."""

    @pytest.mark.asyncio
    async def test_remove_item_success(self, mock_user, mock_cart):
        """Test removing an item from cart successfully."""
        item1 = MagicMock(spec=CartItemEmbed)
        item1.symbol = "BTCUSDT"
        item2 = MagicMock(spec=CartItemEmbed)
        item2.symbol = "ETHUSDT"
        mock_cart.items = [item1, item2]
        
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart
            
            from routes.cart import remove_item_from_cart
            result = await remove_item_from_cart("BTCUSDT", mock_user)
            
            assert "removed from cart" in result["message"]
            assert len(mock_cart.items) == 1
            mock_cart.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_item_not_in_cart(self, mock_user, mock_cart):
        """Test removing an item that doesn't exist in cart."""
        mock_cart.items = []
        
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart
            
            from routes.cart import remove_item_from_cart
            
            with pytest.raises(HTTPException) as exc_info:
                await remove_item_from_cart("BTCUSDT", mock_user)
            
            assert exc_info.value.status_code == 404
            assert "not found in cart" in exc_info.value.detail


class TestCheckoutCartEndpoint:
    """Test cases for /cart/checkout endpoint."""

    @pytest.mark.asyncio
    async def test_checkout_cart_success(self, mock_user, mock_cart, mock_binance_client):
        """Test checking out cart successfully."""
        cart_item = MagicMock(spec=CartItemEmbed)
        cart_item.symbol = MOCK_SYMBOL
        cart_item.order_type = OrderTypeEnum.MARKET
        cart_item.quantity = MOCK_QUANTITY
        cart_item.price = MOCK_PRICE
        mock_cart.items = [cart_item]
        
        with patch("routes.cart.client", mock_binance_client), \
             patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.cart.Order") as mock_order_cls, \
             patch("routes.cart.Transaction") as mock_tx_cls, \
             patch("routes.cart.update_or_create_portfolio", new_callable=AsyncMock), \
             patch("routes.cart.CreditsHistory.insert", new_callable=AsyncMock):
            
            mock_find.return_value = mock_cart
            mock_order_instance = MagicMock()
            mock_order_instance.id = ObjectId()
            mock_order_cls.return_value = mock_order_instance
            mock_order_cls.insert = AsyncMock(return_value=mock_order_instance)
            mock_tx_cls.insert = AsyncMock()
            
            from routes.cart import checkout_cart
            result = await checkout_cart(mock_user)
            
            assert "Cart checked out successfully" in result["message"]
            assert "total_spent" in result
            assert "num_trades" in result

    @pytest.mark.asyncio
    async def test_checkout_cart_insufficient_credits(self, mock_user, mock_cart):
        """Test checkout fails with insufficient credits."""
        mock_user.credits = Decimal("100.00")  # Not enough
        cart_item = MagicMock(spec=CartItemEmbed)
        cart_item.symbol = MOCK_SYMBOL
        cart_item.order_type = OrderTypeEnum.MARKET
        cart_item.quantity = MOCK_QUANTITY
        cart_item.price = Decimal("10000.00")
        mock_cart.items = [cart_item]
        
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.cart.client.create_order", return_value={
                 "orderId": 12345,
                 "status": "FILLED",
                 "fills": [{"qty": "0.5", "price": "10000.00"}]
             }), \
             patch("routes.cart.Order") as mock_order_cls, \
             patch("routes.cart.Transaction") as mock_tx_cls, \
             patch("routes.cart.update_or_create_portfolio", new_callable=AsyncMock), \
             patch("routes.cart.CreditsHistory.insert", new_callable=AsyncMock):
            
            mock_find.return_value = mock_cart
            mock_order_instance = MagicMock()
            mock_order_instance.id = ObjectId()
            mock_order_cls.return_value = mock_order_instance
            mock_order_cls.insert = AsyncMock(return_value=mock_order_instance)
            mock_tx_cls.insert = AsyncMock()
            
            from routes.cart import checkout_cart
            
            with pytest.raises(HTTPException) as exc_info:
                await checkout_cart(mock_user)
            
            assert exc_info.value.status_code == 400
            assert "Insufficient credits" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_checkout_cart_empty_cart(self, mock_user, mock_cart):
        """Test checkout fails with empty cart."""
        mock_cart.items = []
        
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_cart
            
            from routes.cart import checkout_cart
            
            with pytest.raises(HTTPException) as exc_info:
                await checkout_cart(mock_user)
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_checkout_cart_no_active_cart(self, mock_user):
        """Test checkout fails when no active cart exists."""
        with patch("routes.cart.Cart.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            from routes.cart import checkout_cart
            
            with pytest.raises(HTTPException) as exc_info:
                await checkout_cart(mock_user)
            
            assert exc_info.value.status_code == 400
