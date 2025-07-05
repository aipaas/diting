from typing import List
from diting.models.embeddings.base_model import BaseEmbeddings


class MockEmbeddings(BaseEmbeddings):
    async def aembed_query(self, text: str) -> List[float]:
        return [0.1, 0.2, 0.4]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]
