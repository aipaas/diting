#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document as LCDocument

from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCase
from diting_core.models.embeddings.base_model import BaseEmbeddings
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.base_model import BaseLLM
from diting_core.models.llms.factory import llm_factory
from diting_core.utilities.executor import task_wrapper
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_dataset.corpus.graph_corpus_generator import (
    KnowledgeGraphCorpusGenerator,
)
from diting_dataset.dataset.dataset import EvaluationDataset
from diting_dataset.knowledge_graph.schema import Node, NodeType, KnowledgeGraph
from diting_dataset.knowledge_graph.transforms import (
    default_transforms,
    apply_transforms,
)
from diting_core.synthesis import BaseSynthesizer
from diting_core.synthesis import QASynthesizer


@dataclass
class DataSetGenerator:
    """
    Generates an evaluation dataset based on given corpora and parameters.

    Attributes
    ----------
    llm : BaseLLM
        The language model to use for the generation process.
    """

    llm: BaseLLM = field(default_factory=llm_factory)
    embedding_model: BaseEmbeddings = field(default_factory=embedding_factory)
    knowledge_graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)

    async def generate_dataset_from_docs(
        self,
        document_paths: t.Sequence[t.Union[str, Path]],
        dataset_size: int,
        synthesizers: t.Sequence[BaseSynthesizer],
        max_concurrency: int = 10,
        **kwargs: t.Any,
    ) -> EvaluationDataset:
        """
        Generates an evaluation dataset based on given documents path and parameters.

        Parameters
        ----------
        document_paths : Sequence[Path]
            A sequence of documents path to use as source material
        dataset_size : int
            The number of test cases to generate
        synthesizers : Sequence[BaseSynthesizer]
            Custom synthesizers to apply to the documents, by default BaseCorpus only
        max_concurrency: int
            the max concurrency for generate dataset from docs
        kwargs : t.Dict[str, t.Any]
            verbose : bool
                Whether to enable verbose mode. Defaults to False.
            callbacks : Callbacks
                The callback register to the run
            Other Additional keyword arguments.
        Returns
        -------
        EvaluationDataset
            The generated evaluation dataset

        Raises
        ------
        ValueError
            If no documents path is provided either during initialization or as arguments
        """

        if len(document_paths) == 0:
            raise ValueError(
                "the document_paths were not provided. Provide at least one document path as an argument for generate_dataset_from_docs parameter."
            )

        # todo 新建diting-documents项目实现文档解析操作，并将解析后的文档传入generate_dataset_from_langchain_docs实现生成Dataset
        dataset_generation_rm, dataset_generation_grp = await new_group(
            name="generate_dataset_from_docs",
            inputs={"document_paths": document_paths},
            callbacks=kwargs.pop("callbacks", None),
            verbose=kwargs.pop("verbose", False),
        )

        each_load_max_concurrency = 4
        semaphore = asyncio.Semaphore(int(max_concurrency / each_load_max_concurrency))
        documents: t.List[LCDocument] = []
        try:
            tasks = [
                task_wrapper(
                    semaphore,
                    _load_wrapper,
                    document_path=document_path,
                    documents=documents,
                    max_concurrency=each_load_max_concurrency,
                    callbacks=dataset_generation_grp,
                )
                for document_path in document_paths
            ]
            await asyncio.gather(*tasks)

            dataset = await self.generate_dataset_from_langchain_docs(
                documents, dataset_size, synthesizers, callbacks=dataset_generation_grp
            )
            await dataset_generation_rm.on_chain_end({"dataset": dataset})
            return dataset

        except Exception as e:
            await dataset_generation_rm.on_chain_error(e)
            raise e

    async def generate_dataset_from_langchain_docs(
        self,
        documents: t.Sequence[LCDocument],
        dataset_size: int,
        synthesizers: t.Sequence[BaseSynthesizer],
        max_concurrency: int = 10,
        **kwargs: t.Any,
    ) -> EvaluationDataset:
        """
        Generates an evaluation dataset based on given Langchain documents and parameters.

        Parameters
        ----------
        documents : Sequence[LCDocument]
            A sequence of Langchain documents to use as source material
        dataset_size : int
            The number of test cases to generate
        synthesizers : Sequence[BaseSynthesizer]
            Custom synthesizers to apply to the documents, by default BaseCorpus only
        max_concurrency: int
            the max concurrency for generate dataset from docs
        kwargs : t.Dict[str, t.Any]
            verbose : bool
                Whether to enable verbose mode. Defaults to False.
            callbacks : Callbacks
                The callback register to the run
            Other Additional keyword arguments.

        Returns
        -------
        EvaluationDataset
            The generated evaluation dataset

        Raises
        ------
        ValueError
            If no documents is provided either during initialization or as arguments
        """
        if len(documents) == 0:
            raise ValueError(
                "the documents were not provided. Provide at least one document as an argument for generate_dataset_from_langchain_docs parameter."
            )
        dataset_generation_rm, dataset_generation_grp = await new_group(
            name="generate_dataset_from_langchain_docs",
            inputs={"documents_size": len(documents)},
            callbacks=kwargs.pop("callbacks", None),
            verbose=kwargs.pop("verbose", False),
        )

        # convert the documents to knowledge-graph
        nodes: t.List[Node] = []
        for doc in documents:
            node = Node(
                type=NodeType.DOCUMENT,
                properties={
                    "page_content": doc.page_content,
                    "document_metadata": doc.metadata,
                },
            )
            nodes.append(node)

        kg = KnowledgeGraph(nodes=nodes)
        try:
            # apply transforms and update the knowledge graph
            transforms = default_transforms(
                documents=list(documents),
                llm=self.llm,
                embedding_model=self.embedding_model,
            )
            apply_transforms(kg, transforms, max_workers=max_concurrency)
            self.knowledge_graph = kg
            # generate corpus with the knowledge graph
            corpus_generator = KnowledgeGraphCorpusGenerator(
                kg, self.llm, max_concurrency=max_concurrency
            )

            num_corpora = int(dataset_size / (len(synthesizers) or 1))
            corpora = await corpus_generator.generate_corpora(
                num_corpora=num_corpora, callbacks=dataset_generation_grp
            )
            dataset = await self.generate_dataset_from_corpora(
                corpora,
                synthesizers,
                max_concurrency=max_concurrency,
                callbacks=dataset_generation_grp,
            )
            await dataset_generation_rm.on_chain_end({"dataset": dataset})
            return dataset

        except Exception as e:
            await dataset_generation_rm.on_chain_error(e)
            raise e

    # the core method
    async def generate_dataset_from_corpora(
        self,
        corpora: t.Sequence[BaseCorpus],
        synthesizers: t.Sequence[BaseSynthesizer],
        max_concurrency: int = 10,
        **kwargs: t.Any,
    ) -> EvaluationDataset:
        """
        Generates an evaluation dataset based on given corpora and parameters.

        Parameters
        ----------
        corpora : Sequence[BaseCorpus]
            A sequence of corpus to use as source material
        synthesizers : Sequence[BaseSynthesizer]
            Custom synthesizers to apply to the documents, by default BaseCorpus only
        max_concurrency: int
            the max concurrency for generate dataset from corpora
        kwargs : t.Dict[str, t.Any]
            verbose : bool
                Whether to enable verbose mode. Defaults to False.
            callbacks : Callbacks
                The callback register to the run
            Other Additional keyword arguments.
        Returns
        -------
        EvaluationDataset
            The generated evaluation dataset

        Raises
        ------
        ValueError
            If no corpora is provided either during initialization or as arguments
        """
        if len(corpora) == 0:
            raise ValueError(
                "the corpora were not provided. Provide at least one corpus as an argument for generate_dataset_from_corpora parameter."
            )
        # new group for Dataset Generation
        dataset_generation_rm, dataset_generation_grp = await new_group(
            name="generate_dataset_from_corpora",
            inputs={"corpora_size": len(corpora)},
            callbacks=kwargs.pop("callbacks", None),
            verbose=kwargs.pop("verbose", False),
        )

        if len(synthesizers) == 0:
            synthesizers = [QASynthesizer(model=self.llm)]

        semaphore = asyncio.Semaphore(max_concurrency)
        testcases: list[LLMCase] = []
        try:
            tasks = [
                task_wrapper(
                    semaphore,
                    _synthesizer_wrapper,
                    synthesizer=synthesizer,
                    corpus=corpus,
                    testcases=testcases,
                    callbacks=dataset_generation_grp,
                )
                for corpus in corpora
                for synthesizer in synthesizers
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            await dataset_generation_rm.on_chain_error(e)
            raise e

        # build the dataset
        dataset = EvaluationDataset(testcases=testcases)
        await dataset_generation_rm.on_chain_end({"dataset": dataset})

        return dataset


async def _load_wrapper(
    document_path: str,
    documents: list[LCDocument],
    max_concurrency: int,
    **kwargs: t.Any,
) -> None:
    data_load_rm, _ = await new_group(
        name="load_docs",
        inputs={"document_path": document_path},
        callbacks=kwargs.pop("callbacks", None),
        verbose=kwargs.pop("verbose", False),
    )
    try:
        from langchain_community.document_loaders import UnstructuredMarkdownLoader

        loader = UnstructuredMarkdownLoader(
            document_path, max_concurrency=max_concurrency, use_multithreading=True
        )
        docs = await loader.aload()
        await data_load_rm.on_chain_end(outputs={"loaded_documents_size": len(docs)})
        documents.extend(docs)
    except Exception as e:
        await data_load_rm.on_chain_error(e)
        raise e


async def _synthesizer_wrapper(
    synthesizer: BaseSynthesizer,
    corpus: BaseCorpus,
    testcases: list[LLMCase],
    **kwargs: t.Any,
) -> None:
    llm_case = await synthesizer.apply(corpus, **kwargs)
    testcases.append(llm_case)
