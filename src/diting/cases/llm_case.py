from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LLMCase:
    input: str
    actual_output: str
    expected_output: Optional[str] = None
    context: Optional[List[str]] = None
    retrieval_context: Optional[List[str]] = None
