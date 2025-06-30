import unittest
from diting.cases.llm_case import LLMCase
from diting.metrics.base_metric import BaseMetric
from typing import Any, Dict, Optional, Tuple, Union

from diting.models.base_model import BaseLLM


# 1. 定义一个指标，实现算法
class MockMetric(BaseMetric):
    def __init__(
        self,
        model: Optional[Union[str, BaseLLM]] = None,
    ):
        self.model = model

    def compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        # Example logic for computing a metric
        if test_case.input == "error":
            raise ValueError("Invalid input")
        return 1.0

    async def acompute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> float:
        # Example logic for asynchronously computing a metric
        if test_case.input == "error":
            raise ValueError("Invalid input")
        return 1.0


class TestBaseMetric(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 2. 构造评估指标，依赖所评估的模型
        # 3. 评估可解释性数据，存储在 self.metric 实例
        self.metric = MockMetric(model=None)

    def test_compute_valid_case(self):
        test_case = LLMCase(input="Valid input", actual_output="Output")
        result = self.metric.compute(test_case)
        self.assertEqual(result, 1.0)

    def test_compute_error_case(self):
        test_case = LLMCase(input="error", actual_output="Output")
        with self.assertRaises(ValueError) as context:
            self.metric.compute(test_case)
        self.assertEqual(str(context.exception), "Invalid input")

    async def test_acompute_valid_case(self):
        test_case = LLMCase(input="Valid input", actual_output="Output")
        result = await self.metric.acompute(test_case)
        self.assertEqual(result, 1.0)

    async def test_acompute_error_case(self):
        test_case = LLMCase(input="error", actual_output="Output")
        with self.assertRaises(ValueError) as context:
            await self.metric.acompute(test_case)
        self.assertEqual(str(context.exception), "Invalid input")


if __name__ == "__main__":
    unittest.main()
