"""
Unit tests for auth_routes.py
Tests all authentication-related endpoints with mocked dependencies.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from bson import ObjectId

from routes.auth_routes import router, pwd_context
from models import User, UserCreate, UserLogin, TokenResponse


# Mock user data
MOCK_USER_ID = str(ObjectId())
MOCK_USERNAME = "testuser@example.com"
MOCK_PASSWORD = "TestPassword123"
MOCK_PASSWORD_HASH = pwd_context.hash(MOCK_PASSWORD)
MOCK_ACCESS_TOKEN = "mock_access_token_12345"
MOCK_REFRESH_TOKEN = "mock_refresh_token_67890"


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock(spec=User)
    user.id = ObjectId(MOCK_USER_ID)
    user.username = MOCK_USERNAME
    user.password_hash = MOCK_PASSWORD_HASH
    user.credits = 1000.0
    user.insert = AsyncMock(return_value=user)
    user.save = AsyncMock(return_value=user)
    return user


class TestRegisterEndpoint:
    """Test cases for /register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, mock_user):
        """Test successful user registration."""
        with patch("routes.auth_routes.User") as mock_user_cls, \
             patch("routes.auth_routes.create_access_token", return_value=MOCK_ACCESS_TOKEN), \
             patch("routes.auth_routes.create_refresh_token", return_value=MOCK_REFRESH_TOKEN), \
             patch("routes.auth_routes.store_session", new_callable=AsyncMock):
            # Configure class to construct instance and provide find_one
            mock_user_cls.return_value = mock_user
            mock_user_cls.find_one = AsyncMock(return_value=None)
            
            from routes.auth_routes import register
            user_create = UserCreate(username="newuser@example.com", password="NewPass123")
            
            result = await register(user_create)
            
            assert isinstance(result, TokenResponse)
            assert result.access_token == MOCK_ACCESS_TOKEN
            assert result.refresh_token == MOCK_REFRESH_TOKEN

    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, mock_user):
        """Test registration fails when username already exists."""
        with patch("routes.auth_routes.User.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_user  # Existing user
            
            from routes.auth_routes import register
            user_create = UserCreate(username=MOCK_USERNAME, password=MOCK_PASSWORD)
            
            with pytest.raises(HTTPException) as exc_info:
                await register(user_create)
            
            assert exc_info.value.status_code == 400
            assert "already registered" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_register_stores_session(self, mock_user):
        """Test that registration stores user session."""
        with patch("routes.auth_routes.User") as mock_user_cls, \
             patch("routes.auth_routes.create_access_token", return_value=MOCK_ACCESS_TOKEN), \
             patch("routes.auth_routes.create_refresh_token", return_value=MOCK_REFRESH_TOKEN), \
             patch("routes.auth_routes.store_session", new_callable=AsyncMock) as mock_store:
            mock_user_cls.return_value = mock_user
            mock_user_cls.find_one = AsyncMock(return_value=None)
            
            from routes.auth_routes import register
            user_create = UserCreate(username="newuser@example.com", password="NewPass123")
            
            await register(user_create)
            
            mock_store.assert_called_once()


class TestLoginEndpoint:
    """Test cases for /login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success_with_json(self, mock_user):
        """Test successful login with JSON payload."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "username": MOCK_USERNAME,
            "password": MOCK_PASSWORD
        })
        
        with patch("routes.auth_routes.User.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.auth_routes.pwd_context.verify", return_value=True), \
             patch("routes.auth_routes.create_access_token", return_value=MOCK_ACCESS_TOKEN), \
             patch("routes.auth_routes.create_refresh_token", return_value=MOCK_REFRESH_TOKEN), \
             patch("routes.auth_routes.store_session", new_callable=AsyncMock):
            
            mock_find.return_value = mock_user
            
            from routes.auth_routes import login
            result = await login(mock_request, None, None)
            
            assert result.access_token == MOCK_ACCESS_TOKEN
            assert result.refresh_token == MOCK_REFRESH_TOKEN

    @pytest.mark.asyncio
    async def test_login_success_with_form_data(self, mock_user):
        """Test successful login with form data."""
        mock_request = MagicMock()
        
        with patch("routes.auth_routes.User.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.auth_routes.pwd_context.verify", return_value=True), \
             patch("routes.auth_routes.create_access_token", return_value=MOCK_ACCESS_TOKEN), \
             patch("routes.auth_routes.create_refresh_token", return_value=MOCK_REFRESH_TOKEN), \
             patch("routes.auth_routes.store_session", new_callable=AsyncMock):
            
            mock_find.return_value = mock_user
            
            from routes.auth_routes import login
            result = await login(mock_request, MOCK_USERNAME, MOCK_PASSWORD)
            
            assert result.access_token == MOCK_ACCESS_TOKEN
            assert result.refresh_token == MOCK_REFRESH_TOKEN

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_wrong_password(self, mock_user):
        """Test login fails with incorrect password."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "username": MOCK_USERNAME,
            "password": "WrongPassword"
        })
        
        with patch("routes.auth_routes.User.find_one", new_callable=AsyncMock) as mock_find, \
             patch("routes.auth_routes.pwd_context.verify", return_value=False):
            
            mock_find.return_value = mock_user
            
            from routes.auth_routes import login
            result = await login(mock_request, None, None)
            
            assert result.status_code == 401
            assert "Invalid credentials" in result.body.decode()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        """Test login fails when user doesn't exist."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "username": "nonexistent@example.com",
            "password": MOCK_PASSWORD
        })
        
        with patch("routes.auth_routes.User.find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            from routes.auth_routes import login
            result = await login(mock_request, None, None)
            
            assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_credentials(self):
        """Test login fails when credentials are missing."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={})
        
        from routes.auth_routes import login
        result = await login(mock_request, None, None)
        
        assert result.status_code == 422


class TestRefreshTokenEndpoint:
    """Test cases for /refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh."""
        with patch("routes.auth_routes.decode_access_token", return_value={"sub": MOCK_USER_ID}), \
             patch("routes.auth_routes.create_access_token", return_value="new_access_token"), \
             patch("routes.auth_routes.create_refresh_token", return_value="new_refresh_token"):
            
            from routes.auth_routes import refresh_token
            result = await refresh_token(MOCK_REFRESH_TOKEN)
            
            assert result.access_token == "new_access_token"
            assert result.refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(self):
        """Test refresh fails with invalid token."""
        with patch("routes.auth_routes.decode_access_token", return_value=None):
            
            from routes.auth_routes import refresh_token
            
            with pytest.raises(HTTPException) as exc_info:
                await refresh_token("invalid_token")
            
            assert exc_info.value.status_code == 401
            assert "Invalid refresh token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_token_missing_user_id(self):
        """Test refresh fails when token doesn't contain user ID."""
        with patch("routes.auth_routes.decode_access_token", return_value={}):
            
            from routes.auth_routes import refresh_token
            
            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(MOCK_REFRESH_TOKEN)
            
            assert exc_info.value.status_code == 401


class TestLogoutEndpoint:
    """Test cases for /logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, mock_user):
        """Test successful logout."""
        mock_redis = MagicMock()
        mock_cache_query = MagicMock()
        mock_cache_query.delete = AsyncMock()
        
        with patch("routes.auth_routes.redis_client", mock_redis), \
             patch("routes.auth_routes.Cache.find_one", return_value=mock_cache_query):
            
            from routes.auth_routes import logout
            result = await logout(mock_user)
            
            assert result["message"] == "Logged out successfully"
            mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_clears_redis_session(self, mock_user):
        """Test that logout clears Redis session."""
        mock_redis = MagicMock()
        mock_cache_query = MagicMock()
        mock_cache_query.delete = AsyncMock()
        
        with patch("routes.auth_routes.redis_client", mock_redis), \
             patch("routes.auth_routes.Cache.find_one", return_value=mock_cache_query):
            
            from routes.auth_routes import logout
            await logout(mock_user)
            
            expected_key = f"user_session:{mock_user.id}"
            mock_redis.delete.assert_called_with(expected_key)

    @pytest.mark.asyncio
    async def test_logout_clears_database_cache(self, mock_user):
        """Test that logout clears database cache."""
        mock_redis = MagicMock()
        mock_cache_query = MagicMock()
        mock_cache_query.delete = AsyncMock()
        
        with patch("routes.auth_routes.redis_client", mock_redis), \
             patch("routes.auth_routes.Cache.find_one", return_value=mock_cache_query):
            
            from routes.auth_routes import logout
            await logout(mock_user)
            
            mock_cache_query.delete.assert_called_once()
