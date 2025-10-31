#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from diting_core.callbacks.usage import (
    count_tokens,
    BaseTokenCallbackHandler,
    GetEmbedTokenCallbackHandler,
    GetLLMTokenCallbackHandler,
    Usage,
    compute_token_usages,
    ModelType,
)
from diting_core.callbacks.base import ChainType


class TestUsage:
    """Test cases for Usage class."""

    def test_usage_creation_required_fields(self):
        """Test Usage creation with required fields."""
        usage = Usage(model_type=ModelType.LLM)
        assert usage.model_type == ModelType.LLM
        assert usage.prompt_tokens is None
        assert usage.completion_tokens is None
        assert usage.total_tokens is None

    def test_usage_creation_all_fields(self):
        """Test Usage creation with all fields."""
        usage = Usage(
            model_type=ModelType.LLM,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert usage.model_type == ModelType.LLM
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_usage_with_embed_model(self):
        """Test Usage with embedding model."""
        usage = Usage(model_type=ModelType.EMBED, prompt_tokens=200, total_tokens=200)
        assert usage.model_type == ModelType.EMBED
        assert usage.prompt_tokens == 200
        assert usage.total_tokens == 200

    def test_usage_camel_case_alias(self):
        """Test Usage with camelCase aliases."""
        usage = Usage(
            modelType=ModelType.LLM,
            promptTokens=100,
            completionTokens=50,
            totalTokens=150,
        )
        assert usage.model_type == ModelType.LLM
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_usage_validation(self):
        """Test Usage field validation."""
        # Valid usage
        usage = Usage(model_type=ModelType.LLM, prompt_tokens=0)
        assert usage.prompt_tokens == 0

        # Test with negative values (should be allowed as they're Optional[int])
        usage = Usage(model_type=ModelType.LLM, prompt_tokens=-1)
        assert usage.prompt_tokens == -1

    def test_usage_serialization(self):
        """Test Usage serialization."""
        usage = Usage(
            model_type=ModelType.LLM,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        # Test dict conversion
        usage_dict = usage.model_dump()
        expected = {
            "model_type": "llm",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        assert usage_dict == expected

        # Test camelCase serialization
        usage_dict_camel = usage.model_dump(by_alias=True)
        expected_camel = {
            "modelType": "llm",
            "promptTokens": 100,
            "completionTokens": 50,
            "totalTokens": 150,
        }
        assert usage_dict_camel == expected_camel


class TestCountTokens(unittest.TestCase):
    """Test cases for count_tokens function."""

    def test_count_tokens_string(self):
        """Test count_tokens with string input."""
        text = "Hello world"
        result = count_tokens(text)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_count_tokens_list(self):
        """Test count_tokens with list input."""
        texts = ["Hello", "world", "test"]
        result = count_tokens(texts)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_count_tokens_empty_string(self):
        """Test count_tokens with empty string."""
        result = count_tokens("")
        self.assertEqual(result, 0)

    def test_count_tokens_empty_list(self):
        """Test count_tokens with empty list."""
        result = count_tokens([])
        self.assertEqual(result, 0)

    def test_count_tokens_unicode(self):
        """Test count_tokens with unicode text."""
        text = "你好世界"
        result = count_tokens(text)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_count_tokens_invalid_type(self):
        """Test count_tokens with invalid input type."""
        with self.assertRaises(ValueError):
            count_tokens(123)

    def test_count_tokens_mixed_list(self):
        """Test count_tokens with mixed content list."""
        texts = ["Hello", "世界", "test"]
        result = count_tokens(texts)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)


class TestBaseTokenCallbackHandler(unittest.TestCase):
    """Test cases for BaseTokenCallbackHandler class."""

    def test_init(self):
        """Test BaseTokenCallbackHandler initialization."""
        handler = BaseTokenCallbackHandler()
        self.assertEqual(handler.usages, [])

    def test_append_usage_llm(self):
        """Test _append_usage with LLM model type."""
        handler = BaseTokenCallbackHandler()
        handler._append_usage(ModelType.LLM, 100, 50)

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.LLM)
        self.assertEqual(usage.prompt_tokens, 100)
        self.assertEqual(usage.completion_tokens, 50)
        self.assertEqual(usage.total_tokens, 150)

    def test_append_usage_embed(self):
        """Test _append_usage with embedding model type."""
        handler = BaseTokenCallbackHandler()
        handler._append_usage(ModelType.EMBED, 200)

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.EMBED)
        self.assertEqual(usage.prompt_tokens, 200)
        self.assertEqual(usage.completion_tokens, 0)
        self.assertEqual(usage.total_tokens, 200)

    def test_append_usage_multiple(self):
        """Test _append_usage with multiple usages."""
        handler = BaseTokenCallbackHandler()
        handler._append_usage(ModelType.LLM, 100, 50)
        handler._append_usage(ModelType.EMBED, 200)

        self.assertEqual(len(handler.usages), 2)
        self.assertEqual(handler.usages[0].model_type, ModelType.LLM)
        self.assertEqual(handler.usages[1].model_type, ModelType.EMBED)


