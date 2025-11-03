#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import random
import typing as t
from dataclasses import dataclass

import numpy as np

from diting_core.callbacks.base import Callbacks
from diting_core.models.llms.base_model import BaseLLM
from diting_core.synthesis.base_corpus import (
    BaseCorpusGenerator,
)
from diting_dataset.corpus import QueryLength, QueryStyle, Persona, GraphBasedCorpus
from diting_dataset.corpus.persona import (
    generate_personas_from_kg,
    PersonaList,
)
from diting_dataset.corpus.template import (
    ThemesPersonasMatchingPrompt,
    ThemesPersonasInput,
    PersonaThemesMapping,
)
from diting_dataset.knowledge_graph.schema import KnowledgeGraph, Node
from diting_dataset.utilities.pydantic_prompt import PydanticPrompt

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGraphCorpusGenerator(BaseCorpusGenerator):
    knowledge_graph: KnowledgeGraph
    llm: BaseLLM
    theme_persona_matching_prompt: PydanticPrompt[
        ThemesPersonasInput, PersonaThemesMapping
    ] = ThemesPersonasMatchingPrompt()
    property_name: str = "entities"
    max_concurrency: int = 10

    def __post_init__(self):
        nodes = self._get_node_clusters()
        if len(nodes) == 0:
            raise ValueError(
                "No clusters found in the knowledge graph. Try changing the relationship condition."
            )
        self.nodes = nodes

    def _get_node_clusters(self) -> t.List[Node]:
        node_type_dict: t.Dict[str, int] = {"CHUNK": 0, "DOCUMENT": 0}
        for node in self.knowledge_graph.nodes:
            if (
                node.type.name == "CHUNK"
                and node.get_property(self.property_name) is not None
            ):
                node_type_dict["CHUNK"] += 1
            elif (
                node.type.name == "DOCUMENT"
                and node.get_property(self.property_name) is not None
            ):
                node_type_dict["DOCUMENT"] += 1
            else:
                pass

        node_filter = (
            "CHUNK"
            if node_type_dict["CHUNK"] > node_type_dict["DOCUMENT"]
            else "DOCUMENT"
        )

        nodes: t.List[Node] = []
        for node in self.knowledge_graph.nodes:
            if node.type.name == node_filter:
                nodes.append(node)

        return nodes

    async def _generate_corpora(
        self,
        num_corpora: int,
        num_personas: int = 3,
        callbacks: t.Optional[Callbacks] = None,
        **kwargs: t.Any,
    ) -> t.Sequence[GraphBasedCorpus]:
        """
        Generates a list of corpora on type SingleHop
        Steps to generate corpora:
        1. Find nodes with CHUNK type and entities property
        2. Calculate the number of samples that should be created per node to get n samples in total
        3. For each node
            a. Find the entities associated with the node
            b. Map personas to the entities to create query
            c. Prepare all possible combinations of (node, entities, personas, style, length) as base corpora
            d. Sample num_sample_per_node (step 2) corpora from base corpora
        4. Return the list of corpora
        """
        persona_list = await generate_personas_from_kg(
            llm=self.llm,
            kg=self.knowledge_graph,
            num_personas=num_personas,
            max_concurrency=self.max_concurrency,
            callbacks=callbacks,
        )

        nodes = self.nodes
        samples_per_node = int(np.ceil(num_corpora / len(nodes)))

        corpora: t.List[GraphBasedCorpus] = []
        for node in nodes:
            if len(corpora) >= num_corpora:
                break
            themes = node.properties.get(self.property_name, [""])
            prompt_input = ThemesPersonasInput(themes=themes, personas=persona_list)
            persona_concepts = await self.theme_persona_matching_prompt.generate(
                self.llm, data=prompt_input, callbacks=callbacks
            )

            base_corpora = self.prepare_combinations(
                node,
                themes,
                personas=persona_list,
                persona_concepts=persona_concepts.mapping,
            )
            corpora.extend(self.sample_combinations(base_corpora, samples_per_node))

        return corpora

    def prepare_combinations(
        self,
        node: Node,
        terms: t.List[str],
        personas: t.List[Persona],
        persona_concepts: t.Dict[str, t.List[str]],
    ) -> t.List[t.Dict[str, t.Any]]:
        sample: t.Dict[str, t.Any] = {"terms": terms, "node": node}
        valid_personas: t.List[Persona] = []
        persona_list = PersonaList(personas=personas)
        for persona, concepts in persona_concepts.items():
            concepts = [concept.lower() for concept in concepts]
            if any(term.lower() in concepts for term in terms):
                if persona_list[persona]:
                    valid_personas.append(persona_list[persona])
        sample["personas"] = valid_personas
        sample["styles"] = list(QueryStyle)
        sample["lengths"] = list(QueryLength)

        return [sample]

    def sample_combinations(self, data: t.List[t.Dict[str, t.Any]], num_samples: int):
        selected_samples: t.List[t.Dict[str, t.Any]] = []
        node_term_set: t.Set[t.Tuple[t.Any, t.Any]] = set()

        all_combinations: t.List[t.Dict[str, t.Any]] = []
        for entry in data:
            node = entry["node"]
            for term in entry["terms"]:
                for persona in entry["personas"]:
                    for style in entry["styles"]:
                        for length in entry["lengths"]:
                            all_combinations.append(
                                {
                                    "term": term,
                                    "node": node,
                                    "persona": persona,
                                    "style": style,
                                    "length": length,
                                }
                            )

        random.shuffle(all_combinations)
        for sample in all_combinations:
            if len(selected_samples) >= num_samples:
                break

            term = sample["term"]
            node = sample["node"]

            if (node, term) not in node_term_set:
                selected_samples.append(sample)
                node_term_set.add((node, term))
            elif len(selected_samples) < num_samples:
                selected_samples.append(sample)

        return [self.convert_to_corpus(sample) for sample in selected_samples]

    def convert_to_corpus(self, data: t.Dict[str, t.Any]) -> GraphBasedCorpus:
        node = t.cast(Node, data["node"])
        context = node.properties.get("page_content", "")
        return GraphBasedCorpus(
            scenario=data["term"],
            context=[context],
            persona=data["persona"],
            style=data["style"],
            length=data["length"],
        )
