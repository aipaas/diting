#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import field, dataclass
from typing import Any, List, Optional

from diting_core.callbacks.base import Callbacks
from diting_core.cases.llm_case import LLMCaseParams, LLMCase
from diting_core.models.llms.base_model import BaseLLM
from diting_core.synthesis.base_synthesizer import BaseSynthesizer
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_core.synthesis.qa.schema import QA
from diting_core.synthesis.qa.template import QAGenerateTemplate
from diting_core.metrics.utils import detect_language
from diting_server.common.logging_config.config import get_logger

logger = get_logger(__name__)


@dataclass
class EvalQASynthesizer(BaseSynthesizer):
    """
    基于QA生成finetune评估集的合成器

    Attributes:
        model (BaseLLM): 用于生成数据的语言模型
        required_input_fields (List[str]): 合成器所需的输入字段列表
        required_output_fields (List[str]): 合成器预期的输出字段列表
    """

    model: Optional[BaseLLM] = None
    required_input_fields: List[str] = field(
        default_factory=lambda: [
            LLMCaseParams.CONTEXT.value,
        ]
    )

    required_output_fields: List[str] = field(
        default_factory=lambda: [
            LLMCaseParams.USER_INPUT.value,
            LLMCaseParams.EXPECTED_OUTPUT.value,
        ]
    )

    async def _apply(
        self,
        corpus: BaseCorpus,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> LLMCase:
        # 验证输入
        assert self.model is not None, "llm is not set"
        assert corpus.context, "context cannot be empty"
        context = corpus.context

        # 检测语言
        combined_text = " ".join(context)
        language = detect_language(combined_text)

        # 生成问题列表
        prompt = QAGenerateTemplate.generate_simple_qa(context, language=language)

        qa_pairs = await self.model.generate_structured_output(
            prompt, schema=QA, callbacks=callbacks
        )
        qa_pairs = QA.model_validate(qa_pairs)

        llm_case = LLMCase(
            user_input=qa_pairs.question,
            expected_output=qa_pairs.answer,
            context=context,
            metadata={
                "synthesizer": self.name,
            },
        )

        return llm_case
