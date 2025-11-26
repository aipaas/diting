"""Prometheus metrics for monitoring.

This module provides Prometheus metrics for tracking system performance
and resource usage.

Note: Requires prometheus_client to be installed:
    pip install prometheus_client
"""

try:
    from prometheus_client import Counter, Gauge, Histogram

    # Task metrics
    task_created_counter = Counter(
        "diting_tasks_created_total",
        "Total number of tasks created",
        ["task_type"],
    )

    task_completed_counter = Counter(
        "diting_tasks_completed_total",
        "Total number of tasks completed",
        ["task_type", "status"],
    )

    task_duration_histogram = Histogram(
        "diting_task_duration_seconds",
        "Task execution duration in seconds",
        ["task_type"],
        buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
    )

    # Token usage metrics
    token_usage_counter = Counter(
        "diting_tokens_used_total",
        "Total number of tokens used",
        ["task_type", "model"],
    )

    cost_counter = Counter(
        "diting_cost_total",
        "Total cost in dollars",
        ["task_type"],
    )

    # System metrics
    active_tasks_gauge = Gauge(
        "diting_active_tasks",
        "Number of currently active tasks",
        ["status"],
    )

    # Evaluation metrics
    evaluation_score_histogram = Histogram(
        "diting_evaluation_score",
        "Distribution of evaluation scores",
        ["metric_name"],
        buckets=(0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    )

    METRICS_AVAILABLE = True

except ImportError:
    # Prometheus client not installed, provide no-op implementations
    METRICS_AVAILABLE = False

    class NoOpMetric:
        """No-op metric for when prometheus_client is not installed."""

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def time(self):
            class NoOpContextManager:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            return NoOpContextManager()

        def labels(self, *args, **kwargs):
            return self

    task_created_counter = NoOpMetric()
    task_completed_counter = NoOpMetric()
    task_duration_histogram = NoOpMetric()
    token_usage_counter = NoOpMetric()
    cost_counter = NoOpMetric()
    active_tasks_gauge = NoOpMetric()
    evaluation_score_histogram = NoOpMetric()


def record_task_created(task_type: str) -> None:
    """Record that a task was created.

    Args:
        task_type: Type of the task (evaluation, synthesis, etc.)
    """
    task_created_counter.labels(task_type=task_type).inc()


def record_task_completed(task_type: str, status: str, duration_seconds: float) -> None:
    """Record that a task was completed.

    Args:
        task_type: Type of the task
        status: Final status (completed, failed, cancelled)
        duration_seconds: How long the task took
    """
    task_completed_counter.labels(task_type=task_type, status=status).inc()
    task_duration_histogram.labels(task_type=task_type).observe(duration_seconds)


def record_token_usage(task_type: str, model: str, tokens: int, cost: float) -> None:
    """Record token usage and cost.

    Args:
        task_type: Type of the task
        model: Model name (e.g., "gpt-4")
        tokens: Number of tokens used
        cost: Cost in dollars
    """
    token_usage_counter.labels(task_type=task_type, model=model).inc(tokens)
    cost_counter.labels(task_type=task_type).inc(cost)


def update_active_tasks(status: str, delta: int) -> None:
    """Update count of active tasks.

    Args:
        status: Task status (pending, running, etc.)
        delta: Change in count (+1 or -1)
    """
    if delta > 0:
        active_tasks_gauge.labels(status=status).inc(delta)
    else:
        active_tasks_gauge.labels(status=status).dec(abs(delta))


def record_evaluation_score(metric_name: str, score: float) -> None:
    """Record an evaluation score.

    Args:
        metric_name: Name of the metric
        score: Score value (0.0 to 1.0)
    """
    evaluation_score_histogram.labels(metric_name=metric_name).observe(score)



