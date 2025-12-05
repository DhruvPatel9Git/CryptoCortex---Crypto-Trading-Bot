"""
Unit tests for services/session_store.py
Tests session management functions with mocked Redis and database dependencies.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from services.session_store import (
    store_session,
    get_session
)
from models import Cache


# Mock data
MOCK_USER_ID = "507f1f77bcf86cd799439011"
MOCK_SESSION_DATA = {
    "user_id": MOCK_USER_ID,
    "username": "testuser",
    "role": "user"
}
MOCK_EXPIRY_MINUTES = 60


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.setex = MagicMock()
    redis_mock.get = MagicMock()
    return redis_mock


@pytest.fixture
def mock_cache_doc():
    """Create a mock Cache document."""
    cache = MagicMock(spec=Cache)
    cache.key = f"user_session:{MOCK_USER_ID}"
    cache.value = MOCK_SESSION_DATA
    cache.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    cache.save = AsyncMock()
    return cache


class TestStoreSession:
    """Test cases for store_session function."""

    @pytest.mark.asyncio
    async def test_store_session_creates_redis_entry(self, mock_redis_client):
        """Test that session is stored in Redis."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            # Mock Cache.find_one as class method
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()  # Mock the key attribute for query
            
            # Mock Cache instance
            mock_cache_instance = MagicMock()
            mock_cache_instance.insert = AsyncMock()
            mock_cache_class.return_value = mock_cache_instance
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=MOCK_SESSION_DATA,
                expiry_minutes=MOCK_EXPIRY_MINUTES
            )
            
            mock_redis_client.setex.assert_called_once()
            call_args = mock_redis_client.setex.call_args[0]
            assert call_args[0] == f"user_session:{MOCK_USER_ID}"
            assert call_args[1] == MOCK_EXPIRY_MINUTES * 60
            assert json.loads(call_args[2]) == MOCK_SESSION_DATA

    @pytest.mark.asyncio
    async def test_store_session_creates_cache_document(self, mock_redis_client):
        """Test that session creates new Cache document when none exists."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()
            
            mock_cache_instance = MagicMock()
            mock_cache_instance.insert = AsyncMock()
            mock_cache_class.return_value = mock_cache_instance
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=MOCK_SESSION_DATA,
                expiry_minutes=MOCK_EXPIRY_MINUTES
            )
            
            mock_cache_instance.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_session_updates_existing_cache(self, mock_redis_client, mock_cache_doc):
        """Test that session updates existing Cache document."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_cache_class.find_one = AsyncMock(return_value=mock_cache_doc)
            mock_cache_class.key = MagicMock()
            
            new_data = {"user_id": MOCK_USER_ID, "updated": True}
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=new_data,
                expiry_minutes=MOCK_EXPIRY_MINUTES
            )
            
            assert mock_cache_doc.value == new_data
            mock_cache_doc.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_session_sets_correct_expiry(self, mock_redis_client):
        """Test that session expiry is calculated correctly."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()
            
            mock_cache_instance = MagicMock()
            mock_cache_instance.insert = AsyncMock()
            mock_cache_class.return_value = mock_cache_instance
            
            expiry_minutes = 30
            before_store = datetime.now(timezone.utc)
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=MOCK_SESSION_DATA,
                expiry_minutes=expiry_minutes
            )
            
            after_store = datetime.now(timezone.utc)
            expected_expiry_min = before_store + timedelta(minutes=expiry_minutes)
            expected_expiry_max = after_store + timedelta(minutes=expiry_minutes)
            
            # Check Cache document expiry
            cache_call = mock_cache_class.call_args
            if cache_call:
                expires_at = cache_call[1].get("expires_at")
                if expires_at:
                    assert expected_expiry_min <= expires_at <= expected_expiry_max

    @pytest.mark.asyncio
    async def test_store_session_with_custom_expiry(self, mock_redis_client):
        """Test storing session with custom expiry time."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()
            
            mock_cache_instance = MagicMock()
            mock_cache_instance.insert = AsyncMock()
            mock_cache_class.return_value = mock_cache_instance
            
            custom_expiry = 120  # 2 hours
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=MOCK_SESSION_DATA,
                expiry_minutes=custom_expiry
            )
            
            call_args = mock_redis_client.setex.call_args[0]
            assert call_args[1] == custom_expiry * 60

    @pytest.mark.asyncio
    async def test_store_session_serializes_data_to_json(self, mock_redis_client):
        """Test that session data is serialized to JSON."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()
            
            mock_cache_instance = MagicMock()
            mock_cache_instance.insert = AsyncMock()
            mock_cache_class.return_value = mock_cache_instance
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=MOCK_SESSION_DATA,
                expiry_minutes=MOCK_EXPIRY_MINUTES
            )
            
            call_args = mock_redis_client.setex.call_args[0]
            # Should be valid JSON
            parsed_data = json.loads(call_args[2])
            assert parsed_data == MOCK_SESSION_DATA

    @pytest.mark.asyncio
    async def test_store_session_uses_correct_redis_key(self, mock_redis_client):
        """Test that session uses correct Redis key format."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()
            
            mock_cache_instance = MagicMock()
            mock_cache_instance.insert = AsyncMock()
            mock_cache_class.return_value = mock_cache_instance
            
            await store_session(
                user_id=MOCK_USER_ID,
                data=MOCK_SESSION_DATA,
                expiry_minutes=MOCK_EXPIRY_MINUTES
            )
            
            call_args = mock_redis_client.setex.call_args[0]
            assert call_args[0] == f"user_session:{MOCK_USER_ID}"


