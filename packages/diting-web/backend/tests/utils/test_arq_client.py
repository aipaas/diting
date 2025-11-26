"""Tests for ARQ Client Redis URL parsing."""

import pytest
from unittest.mock import MagicMock, patch
from arq.connections import RedisSettings

from diting_web.utils.arq_client import ARQClient


class TestARQClientRedisURLParsing:
    """Tests for Redis URL parsing in ARQ Client.
    
    This test suite verifies the fix for:
    - Issue: Simple string split parsing couldn't handle passwords, TLS, IPv6, etc.
    - Fix: Use urllib.parse for robust URL parsing supporting all Redis URL formats
    """

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_basic_redis_url(self, mock_get_settings):
        """Test parsing basic Redis URL without password."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "localhost"
        assert client.redis_settings.port == 6379
        assert client.redis_settings.database == 0
        assert client.redis_settings.password is None
        assert client.redis_settings.ssl is False

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_with_password(self, mock_get_settings):
        """Test parsing Redis URL with password (production scenario)."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://:mypassword123@redis.example.com:6379/1"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "redis.example.com"
        assert client.redis_settings.port == 6379
        assert client.redis_settings.database == 1
        assert client.redis_settings.password == "mypassword123"
        assert client.redis_settings.ssl is False

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_with_username_and_password(self, mock_get_settings):
        """Test parsing Redis URL with username and password."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://user:pass@redis.example.com:6379/2"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "redis.example.com"
        assert client.redis_settings.port == 6379
        assert client.redis_settings.database == 2
        assert client.redis_settings.password == "pass"
        assert client.redis_settings.ssl is False

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_rediss_url_with_tls(self, mock_get_settings):
        """Test parsing Redis URL with TLS (rediss://)."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "rediss://:secure_password@redis-tls.example.com:6380/0"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "redis-tls.example.com"
        assert client.redis_settings.port == 6380
        assert client.redis_settings.database == 0
        assert client.redis_settings.password == "secure_password"
        assert client.redis_settings.ssl is True  # TLS enabled

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_default_values(self, mock_get_settings):
        """Test parsing Redis URL with minimal info uses defaults."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://myhost"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "myhost"
        assert client.redis_settings.port == 6379  # Default port
        assert client.redis_settings.database == 0  # Default database
        assert client.redis_settings.password is None
        assert client.redis_settings.ssl is False

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_custom_port(self, mock_get_settings):
        """Test parsing Redis URL with custom port."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://localhost:7000/5"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "localhost"
        assert client.redis_settings.port == 7000
        assert client.redis_settings.database == 5

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_without_database(self, mock_get_settings):
        """Test parsing Redis URL without database number."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://localhost:6379"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "localhost"
        assert client.redis_settings.port == 6379
        assert client.redis_settings.database == 0  # Default to 0

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_with_slash_but_no_db(self, mock_get_settings):
        """Test parsing Redis URL with trailing slash but no database number."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.redis_url = "redis://localhost:6379/"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.database == 0  # Default to 0

    @patch("diting_web.utils.arq_client.get_settings")
    def test_parse_redis_url_with_special_chars_in_password(self, mock_get_settings):
        """Test parsing Redis URL with special characters in password."""
        # Arrange
        mock_settings = MagicMock()
        # Password with special chars: p@ss:w/rd
        mock_settings.redis_url = "redis://:p%40ss%3Aw%2Frd@localhost:6379/0"
        mock_get_settings.return_value = mock_settings

        # Act
        client = ARQClient()

        # Assert
        assert client.redis_settings.host == "localhost"
        # URL-encoded password should be decoded by urlparse
        assert client.redis_settings.password == "p@ss:w/rd"

