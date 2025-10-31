"""提示词配置类

存放在 target/ 目录下，与未来的 parameter_config.py、tool_config.py 等并列，
体现优化目标的扩展性设计。

设计理念：
- 配置类自包含执行逻辑
- 通过依赖注入实现可测试性
- 支持链式调用和工厂方法
"""

import copy
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from diting_optimizer.target.base_config import BaseConfig
from diting_core.models.llms.base_model import BaseLLM


class PromptConfig(BaseConfig):
    """提示词配置类，适配 Opik 的 ChatPrompt

    支持两种提示格式：
    1. 系统提示 + 用户提示
    2. 消息列表格式

    Attributes:
        system: 系统提示词
        user: 用户提示词
        messages: 消息列表格式 [{"role": "system", "content": "..."}]
        model_params: 模型参数（temperature、max_tokens、top_p、top_k 等）
    """

    name: Optional[str] = Field(default="chat-prompt", description="提示词名称")
    system: Optional[str] = Field(default=None, description="系统提示词")
    user: Optional[str] = Field(default=None, description="用户提示词")
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None, description="消息列表格式"
    )
    model_params: Optional[Dict[str, Any]] = Field(
        default=None, description="模型参数（temperature、max_tokens、top_p、top_k 等）"
    )

    llm: Optional[BaseLLM] = Field(default=None, description="使用的模型")

    @field_validator("messages")
    @classmethod
    def validate_messages(
        cls, v: Optional[List[Dict[str, str]]]
    ) -> Optional[List[Dict[str, str]]]:
        """验证消息格式"""
        if v is not None:
            for msg in v:
                if "role" not in msg or "content" not in msg:
                    raise ValueError("messages 中每个消息必须包含 'role' 和 'content'")
        return v

    def validate_dependencies(self) -> None:
        """验证依赖是否已注入"""
        if not self.llm:
            raise ValueError("LLM not configured. set llm first.")

    def deep_copy(self) -> "PromptConfig":
        """Shallow clone preserving model configuration and tools."""

        model_params = (
            copy.deepcopy(self.model_params) if self.model_params is not None else {}
        )
        return PromptConfig(
            name=self.name,
            system=self.system,
            user=self.user,
            messages=copy.deepcopy(self.messages),
            llm=self.llm,
            model_params=model_params,
        )

    async def execute(
        self, dataset_item: dict[str, str] | None = None, **kwargs
    ) -> str:
        """执行提示词生成

        Args:
            dataset_item: 测试数据
            **kwargs: 额外参数传递给LLM
        Returns:
            LLM生成的响应

        Raises:
            ValueError: 当LLM未配置时
        """
        self.validate_dependencies()

        # 格式化提示词
        messages = self.get_messages(dataset_item)
        prompt_str = self.format_messages(messages)

        # 获取模型参数并合并额外参数
        model_params = self._get_model_params()
        final_kwargs = {**model_params, **kwargs}

        # 调用LLM生成
        return await self.llm.generate(prompt_str, **final_kwargs)

    @staticmethod
    def format_messages(messages: List[Dict[str, str]]) -> str:
        """格式化消息列表为字符串

        Args:
            messages: 消息列表

        Returns:
            格式化后的提示词
        """
        formatted_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            formatted_parts.append(f"{role}: {content}")
        return "\n\n".join(formatted_parts)

    def _get_model_params(self) -> Dict[str, Any]:
        """获取模型参数

        Returns:
            模型参数字典
        """
        return self.model_params or {}

    def get_messages(
        self, dataset_item: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """获取格式化的消息列表

        参考 Opik ChatPrompt.get_messages() 方法。
        将配置转换为标准消息格式，并可选地替换数据集字段。

        Args:
            dataset_item: 数据集项，用于替换消息中的占位符（如 {input}）

        Returns:
            标准化的消息列表
        """
        # 标准化为消息格式
        messages_list: List[Dict[str, str]] = []

        if self.system:
            messages_list.append({"role": "system", "content": self.system})

        if self.messages:
            messages_list.extend(copy.deepcopy(self.messages))

        if self.user:
            messages_list.append({"role": "user", "content": self.user})

        # 替换数据集字段
        if dataset_item:
            for key, value in dataset_item.items():
                label = "{" + key + "}"
                for message in messages_list:
                    if label in message["content"]:
                        message["content"] = message["content"].replace(
                            label, str(value)
                        )

        return messages_list

    def set_messages(self, messages: List[Dict[str, str]]) -> None:
        """设置消息列表并清空其他提示字段

        参考 Opik ChatPrompt.set_messages() 方法。

        Args:
            messages: 新的消息列表
        """
        self.system = None
        self.user = None
        self.messages = copy.deepcopy(messages)
