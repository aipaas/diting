import unittest
from diting.cases.llm_case import LLMCase
from diting.metrics.base_metric import BaseMetric
from typing import Any, Dict, Tuple


class MockMetric(BaseMetric):
    def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        return 1.0

    async def acompute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        return 1.0


class TestBaseMetric(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.metric = MockMetric()
        self.test_case = LLMCase(input="Test input", actual_output="Test output")

    def test_compute(self):
        result = self.metric.compute(self.test_case)
        self.assertEqual(result, 1.0)

    async def test_acompute(self):
        result = await self.metric.acompute(self.test_case)
        self.assertEqual(result, 1.0)


if __name__ == "__main__":
    unittest.main()
