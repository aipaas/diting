#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from enum import Enum
from typing import Optional, List

from diting_core.synthesis.base_corpus import BaseCorpus
from pydantic import BaseModel, ConfigDict


class QueryLength(str, Enum):
    """
    Enumeration of query lengths. Available options are: LONG, MEDIUM, SHORT
    """

    LONG = "long"
    MEDIUM = "medium"
    SHORT = "short"


class QueryStyle(str, Enum):
    """
    Enumeration of query styles. Available options are: MISSPELLED, PERFECT_GRAMMAR, POOR_GRAMMAR, WEB_SEARCH_LIKE
    """

    MISSPELLED = "Misspelled queries"
    PERFECT_GRAMMAR = "Perfect grammar"
    POOR_GRAMMAR = "Poor grammar"
    WEB_SEARCH_LIKE = "Web search like queries"


class Persona(BaseModel):
    name: str
    role_description: str


class GraphBasedCorpus(BaseCorpus):
    """
    Base class for representing a corpus for generating LLMCase.

    Attributes
    ----------
    context : List[str]
        List of background information involved in the corpus.
    scenario: Optional[str] = None
        The scenario within the corpus
    """

    context: Optional[List[str]] = None
    scenario: Optional[str] = None
    style: Optional[QueryStyle] = None
    length: Optional[QueryLength] = None
    persona: Optional[Persona] = None
    model_config = ConfigDict(extra="allow")  # 允许任意额外属性
