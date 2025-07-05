#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from diting_core.models.llms.base_model import BaseLLM, _DictOrPydanticClass, _Pydantic
import typing as t


class MockLLM(BaseLLM):
    async def generate(
        self, *args: t.Tuple[t.Any], **kwargs: t.Dict[str, t.Any]
    ) -> str:
        return "Generated Response"

    async def generate_structured_output(
        self,
        prompt: str,
        schema: t.Optional[_DictOrPydanticClass] = None,
        **kwargs: t.Any,
    ) -> _Pydantic:
        return {"testkey": "testval"}
