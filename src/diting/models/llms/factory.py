#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from diting.models.llms.base_model import BaseLLM

from diting.models.llms.openai_model import OpenAIModel


def llm_factory() -> BaseLLM:
    return OpenAIModel()