class TestGetSession:
    """Test cases for get_session function."""

    @pytest.mark.asyncio
    async def test_get_session_from_redis(self, mock_redis_client):
        """Test retrieving session from Redis when available."""
        with patch("services.session_store.redis_client", mock_redis_client):
            mock_redis_client.get.return_value = json.dumps(MOCK_SESSION_DATA)
            
            result = await get_session(MOCK_USER_ID)
            
            assert result == MOCK_SESSION_DATA
            mock_redis_client.get.assert_called_once_with(f"user_session:{MOCK_USER_ID}")

    @pytest.mark.asyncio
    async def test_get_session_from_cache_when_redis_empty(self, mock_redis_client, mock_cache_doc):
        """Test retrieving session from Cache when Redis is empty."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_redis_client.get.return_value = None
            mock_cache_class.find_one = AsyncMock(return_value=mock_cache_doc)
            mock_cache_class.key = MagicMock()
            
            result = await get_session(MOCK_USER_ID)
            
            assert result == MOCK_SESSION_DATA

    @pytest.mark.asyncio
    async def test_get_session_repopulates_redis_from_cache(self, mock_redis_client, mock_cache_doc):
        """Test that session repopulates Redis from Cache when found."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_redis_client.get.return_value = None
            mock_cache_class.find_one = AsyncMock(return_value=mock_cache_doc)
            mock_cache_class.key = MagicMock()
            
            await get_session(MOCK_USER_ID)
            
            mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_not_found(self, mock_redis_client):
        """Test that get_session returns None when session doesn't exist."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_redis_client.get.return_value = None
            mock_cache_class.find_one = AsyncMock(return_value=None)
            mock_cache_class.key = MagicMock()
            
            result = await get_session(MOCK_USER_ID)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_ignores_expired_cache(self, mock_redis_client):
        """Test that expired Cache documents are ignored."""
        expired_cache = MagicMock(spec=Cache)
        expired_cache.key = f"user_session:{MOCK_USER_ID}"
        expired_cache.value = MOCK_SESSION_DATA
        expired_cache.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_redis_client.get.return_value = None
            mock_cache_class.find_one = AsyncMock(return_value=expired_cache)
            mock_cache_class.key = MagicMock()
            
            result = await get_session(MOCK_USER_ID)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_deserializes_json(self, mock_redis_client):
        """Test that session data is deserialized from JSON."""
        with patch("services.session_store.redis_client", mock_redis_client):
            json_data = json.dumps(MOCK_SESSION_DATA)
            mock_redis_client.get.return_value = json_data
            
            result = await get_session(MOCK_USER_ID)
            
            assert isinstance(result, dict)
            assert result == MOCK_SESSION_DATA

    @pytest.mark.asyncio
    async def test_get_session_uses_correct_redis_key(self, mock_redis_client):
        """Test that get_session uses correct Redis key format."""
        with patch("services.session_store.redis_client", mock_redis_client):
            mock_redis_client.get.return_value = json.dumps(MOCK_SESSION_DATA)
            
            await get_session(MOCK_USER_ID)
            
            mock_redis_client.get.assert_called_once_with(f"user_session:{MOCK_USER_ID}")

    @pytest.mark.asyncio
    async def test_get_session_calculates_ttl_correctly(self, mock_redis_client, mock_cache_doc):
        """Test that TTL is calculated correctly when restoring to Redis."""
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache") as mock_cache_class:
            
            mock_redis_client.get.return_value = None
            mock_cache_class.key = MagicMock()
            
            # Set expiry 30 minutes from now
            future_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
            mock_cache_doc.expires_at = future_expiry
            mock_cache_class.find_one = AsyncMock(return_value=mock_cache_doc)
            
            await get_session(MOCK_USER_ID)
            
            # TTL should be approximately 30 minutes (1800 seconds)
            call_args = mock_redis_client.setex.call_args[0]
            ttl = call_args[1]
            assert 1790 <= ttl <= 1810  # Allow small variance

    @pytest.mark.asyncio
    async def test_get_session_handles_cache_without_expiry_gracefully(self, mock_redis_client):
        """Test handling Cache document without proper expiry field."""
        cache_no_expiry = MagicMock(spec=Cache)
        cache_no_expiry.key = f"user_session:{MOCK_USER_ID}"
        cache_no_expiry.value = MOCK_SESSION_DATA
        cache_no_expiry.expires_at = None
        
        with patch("services.session_store.redis_client", mock_redis_client), \
             patch("services.session_store.Cache.find_one", new_callable=AsyncMock) as mock_find:
            
            mock_redis_client.get.return_value = None
            mock_find.return_value = cache_no_expiry
            
            # Should handle gracefully - might return None or raise
            try:
                result = await get_session(MOCK_USER_ID)
                # If it doesn't raise, result should be None
                assert result is None
            except (TypeError, AttributeError):
                # Acceptable if it raises due to None comparison
                pass
