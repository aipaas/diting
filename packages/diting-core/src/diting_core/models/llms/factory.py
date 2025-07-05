#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from diting_core.models.llms.base_model import BaseLLM

from diting_core.models.llms.openai_model import OpenAIModel


def llm_factory() -> BaseLLM:
    return OpenAIModel()
