#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import typing as t

from pydantic import BaseModel

from diting_core.callbacks.base import Callbacks
from diting_core.models.llms.base_model import BaseLLM

# type variables for input and output models
InputModel = t.TypeVar("InputModel", bound=BaseModel)
OutputModel = t.TypeVar("OutputModel", bound=BaseModel)


class PydanticPrompt(t.Generic[InputModel, OutputModel]):
    # these are class attributes
    input_model: t.Type[InputModel]
    output_model: t.Type[OutputModel]
    instruction: str
    examples: t.List[t.Tuple[InputModel, OutputModel]] = []

    def _form_output_signature(self) -> str:
        return (
            f"Please return the output in a JSON format that complies with the "
            f"following schema as specified in JSON Schema:\n"
            f"{json.dumps(self.output_model.model_json_schema(), ensure_ascii=False, indent=4)}"
            "Do not use single quotes in your response but double quotes,"
            "properly escaped with a backslash."
        )

    def _form_examples(self) -> str:
        if self.examples:
            example_strings: t.List[str] = []
            for idx, e in enumerate(self.examples):
                input_data, output_data = e
                example_strings.append(
                    f"Example {idx + 1}\n"
                    + "Input: "
                    + input_data.model_dump_json(indent=4)
                    + "\n"
                    + "Output: "
                    + output_data.model_dump_json(indent=4)
                )

            return "\n--------EXAMPLES-----------\n" + "\n\n".join(example_strings)
        # if no examples are provided
        else:
            return ""

    def _form_str_prompt(self, data: t.Optional[InputModel] = None) -> str:
        return (
            f"{self.instruction}\n"
            + self._form_output_signature()
            + "\n"
            + self._form_examples()
            + "\n-----------------------------\n"
            + "\nNow perform the same with the following input\n"
            + (
                "input: " + data.model_dump_json(indent=4, exclude_none=True) + "\n"
                if data is not None
                else "Input: (None)\n"
            )
            + "Output: "
        )

    async def generate(
        self,
        llm: BaseLLM,
        data: InputModel,
        temperature: t.Optional[float] = None,
        callbacks: t.Optional[Callbacks] = None,
    ) -> OutputModel:
        """
        Generate a single output using the provided language model and input data.

        This method is a special case of `generate_multiple` where only one output is generated.

        Parameters
        ----------
        llm : BaseLLM
            The language model to use for generation.
        data : InputModel
            The input data for generation.
        temperature : float, optional
            The temperature parameter for controlling randomness in generation.
        stop : List[str], optional
            A list of stop sequences to end generation.
        callbacks : Callbacks, optional
            Callback functions to be called during the generation process.

        Returns
        -------
        OutputModel
            The generated output.

        Notes
        -----
        This method internally calls `generate_multiple` with `n=1` and returns the first (and only) result.
        """
        callbacks = callbacks or []

        # this is just a special case of generate_multiple
        prompt = self._form_str_prompt(data)
        output = await llm.generate_structured_output(
            prompt,
            schema=self.output_model,
            temperature=temperature,
            callbacks=callbacks,
        )
        return self.output_model.model_validate(output)
