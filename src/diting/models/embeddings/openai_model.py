#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any, List
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field

from diting.models.embeddings.base_model import BaseEmbeddings


class PrivateEmbeddings(BaseModel, Embeddings):
    model: str
    client: Any = Field(default=None, exclude=True)
    async_client: Any = Field(default=None, exclude=True)

    def embed_query(self, text: str) -> List[float]:
        result = self.client.embeddings.create(model=self.model, input=[text])
        return result.data[0].embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = self.client.embeddings.create(model=self.model, input=texts)
        return [embedding.embedding for embedding in result.data]

    async def aembed_query(self, text: str) -> List[float]:
        result = await self.async_client.embeddings.create(
            model=self.model, input=[text]
        )
        return result.data[0].embedding

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        result = await self.async_client.embeddings.create(
            model=self.model, input=texts
        )
        return [embedding.embedding for embedding in result.data]


class LangchainEmbeddingsWrapper(BaseEmbeddings):
    """
    Wrapper for any embeddings from langchain.
    """

    def __init__(
        self,
        embeddings: Embeddings,
    ):
        self.embeddings = embeddings
        super().__init__()

    async def aembed_query(self, text: str) -> List[float]:
        """
        Asynchronously embed a single query text.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text)}")
        return await self.embeddings.aembed_query(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Asynchronously embed multiple documents.
        """
        if not isinstance(texts, list):
            raise TypeError(f"texts must be a list, got {type(texts)}")
        return await self.embeddings.aembed_documents(texts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(embeddings={self.embeddings.__class__.__name__}(...))"
