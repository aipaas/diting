import asyncio
from copy import deepcopy
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from enum import Enum

from diting_core.models.llms.factory import llm_factory
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_core.utilities.slug import camel_to_snake
from diting_core.synthesis.base_synthesizer import BaseSynthesizer
from diting_inspect.models.case_model import LLMCaseData, CaseRepository
from diting_inspect.models.model_management import ModelManagementData, ModelType
from diting_inspect.models.synthesizer_model import (
    SynthesizerRepository,
    SynthesizerResult,
)
from diting_inspect.synthesizers import SynthesizerFactory


logger = logging.getLogger(__name__)


class SynthesizerStatus(Enum):
    """Enumeration of evaluation statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SynthesizerService:
    """
    Service for managing and executing synthesizers.

    Provides functionality to run synthesizer on test cases concurrently,
    track synthesizer progress, and store results.
    """

    def __init__(
        self,
        synthesizer_repository: SynthesizerRepository,
        case_repository: Optional[CaseRepository] = None,
        max_concurrent_evaluations: int = 10,
    ):
        """
        Initialize synthesizer service.

        Args:
            evaluation_repository: Repository for storing evaluation results
            case_repository: Repository for accessing test cases
            max_concurrent_evaluations: Maximum concurrent evaluations
        """
        self._synthesizer_repository = synthesizer_repository
        self._case_repository = case_repository
        self._max_concurrent = max_concurrent_evaluations
        self._active_synthesizers: Dict[str, Dict[str, Any]] = {}

    async def _synthesize_case_with_synthesizer(
        self,
        case: LLMCaseData,
        synthesizer_config: Dict[str, Any],
        synthesizer_id: str,
        model_configs: Optional[List[ModelManagementData]] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            synthesizer_case = BaseCorpus(context=case.context)
            synthesizer: BaseSynthesizer = synthesizer_config["class"]()

            is_model_deps = hasattr(synthesizer, "model")
            llm_model_configs = None
            if model_configs:
                llm_model_configs = [
                    m for m in model_configs if m.model_type == ModelType.INFERENCE
                ]

            if is_model_deps and llm_model_configs:
                _model = llm_model_configs[0]
                llm_model = llm_factory(
                    model=_model.model_name,
                    base_url=_model.access_endpoint,
                    api_key=_model.api_key,
                )
                setattr(synthesizer, "model", llm_model)

            llm_case = await synthesizer.apply(
                synthesizer_case, verbose=synthesizer_config["debug"]
            )
            # generate case input, expected_output
            llm_case_data = LLMCaseData(
                id=case.id.strip(),
                input=llm_case.user_input or "",
                actual_output=llm_case.actual_output or "",
                expected_output=llm_case.expected_output,
                context=llm_case.context,
                retrieval_context=llm_case.retrieval_context,
                created_at=case.created_at,
                tags=case.tags,
            )
            if self._case_repository:
                await self._case_repository.update(case.id.strip(), llm_case_data)
            result = {
                "case_id": case.id,
                "synthesizer_name": synthesizer.name,
                "case": llm_case,
                "evaluated_at": datetime.now().isoformat(),
            }
            # Update progress
            if synthesizer_id in self._active_synthesizers:
                self._active_synthesizers[synthesizer_id]["completed_cases"] += 1

            return result

        except Exception as e:
            logger.error(
                f"Failed to evaluate case {case.id} with {camel_to_snake(synthesizer_config['class'].__name__)}: {e}"
            )
            return {
                "case_id": case.id,
                "metric_name": camel_to_snake(synthesizer_config["class"].__name__),
                "score": None,
                "error": str(e),
                "evaluated_at": datetime.now().isoformat(),
            }

    def _load_synthesizers(self, configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        configs_copy = deepcopy(configs)
        synthesizer_factory = SynthesizerFactory()

        for config in configs_copy:
            synthesizer_type = config.get("type", "")
            synthesizer = synthesizer_factory.create(synthesizer_type)
            config["class"] = synthesizer

        return configs_copy

    async def run_synthesizer(
        self,
        synthesizer_id: str,
        case_ids: List[str],
        synthesizer_configs: List[Dict[str, Any]],
        model_configs: Optional[List[ModelManagementData]] = None,
    ) -> None:
        """
        Run synthesizer data on specified cases with given synthesizer.

        Args:
            synthesizer_id: Unique identifier for this synthesizer
            case_ids: List of test case IDs to evaluate
            synthesizer_configs: List of synthesizer configurations
        """
        try:
            # Initialize synthesizer tracking
            self._active_synthesizers[synthesizer_id] = {
                "status": SynthesizerStatus.RUNNING.value,
                "started_at": datetime.now(),
                "total_cases": len(case_ids),
                "completed_cases": 0,
                "results": [],
            }

            # Save initial evaluation status to the repository
            initial_result = SynthesizerResult(
                id=synthesizer_id,
                case_ids=case_ids,
                synthesizer_configs=synthesizer_configs,
                model_configs=model_configs,
                results=[],
                status=SynthesizerStatus.RUNNING.value,
                started_at=datetime.now(),
                completed_at=None,
                total_cases=len(case_ids),
                total_synthesizers=len(synthesizer_configs),
                error=None,
            )
            await self._synthesizer_repository.save(initial_result)

            # Get test cases
            cases: list[LLMCaseData] = []
            if self._case_repository:
                for case_id in case_ids:
                    case = await self._case_repository.get_by_id(case_id)
                    if case:
                        cases.append(case)

            if not cases:
                raise ValueError("No valid test cases found")

            # Load metrics from configs
            synthesizer_configs_loaded = self._load_synthesizers(synthesizer_configs)

            # Create a semaphore to limit concurrent evaluations
            semaphore = asyncio.Semaphore(self._max_concurrent)

            async def synthesize_case(
                case: LLMCaseData,
                synthesizer_config: Dict[str, Any],
                model_config: Optional[List[ModelManagementData]] = None,
            ):
                async with semaphore:
                    return await self._synthesize_case_with_synthesizer(
                        case, synthesizer_config, synthesizer_id, model_config
                    )

            # Run evaluations concurrently using TaskGroup
            tasks: list[asyncio.Task[Any]] = []
            async with asyncio.TaskGroup() as tg:
                for case in cases:
                    assert len(synthesizer_configs_loaded) > 0
                    task = tg.create_task(
                        synthesize_case(
                            case, synthesizer_configs_loaded[0], model_configs
                        )
                    )
                    tasks.append(task)

            # Process results
            synthesizer_results: List[Dict[str, Any]] = []
            for task in tasks:
                try:
                    result = await task
                    if result:
                        synthesizer_results.append(result)
                except Exception as e:
                    logger.error(f"Error processing task: {e}")

            # Save final results
            final_result = SynthesizerResult(
                id=synthesizer_id,
                case_ids=case_ids,
                synthesizer_configs=synthesizer_configs,
                model_configs=model_configs,
                results=synthesizer_results,
                status=SynthesizerStatus.COMPLETED.value,
                started_at=self._active_synthesizers[synthesizer_id]["started_at"],
                completed_at=datetime.now(),
                total_cases=len(cases),
                total_synthesizers=len(synthesizer_configs),
                error=None,
            )

            await self._synthesizer_repository.save(final_result)

            # Update tracking
            self._active_synthesizers[synthesizer_id].update(
                {
                    "status": SynthesizerStatus.COMPLETED.value,
                    "completed_at": datetime.now(),
                    "results": synthesizer_results,
                }
            )

        except Exception as e:
            logger.error(f"Synthesizer {synthesizer_id} failed: {e}")

            # Mark as failed
            if synthesizer_id in self._active_synthesizers:
                self._active_synthesizers[synthesizer_id].update(
                    {
                        "status": SynthesizerStatus.FAILED.value,
                        "error": str(e),
                        "completed_at": datetime.now(),
                    }
                )
