"""Evaluation runner using diting-core metrics.

Provides a wrapper to execute evaluations using diting-core metrics
with configuration from the web backend.
"""

from typing import Any, Optional

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics.answer_correctness.answer_correctness import AnswerCorrectness
from diting_core.metrics.answer_relevancy.answer_relevancy import AnswerRelevancy
from diting_core.metrics.answer_similarity.answer_similarity import AnswerSimilarity
from diting_core.metrics.base_metric import BaseMetric, MetricValue
from diting_core.metrics.context_precision.context_precision import ContextPrecision
from diting_core.metrics.context_recall.context_recall import ContextRecall
from diting_core.metrics.custom_metric.custom_metric import CustomMetric
from diting_core.metrics.faithfulness.faithfulness import Faithfulness

from diting_web.common.logging import get_logger
from diting_web.integrations.core_adapter.config_mapper import (
    create_embedding_from_config,
    create_llm_from_config,
)

logger = get_logger(__name__)


class EvaluationRunner:
    """Runner for executing diting-core metric evaluations.
    
    This class provides a high-level interface to:
    1. Create metric instances from configuration
    2. Execute evaluations on test cases
    3. Return structured results with usage statistics
    """

    # Mapping of metric names to their classes
    METRIC_REGISTRY: dict[str, type[BaseMetric]] = {
        "answer_correctness": AnswerCorrectness,
        "answer_relevancy": AnswerRelevancy,
        "answer_similarity": AnswerSimilarity,
        "context_precision": ContextPrecision,
        "context_recall": ContextRecall,
        "faithfulness": Faithfulness,
        "custom_metric": CustomMetric,
    }

    @classmethod
    def create_metric(
        cls,
        metric_name: str,
        llm_config: Optional[dict[str, Any]] = None,
        embedding_config: Optional[dict[str, Any]] = None,
        metric_params: Optional[dict[str, Any]] = None,
    ) -> BaseMetric:
        """Create a metric instance from configuration.
        
        Args:
            metric_name: Name of the metric (e.g., "answer_correctness")
            llm_config: LLM configuration dictionary
            embedding_config: Embedding configuration dictionary
            metric_params: Additional metric-specific parameters
        
        Returns:
            BaseMetric: Configured metric instance
        
        Raises:
            ValueError: If metric name is not recognized
        """
        if metric_name not in cls.METRIC_REGISTRY:
            raise ValueError(
                f"Unknown metric: {metric_name}. "
                f"Available metrics: {list(cls.METRIC_REGISTRY.keys())}"
            )

        metric_class = cls.METRIC_REGISTRY[metric_name]
        metric_params = metric_params or {}

        logger.info(
            "Creating metric",
            metric_name=metric_name,
            has_llm_config=bool(llm_config),
            has_embedding_config=bool(embedding_config),
            metric_params=metric_params,
        )

        # Create LLM if needed
        llm = None
        if llm_config:
            try:
                llm = create_llm_from_config(llm_config)
            except Exception as e:
                logger.error("Failed to create LLM for metric", error=str(e))
                raise

        # Create embedding if needed
        embedding = None
        if embedding_config:
            try:
                embedding = create_embedding_from_config(embedding_config)
            except Exception as e:
                logger.error("Failed to create embedding for metric", error=str(e))
                raise

        # Instantiate metric
        try:
            metric = metric_class(
                model=llm,
                embedding_model=embedding,
                **metric_params,
            )
            logger.info("Metric created successfully", metric_name=metric_name)
            return metric
        except Exception as e:
            logger.error("Failed to instantiate metric", metric_name=metric_name, error=str(e))
            raise

    @classmethod
    async def run_evaluation(
        cls,
        metric_name: str,
        test_case_data: dict[str, Any],
        llm_config: Optional[dict[str, Any]] = None,
        embedding_config: Optional[dict[str, Any]] = None,
        metric_params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run a single evaluation.
        
        Args:
            metric_name: Name of the metric to use
            test_case_data: Test case data dictionary with fields:
                - user_input (str, optional)
                - actual_output (str, optional)
                - expected_output (str, optional)
                - context (list[str], optional)
                - retrieval_context (list[str], optional)
            llm_config: LLM configuration
            embedding_config: Embedding configuration
            metric_params: Additional metric parameters
        
        Returns:
            dict: Evaluation result with fields:
                - metric_name (str)
                - score (float)
                - reason (str, optional)
                - run_logs (dict, optional)
                - usages (list[dict]): Token usage information
        
        Examples:
            >>> result = await EvaluationRunner.run_evaluation(
            ...     metric_name="answer_correctness",
            ...     test_case_data={
            ...         "user_input": "What is Python?",
            ...         "actual_output": "A programming language",
            ...         "expected_output": "Python is a high-level programming language"
            ...     },
            ...     llm_config={"model_name": "gpt-4"}
            ... )
        """
        logger.info(
            "Running evaluation",
            metric_name=metric_name,
            test_case_fields=list(test_case_data.keys()),
        )

        # Create test case
        test_case = LLMCase(**test_case_data)

        # Create metric
        metric = cls.create_metric(
            metric_name=metric_name,
            llm_config=llm_config,
            embedding_config=embedding_config,
            metric_params=metric_params,
        )

        # Run evaluation
        try:
            metric_value: MetricValue = await metric.compute(
                test_case=test_case,
                verbose=True,
            )

            # Extract usage information
            usages = cls._extract_usages(metric_value)

            result = {
                "metric_name": metric_value.metric_name or metric_name,
                "score": metric_value.score,
                "reason": metric_value.reason,
                "run_logs": metric_value.run_logs,
                "usages": usages,
            }

            logger.info(
                "Evaluation completed",
                metric_name=metric_name,
                score=metric_value.score,
                total_tokens=sum(u.get("total_tokens", 0) for u in usages),
            )

            return result

        except Exception as e:
            logger.error(
                "Evaluation failed",
                metric_name=metric_name,
                error=str(e),
                exc_info=True,
            )
            raise

    @classmethod
    def _extract_usages(cls, metric_value: MetricValue) -> list[dict[str, Any]]:
        """Extract token usage information from metric value.
        
        Args:
            metric_value: Metric value from evaluation
        
        Returns:
            list: Usage information dictionaries
        """
        usages = []
        
        # TODO: Implement actual usage extraction from metric_value.run_logs
        # For now, return mock usage data
        # In real implementation, parse callbacks or run_logs to get actual token counts
        
        # Mock usage data
        usages.append({
            "model_type": "llm",
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200,
        })
        
        return usages

