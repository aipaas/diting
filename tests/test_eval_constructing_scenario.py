import unittest
from diting.cases.llm_case import LLMCase
from diting.metrics.base_metric import BaseMetric, MetricValue
from typing import Any, Dict, Tuple

from diting.models.base_model import BaseLLM


# 1. 定义一个指标，实现算法
class MockMetric(BaseMetric):
    def __init__(
        self,
        model: BaseLLM | None,
    ):
        self.model = model

    async def _compute(
        self, test_case: LLMCase, *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> MetricValue:
        # Example logic for computing a metric
        if test_case.user_input == "error":
            raise ValueError("Invalid input")
        return MetricValue(score=1.0)


class TestBaseMetric(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 2. 构造评估指标，依赖所评估的模型
        # 3. 评估可解释性数据，存储在 self.metric 实例
        self.metric = MockMetric(model=None)

    async def test_compute_valid_case(self):
        test_case = LLMCase(user_input="Valid input", actual_output="Output")
        result = await self.metric.compute(test_case)
        self.assertEqual(result.score, 1.0)

    async def test_compute_error_case(self):
        test_case = LLMCase(user_input="error", actual_output="Output")
        with self.assertRaises(ValueError) as context:
            await self.metric.compute(test_case)
        self.assertEqual(str(context.exception), "Invalid input")


if __name__ == "__main__":
    unittest.main()
