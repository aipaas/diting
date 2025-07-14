#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from enum import Enum
from pydantic import BaseModel


class Verdicts(BaseModel):
    result: str
    reason: str


class EvaluationResult(str, Enum):
    UNKNOWN = "Unknown"
    ACCURACY = "Accuracy"
    NO_RETRIEVAL_CONTEXT = "No_Retrieval_Context"
    INCOMPLETE_RETRIEVAL_CONTEXT = "Incomplete_Retrieval_Context"
    FABRICATE_OUTPUT = "Fabricate_Output"
    INCOMPLETE_OUTPUT = "Incomplete_Output"
    RETRIEVAL_CONTEXT_NOISE = "Retrieval_Context_Noise"
