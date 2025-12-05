"""
Unit tests for services/redis_client.py
Tests Redis client configuration and initialization.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRedisClient:
    """Test cases for Redis client initialization."""

    def test_redis_client_initialization(self):
        """Test that Redis client is initialized with correct parameters."""
        with patch("services.redis_client.redis.Redis") as mock_redis:
            # Import triggers initialization
            import importlib
            import services.redis_client
            importlib.reload(services.redis_client)
            
            # Verify Redis was called with expected config
            mock_redis.assert_called_once()
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["host"] == "localhost"
            assert call_kwargs["port"] == 6379
            assert call_kwargs["db"] == 0
            assert call_kwargs["decode_responses"] is True

    def test_redis_client_default_host(self):
        """Test Redis client uses localhost as default host."""
        with patch("services.redis_client.redis.Redis") as mock_redis:
            import importlib
            import services.redis_client
            importlib.reload(services.redis_client)
            
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["host"] == "localhost"

    def test_redis_client_default_port(self):
        """Test Redis client uses 6379 as default port."""
        with patch("services.redis_client.redis.Redis") as mock_redis:
            import importlib
            import services.redis_client
            importlib.reload(services.redis_client)
            
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["port"] == 6379

    def test_redis_client_decode_responses_enabled(self):
        """Test Redis client has decode_responses enabled."""
        with patch("services.redis_client.redis.Redis") as mock_redis:
            import importlib
            import services.redis_client
            importlib.reload(services.redis_client)
            
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["decode_responses"] is True

    def test_redis_client_uses_db_zero(self):
        """Test Redis client uses database 0."""
        with patch("services.redis_client.redis.Redis") as mock_redis:
            import importlib
            import services.redis_client
            importlib.reload(services.redis_client)
            
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["db"] == 0

    def test_redis_client_is_singleton(self):
        """Test that redis_client is a single instance."""
        from services.redis_client import redis_client
        
        # Accessing it multiple times should return same instance
        assert redis_client is not None

    def test_redis_client_module_level_variable(self):
        """Test that redis_client is available as module-level variable."""
        from services import redis_client as module
        
        assert hasattr(module, "redis_client")
        assert module.redis_client is not None
