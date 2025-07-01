import unittest
from diting.cases.llm_case import LLMCase
from diting.metrics.length_ratio_metric import LengthRatioExampleMetric


class TestLengthRatioExampleMetric(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.metric = LengthRatioExampleMetric()

    async def test_compute_valid_length_rate_case(self):
        test_case = LLMCase(
            user_input="Test input",
            actual_output="Test output",
            expected_output="Expected output",
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        assert test_case.expected_output is not None
        result = await self.metric.compute(test_case)
        expected_ratio = len(test_case.actual_output) / len(test_case.expected_output)  # type: ignore
        self.assertEqual(result.score, expected_ratio)

    async def test_compute_no_expected_length_rate_output(self):
        test_case = LLMCase(
            user_input="Test input",
            actual_output="Test output",
            expected_output=None,
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        with self.assertRaises(ValueError) as context:
            await self.metric.compute(test_case)
            expected_error = "'expected_output' cannot be None for the 'length_ratio_example_metric' metric"
            self.assertEqual(str(context.exception), expected_error)

    async def test_compute_empty_actual_length_rate_output(self):
        test_case = LLMCase(
            user_input="Test input",
            actual_output="",
            expected_output="Expected output",
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        result = await self.metric.compute(test_case)
        expected_ratio = 0.0  # since actual output is empty
        self.assertEqual(result.score, expected_ratio)

    async def test_compute_empty_expected_length_rate_output(self):
        test_case = LLMCase(
            user_input="Test input",
            actual_output="Test output",
            expected_output="",
            context=["context1"],
            retrieval_context=["retrieval1"],
        )
        result = await self.metric.compute(test_case)
        expected_ratio = 0.0  # since expected output is empty
        self.assertEqual(result.score, expected_ratio)


if __name__ == "__main__":
    unittest.main()
