#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Any, Type, List, Dict
from diting_server.apis.v1.synthesis.data_models import (
    DatasetSynthesisRequest,
    DatasetSynthesisResponse,
    QuestionListResponse,
    QuestionList,
    ModelConfig,
    SynthesizerConfig,
    SyntheticQAResult,
    QAPair,
    FineTuneDataItem,
    FineTuneSample,
)
from diting_core.synthesis.base_synthesizer import BaseSynthesizer
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_server.services.synthesis.synthesizers import SynthesizerFactory
from diting_core.models.llms.factory import llm_factory
from diting_server.common.logging_config.config import get_logger
from diting_core.models.embeddings.factory import embedding_factory
from diting_server.common.callback import (
    GetEmbedTokenCallbackHandler,
    GetLLMTokenCallbackHandler,
)
from diting_server.exceptions.synthesis import (
    ModelConfigException,
    SynthesizerNotFoundException,
)
from diting_server.common.utils import resolve_model_config
from diting_server.common.schema import StatusEnum
from diting_server.common.utils import compute_token_usage

logger = get_logger(__name__)


class SynthesizerService:
    async def run_synthesizer(
        self, request: DatasetSynthesisRequest, request_id: str
    ) -> DatasetSynthesisResponse:
        corpus = BaseCorpus(
            context=request.input_data.context, themes=request.input_data.context
        )
        try:
            result = await self._synthesize_case_with_synthesizer(
                corpus=corpus,
                synthesizer_config=request.synthesizer_config,
                llm_config=request.llm_config,
                embedding_config=request.embedding_config,
            )
            synthesizer_result = result.get("llm_case")
            usages = result.get("usages", [])
            error_msg = result.get("error", None)
        except (ModelConfigException, SynthesizerNotFoundException) as e:
            logger.error(f"Error in synthesizing case: {str(e)}")
            raise e
        if request.synthesizer_config.synthesizer_name == "question_list_synthesizer":
            # 生成 1*10 indexes
            questions = QuestionList(
                questions=[]
                if error_msg
                else (
                    [question for question in synthesizer_result.context]
                    if synthesizer_result
                    else []
                )
            )
            status = StatusEnum.FAILED if error_msg else StatusEnum.SUCCESS
            response = QuestionListResponse(
                request_id=request_id,
                data=questions,
                usages=usages,
                status=status,
                error=error_msg,
                metadata=None,
            )

            return response
        else:
            q_a_pair = QAPair(
                question=""
                if error_msg
                else (synthesizer_result.user_input if synthesizer_result else ""),
                answer=""
                if error_msg
                else (synthesizer_result.expected_output if synthesizer_result else ""),
            )
            data = SyntheticQAResult(
                qa_pair=q_a_pair,
                metadata={}
                if error_msg
                else (synthesizer_result.metadata if synthesizer_result else {}),
            )
            status = StatusEnum.FAILED if error_msg else StatusEnum.SUCCESS
            response = DatasetSynthesisResponse(
                request_id=request_id,
                data=data,
                usages=usages,
                status=status,
                error=error_msg,
                metadata=None,
            )

            return response

    async def _synthesize_case_with_synthesizer(
        self,
        corpus: BaseCorpus,
        synthesizer_config: SynthesizerConfig,
        llm_config: Optional[ModelConfig] = None,
        embedding_config: Optional[ModelConfig] = None,
    ) -> dict[str, Any]:
        try:
            synthesizer: BaseSynthesizer = self._load_synthesizer(
                synthesizer_config.synthesizer_name
            )()
        except Exception as ex:
            error = str(ex)
            logger.error(
                f"Failed to load the synthesizer {synthesizer_config.synthesizer_name}. "
                f"Original error: {error}",
                exc_info=True,
            )
            raise SynthesizerNotFoundException(
                f"Failed to load the synthesizer {synthesizer_config.synthesizer_name}. "
                "Please ensure that this synthesizer is supported and correctly configured. "
                f"Original error: {error}"
            )

        is_llm_required = hasattr(synthesizer, "model")
        is_embedding_required = hasattr(synthesizer, "embedding_model")
        callbacks: list[Any] = []
        get_embed_token = GetEmbedTokenCallbackHandler()
        get_llm_token = GetLLMTokenCallbackHandler()
        if is_llm_required and llm_config:
            llm_config_resolved = resolve_model_config(
                model=llm_config.name,
                base_url=llm_config.base_url,
                api_key=llm_config.api_key,
            )
            llm_model = llm_factory(**llm_config_resolved, timeout=llm_config.timeout)
            setattr(synthesizer, "model", llm_model)
            callbacks.append(get_llm_token)
        elif is_llm_required and (not llm_config):
            logger.error(
                f"LLM model is required for synthesizer {synthesizer_config.synthesizer_name}. "
                "Please ensure that you have configured the appropriate LLM model."
            )
            raise ModelConfigException(
                f"LLM model is required for synthesizer {synthesizer_config.synthesizer_name}. "
                "Please ensure that you have configured the appropriate LLM model."
            )

        if is_embedding_required and embedding_config:
            embedding_config_resolved = resolve_model_config(
                model=embedding_config.name,
                base_url=embedding_config.base_url,
                api_key=embedding_config.api_key,
            )
            embedding_model = embedding_factory(
                **embedding_config_resolved, timeout=embedding_config.timeout
            )
            setattr(synthesizer, "embedding_model", embedding_model)
            callbacks.append(get_embed_token)
        elif is_embedding_required and (not embedding_config):
            logger.error(
                f"Embedding model is required for synthesizer {synthesizer_config.synthesizer_name}. "
                "Please ensure that you have configured the appropriate embedding model."
            )
            raise ModelConfigException(
                f"Embedding model is required for synthesizer {synthesizer_config.synthesizer_name} "
                "Please ensure that you have configured the appropriate embedding model."
            )
        llm_case = None
        error = None
        try:
            llm_case = await synthesizer.apply(corpus=corpus, callbacks=callbacks)
        except Exception as ex:
            error = str(ex)
            logger.error(f"Synthesizer application: {error}", exc_info=True)
        finally:
            usages = compute_token_usage(
                llm_usages=get_llm_token.usages,
                embed_usages=get_embed_token.usages,
                rerank_usages=None,
            )

        return {"llm_case": llm_case, "usages": usages, "error": error}

    def _load_synthesizer(self, synthesizer_name: str) -> Type[BaseSynthesizer]:
        synthesizer_factory = SynthesizerFactory()
        synthesizer = synthesizer_factory.create(synthesizer_name)
        return synthesizer

    async def build_fine_tune_data(
        self,
        items: List[FineTuneDataItem],
        min_negative_samples: int,
        max_negative_samples: int,
        include_original_q: bool,
        request_id: str,
    ) -> Dict[str, Any]:
        """
        构建微调数据
        """
        try:
            synthesizer_class = self._load_synthesizer("fine_tune_data_synthesizer")
            synthesizer = synthesizer_class()

            corpus = BaseCorpus()
            corpus.fine_tune_items = items
            corpus.min_negative_samples = min_negative_samples
            corpus.max_negative_samples = max_negative_samples
            corpus.include_original_q = include_original_q
            corpus.request_id = request_id

            llm_case = await synthesizer.apply(corpus=corpus)

            # 从 metadata 中提取结果
            result = llm_case.metadata.get("result", {})

            # 将字典格式的样本转换为 FineTuneSample 对象
            samples = result.get("samples", [])
            converted_samples = []
            for sample_dict in samples:
                if isinstance(sample_dict, dict):
                    # 转换为 FineTuneSample 对象
                    sample = FineTuneSample(
                        query=sample_dict.get("query", ""),
                        positive=sample_dict.get("positive", []),
                        negatives=sample_dict.get("negatives", []),
                        source_id=sample_dict.get("source_id", ""),
                        collection_id=sample_dict.get("collection_id", ""),
                        original_q=sample_dict.get("original_q"),
                        original_a=sample_dict.get("original_a"),
                        metadata=sample_dict.get("metadata", {}),
                    )
                    converted_samples.append(sample)
                else:
                    # 如果已经是 FineTuneSample 对象，直接使用
                    converted_samples.append(sample_dict)

            # 更新结果中的样本
            result["samples"] = converted_samples

            logger.info(
                f"Request {request_id}: Built {result.get('total_samples', 0)} samples from {len(items)} items using synthesizer"
            )

            return result

        except Exception as e:
            logger.error(
                f"Request {request_id}: Error building fine tune data with synthesizer: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to build fine tune data: {str(e)}") from e


synthesizer_service = SynthesizerService()
