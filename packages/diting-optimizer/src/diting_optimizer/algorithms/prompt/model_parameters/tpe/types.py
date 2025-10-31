"""参数优化器类型定义"""

from enum import Enum


class ParameterType(str, Enum):
    """参数类型枚举"""

    FLOAT = "float"
    INT = "int"
    CATEGORICAL = "categorical"


class ScaleType(str, Enum):
    """缩放类型枚举"""

    LINEAR = "linear"
    LOG = "log"
