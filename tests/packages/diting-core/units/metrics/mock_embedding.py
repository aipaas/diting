from typing import List, Any
from diting_core.models.embeddings.base_model import BaseEmbeddings


class MockEmbeddings(BaseEmbeddings):
    async def embed_text(self, text: str, **kwargs: Any) -> List[float]:
        return [0.1, 0.2, 0.4]

    async def embed_texts(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]
