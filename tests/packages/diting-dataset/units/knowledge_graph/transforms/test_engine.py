#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, patch

from diting_dataset.knowledge_graph.schema import KnowledgeGraph
from diting_dataset.knowledge_graph.transforms import BaseGraphTransformation
from diting_dataset.knowledge_graph.transforms.engine import (
    Parallel,
    apply_transforms,
    run_coroutines,
    apply_nest_asyncio,
)


@dataclass
class Counter:
    count = 0


async def mock_coroutine(counter: Optional[Counter] = None) -> None:
    if not counter:
        return
    counter.count += 1


async def mock_coroutine_err() -> None:
    raise ValueError("Test Exception")


class TestParallel(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.kg = MagicMock(spec=KnowledgeGraph)
        self.transformation1 = MagicMock(spec=BaseGraphTransformation)
        self.transformation2 = MagicMock(spec=BaseGraphTransformation)
        self.parallel_transform = Parallel(self.transformation1, self.transformation2)

    @patch("diting_dataset.knowledge_graph.transforms.engine.run_coroutines")
    def test_generate_execution_plan(self, mock_run_coroutines):
        self.transformation1.generate_execution_plan = MagicMock(
            return_value=[mock_coroutine()]
        )
        self.transformation2.generate_execution_plan = MagicMock(
            return_value=[mock_coroutine()]
        )

        coroutines = self.parallel_transform.generate_execution_plan(self.kg)

        self.assertEqual(len(coroutines), 2)
        self.transformation1.generate_execution_plan.assert_called_once_with(self.kg)
        self.transformation2.generate_execution_plan.assert_called_once_with(self.kg)

    @patch("diting_dataset.knowledge_graph.transforms.engine.run_coroutines")
    def test_apply_transforms_with_single_transformation(self, mock_run_coroutines):
        apply_transforms(self.kg, self.transformation1)
        mock_run_coroutines.assert_called_once()

    @patch("diting_dataset.knowledge_graph.transforms.engine.run_coroutines")
    def test_apply_transforms_with_parallel(self, mock_run_coroutines):
        apply_transforms(self.kg, self.parallel_transform)
        mock_run_coroutines.assert_called_once()

    def test_apply_transforms_with_invalid_type(self):
        with self.assertRaises(ValueError):
            apply_transforms(self.kg, "invalid_type")

    # @patch(
    #     "diting_dataset.knowledge_graph.transforms.engine.is_event_loop_running",
    #     return_value=True,
    # )
    # @patch("nest_asyncio.apply")
    # def test_apply_nest_asyncio_when_event_loop_running(
    #     self, mock_nest_asyncio, mock_is_event_loop_running
    # ):
    #     apply_nest_asyncio()
    #     mock_nest_asyncio.assert_called_once()

    @patch(
        "diting_dataset.knowledge_graph.transforms.engine.is_event_loop_running",
        return_value=True,
    )
    def test_apply_nest_asyncio_when_event_loop_running(
        self, mock_is_event_loop_running
    ):
        apply_nest_asyncio()

    @patch(
        "diting_dataset.knowledge_graph.transforms.engine.is_event_loop_running",
        return_value=False,
    )
    def test_apply_nest_asyncio_when_no_event_loop(self, mock_is_event_loop_running):
        apply_nest_asyncio()
        # No assertion needed, just ensure it runs without error

    async def test_run_coroutines_success(self):
        # Call the function to run coroutines
        counter = Counter()
        await run_coroutines(
            [mock_coroutine(counter), mock_coroutine(counter), mock_coroutine(counter)],
            max_workers=2,
        )
        self.assertEqual(counter.count, 3)

    @patch("diting_dataset.knowledge_graph.transforms.engine.logger")
    async def test_run_coroutines_with_exception(self, mock_logger):
        # Call the function to run coroutines
        await run_coroutines([mock_coroutine_err()], max_workers=2)
        mock_logger.error.assert_called_once_with(
            "unable to apply transformation: Test Exception"
        )


if __name__ == "__main__":
    unittest.main()
