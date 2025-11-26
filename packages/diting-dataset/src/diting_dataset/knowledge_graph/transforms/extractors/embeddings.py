import typing as t
from dataclasses import dataclass, field

from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_core.models.embeddings.factory import embedding_factory
from diting_dataset.knowledge_graph.schema import Node
from diting_dataset.knowledge_graph.transforms import Extractor


@dataclass
class EmbeddingExtractor(Extractor):
    """
    A class for extracting embeddings from nodes in a knowledge graph.

    Attributes
    ----------
    property_name : str
        The name of the property to store the embedding
    embed_property_name : str
        The name of the property containing the text to embed
    embedding_model : BaseEmbeddings
        The embedding model used for generating embeddings
    """

    property_name: str = "embedding"
    embed_property_name: str = "page_content"
    embedding_model: BaseEmbeddings = field(default_factory=embedding_factory)

    async def extract(self, node: Node) -> t.Tuple[str, t.Any]:
        """
        Extracts the embedding for a given node.

        Raises
        ------
        ValueError
            If the property to be embedded is not a string.
        """
        text = node.get_property(self.embed_property_name)
        if not isinstance(text, str):
            raise ValueError(
                f"node.property('{self.embed_property_name}') must be a string, found '{type(text)}'"
            )
        embedding = await self.embedding_model.embed_text(text)
        return self.property_name, embedding
