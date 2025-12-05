"""Shared pytest fixtures and configuration for route tests.

Adds project root to ``sys.path`` so tests can import the backend ``routes``
package using ``from routes.x import ...`` without relative imports.
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from decimal import Decimal

# Ensure the Backend root directory is on sys.path for module resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # .../Backend/tests -> parent is Backend
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def mock_object_id():
    """Provide a reusable ObjectId."""
    return ObjectId()


@pytest.fixture
def base_mock_user(mock_object_id):
    """
    Create a base mock user object with common attributes.
    Tests can override specific attributes as needed.
    """
    user = MagicMock()
    user.id = mock_object_id
    user.username = "testuser@example.com"
    user.password_hash = "$2b$12$mockhashedpassword"
    user.credits = Decimal("1000.00")
    user.created_at = MagicMock()
    user.updated_at = MagicMock()
    user.save = AsyncMock()
    user.insert = AsyncMock()
    user.delete = AsyncMock()
    return user


@pytest.fixture
def mock_binance_client_factory():
    """
    Factory fixture for creating mock Binance clients with custom responses.
    """
    def create_mock_client(
        ticker_price="50000.00",
        account_balances=None,
        order_response=None
    ):
        client = MagicMock()
        
        # Default ticker response
        client.get_symbol_ticker = MagicMock(
            return_value={"price": ticker_price}
        )
        
        # Default account info
        if account_balances is None:
            account_balances = [
                {"asset": "BTC", "free": "1.0", "locked": "0.0"},
                {"asset": "USDT", "free": "10000.0", "locked": "0.0"}
            ]
        client.get_account = MagicMock(
            return_value={"balances": account_balances}
        )
        
        # Default order response
        if order_response is None:
            order_response = {
                "orderId": 12345,
                "status": "FILLED",
                "fills": [{"qty": "0.5", "price": "50000.00"}]
            }
        client.create_order = MagicMock(return_value=order_response)
        
        return client
    
    return create_mock_client


@pytest.fixture
def mock_database_query():
    """
    Create a mock database query object for Beanie operations.
    """
    query = MagicMock()
    query.find = MagicMock(return_value=query)
    query.find_one = AsyncMock()
    query.skip = MagicMock(return_value=query)
    query.limit = MagicMock(return_value=query)
    query.sort = MagicMock(return_value=query)
    query.to_list = AsyncMock(return_value=[])
    query.count = AsyncMock(return_value=0)
    query.save = AsyncMock()
    query.insert = AsyncMock()
    query.delete = AsyncMock()
    return query


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    import asyncio
    return asyncio.get_event_loop_policy()
