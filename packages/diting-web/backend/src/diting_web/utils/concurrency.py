"""Concurrency control utilities.

Provides utilities for controlling concurrent task execution to avoid
overwhelming external APIs or database connections.
"""

import asyncio
from typing import Any, Awaitable, Callable, Optional, TypeVar

from diting_web.common.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ConcurrencyController:
    """Controller for limiting concurrent task execution.
    
    This class uses a semaphore to limit the number of concurrent tasks,
    preventing overwhelming of external services or database connections.
    
    Example:
        >>> controller = ConcurrencyController(max_concurrent=10)
        >>> tasks = [controller.run(process_item, item) for item in items]
        >>> results = await asyncio.gather(*tasks, return_exceptions=True)
    """

    def __init__(self, max_concurrent: int = 10):
        """Initialize controller.
        
        Args:
            max_concurrent: Maximum number of concurrent tasks (default: 10)
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        logger.info(f"ConcurrencyController initialized with max_concurrent={max_concurrent}")

    async def run(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Run a function with concurrency control.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Result from the function
        
        Raises:
            Any exception raised by the function
        """
        async with self.semaphore:
            return await func(*args, **kwargs)


async def run_with_concurrency_limit(
    tasks: list[Awaitable[T]],
    max_concurrent: int = 10,
    return_exceptions: bool = False,
) -> list[T]:
    """Run multiple tasks with concurrency limit.
    
    This is a convenience function that creates a temporary ConcurrencyController
    and runs all tasks through it.
    
    Args:
        tasks: List of awaitable tasks
        max_concurrent: Maximum number of concurrent tasks
        return_exceptions: If True, exceptions are returned as results instead of raising
    
    Returns:
        List of results from all tasks
    
    Example:
        >>> tasks = [evaluate_row(row) for row in rows]
        >>> results = await run_with_concurrency_limit(tasks, max_concurrent=10)
    """
    controller = ConcurrencyController(max_concurrent=max_concurrent)
    
    # Wrap each task with concurrency control
    controlled_tasks = [controller.run(lambda t=task: t) for task in tasks]
    
    # Run all tasks
    results = await asyncio.gather(*controlled_tasks, return_exceptions=return_exceptions)
    
    return results


async def batch_process(
    items: list[Any],
    processor: Callable[[Any], Awaitable[T]],
    max_concurrent: int = 10,
    batch_size: Optional[int] = None,
) -> list[T]:
    """Process items in batches with concurrency control.
    
    This function processes items in batches, with each batch having a maximum
    number of concurrent tasks. This is useful for processing large datasets
    without overwhelming system resources.
    
    Args:
        items: List of items to process
        processor: Async function to process each item
        max_concurrent: Maximum concurrent tasks per batch
        batch_size: Size of each batch (default: max_concurrent * 5)
    
    Returns:
        List of processing results
    
    Example:
        >>> async def evaluate_item(item):
        ...     return await evaluate(item)
        >>> 
        >>> results = await batch_process(
        ...     items=dataset_rows,
        ...     processor=evaluate_item,
        ...     max_concurrent=10
        ... )
    """
    if batch_size is None:
        batch_size = max_concurrent * 5

    controller = ConcurrencyController(max_concurrent=max_concurrent)
    all_results = []

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1}, items {i} to {i + len(batch)}")

        # Create tasks for this batch
        tasks = [controller.run(processor, item) for item in batch]
        
        # Process batch
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results.extend(batch_results)

        logger.info(f"Batch {i // batch_size + 1} completed")

    return all_results



