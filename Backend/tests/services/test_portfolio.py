"""
Unit tests for services/portfolio.py
Tests all portfolio management functions with mocked dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone
from bson import ObjectId

from services.portfolio import (
    update_or_create_portfolio,
    update_portfolio_on_sell,
    get_user_by_id,
    get_user_by_id_sync
)
from models import Portfolio, User


# Mock data
MOCK_USER_ID = ObjectId()
MOCK_SYMBOL = "BTCUSDT"
MOCK_QUANTITY = Decimal("1.5")
MOCK_PRICE = Decimal("50000.00")


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock(spec=User)
    user.id = MOCK_USER_ID
    user.username = "testuser@example.com"
    return user


@pytest.fixture
def mock_portfolio():
    """Create a mock portfolio object."""
    portfolio = MagicMock(spec=Portfolio)
    portfolio.user = MagicMock()
    portfolio.user.id = MOCK_USER_ID
    portfolio.symbol = MOCK_SYMBOL
    portfolio.quantity = Decimal("2.0")
    portfolio.avg_buy_price = Decimal("48000.00")
    portfolio.updated_at = datetime.now(timezone.utc)
    portfolio.save = AsyncMock()
    portfolio.delete = AsyncMock()
    return portfolio


class TestUpdateOrCreatePortfolio:
    """Test cases for update_or_create_portfolio function."""

    @pytest.mark.asyncio
    async def test_create_new_portfolio(self, mock_user):
        """Test creating a new portfolio entry when user has no existing holdings."""
        with patch("services.portfolio.Portfolio") as mock_portfolio_class:
            # Mock find_one to return None
            mock_portfolio_class.find_one = AsyncMock(return_value=None)
            
            # Mock the Portfolio instance that will be created
            mock_portfolio_instance = MagicMock()
            mock_portfolio_instance.insert = AsyncMock()
            mock_portfolio_class.return_value = mock_portfolio_instance
            
            await update_or_create_portfolio(
                user_link=mock_user,
                symbol=MOCK_SYMBOL,
                quantity=MOCK_QUANTITY,
                price=MOCK_PRICE
            )
            
            mock_portfolio_class.find_one.assert_called_once()
            mock_portfolio_instance.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_portfolio(self, mock_user, mock_portfolio):
        """Test updating existing portfolio when user already has holdings."""
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            await update_or_create_portfolio(
                user_link=mock_user,
                symbol=MOCK_SYMBOL,
                quantity=MOCK_QUANTITY,
                price=MOCK_PRICE
            )
            
            mock_find.assert_called_once()
            mock_portfolio.save.assert_called_once()
            assert mock_portfolio.quantity > Decimal("2.0")

    @pytest.mark.asyncio
    async def test_update_calculates_weighted_average_price(self, mock_user, mock_portfolio):
        """Test that updating portfolio correctly calculates weighted average buy price."""
        original_quantity = Decimal("2.0")
        original_price = Decimal("48000.00")
        new_quantity = Decimal("1.5")
        new_price = Decimal("50000.00")
        
        mock_portfolio.quantity = original_quantity
        mock_portfolio.avg_buy_price = original_price
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            await update_or_create_portfolio(
                user_link=mock_user,
                symbol=MOCK_SYMBOL,
                quantity=new_quantity,
                price=new_price
            )
            
            expected_total_quantity = original_quantity + new_quantity
            expected_total_cost = (original_quantity * original_price) + (new_quantity * new_price)
            expected_avg_price = expected_total_cost / expected_total_quantity
            
            assert mock_portfolio.quantity == expected_total_quantity
            assert mock_portfolio.avg_buy_price == expected_avg_price
            mock_portfolio.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_sets_timestamp(self, mock_user, mock_portfolio):
        """Test that update sets updated_at timestamp."""
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            before_update = datetime.now(timezone.utc)
            
            await update_or_create_portfolio(
                user_link=mock_user,
                symbol=MOCK_SYMBOL,
                quantity=MOCK_QUANTITY,
                price=MOCK_PRICE
            )
            
            assert mock_portfolio.updated_at >= before_update
            mock_portfolio.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_string_quantity_and_price(self, mock_user):
        """Test that function correctly converts string inputs to Decimal."""
        with patch("services.portfolio.Portfolio") as mock_portfolio_class:
            # Mock find_one to return None
            mock_portfolio_class.find_one = AsyncMock(return_value=None)
            
            mock_portfolio_instance = MagicMock()
            mock_portfolio_instance.insert = AsyncMock()
            mock_portfolio_class.return_value = mock_portfolio_instance
            
            await update_or_create_portfolio(
                user_link=mock_user,
                symbol=MOCK_SYMBOL,
                quantity="1.5",  # String input
                price="50000.00"  # String input
            )
            
            mock_portfolio_class.find_one.assert_called_once()


class TestUpdatePortfolioOnSell:
    """Test cases for update_portfolio_on_sell function."""

    @pytest.mark.asyncio
    async def test_sell_partial_quantity(self, mock_portfolio):
        """Test selling partial quantity updates portfolio correctly."""
        mock_portfolio.quantity = Decimal("2.0")
        quantity_to_sell = Decimal("0.5")
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            result = await update_portfolio_on_sell(
                user_id=MOCK_USER_ID,
                symbol=MOCK_SYMBOL,
                quantity_sold=quantity_to_sell
            )
            
            assert result["status"] == "updated"
            assert result["symbol"] == MOCK_SYMBOL
            assert Decimal(result["remaining_quantity"]) == Decimal("1.5")
            mock_portfolio.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_sell_all_quantity_deletes_portfolio(self, mock_portfolio):
        """Test selling all quantity deletes the portfolio entry."""
        mock_portfolio.quantity = Decimal("1.5")
        quantity_to_sell = Decimal("1.5")
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            result = await update_portfolio_on_sell(
                user_id=MOCK_USER_ID,
                symbol=MOCK_SYMBOL,
                quantity_sold=quantity_to_sell
            )
            
            assert result["status"] == "deleted"
            assert result["symbol"] == MOCK_SYMBOL
            mock_portfolio.delete.assert_called_once()
            mock_portfolio.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_sell_no_holdings_raises_error(self):
        """Test selling when no holdings exist raises ValueError."""
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await update_portfolio_on_sell(
                    user_id=MOCK_USER_ID,
                    symbol=MOCK_SYMBOL,
                    quantity_sold=Decimal("1.0")
                )
            
            assert "No holdings found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sell_insufficient_quantity_raises_error(self, mock_portfolio):
        """Test selling more than available quantity raises ValueError."""
        mock_portfolio.quantity = Decimal("0.5")
        quantity_to_sell = Decimal("1.0")
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            with pytest.raises(ValueError) as exc_info:
                await update_portfolio_on_sell(
                    user_id=MOCK_USER_ID,
                    symbol=MOCK_SYMBOL,
                    quantity_sold=quantity_to_sell
                )
            
            assert "Insufficient quantity" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sell_quantizes_to_8_decimals(self, mock_portfolio):
        """Test that sell quantity is quantized to 8 decimal places."""
        mock_portfolio.quantity = Decimal("1.123456789")
        quantity_to_sell = Decimal("0.123456789")
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            result = await update_portfolio_on_sell(
                user_id=MOCK_USER_ID,
                symbol=MOCK_SYMBOL,
                quantity_sold=quantity_to_sell
            )
            
            remaining = Decimal(result["remaining_quantity"])
            # Check it's quantized to 8 decimals
            assert len(str(remaining).split('.')[-1]) <= 8

    @pytest.mark.asyncio
    async def test_sell_updates_timestamp(self, mock_portfolio):
        """Test that sell operation updates the timestamp."""
        mock_portfolio.quantity = Decimal("2.0")
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            before_sell = datetime.now(timezone.utc)
            
            await update_portfolio_on_sell(
                user_id=MOCK_USER_ID,
                symbol=MOCK_SYMBOL,
                quantity_sold=Decimal("0.5")
            )
            
            assert mock_portfolio.updated_at >= before_sell

    @pytest.mark.asyncio
    async def test_sell_handles_string_input(self, mock_portfolio):
        """Test that function converts string input to Decimal."""
        mock_portfolio.quantity = Decimal("2.0")
        
        with patch("services.portfolio.Portfolio.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_portfolio
            
            result = await update_portfolio_on_sell(
                user_id=MOCK_USER_ID,
                symbol=MOCK_SYMBOL,
                quantity_sold="0.5"  # String input
            )
            
            assert result["status"] == "updated"


class TestGetUserById:
    """Test cases for get_user_by_id function."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, mock_user):
        """Test successfully fetching user by ID."""
        with patch("services.portfolio.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            result = await get_user_by_id(str(MOCK_USER_ID))
            
            assert result == mock_user
            mock_get.assert_called_once_with(str(MOCK_USER_ID))

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        """Test fetching non-existent user."""
        with patch("services.portfolio.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            result = await get_user_by_id(str(MOCK_USER_ID))
            
            assert result is None


class TestGetUserByIdSync:
    """Test cases for get_user_by_id_sync function."""

    def test_get_user_by_id_sync_success(self, mock_user):
        """Test successfully fetching user synchronously."""
        with patch("services.portfolio.asyncio.run") as mock_run, \
             patch("services.portfolio.get_user_by_id", new_callable=AsyncMock) as mock_async_get:
            
            mock_async_get.return_value = mock_user
            mock_run.return_value = mock_user
            
            result = get_user_by_id_sync(str(MOCK_USER_ID))
            
            assert result == mock_user
            mock_run.assert_called_once()

    def test_get_user_by_id_sync_uses_asyncio_run(self):
        """Test that sync function uses asyncio.run to execute async function."""
        with patch("services.portfolio.asyncio.run") as mock_run:
            mock_run.return_value = None
            
            get_user_by_id_sync(str(MOCK_USER_ID))
            
            mock_run.assert_called_once()