class TestGetEmbedTokenCallbackHandler(unittest.IsolatedAsyncioTestCase):
    """Test cases for GetEmbedTokenCallbackHandler class."""

    def test_init(self):
        """Test GetEmbedTokenCallbackHandler initialization."""
        handler = GetEmbedTokenCallbackHandler()
        self.assertEqual(handler.usages, [])

    async def test_on_chain_end_embed_chain_with_usage(self):
        """Test on_chain_end with embed chain type and usage in result."""
        handler = GetEmbedTokenCallbackHandler()

        # Mock usage object
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 0
        mock_usage.total_tokens = 100

        # Mock embed result with usage
        mock_result = MagicMock()
        mock_result.usage = mock_usage

        outputs = {"result": mock_result}
        run_id = uuid4()

        await handler.on_chain_end(
            outputs=outputs, run_id=run_id, chain_type=ChainType.EMBED
        )

        self.assertEqual(len(handler.usages), 1)
        self.assertEqual(handler.usages[0], mock_usage)

    async def test_on_chain_end_embed_chain_without_usage(self):
        """Test on_chain_end with embed chain type but no usage in result."""
        handler = GetEmbedTokenCallbackHandler()

        # Mock embed result without usage
        mock_result = MagicMock()
        mock_result.usage = None

        outputs = {"result": mock_result}
        inputs = {"embed_input": "test input"}
        run_id = uuid4()

        with patch("diting_core.callbacks.usage.count_tokens", return_value=10):
            await handler.on_chain_end(
                outputs=outputs,
                run_id=run_id,
                chain_type=ChainType.EMBED,
                inputs=inputs,
            )

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.EMBED)
        self.assertEqual(usage.prompt_tokens, 10)
        self.assertEqual(usage.completion_tokens, 0)
        self.assertEqual(usage.total_tokens, 10)

    async def test_on_chain_end_non_embed_chain(self):
        """Test on_chain_end with non-embed chain type."""
        handler = GetEmbedTokenCallbackHandler()

        outputs = {"result": MagicMock()}
        run_id = uuid4()

        await handler.on_chain_end(
            outputs=outputs,
            run_id=run_id,
            chain_type=ChainType.LLM,  # Different chain type
        )

        self.assertEqual(len(handler.usages), 0)

    async def test_on_chain_end_no_result(self):
        """Test on_chain_end with no result in outputs."""
        handler = GetEmbedTokenCallbackHandler()

        outputs = {}
        inputs = {"embed_input": "test input"}
        run_id = uuid4()

        with patch("diting_core.callbacks.usage.count_tokens", return_value=5):
            await handler.on_chain_end(
                outputs=outputs,
                run_id=run_id,
                chain_type=ChainType.EMBED,
                inputs=inputs,
            )

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.EMBED)
        self.assertEqual(usage.prompt_tokens, 5)


