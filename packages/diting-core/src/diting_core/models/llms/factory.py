#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional
from langchain_openai import ChatOpenAI

from diting_core.models.llms.base_model import BaseLLM
from pydantic import SecretStr
from diting_core.models.llms.openai_model import LangchainLLMWrapper


def llm_factory(
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    is_guided_json_support: bool = False,
    is_structured_output_support: bool = False,
) -> BaseLLM:
    if api_key:
        llm = ChatOpenAI(model=model, base_url=base_url, api_key=SecretStr(api_key))
    else:
        llm = ChatOpenAI(model=model, base_url=base_url)
    return LangchainLLMWrapper(
        llm=llm,
        is_structured_output_support=is_structured_output_support,
        is_guided_json_support=is_guided_json_support,
    )
