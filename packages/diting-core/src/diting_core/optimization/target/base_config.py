"""优化目标配置基类"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseConfig(BaseModel, ABC):
    """优化目标配置基类

    所有优化目标配置都应继承此类并实现execute方法。
    配置类负责：
    1. 存储配置参数
    2. 验证和格式化输入
    3. 执行对应的操作（通过注入的依赖）

    设计原则：
    - 配置与执行逻辑分离但自包含
    - 通过依赖注入实现可测试性
    - 支持链式调用
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    @abstractmethod
    def validate_dependencies(self) -> None:
        """验证依赖是否已正确注入

        子类应实现此方法检查必要的依赖是否已设置。
        如果依赖缺失，应抛出ValueError。
        """
        pass

    @abstractmethod
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """执行配置对应的操作

        Args:
            input_data: 输入数据，具体类型由子类定义
            **kwargs: 额外参数

        Returns:
            执行结果，具体类型由子类定义

        Raises:
            ValueError: 当依赖未正确配置时
        """
        pass
