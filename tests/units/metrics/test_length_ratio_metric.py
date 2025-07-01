import unittest
from diting.cases.llm_case import LLMCase
from diting.metrics.length_ratio_metric import LengthRatioExampleMetric


class TestLengthRatioExampleMetric(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.metric = LengthRatioExampleMetric()

    async def test_compute_valid_length_rate_case(self):
        test_case = LLMCase(
            input="Test input",
            actual_output="Test output",
            expected_output="Expected output",
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        assert test_case.expected_output is not None
        result = await self.metric.compute(test_case)
        expected_ratio = len(test_case.actual_output) / len(test_case.expected_output)
        self.assertEqual(result, expected_ratio)

    async def test_compute_no_expected_length_rate_output(self):
        test_case = LLMCase(
            input="Test input",
            actual_output="Test output",
            expected_output=None,
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        result = await self.metric.compute(test_case)
        self.assertEqual(result, 0.0)

    async def test_compute_empty_actual_length_rate_output(self):
        test_case = LLMCase(
            input="Test input",
            actual_output="",
            expected_output="Expected output",
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        result = await self.metric.compute(test_case)
        expected_ratio = 0.0  # since actual output is empty
        self.assertEqual(result, expected_ratio)

    async def test_compute_empty_expected_length_rate_output(self):
        test_case = LLMCase(
            input="Test input",
            actual_output="Test output",
            expected_output="",
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        result = await self.metric.compute(test_case)
        expected_ratio = 0.0  # since expected output is empty
        self.assertEqual(result, expected_ratio)


if __name__ == "__main__":
    unittest.main()
