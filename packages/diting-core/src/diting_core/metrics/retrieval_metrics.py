"""Retrieval-specific metrics for RAG optimization."""

from __future__ import annotations

from typing import Any, Dict, List

from diting_core.metrics.base_metric import BaseMetric


class AverageSimilarityMetric(BaseMetric):
    """Simple metric that averages similarity scores from retrieval results.

    This metric computes the mean of similarity scores across all retrieved documents.
    Higher scores indicate better retrieval quality.
    """

    async def _compute(self, results: List[Dict[str, Any]], **kwargs: Any) -> float:  # type: ignore[override]
        """Compute average similarity score.

        Args:
            results: List of retrieval results, each containing a 'similarity' field
            **kwargs: Additional arguments (unused)

        Returns:
            Average similarity score, or 0.0 if no results
        """
        if not results:
            return 0.0
        similarities = [float(item.get("similarity", 0.0)) for item in results]
        return sum(similarities) / len(similarities)


class TopDocumentMatchMetric(BaseMetric):
    """Metric that rewards hitting a desired document in the top results.

    This metric checks if a target document appears in the top-k results.
    Returns 1.0 if found, 0.0 otherwise.
    """

    def __init__(self, target_document: str, top_k: int = 3) -> None:
        """Initialize the metric.

        Args:
            target_document: ID of the target document to look for
            top_k: Number of top results to check (default: 3)
        """
        super().__init__()
        self.target_document = target_document
        self.top_k = top_k

    async def _compute(self, results: List[Dict[str, Any]], **kwargs: Any) -> float:  # type: ignore[override]
        """Check if target document is in top-k results.

        Args:
            results: List of retrieval results
            **kwargs: Additional arguments (unused)

        Returns:
            1.0 if target document found in top-k, 0.0 otherwise
        """
        if not results:
            return 0.0
        top_ids = [doc.get("id") for doc in results[:self.top_k]]
        return 1.0 if self.target_document in top_ids else 0.0


class WeightedRetrievalMetric(BaseMetric):
    """Combine average similarity with target document match for richer scoring.

    This metric combines two sub-metrics with a weighted average:
    - Average similarity score (weight: alpha)
    - Target document hit (weight: 1-alpha)
    """

    def __init__(self, target_document: str, alpha: float = 0.7, top_k: int = 3) -> None:
        """Initialize the metric.

        Args:
            target_document: ID of the target document to look for
            alpha: Weight for average similarity (default: 0.7)
            top_k: Number of top results to check for target document (default: 3)
        """
        super().__init__()
        self.alpha = alpha
        self.sim_metric = AverageSimilarityMetric()
        self.hit_metric = TopDocumentMatchMetric(target_document, top_k)

    async def _compute(self, results: List[Dict[str, Any]], **kwargs: Any) -> float:  # type: ignore[override]
        """Compute weighted combination of similarity and target hit.

        Args:
            results: List of retrieval results
            **kwargs: Additional arguments (unused)

        Returns:
            Weighted score combining similarity and target hit
        """
        avg_sim = await self.sim_metric._compute(results)
        hit_score = await self.hit_metric._compute(results)
        return self.alpha * avg_sim + (1 - self.alpha) * hit_score
