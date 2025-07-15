from __future__ import annotations

import asyncio
import logging
import typing as t

from diting_core.callbacks.base import Callbacks
from diting_core.utilities.executor import as_completed, is_event_loop_running
from diting_dataset.knowledge_graph.graph import KnowledgeGraph
from diting_dataset.knowledge_graph.transforms import BaseGraphTransformation

logger = logging.getLogger(__name__)

Transforms = t.Union[
    t.Sequence[BaseGraphTransformation],
    BaseGraphTransformation,
]


class Parallel(BaseGraphTransformation):
    """
    Collection of transformations to be applied in parallel.

    Examples
    --------
    >>> Parallel(HeadlinesExtractor(), SummaryExtractor())
    """

    def __init__(self, *transformations: BaseGraphTransformation):
        self.transformations = list(transformations)

    async def transform(self, kg: KnowledgeGraph) -> t.Any:
        raise NotImplementedError

    def generate_execution_plan(
        self, kg: KnowledgeGraph
    ) -> t.List[t.Coroutine[t.Any, t.Any, None]]:
        coroutines: t.List[t.Coroutine[t.Any, t.Any, None]] = []
        for transformation in self.transformations:
            coroutines.extend(transformation.generate_execution_plan(kg))
        return coroutines


async def run_coroutines(
    coroutines: t.List[t.Coroutine[t.Any, t.Any, None]], max_workers: int
) -> None:
    """
    Run a list of coroutines in parallel.
    """
    for future in await as_completed(coroutines, max_workers=max_workers):
        try:
            await future
        except Exception as e:
            logger.error(f"unable to apply transformation: {e}")


nest_asyncio_applied: bool = False  # 全局变量


def apply_nest_asyncio():
    global nest_asyncio_applied
    if is_event_loop_running():
        # an event loop is running so call nested_asyncio to fix this
        try:
            import nest_asyncio
        except ImportError:
            raise ImportError(
                "It seems like your running this in a jupyter-like environment. Please install nest_asyncio with `pip install nest_asyncio` to make it work."
            )

        if not nest_asyncio_applied:
            nest_asyncio.apply()  # type: ignore
            nest_asyncio_applied = True


def apply_transforms(
    kg: KnowledgeGraph,
    transforms: Transforms,
    max_workers: int = 16,
    callbacks: t.Optional[Callbacks] = None,
):
    """
    Apply a list of transformations to a knowledge graph in place.
    """
    # apply nest_asyncio to fix the event loop issue in jupyter or asyncio.run(main)
    apply_nest_asyncio()

    # if single transformation, wrap it in a list
    if isinstance(transforms, BaseGraphTransformation):
        transforms = [transforms]

    # apply the transformations
    # if Sequences, apply each transformation sequentially
    if isinstance(transforms, t.List):
        for transform in transforms:
            asyncio.run(
                run_coroutines(
                    transform.generate_execution_plan(kg),
                    max_workers,
                )
            )
    # if Parallel, collect inside it and run it all
    elif isinstance(transforms, Parallel):
        asyncio.run(
            run_coroutines(
                transforms.generate_execution_plan(kg),
                max_workers,
            )
        )
    else:
        raise ValueError(
            f"Invalid transforms type: {type(transforms)}. Expects a list of BaseGraphTransformations or a Parallel instance."
        )
