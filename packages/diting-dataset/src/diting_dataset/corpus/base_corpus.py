#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict

from diting_core.callbacks.manager import new_group
from diting_core.utilities.slug import camel_to_snake
from diting_dataset.knowledge_graph.persona import Persona


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


class BaseCorpus(BaseModel):
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


class BaseCorpusGenerator(ABC):
    async def generate_corpora(
        self, num_corpora: int = 5, **kwargs: Any
    ) -> List[BaseCorpus]:
        """
        生成语料（内部流程：构建图谱→聚合节点→生成聚类子图→构造语料）

        Args:
            num_corpora: 生成的语料数量

        Returns:
            基于聚类子图的语料列表
        """
        from diting_core.callbacks.base import ChainType

        run_manager, grp_cb = await new_group(
            name=self.name,
            inputs={"num_corpora": num_corpora},
            callbacks=kwargs.pop("callbacks", None),
            verbose=kwargs.pop("verbose", False),
            chain_type=ChainType.CORPORA,
        )
        try:
            corpora = await self._generate_corpora(
                num_corpora, callbacks=grp_cb, **kwargs
            )
        except Exception as e:
            await run_manager.on_chain_error(e)
            raise e
        await run_manager.on_chain_end({"corpora": corpora})
        return corpora

    @abstractmethod
    async def _generate_corpora(
        self, num_corpora: int, **kwargs: Any
    ) -> List[BaseCorpus]:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return camel_to_snake(self.__class__.__name__)
