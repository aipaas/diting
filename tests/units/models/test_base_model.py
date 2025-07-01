import unittest
from diting.models.base_model import BaseLLM
from typing import Any, Dict, Tuple


class MockLLM(BaseLLM):
    def load_model(self, *args: Tuple[Any], **kwargs: Dict[str, Any]):
        return None

    def generate(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> str:
        return "Generated Response"

    async def a_generate(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> str:
        return "Async Generated Response"

    def get_model_name(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> str:
        return "Mock Model"


class TestBaseLLM(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.model = MockLLM()

    def test_load_model(self):
        result = self.model.load_model()
        self.assertEqual(result, None)

    def test_generate(self):
        result = self.model.generate()
        self.assertEqual(result, "Generated Response")

    async def test_a_generate(self):
        result = await self.model.a_generate()
        self.assertEqual(result, "Async Generated Response")

    def test_get_model_name(self):
        result = self.model.get_model_name()
        self.assertEqual(result, "Mock Model")


if __name__ == "__main__":
    unittest.main()
