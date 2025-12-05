"""
Unit tests for portfolio.py
Tests portfolio-related endpoints with mocked dependencies.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from decimal import Decimal

from routes.portfolio import router
from models import Portfolio


# Mock data
MOCK_USER_ID = str(ObjectId())


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = ObjectId(MOCK_USER_ID)
    user.username = "testuser@example.com"
    return user


@pytest.fixture
def mock_portfolios():
    """Create mock portfolio objects."""
    portfolios = []
    symbols = ["BTCUSDT", "ETHUSDT"]
    for symbol in symbols:
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user = MagicMock()
        portfolio.user.id = ObjectId(MOCK_USER_ID)
        portfolio.symbol = symbol
        portfolio.quantity = Decimal("10.5")
        portfolio.avg_buy_price = Decimal("50000.00")
        portfolios.append(portfolio)
    return portfolios


class TestGetUserPortfolioEndpoint:
    """Test cases for /portfolio/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_portfolio_success(self, mock_user, mock_portfolios):
        """Test getting user portfolio successfully."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_portfolios)
        
        with patch("routes.portfolio.Portfolio.find", return_value=mock_query):
            from routes.portfolio import get_user_portfolio
            
            result = await get_user_portfolio(MOCK_USER_ID, mock_user)
            
            assert len(result) == 2
            assert result == mock_portfolios

    @pytest.mark.asyncio
    async def test_get_user_portfolio_empty(self, mock_user):
        """Test getting portfolio when user has no holdings."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.portfolio.Portfolio.find", return_value=mock_query):
            from routes.portfolio import get_user_portfolio
            
            result = await get_user_portfolio(MOCK_USER_ID, mock_user)
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_user_portfolio_invalid_user_id(self, mock_user):
        """Test getting portfolio with invalid user ID format."""
        from routes.portfolio import get_user_portfolio
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user_portfolio("invalid_id", mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Invalid user ID format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_portfolio_unauthorized_access(self, mock_user):
        """Test that users cannot view other users' portfolios."""
        different_user_id = str(ObjectId())
        
        from routes.portfolio import get_user_portfolio
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user_portfolio(different_user_id, mock_user)
        
        assert exc_info.value.status_code == 403
        assert "not allowed to view this portfolio" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_portfolio_queries_correct_user(self, mock_user, mock_portfolios):
        """Test that portfolio query filters by correct user ID."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_portfolios)
        
        with patch("routes.portfolio.Portfolio.find", return_value=mock_query) as mock_find:
            from routes.portfolio import get_user_portfolio
            
            await get_user_portfolio(MOCK_USER_ID, mock_user)
            
            # Verify the find was called with user.$id filter
            mock_find.assert_called_once()
            call_args = mock_find.call_args[0][0]
            assert "user.$id" in call_args

    @pytest.mark.asyncio
    async def test_get_user_portfolio_returns_list_of_portfolios(self, mock_user, mock_portfolios):
        """Test that endpoint returns a list of Portfolio objects."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_portfolios)
        
        with patch("routes.portfolio.Portfolio.find", return_value=mock_query):
            from routes.portfolio import get_user_portfolio
            
            result = await get_user_portfolio(MOCK_USER_ID, mock_user)
            
            assert isinstance(result, list)
            assert all(hasattr(p, 'symbol') for p in result)
            assert all(hasattr(p, 'quantity') for p in result)

    @pytest.mark.asyncio
    async def test_get_user_portfolio_requires_authentication(self):
        """Test that portfolio endpoint requires authentication."""
        from routes.portfolio import get_user_portfolio
        import inspect
        
        sig = inspect.signature(get_user_portfolio)
        assert "current_user" in sig.parameters

    @pytest.mark.asyncio
    async def test_get_user_portfolio_with_objectid(self, mock_user, mock_portfolios):
        """Test getting portfolio with ObjectId conversion."""
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=mock_portfolios)
        
        with patch("routes.portfolio.Portfolio.find", return_value=mock_query), \
             patch("routes.portfolio.PydanticObjectId") as mock_pydantic_id:
            
            mock_pydantic_id.return_value = ObjectId(MOCK_USER_ID)
            
            from routes.portfolio import get_user_portfolio
            
            result = await get_user_portfolio(MOCK_USER_ID, mock_user)
            
            # Verify PydanticObjectId was called with the user_id
            mock_pydantic_id.assert_called_once_with(MOCK_USER_ID)

    @pytest.mark.asyncio
    async def test_get_user_portfolio_multiple_holdings(self, mock_user):
        """Test getting portfolio with multiple holdings."""
        many_portfolios = []
        for i, symbol in enumerate(["BTCUSDT", "ETHUSDT", "ADAUSDT", "BNBUSDT"]):
            portfolio = MagicMock(spec=Portfolio)
            portfolio.symbol = symbol
            portfolio.quantity = Decimal(str(10 + i))
            portfolio.avg_buy_price = Decimal(str(1000 * (i + 1)))
            many_portfolios.append(portfolio)
        
        mock_query = MagicMock()
        mock_query.to_list = AsyncMock(return_value=many_portfolios)
        
        with patch("routes.portfolio.Portfolio.find", return_value=mock_query):
            from routes.portfolio import get_user_portfolio
            
            result = await get_user_portfolio(MOCK_USER_ID, mock_user)
            
            assert len(result) == 4
            symbols = [p.symbol for p in result]
            assert "BTCUSDT" in symbols
            assert "ETHUSDT" in symbols
            assert "ADAUSDT" in symbols
            assert "BNBUSDT" in symbols