class TestGetLLMTokenCallbackHandler(unittest.IsolatedAsyncioTestCase):
    """Test cases for GetLLMTokenCallbackHandler class."""

    def test_init(self):
        """Test GetLLMTokenCallbackHandler initialization."""
        handler = GetLLMTokenCallbackHandler()
        self.assertEqual(handler.usages, [])

    async def test_on_chain_end_llm_chain_with_token_usage(self):
        """Test on_chain_end with LLM chain type and token_usage in llm_output."""
        handler = GetLLMTokenCallbackHandler()

        # Mock token usage
        mock_token_usage = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        # Mock LLM result with token usage
        mock_llm_output = {"token_usage": mock_token_usage}
        mock_llm_result = MagicMock()
        mock_llm_result.llm_output = mock_llm_output

        outputs = {"llm_result": mock_llm_result}
        run_id = uuid4()

        await handler.on_chain_end(
            outputs=outputs, run_id=run_id, chain_type=ChainType.LLM
        )

        self.assertEqual(len(handler.usages), 1)
        self.assertEqual(handler.usages[0], mock_token_usage)

    async def test_on_chain_end_llm_chain_without_token_usage(self):
        """Test on_chain_end with LLM chain type but no token_usage."""
        handler = GetLLMTokenCallbackHandler()

        # Mock LLM result without token usage
        mock_llm_output = {}
        mock_llm_result = MagicMock()
        mock_llm_result.llm_output = mock_llm_output

        # Mock generations
        mock_generation = MagicMock()
        mock_generation.text = "test response"
        mock_llm_result.generations = [[mock_generation]]

        outputs = {"llm_result": mock_llm_result}
        inputs = {"prompt": "test prompt"}
        run_id = uuid4()

        with patch("diting_core.callbacks.usage.count_tokens", side_effect=[10, 5]):
            await handler.on_chain_end(
                outputs=outputs, run_id=run_id, chain_type=ChainType.LLM, inputs=inputs
            )

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.LLM)
        self.assertEqual(usage.prompt_tokens, 10)
        self.assertEqual(usage.completion_tokens, 5)
        self.assertEqual(usage.total_tokens, 15)

    async def test_on_chain_end_non_llm_chain(self):
        """Test on_chain_end with non-LLM chain type."""
        handler = GetLLMTokenCallbackHandler()

        outputs = {"llm_result": MagicMock()}
        run_id = uuid4()

        await handler.on_chain_end(
            outputs=outputs,
            run_id=run_id,
            chain_type=ChainType.EMBED,  # Different chain type
        )

        self.assertEqual(len(handler.usages), 0)

    async def test_on_chain_end_no_llm_result(self):
        """Test on_chain_end with no llm_result in outputs."""
        handler = GetLLMTokenCallbackHandler()

        # Mock llm_result with generations but no token_usage
        mock_llm_output = {}
        mock_llm_result = MagicMock()
        mock_llm_result.llm_output = mock_llm_output

        # Mock generations
        mock_generation = MagicMock()
        mock_generation.text = "test response"
        mock_llm_result.generations = [[mock_generation]]

        outputs = {"llm_result": mock_llm_result}
        inputs = {"prompt": "test prompt"}
        run_id = uuid4()

        with patch("diting_core.callbacks.usage.count_tokens", side_effect=[8, 8]):
            await handler.on_chain_end(
                outputs=outputs, run_id=run_id, chain_type=ChainType.LLM, inputs=inputs
            )

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.LLM)
        self.assertEqual(usage.prompt_tokens, 8)
        self.assertEqual(usage.completion_tokens, 8)
        self.assertEqual(usage.total_tokens, 16)

    async def test_on_chain_end_no_prompt_in_inputs(self):
        """Test on_chain_end with no prompt in inputs."""
        handler = GetLLMTokenCallbackHandler()

        # Mock llm_result with generations but no token_usage
        mock_llm_output = {}
        mock_llm_result = MagicMock()
        mock_llm_result.llm_output = mock_llm_output

        # Mock generations
        mock_generation = MagicMock()
        mock_generation.text = "test response"
        mock_llm_result.generations = [[mock_generation]]

        outputs = {"llm_result": mock_llm_result}
        inputs = {}
        run_id = uuid4()

        with patch("diting_core.callbacks.usage.count_tokens", return_value=3):
            await handler.on_chain_end(
                outputs=outputs, run_id=run_id, chain_type=ChainType.LLM, inputs=inputs
            )

        self.assertEqual(len(handler.usages), 1)
        usage = handler.usages[0]
        self.assertEqual(usage.model_type, ModelType.LLM)
        self.assertEqual(usage.prompt_tokens, 0)  # No prompt provided
        self.assertEqual(usage.completion_tokens, 3)
        self.assertEqual(usage.total_tokens, 3)


