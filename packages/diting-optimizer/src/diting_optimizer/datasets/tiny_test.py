"""Tiny test dataset for quick validation.

Small test dataset for quickly validating optimizer functionality.
"""

from __future__ import annotations

from diting_core.cases.llm_case import LLMCaseParams
from diting_optimizer.datasets.base_dataset import BaseDataset, InMemoryDataset


def tiny_test() -> BaseDataset:
    """Create tiny test dataset for quick validation.

    Contains 3 simple question-answer pairs suitable for quick testing and debugging.

    Returns
    -------
    BaseDataset
        Tiny test dataset instance

    Notes:
        - Contains basic factual questions with clear answers
        - Suitable for unit tests and quick debugging
        - Minimal computational overhead
    """
    items = [
        {
            "id": "tiny_1",
            LLMCaseParams.USER_INPUT.value: "What is the capital of France?",
            LLMCaseParams.EXPECTED_OUTPUT.value: "Paris",
        },
        {
            "id": "tiny_2",
            LLMCaseParams.USER_INPUT.value: "What is 2 + 2?",
            LLMCaseParams.EXPECTED_OUTPUT.value: "4",
        },
        {
            "id": "tiny_3",
            LLMCaseParams.USER_INPUT.value: "Who wrote Romeo and Juliet?",
            LLMCaseParams.EXPECTED_OUTPUT.value: "William Shakespeare",
        },
    ]
    return InMemoryDataset("tiny_test", items)
