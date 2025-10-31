#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

from diting_server.common.utils import resolve_model_config


class TestResolveModelConfig(unittest.TestCase):
    """Test cases for resolve_model_config function."""

    def test_resolve_model_config_with_all_params(self):
        """Test resolve_model_config with all parameters provided."""
        result = resolve_model_config(
            model="test-model", base_url="https://api.example.com", api_key="test-key"
        )

        expected = {
            "model": "test-model",
            "base_url": "https://api.example.com",
            "api_key": "test-key",
        }
        self.assertEqual(result, expected)

    def test_resolve_model_config_with_partial_params(self):
        """Test resolve_model_config with partial parameters."""
        with patch.dict(
            "os.environ",
            {
                "AIPROXY_API_ENDPOIN": "https://default.example.com",
                "AIPROXY_API_TOKEN": "default-token",
            },
        ):
            result = resolve_model_config(
                model="test-model", base_url="https://custom.example.com", api_key=None
            )

            expected = {
                "model": "test-model",
                "base_url": "https://custom.example.com",
                "api_key": None,
            }
            self.assertEqual(result, expected)

    def test_resolve_model_config_url_with_v1_path(self):
        """Test resolve_model_config with URL containing /v1 path."""
        result = resolve_model_config(
            model="test-model",
            base_url="https://api.example.com/v1",
            api_key="test-key",
        )

        expected = {
            "model": "test-model",
            "base_url": "https://api.example.com/v1",
            "api_key": "test-key",
        }
        self.assertEqual(result, expected)

    def test_resolve_model_config_url_with_custom_path(self):
        """Test resolve_model_config with URL containing custom path."""
        result = resolve_model_config(
            model="test-model",
            base_url="https://api.example.com/custom/path",
            api_key="test-key",
        )

        expected = {
            "model": "test-model",
            "base_url": "https://api.example.com/custom/path/v1",
            "api_key": "test-key",
        }
        self.assertEqual(result, expected)

    def test_resolve_model_config_url_with_v1_in_path(self):
        """Test resolve_model_config with URL containing /v1 in the middle of path."""
        result = resolve_model_config(
            model="test-model",
            base_url="https://api.example.com/custom/v1/endpoint",
            api_key="test-key",
        )

        expected = {
            "model": "test-model",
            "base_url": "https://api.example.com/custom/v1",
            "api_key": "test-key",
        }
        self.assertEqual(result, expected)

    def test_resolve_model_config_url_with_trailing_slash(self):
        """Test resolve_model_config with URL having trailing slash."""
        result = resolve_model_config(
            model="test-model",
            base_url="https://api.example.com/custom/",
            api_key="test-key",
        )

        expected = {
            "model": "test-model",
            "base_url": "https://api.example.com/custom/v1",
            "api_key": "test-key",
        }
        self.assertEqual(result, expected)

    def test_resolve_model_config_no_environment_variables(self):
        """Test resolve_model_config when no environment variables are set."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError) as context:
                resolve_model_config(model="test-model", base_url=None, api_key=None)

            self.assertIn("AIPROXY_API_ENDPOINT is not set", str(context.exception))
