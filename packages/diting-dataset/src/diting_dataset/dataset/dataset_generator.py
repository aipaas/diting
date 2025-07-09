#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import typing as t
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document as LCDocument

from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCase
from diting_core.models.llms.base_model import BaseLLM
from diting_core.utilities.executor import task_wrapper

from diting_dataset.dataset.dataset import EvaluationDataset
from diting_dataset.synthesis.base_synthesizer import BaseSynthesizer, BaseCorpus
from diting_dataset.synthesis.qa.qa_synthesizer import QASynthesizer


@dataclass
class DataSetGenerator:
    """
    Generates an evaluation dataset based on given corpora and parameters.

    Attributes
    ----------
    llm : BaseJudgeLLM
        The language model to use for the generation process.
    """

    llm: t.Optional[BaseLLM]

    async def generate_dataset_from_langchain_docs(
        self,
        documents: t.Sequence[LCDocument],
        synthesizers: t.Sequence[BaseCorpus],
        **kwargs: t.Any,
    ) -> EvaluationDataset:
        """
        Generates an evaluation dataset based on given Langchain documents and parameters.

        Parameters
        ----------
        documents : Sequence[LCDocument]
            A sequence of Langchain documents to use as source material
        synthesizers : Sequence[BaseSynthesizer]
            Custom synthesizers to apply to the documents, by default BaseCorpus only
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
        ...

    async def generate_dataset_from_docs(
        self,
        document_paths: t.Sequence[Path],
        synthesizers: t.Sequence[BaseCorpus],
        **kwargs: t.Any,
    ) -> EvaluationDataset:
        """
        Generates an evaluation dataset based on given documents path and parameters.

        Parameters
        ----------
        document_paths : Sequence[Path]
            A sequence of documents path to use as source material
        synthesizers : Sequence[BaseSynthesizer]
            Custom synthesizers to apply to the documents, by default BaseCorpus only
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
        ...

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
        # callbacks.add_handler(CostCallbackHandler)
        # new group for Dataset Generation
        assert self.llm is not None, "llm is not set"
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
        testcases = []
        dataset = EvaluationDataset(testcases=testcases)
        await dataset_generation_rm.on_chain_end({"dataset": dataset})

        return dataset


async def _synthesizer_wrapper(
    synthesizer: BaseSynthesizer,
    corpus: BaseCorpus,
    testcases: list[LLMCase],
    **kwargs: t.Any,
) -> None:
    llm_case = await synthesizer.apply(corpus, **kwargs)
    testcases.append(llm_case)
