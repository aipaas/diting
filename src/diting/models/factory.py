#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from diting.models.base_model import BaseLLM

from diting.models.openai import OpenAIModel


def llm_factory() -> BaseLLM:
    return OpenAIModel()
