#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from diting_core.models.llms.base_model import BaseLLM

from diting_core.models.llms.openai_model import LangchainLLMWrapper


def llm_factory(
    model: str,
    base_url: Optional[str] = None,
    api_key: Optional[SecretStr] = None,
    is_guided_json_support: bool = False,
    is_structured_output_support: bool = False,
) -> BaseLLM:
    llm = ChatOpenAI(model=model, base_url=base_url, api_key=api_key)
    return LangchainLLMWrapper(
        llm=llm,
        is_structured_output_support=is_structured_output_support,
        is_guided_json_support=is_guided_json_support,
    )
