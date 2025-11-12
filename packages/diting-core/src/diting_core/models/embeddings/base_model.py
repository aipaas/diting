#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import typing as t

from diting_core.utilities.cache import CacheInterface, cacher  # type: ignore


class BaseEmbeddings(ABC):
    cache: t.Optional[CacheInterface] = None

    def __init__(self, cache: t.Optional[CacheInterface] = None):
        self.cache = cache
        if self.cache is not None:
            self.embed_text = cacher(cache_backend=self.cache)(self.embed_text)
            self.embed_texts = cacher(cache_backend=self.cache)(self.embed_texts)

    @abstractmethod
    async def embed_text(self, text: str, **kwargs: t.Any) -> t.List[float]: ...

    @abstractmethod
    async def embed_texts(
        self, texts: t.List[str], **kwargs: t.Any
    ) -> t.List[t.List[float]]: ...