class TestModelType:
    """Test cases for ModelType enum."""

    def test_model_type_values(self):
        """Test ModelType enum values."""
        assert ModelType.LLM == "llm"
        assert ModelType.EMBED == "embed"

    def test_model_type_string_enum(self):
        """Test that ModelType is a string enum."""
        assert isinstance(ModelType.LLM, str)
        assert isinstance(ModelType.EMBED, str)

    def test_model_type_comparison(self):
        """Test ModelType comparison."""
        assert ModelType.LLM == "llm"
        assert ModelType.EMBED == "embed"
        assert ModelType.LLM != ModelType.EMBED


class TestComputeTokenUsage(unittest.TestCase):
    """Test cases for compute_token_usages function."""

    def test_compute_token_usages_empty_lists(self):
        """Test compute_token_usages with empty lists."""
        result = compute_token_usages([], [])
        self.assertEqual(result, [])

    def test_compute_token_usages_embed_only(self):
        """Test compute_token_usages with embedding usage only."""
        # Mock embedding usage objects
        embed_usage1 = MagicMock()
        embed_usage1.prompt_tokens = 100
        embed_usage1.completion_tokens = 0
        embed_usage1.total_tokens = 100

        embed_usage2 = MagicMock()
        embed_usage2.prompt_tokens = 50
        embed_usage2.completion_tokens = 0
        embed_usage2.total_tokens = 50

        embed_usages = [embed_usage1, embed_usage2]
        llm_usages = []

        result = compute_token_usages(llm_usages, embed_usages)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_type, ModelType.EMBED)
        self.assertEqual(result[0].prompt_tokens, 150)  # 100 + 50
        self.assertEqual(result[0].completion_tokens, 0)
        self.assertEqual(result[0].total_tokens, 150)  # 100 + 50

    def test_compute_token_usages_llm_only(self):
        """Test compute_token_usages with LLM usage only."""
        llm_usages = [
            {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
            {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225},
        ]
        embed_usages = []

        result = compute_token_usages(llm_usages, embed_usages)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_type, ModelType.LLM)
        self.assertEqual(result[0].prompt_tokens, 350)  # 200 + 150
        self.assertEqual(result[0].completion_tokens, 175)  # 100 + 75
        self.assertEqual(result[0].total_tokens, 525)  # 300 + 225

    def test_compute_token_usages_both_types(self):
        """Test compute_token_usages with both LLM and embedding usage."""
        # Mock embedding usage
        embed_usage = MagicMock()
        embed_usage.prompt_tokens = 100
        embed_usage.completion_tokens = 0
        embed_usage.total_tokens = 100

        llm_usages = [
            {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
        ]
        embed_usages = [embed_usage]

        result = compute_token_usages(llm_usages, embed_usages)

        self.assertEqual(len(result), 2)

        # Check embedding usage
        embed_result = next(r for r in result if r.model_type == ModelType.EMBED)
        self.assertEqual(embed_result.prompt_tokens, 100)
        self.assertEqual(embed_result.completion_tokens, 0)
        self.assertEqual(embed_result.total_tokens, 100)

        # Check LLM usage
        llm_result = next(r for r in result if r.model_type == ModelType.LLM)
        self.assertEqual(llm_result.prompt_tokens, 200)
        self.assertEqual(llm_result.completion_tokens, 100)
        self.assertEqual(llm_result.total_tokens, 300)

    def test_compute_token_usages_missing_completion_tokens(self):
        """Test compute_token_usages with missing completion_tokens in LLM usage."""
        llm_usages = [
            {"prompt_tokens": 200, "total_tokens": 200},  # Missing completion_tokens
            {"prompt_tokens": 150, "completion_tokens": 75, "total_tokens": 225},
        ]
        embed_usages = []

        result = compute_token_usages(llm_usages, embed_usages)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_type, ModelType.LLM)
        self.assertEqual(result[0].prompt_tokens, 350)  # 200 + 150
        self.assertEqual(
            result[0].completion_tokens, 75
        )  # 0 + 75 (missing treated as 0)
        self.assertEqual(result[0].total_tokens, 425)  # 200 + 225

    def test_compute_token_usages_zero_values(self):
        """Test compute_token_usages with zero values."""
        llm_usages = [{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}]
        embed_usages = []

        result = compute_token_usages(llm_usages, embed_usages)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model_type, ModelType.LLM)
        self.assertEqual(result[0].prompt_tokens, 0)
        self.assertEqual(result[0].completion_tokens, 0)
        self.assertEqual(result[0].total_tokens, 0)
