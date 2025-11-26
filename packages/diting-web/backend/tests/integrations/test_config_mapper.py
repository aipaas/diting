"""Tests for model_helpers module."""

import pytest
from unittest.mock import MagicMock, patch

from diting_web.utils.model_helpers import (
    create_embedding_from_config,
    create_llm_from_config,
    get_default_embedding_config,
    get_default_llm_config,
)


class TestCreateLLMFromConfig:
    """Tests for create_llm_from_config function."""

    @patch("diting_web.utils.model_helpers.llm_factory")
    def test_create_llm_with_basic_config(self, mock_llm_factory):
        """Test creating LLM with basic configuration."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        config = {
            "model_name": "gpt-4",
            "api_key": "sk-test",
            "base_url": "http://test.com",
            "timeout": 60.0,
        }

        # Act
        llm = create_llm_from_config(config)

        # Assert
        assert llm == mock_llm
        mock_llm_factory.assert_called_once_with(
            model="gpt-4",
            api_key="sk-test",
            base_url="http://test.com",
            timeout=60.0,
        )

    @patch("diting_web.utils.model_helpers.llm_factory")
    def test_create_llm_with_additional_params(self, mock_llm_factory):
        """Test creating LLM with additional parameters."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        config = {
            "model_name": "gpt-4",
            "api_key": "sk-test",
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
        }

        # Act
        llm = create_llm_from_config(config)

        # Assert
        mock_llm_factory.assert_called_once()
        call_kwargs = mock_llm_factory.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["top_p"] == 0.9

    @patch("diting_web.utils.model_helpers.llm_factory")
    def test_create_llm_with_defaults(self, mock_llm_factory):
        """Test creating LLM uses defaults when not specified."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        config = {}

        # Act
        llm = create_llm_from_config(config)

        # Assert
        call_kwargs = mock_llm_factory.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"  # Default model
        assert call_kwargs["timeout"] == 60.0  # Default timeout

    @patch("diting_web.utils.model_helpers.llm_factory")
    def test_create_llm_raises_on_error(self, mock_llm_factory):
        """Test that errors from llm_factory are propagated."""
        # Arrange
        mock_llm_factory.side_effect = ValueError("Invalid model")

        config = {"model_name": "invalid-model"}

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid model"):
            create_llm_from_config(config)


class TestCreateEmbeddingFromConfig:
    """Tests for create_embedding_from_config function."""

    @patch("diting_web.utils.model_helpers.embedding_factory")
    def test_create_embedding_with_basic_config(self, mock_embedding_factory):
        """Test creating embedding with basic configuration."""
        # Arrange
        mock_embedding = MagicMock()
        mock_embedding_factory.return_value = mock_embedding

        config = {
            "model_name": "text-embedding-ada-002",
            "api_key": "sk-test",
            "base_url": "http://test.com",
            "timeout": 60.0,
        }

        # Act
        embedding = create_embedding_from_config(config)

        # Assert
        assert embedding == mock_embedding
        mock_embedding_factory.assert_called_once_with(
            model="text-embedding-ada-002",
            api_key="sk-test",
            base_url="http://test.com",
            timeout=60.0,
        )

    @patch("diting_web.utils.model_helpers.embedding_factory")
    def test_create_embedding_with_defaults(self, mock_embedding_factory):
        """Test creating embedding uses defaults when not specified."""
        # Arrange
        mock_embedding = MagicMock()
        mock_embedding_factory.return_value = mock_embedding

        config = {}

        # Act
        embedding = create_embedding_from_config(config)

        # Assert
        call_kwargs = mock_embedding_factory.call_args[1]
        assert call_kwargs["model"] == "bge-m3"  # Default model
        assert call_kwargs["timeout"] == 60.0  # Default timeout


class TestGetDefaultConfigs:
    """Tests for get_default_*_config functions."""

    @patch("diting_web.utils.model_helpers.get_settings")
    def test_get_default_llm_config(self, mock_get_settings):
        """Test getting default LLM config from settings."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.default_llm_model = "gpt-4"
        mock_settings.llm_base_url = "http://test.com"
        mock_settings.llm_api_key = "sk-test"
        mock_settings.llm_timeout = 30.0
        mock_get_settings.return_value = mock_settings

        # Act
        config = get_default_llm_config()

        # Assert
        assert config["model_name"] == "gpt-4"
        assert config["base_url"] == "http://test.com"
        assert config["api_key"] == "sk-test"
        assert config["timeout"] == 30.0

    @patch("diting_web.utils.model_helpers.get_settings")
    def test_get_default_embedding_config(self, mock_get_settings):
        """Test getting default embedding config from settings."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.default_embedding_model = "bge-m3"
        mock_settings.embedding_base_url = "http://test.com"
        mock_settings.embedding_api_key = "sk-test"
        mock_settings.embedding_timeout = 30.0
        mock_get_settings.return_value = mock_settings

        # Act
        config = get_default_embedding_config()

        # Assert
        assert config["model_name"] == "bge-m3"
        assert config["base_url"] == "http://test.com"
        assert config["api_key"] == "sk-test"
        assert config["timeout"] == 30.0

    @patch("diting_web.utils.model_helpers.get_settings")
    def test_get_default_config_handles_missing_attributes(self, mock_get_settings):
        """Test that default configs handle missing settings attributes."""
        # Arrange
        mock_settings = MagicMock()
        # Remove some attributes
        delattr(type(mock_settings), "default_llm_model")
        mock_get_settings.return_value = mock_settings

        # Act
        config = get_default_llm_config()

        # Assert - should use hardcoded defaults
        assert config["model_name"] == "gpt-4o-mini"



