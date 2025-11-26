"""Data synthesis using diting-core SDK.

Provides wrapper to execute data synthesis using diting-core synthesizers.
"""

from typing import Any, Optional

from diting_core.cases.llm_case import LLMCase
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_core.synthesis.base_synthesizer import BaseSynthesizer

# Import utilities from diting-server (same as EvaluationRunner)
from diting_server.services.synthesis.synthesizers import SynthesizerFactory
from diting_server.common.callback import GetLLMTokenCallbackHandler
from diting_server.common.utils import compute_token_usage

from diting_web.common.logging import get_logger
from diting_web.utils.model_helpers import create_llm_from_config

logger = get_logger(__name__)


class SynthesisRunner:
    """Runner for executing diting-core data synthesis.
    
    Directly uses diting-server's SynthesizerFactory for automatic synthesizer discovery,
    providing the same behavior as diting-server's SynthesizerService.
    
    This class provides a high-level interface to:
    1. Create synthesizer instances from configuration using SynthesizerFactory
    2. Execute synthesis on corpus data
    3. Return structured synthetic data
    """

    # Use diting-server's SynthesizerFactory (same as EvaluationRunner uses MetricFactory)
    _synthesizer_factory = SynthesizerFactory()

    @classmethod
    def _load_synthesizer(cls, synthesizer_type: str) -> type[BaseSynthesizer]:
        """Load synthesizer class using diting-server's SynthesizerFactory.
        
        Args:
            synthesizer_type: Type of synthesizer (e.g., "qa", "qa_synthesizer")
        
        Returns:
            type[BaseSynthesizer]: Synthesizer class
        
        Raises:
            ValueError: If synthesizer type is not recognized
        """
        return cls._synthesizer_factory.create(synthesizer_type)

    @classmethod
    def create_synthesizer(
        cls,
        synthesizer_type: str,
        llm_config: dict[str, Any],
        synthesizer_params: Optional[dict[str, Any]] = None,
    ) -> BaseSynthesizer:
        """Create a synthesizer instance from configuration.
        
        Uses diting-server's SynthesizerFactory for automatic synthesizer discovery.
        
        Args:
            synthesizer_type: Type of synthesizer (e.g., "qa", "qa_synthesizer")
            llm_config: LLM configuration dictionary
            synthesizer_params: Additional synthesizer-specific parameters
        
        Returns:
            BaseSynthesizer: Configured synthesizer instance
        
        Raises:
            ValueError: If synthesizer type is not recognized
        """
        synthesizer_params = synthesizer_params or {}

        logger.info(
            "Creating synthesizer",
            synthesizer_type=synthesizer_type,
            synthesizer_params=synthesizer_params,
        )

        # Load synthesizer using factory (same as EvaluationRunner)
        try:
            synthesizer_class = cls._load_synthesizer(synthesizer_type)
        except Exception as ex:
            error = str(ex)
            logger.error(
                f"Failed to load synthesizer {synthesizer_type}. Error: {error}",
                exc_info=True,
            )
            raise ValueError(f"Failed to load synthesizer {synthesizer_type}: {error}")

        # Create LLM using helper
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
    ) -> tuple[list[dict[str, Any]], list[Any]]:
        """Run data synthesis using diting-core SDK.
        
        Creates callbacks internally for token tracking (same as EvaluationRunner).
        
        Args:
            synthesizer_type: Type of synthesizer to use. Must match the snake_case name
                from SynthesizerFactory. For QASynthesizer, use "q_a_synthesizer"
                (not "qa" or "qa_synthesizer"). The factory converts class names using
                camel_to_snake: QASynthesizer -> q_a_synthesizer
            corpus_data: Corpus data dictionary with fields:
                - context (list[str], required for QA): List of context documents
                - document (str, optional): Single document text
                - metadata (dict, optional): Additional metadata
            llm_config: LLM configuration
            synthesizer_params: Additional synthesizer parameters
            num_generations: Number of synthetic samples to generate (default: 1)
        
        Returns:
            tuple: (list of synthesized data items, list of token usages)
                - Each data item contains:
                    - question (str): Generated question
                    - answer (str): Generated answer
                    - context (list[str], optional): Associated context
                    - metadata (dict, optional): Additional metadata
                - Token usages computed from internal callbacks
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

        # Setup callbacks for token tracking (same as EvaluationRunner and diting-server)
        get_llm_token = GetLLMTokenCallbackHandler()
        callbacks = [get_llm_token]

        # Run synthesis multiple times
        results = []
        for i in range(num_generations):
            try:
                # 仅在首次和最后一次记录日志，避免大量生成时刷屏
                if i == 0 or i == num_generations - 1:
                    logger.info(f"Generating sample {i+1}/{num_generations}")
                
                # Pass callbacks to synthesizer.apply
                # verbose=False 降低中间过程日志输出
                llm_case: LLMCase = await synthesizer.apply(
                    corpus=corpus,
                    verbose=False,  # 关闭详细日志
                    callbacks=callbacks,
                )

                result = {
                    "question": llm_case.user_input,
                    "answer": llm_case.expected_output,
                    "context": llm_case.context,
                    "metadata": llm_case.metadata or {},
                }

                results.append(result)

                # 仅在首次和最后一次记录详细信息
                if i == 0 or i == num_generations - 1:
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

        # Compute token usage from callbacks (same as EvaluationRunner and diting-server)
        usages = compute_token_usage(
            llm_usages=get_llm_token.usages,
            embed_usages=[],  # Synthesis doesn't use embeddings
        )

        return results, usages

