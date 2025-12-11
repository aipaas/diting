#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import field, dataclass
from typing import Any, List, Optional

from diting_core.callbacks.base import Callbacks
from diting_core.cases.llm_case import LLMCase
from diting_core.models.llms.base_model import BaseLLM
from diting_core.synthesis.base_synthesizer import BaseSynthesizer
from diting_core.synthesis.base_corpus import BaseCorpus
from diting_core.synthesis.qa.schema import QuestionPairs
from diting_core.synthesis.qa.template import QAGenerateTemplate
from diting_core.metrics.utils import detect_language
from diting_server.common.logging_config.config import get_logger
logger = get_logger(__name__)


@dataclass
class QuestionListSynthesizer(BaseSynthesizer):
    """
    基于文本生成问题列表的合成器。
    
    与QASynthesizer不同，这个合成器专注于生成多个问题而不是单个最佳QA对。
    它复用了QASynthesizer的模板和基础逻辑，但简化了输出格式。
    
    Attributes:
        model (BaseLLM): 用于生成数据的语言模型
        required_input_fields (List[str]): 合成器所需的输入字段列表
        required_output_fields (List[str]): 合成器预期的输出字段列表
    """

    model: Optional[BaseLLM] = None
    required_input_fields: List[str] = field(
        default_factory=lambda: [
            "context",
        ]
    )

    required_output_fields: List[str] = field(
        default_factory=lambda: [
            "context",
        ]
    )

    async def _apply(
        self,
        corpus: BaseCorpus,
        callbacks: Optional[Callbacks] = None,
        **kwargs: Any,
    ) -> LLMCase:
        """应用问题列表合成器到提供的输入数据。

        这个方法基于输入的上下文生成问题列表，专注于生成多个问题而不是单个最佳QA对。

        Args:
            corpus (BaseCorpus): 合成器的输入数据，必须包含指定的必需字段
            callbacks (Optional[Callbacks]): 在合成器应用期间执行的可选回调函数

        Returns:
            LLMCase: 包含生成问题列表的输出数据

        Raises:
            Exception: 如果生成过程中出现错误
        """
        # 验证输入
        assert self.model is not None, "LLM模型未设置"
        assert corpus.context, "上下文不能为空"

        context = corpus.context
        
        # 检测语言
        combined_text = " ".join(context)
        language = detect_language(combined_text)

        # 生成问题列表
        prompt = QAGenerateTemplate.generate_question_pairs(
            context, 
            language=language
        )
        
        question_pairs = await self.model.generate_structured_output(
            prompt, schema=QuestionPairs, callbacks=callbacks
        )
        question_pairs = QuestionPairs.model_validate(question_pairs).five_QAstyle_viewpoints
        
        # 提取问题列表
        questions = []
        for pair in question_pairs:
            questions.append(pair.question1)
            questions.append(pair.question2)
        
        # 创建LLMCase，将问题列表存储在metadata中
        llm_case = LLMCase(
            user_input=context[0], 
            context=questions,
            metadata={
                "synthesizer": self.name,
                "language": language.value if hasattr(language, 'value') else str(language),
            },
        )

        return llm_case