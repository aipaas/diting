#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional

import json_repair
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage

from diting_core.callbacks.base import ChainType
from diting_core.callbacks.manager import new_group
from diting_core.models.llms.base_model import (
    BaseLLM,
    DictOrPydantic,
    PydanticClass,
)
from diting_core.models.utils import filter_model_output


class LangchainLLMWrapper(BaseLLM):
    """
    A simple wrapper class for DiTing Large Language Models (LLMs) based on Langchain's
    BaseLanguageModel interface.

    This class provides two main asynchronous methods:
    - `generate`: placeholder for generating text (to be implemented).
    - `generate_structured_output`: generates structured output by invoking the underlying LLM
      with optional support for guided JSON schema or structured output features.

    Attributes:
        llm (BaseLanguageModel[BaseMessage]): The underlying Langchain LLM instance to wrap.
        is_guided_json_support (bool): Indicates if the LLM supports guided JSON schema
            prompting (default: False).
        is_structured_output_support (bool): Indicates if the LLM supports structured output
            interface (default: False).
    """

    def __init__(
        self,
        llm: BaseLanguageModel[BaseMessage],
        is_guided_json_support: bool = False,
        is_structured_output_support: bool = False,
    ):
        super().__init__()
        self.llm = llm
        self.is_guided_json_support: bool = is_guided_json_support
        self.is_structured_output_support: bool = is_structured_output_support

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(llm={self.llm.__class__.__name__}(...))"

    async def generate(self, *args: Any, **kwargs: Dict[str, Any]) -> str:
        return ""

    async def _invoke_and_parse(
        self,
        prompt: str,
        schema: Optional[PydanticClass] = None,
        use_guided_json: bool = False,
        use_structured_output: bool = False,
        **kwargs: Any,
    ) -> Any:
        run_manager, _ = await new_group(
            name=self.__repr__(),
            inputs={"prompt": prompt},
            callbacks=kwargs.pop("callbacks", None),
            verbose=kwargs.pop("verbose", False),
            chain_type=ChainType.LLM,
            schema=schema,
        )
        try:
            if schema is None:
                res = await self.llm.ainvoke(prompt, **kwargs)
                fmt_output = filter_model_output(res.content)  # type: ignore
                output_model = json_repair.loads(fmt_output)
            elif use_guided_json:
                json_schema = schema.model_json_schema()
                self.llm.extra_body = {"guided_json": json_schema}  # type: ignore
                res = await self.llm.ainvoke(prompt, **kwargs)
                fmt_output = filter_model_output(res.content)  # type: ignore
                json_output = json_repair.loads(fmt_output)
                output_model = schema.model_validate(json_output)

            elif use_structured_output:
                # tool call
                llm_structured = self.llm.with_structured_output(schema)  # type: ignore
                res = await llm_structured.ainvoke(prompt, **kwargs)  # type: ignore
                output_model = schema.model_validate(res)
            else:
                res = await self.llm.ainvoke(prompt, **kwargs)
                fmt_output = filter_model_output(res.content)  # type: ignore
                json_output = json_repair.loads(fmt_output)
                output_model = schema.model_validate(json_output)
        except Exception as e:
            await run_manager.on_chain_error(e)
            raise e

        await run_manager.on_chain_end(outputs={"llm_output": output_model})
        return output_model

    async def generate_structured_output(
        self,
        prompt: str,
        schema: Optional[PydanticClass] = None,
        **kwargs: Any,
    ) -> DictOrPydantic:
        return await self._invoke_and_parse(
            prompt,
            schema=schema,
            use_guided_json=self.is_guided_json_support,
            use_structured_output=self.is_structured_output_support,
            **kwargs,
        )
