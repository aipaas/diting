"""Evaluation execution using diting-core SDK.

Provides direct wrapper over diting-core's metric evaluation functionality,
reusing diting-server's utilities for token tracking and model configuration.
"""

from typing import Any, Optional, Type

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics.base_metric import BaseMetric
from diting_core.models.llms.factory import llm_factory
from diting_core.models.embeddings.factory import embedding_factory

# Import utilities from diting-server
from diting_server.services.evaluation.metrics import MetricFactory
from diting_server.common.callback import (
    GetEmbedTokenCallbackHandler,
    GetLLMTokenCallbackHandler,
)
from diting_server.common.utils import resolve_model_config, compute_token_usage

from diting_web.common.logging import get_logger

logger = get_logger(__name__)


class EvaluationRunner:
    """Runner for executing diting-core metric evaluations.
    
    Directly uses diting-core SDK with diting-server's utilities for:
    - MetricFactory for automatic metric discovery
    - Callbacks for token tracking
    - Model configuration resolution
    """

    # Use diting-server's MetricFactory
    _metric_factory = MetricFactory()

    @classmethod
    def _load_metric(cls, metric_name: str) -> Type[BaseMetric]:
        """Load metric class using diting-server's MetricFactory."""
        return cls._metric_factory.create(metric_name)

    @classmethod
    async def run_evaluation(
        cls,
        metric_name: str,
        test_case_data: dict[str, Any],
        llm_config: Optional[dict[str, Any]] = None,
        embedding_config: Optional[dict[str, Any]] = None,
        metric_params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run a single evaluation using diting-core SDK.
        
        Args:
            metric_name: Name of the metric to use
            test_case_data: Test case data dictionary
            llm_config: LLM configuration dict
            embedding_config: Embedding configuration dict
            metric_params: Additional metric parameters
        
        Returns:
            dict with keys: metric_name, score, reason, run_logs, usages
        """
        logger.info(
            "Running evaluation",
            metric_name=metric_name,
            test_case_fields=list(test_case_data.keys()),
        )
        
        # Create test case
        case = LLMCase(**test_case_data)
        
        # Load metric using MetricFactory
        try:
            metric: BaseMetric = cls._load_metric(metric_name)()
        except Exception as ex:
            error = str(ex)
            logger.error(
                f"Failed to load metric {metric_name}. Error: {error}",
                exc_info=True,
            )
            raise ValueError(f"Failed to load metric {metric_name}: {error}")
        
        # Check what the metric needs
        is_llm_required = hasattr(metric, "model")
        is_embedding_required = hasattr(metric, "embedding_model")
        
        # Setup callbacks for token tracking
        callbacks: list[Any] = []
        get_embed_token = GetEmbedTokenCallbackHandler()
        get_llm_token = GetLLMTokenCallbackHandler()
        
        # Setup LLM if needed
        if is_llm_required and llm_config:
            llm_config_resolved = resolve_model_config(
                model=llm_config.get("model_name") or llm_config.get("name", ""),
                base_url=llm_config.get("base_url") or None,
                api_key=llm_config.get("api_key") or None,
            )
            llm_model = llm_factory(**llm_config_resolved, timeout=llm_config.get("timeout", 600))
            setattr(metric, "model", llm_model)
            callbacks.append(get_llm_token)
        elif is_llm_required and not llm_config:
            raise ValueError(
                f"LLM model is required for metric {metric_name}. "
                "Please ensure that you have configured the appropriate LLM model."
            )
        
        # Setup embedding if needed
        if is_embedding_required and embedding_config:
            logger.info(
                "Setting up embedding model",
                metric_name=metric_name,
                model_name=embedding_config.get("model_name") or embedding_config.get("name", ""),
                has_base_url=bool(embedding_config.get("base_url")),
                has_api_key=bool(embedding_config.get("api_key")),
                base_url_value=embedding_config.get("base_url"),
            )
            
            embedding_config_resolved = resolve_model_config(
                model=embedding_config.get("model_name") or embedding_config.get("name", ""),
                base_url=embedding_config.get("base_url") or None,
                api_key=embedding_config.get("api_key") or None,
            )
            
            logger.info(
                "Resolved embedding config",
                resolved_config=embedding_config_resolved,
            )
            
            embedding_model = embedding_factory(
                **embedding_config_resolved,
                timeout=embedding_config.get("timeout", 60)
            )
            setattr(metric, "embedding_model", embedding_model)
            callbacks.append(get_embed_token)
        elif is_embedding_required and not embedding_config:
            raise ValueError(
                f"Embedding model is required for metric {metric_name}. "
                "Please ensure that you have configured the appropriate embedding model."
            )
        
        # Run evaluation with callbacks
        metric_value = None
        error = None
        try:
            metric_value = await metric.compute(test_case=case, callbacks=callbacks)
        except Exception as ex:
            error = str(ex)
            logger.error(f"Metric compute error: {error}", exc_info=True)
            raise
        finally:
            # Compute token usage from callbacks
            usages = compute_token_usage(
                llm_usages=get_llm_token.usages,
                embed_usages=get_embed_token.usages,
            )
        
        # Format result
        result = {
            "metric_name": metric_value.metric_name or metric_name,
            "score": metric_value.score,
            "reason": metric_value.reason,
            "run_logs": metric_value.run_logs,
            "usages": [
                {
                    "model_type": u.model_type,
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                }
                for u in usages
            ] if usages else [],
        }
        
        logger.info(
            "Evaluation completed",
            metric_name=metric_name,
            score=result["score"],
            total_tokens=sum(u["total_tokens"] for u in result["usages"]),
        )
        
        return result

