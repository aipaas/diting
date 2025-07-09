import unittest
from unittest.mock import AsyncMock, patch

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage
from diting_core.models.llms.openai_model import LangchainLLMWrapper


class TestLangchainLLMWrapper(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_llm = AsyncMock(spec=BaseLanguageModel[BaseMessage])
        self.wrapper = LangchainLLMWrapper(
            llm=self.mock_llm,
            is_guided_json_support=True,
            is_structured_output_support=True,
        )

    @patch("diting_core.models.utils.filter_model_output")
    @patch("json_repair.loads")
    async def test_invoke_and_parse_without_schema(
        self, mock_json_repair, mock_filter_output
    ):
        # Mock response content
        self.mock_llm.ainvoke.return_value = AsyncMock(content='{"key": "value"}')
        mock_filter_output.return_value = '{"key": "value"}'
        mock_json_repair.return_value = {"key": "value"}

        result = await self.wrapper._invoke_and_parse("Some prompt")

        self.assertEqual(result, {"key": "value"})
        self.mock_llm.ainvoke.assert_called_once_with("Some prompt")

    @patch("diting_core.models.utils.filter_model_output")
    @patch("json_repair.loads")
    async def test_invoke_and_parse_with_schema(
        self, mock_json_repair, mock_filter_output
    ):
        from pydantic import BaseModel

        class Schema(BaseModel):
            key: str

        # Mock response content
        self.mock_llm.ainvoke.return_value = AsyncMock(content='{"key": "value"}')
        mock_filter_output.return_value = '{"key": "value"}'
        mock_json_repair.return_value = {"key": "value"}

        result = await self.wrapper._invoke_and_parse("Some prompt", Schema)

        self.assertEqual(result, Schema(key="value"))

    @patch("diting_core.models.utils.filter_model_output")
    @patch("json_repair.loads")
    async def test_invoke_and_parse_with_use_guided_json(
        self, mock_json_repair, mock_filter_output
    ):
        from pydantic import BaseModel

        class Schema(BaseModel):
            key: str

        # Mock response content
        self.mock_llm.ainvoke.return_value = AsyncMock(content='{"key": "value"}')
        mock_filter_output.return_value = '{"key": "value"}'
        mock_json_repair.return_value = {"key": "value"}

        result = await self.wrapper._invoke_and_parse(
            "Some prompt", Schema, use_guided_json=True
        )

        self.assertEqual(result, Schema(key="value"))
