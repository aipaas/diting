#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import typing as t

from diting_core.models.llms.base_model import (
    BaseLLM,
    DictOrPydanticClass,
    DictOrPydantic,
)


class OpenAIModel(BaseLLM):
    async def generate(self, *args: t.Any, **kwargs: t.Dict[str, t.Any]) -> str: ...

    async def generate_structured_output(
        self,
        prompt: str,
        schema: t.Optional[DictOrPydanticClass] = None,
        **kwargs: t.Any,
    ) -> DictOrPydantic: ...
