#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import AsyncMock
from diting_dataset.knowledge_graph.schema import Node
from diting_dataset.utilities.pydantic_prompt import StringIO
from diting_dataset.knowledge_graph.transforms.extractors.llm_based import (
    SummaryExtractor,
    KeyphrasesExtractor,
    TitleExtractor,
    HeadlinesExtractor,
    NERExtractor,
    TopicDescriptionExtractor,
    ThemesExtractor,
    Keyphrases,
    Headlines,
    NEROutput,
    TopicDescription,
    ThemesAndConcepts,
)


class TestExtractors(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Node and LLM
        self.node = Node(properties={"page_content": "This is a test content."})
        self.llm_mock = AsyncMock()

    async def test_summary_extractor(self):
        extractor = SummaryExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=StringIO(text="This is a summary.")
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "summary")
        self.assertEqual(result, "This is a summary.")

    async def test_keyphrases_extractor(self):
        extractor = KeyphrasesExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=Keyphrases(keyphrases=["keyphrase1", "keyphrase2"])
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "keyphrases")
        self.assertEqual(result, ["keyphrase1", "keyphrase2"])

    async def test_title_extractor(self):
        extractor = TitleExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=StringIO(text="This is a title.")
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "title")
        self.assertEqual(result, "This is a title.")

    async def test_headlines_extractor(self):
        extractor = HeadlinesExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=Headlines(headlines=["Headline 1", "Headline 2"])
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "headlines")
        self.assertEqual(result, ["Headline 1", "Headline 2"])

    async def test_ner_extractor(self):
        extractor = NERExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=NEROutput(entities=["Entity1", "Entity2"])
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "entities")
        self.assertEqual(result, ["Entity1", "Entity2"])

    async def test_topic_description_extractor(self):
        extractor = TopicDescriptionExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=TopicDescription(description="This is a topic description.")
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "topic_description")
        self.assertEqual(result, "This is a topic description.")

    async def test_themes_extractor(self):
        extractor = ThemesExtractor(llm=self.llm_mock)
        self.llm_mock.generate_structured_output = AsyncMock(
            return_value=ThemesAndConcepts(output=["Theme1", "Theme2"])
        )

        property_name, result = await extractor.extract(self.node)

        self.assertEqual(property_name, "themes")
        self.assertEqual(result, ["Theme1", "Theme2"])


if __name__ == "__main__":
    unittest.main()
