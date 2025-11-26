"""Synthesis runner using diting-core synthesizers.

Provides a wrapper to execute data synthesis using diting-core synthesizers
with configuration from the web backend.
"""

from typing import Any, Optional

from diting_core.cases.llm_case import LLMCase
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_core.synthesis.base_synthesizer import BaseSynthesizer
from diting_core.synthesis.qa.qa_synthesizer import QASynthesizer

from diting_web.common.logging import get_logger
from diting_web.integrations.core_adapter.config_mapper import create_llm_from_config

logger = get_logger(__name__)


class SynthesisRunner:
    """Runner for executing diting-core data synthesis.
    
    This class provides a high-level interface to:
    1. Create synthesizer instances from configuration
    2. Execute synthesis on corpus data
    3. Return structured synthetic data
    """

    # Mapping of synthesizer names to their classes
    SYNTHESIZER_REGISTRY: dict[str, type[BaseSynthesizer]] = {
        "qa": QASynthesizer,
        "qa_synthesizer": QASynthesizer,
    }

    @classmethod
    def create_synthesizer(
        cls,
        synthesizer_type: str,
        llm_config: dict[str, Any],
        synthesizer_params: Optional[dict[str, Any]] = None,
    ) -> BaseSynthesizer:
        """Create a synthesizer instance from configuration.
        
        Args:
            synthesizer_type: Type of synthesizer (e.g., "qa")
            llm_config: LLM configuration dictionary
            synthesizer_params: Additional synthesizer-specific parameters
        
        Returns:
            BaseSynthesizer: Configured synthesizer instance
        
        Raises:
            ValueError: If synthesizer type is not recognized
        """
        if synthesizer_type not in cls.SYNTHESIZER_REGISTRY:
            raise ValueError(
                f"Unknown synthesizer: {synthesizer_type}. "
                f"Available synthesizers: {list(cls.SYNTHESIZER_REGISTRY.keys())}"
            )

        synthesizer_class = cls.SYNTHESIZER_REGISTRY[synthesizer_type]
        synthesizer_params = synthesizer_params or {}

        logger.info(
            "Creating synthesizer",
            synthesizer_type=synthesizer_type,
            synthesizer_params=synthesizer_params,
        )

        # Create LLM
        try:
            llm = create_llm_from_config(llm_config)
        except Exception as e:
            logger.error("Failed to create LLM for synthesizer", error=str(e))
            raise

        # Instantiate synthesizer
        try:
            synthesizer = synthesizer_class(
                model=llm,
                **synthesizer_params,
            )
            logger.info("Synthesizer created successfully", synthesizer_type=synthesizer_type)
            return synthesizer
        except Exception as e:
            logger.error("Failed to instantiate synthesizer", synthesizer_type=synthesizer_type, error=str(e))
            raise

    @classmethod
    async def run_synthesis(
        cls,
        synthesizer_type: str,
        corpus_data: dict[str, Any],
        llm_config: dict[str, Any],
        synthesizer_params: Optional[dict[str, Any]] = None,
        num_generations: int = 1,
    ) -> list[dict[str, Any]]:
        """Run data synthesis.
        
        Args:
            synthesizer_type: Type of synthesizer to use
            corpus_data: Corpus data dictionary with fields:
                - context (list[str], required for QA): List of context documents
                - document (str, optional): Single document text
                - metadata (dict, optional): Additional metadata
            llm_config: LLM configuration
            synthesizer_params: Additional synthesizer parameters
            num_generations: Number of synthetic samples to generate (default: 1)
        
        Returns:
            list[dict]: List of synthesized data items, each with:
                - question (str): Generated question
                - answer (str): Generated answer
                - context (list[str], optional): Associated context
                - metadata (dict, optional): Additional metadata
        
        Examples:
            >>> results = await SynthesisRunner.run_synthesis(
            ...     synthesizer_type="qa",
            ...     corpus_data={
            ...         "context": ["Python is a programming language.", "Python was created by Guido van Rossum."]
            ...     },
            ...     llm_config={"model_name": "gpt-4"},
            ...     num_generations=3
            ... )
        """
        logger.info(
            "Running synthesis",
            synthesizer_type=synthesizer_type,
            num_generations=num_generations,
            corpus_fields=list(corpus_data.keys()),
        )

        # Create corpus
        corpus = BaseCorpus(**corpus_data)

        # Create synthesizer
        synthesizer = cls.create_synthesizer(
            synthesizer_type=synthesizer_type,
            llm_config=llm_config,
            synthesizer_params=synthesizer_params,
        )

        # Run synthesis multiple times
        results = []
        for i in range(num_generations):
            try:
                logger.info(f"Generating sample {i+1}/{num_generations}")
                
                llm_case: LLMCase = await synthesizer.apply(
                    corpus=corpus,
                    verbose=True,
                )

                result = {
                    "question": llm_case.user_input,
                    "answer": llm_case.expected_output,
                    "context": llm_case.context,
                    "metadata": llm_case.metadata or {},
                }

                results.append(result)

                logger.info(
                    f"Sample {i+1} generated",
                    question_len=len(result["question"]) if result["question"] else 0,
                    answer_len=len(result["answer"]) if result["answer"] else 0,
                    quality_score=result["metadata"].get("score"),
                )

            except Exception as e:
                logger.error(
                    f"Failed to generate sample {i+1}",
                    error=str(e),
                    exc_info=True,
                )
                # Continue generating other samples even if one fails
                continue

        logger.info(
            "Synthesis completed",
            synthesizer_type=synthesizer_type,
            requested=num_generations,
            generated=len(results),
        )

        return results

