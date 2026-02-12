"""测试BaseConfig基类"""

import pytest
from typing import Any

from diting_optimizer.target.base_config import BaseConfig


class MockConfig(BaseConfig):
    """用于测试的Mock配置类"""

    def __init__(self, value: str = "test"):
        super().__init__()
        self.value = value
        self._dependency = None

    def set_dependency(self, dependency: Any) -> "MockConfig":
        """设置依赖"""
        self._dependency = dependency
        return self

    def validate_dependencies(self) -> None:
        """验证依赖"""
        if not self._dependency:
            raise ValueError("Dependency not configured")

    async def execute(self, input_data: str, **kwargs) -> str:
        """执行操作"""
        self.validate_dependencies()
        return f"{self.value}:{input_data}:{self._dependency}"


class TestBaseConfig:
    """测试BaseConfig基类"""

    def test_base_config_is_abstract(self):
        """测试BaseConfig是抽象类"""
        with pytest.raises(TypeError):
            BaseConfig()

    def test_mock_config_creation(self):
        """测试Mock配置创建"""
        config = MockConfig("hello")
        assert config.value == "hello"

    def test_dependency_injection(self):
        """测试依赖注入"""
        config = MockConfig()
        result = config.set_dependency("test_dep")

        # 应该返回自身以支持链式调用
        assert result is config
        assert config._dependency == "test_dep"

    def test_validate_dependencies_success(self):
        """测试依赖验证成功"""
        config = MockConfig().set_dependency("test_dep")
        config.validate_dependencies()  # 不应该抛出异常

    def test_validate_dependencies_failure(self):
        """测试依赖验证失败"""
        config = MockConfig()
        with pytest.raises(ValueError, match="Dependency not configured"):
            config.validate_dependencies()

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """测试执行成功"""
        config = MockConfig("hello").set_dependency("world")
        result = await config.execute("input")
        assert result == "hello:input:world"

    @pytest.mark.asyncio
    async def test_execute_without_dependency(self):
        """测试没有依赖时执行失败"""
        config = MockConfig()
        with pytest.raises(ValueError, match="Dependency not configured"):
            await config.execute("input")
