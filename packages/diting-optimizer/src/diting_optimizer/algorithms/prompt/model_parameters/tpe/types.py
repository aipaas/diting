"""Parameter optimizer type definitions."""

from __future__ import annotations

from enum import Enum


class ParameterType(str, Enum):
    """Enumeration for parameter types."""

    FLOAT = "float"
    INT = "int"
    CATEGORICAL = "categorical"


class ScaleType(str, Enum):
    """Enumeration for scaling types."""

    LINEAR = "linear"
    LOG = "log"
