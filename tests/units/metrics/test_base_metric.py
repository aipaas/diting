import unittest
from diting.cases.llm_case import LLMCase
from diting.metrics.base_metric import BaseMetric
from typing import Any, Dict, Tuple


class MockMetric(BaseMetric):
    async def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        return 1.0


class TestBaseMetric(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.metric = MockMetric()
        self.test_case = LLMCase(input="Test input", actual_output="Test output")

    async def test_compute(self):
        result = await self.metric.compute(self.test_case)
        self.assertEqual(result, 1.0)


if __name__ == "__main__":
    unittest.main()
