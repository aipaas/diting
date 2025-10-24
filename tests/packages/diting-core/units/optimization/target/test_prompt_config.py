"""测试重构后的PromptConfig"""

import pytest

from diting_core.optimization.target.prompt_config import PromptConfig
from diting_core.models.llms.base_model import BaseLLM


class MockLLM(BaseLLM):
    """用于测试的Mock LLM"""

    def __init__(self, response: str = "mock response"):
        self.response = response
        self.generate_calls = []
        self.structured_calls = []

    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock生成方法"""
        self.generate_calls.append({"prompt": prompt, "kwargs": kwargs})
        return self.response

    async def generate_structured_output(
        self, prompt: str, schema, seed: int = 42, **kwargs
    ):
        """Mock结构化输出方法"""
        self.structured_calls.append(
            {"prompt": prompt, "schema": schema, "seed": seed, "kwargs": kwargs}
        )
        return {"mock": "structured_output"}


class TestPromptConfig:
    """测试PromptConfig类"""

    def test_prompt_config_creation_basic(self):
        """测试基本创建"""
        config = PromptConfig(
            system="You are a helpful assistant", user="Answer: {input}"
        )

        assert config.system == "You are a helpful assistant"
        assert config.user == "Answer: {input}"
        assert config.messages is None
        assert config.model_params is None

    def test_prompt_config_creation_with_messages(self):
        """测试使用messages格式创建"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        config = PromptConfig(messages=messages)

        assert config.messages == messages
        assert config.system is None
        assert config.user is None

    def test_prompt_config_creation_with_model_params(self):
        """测试包含模型参数的创建"""
        config = PromptConfig(
            system="Test", model_params={"temperature": 0.7, "max_tokens": 100}
        )

        assert config.model_params == {"temperature": 0.7, "max_tokens": 100}

    def test_create_with_llm_factory_method(self):
        """测试create_with_llm工厂方法"""
        llm = MockLLM()
        config = PromptConfig(
            llm=llm,
            system="You are helpful",
            user="Answer: {input}",
            model_params={"temperature": 0.5},
        )

        assert config.system == "You are helpful"
        assert config.user == "Answer: {input}"
        assert config.model_params == {"temperature": 0.5}
        assert config.llm is llm

    def test_validate_dependencies_success(self):
        """测试依赖验证成功"""
        config = PromptConfig(system="Test", llm=MockLLM())
        config.validate_dependencies()  # 不应该抛出异常

    def test_validate_dependencies_failure(self):
        """测试依赖验证失败"""
        config = PromptConfig(system="Test")
        with pytest.raises(ValueError, match="LLM not configured"):
            config.validate_dependencies()

    def test_format_prompt_system_and_user(self):
        """测试格式化系统提示和用户提示"""
        config = PromptConfig(system="You are helpful", user="Answer: {input}")

        messages = config.get_messages({"input": "What is AI?"})
        prompt = config.format_messages(messages)
        expected = "system: You are helpful\n\nuser: Answer: What is AI?"
        assert prompt == expected

    def test_format_prompt_only_user(self):
        """测试只有用户提示的格式化"""
        config = PromptConfig(user="Question: {input}")
        messages = config.get_messages({"input": "What is AI?"})
        prompt = config.format_messages(messages)
        expected = "user: Question: What is AI?"
        assert prompt == expected

    def test_format_prompt_messages_format(self):
        """测试messages格式的格式化"""
        config = PromptConfig(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Answer: {input}"},
            ]
        )
        messages = config.get_messages({"input": "What is AI?"})
        prompt = config.format_messages(messages)

        expected = "system: You are helpful\n\nuser: Answer: What is AI?"
        assert prompt == expected

    def test_get_model_params_with_params(self):
        """测试获取模型参数"""
        config = PromptConfig(
            system="Test", model_params={"temperature": 0.7, "max_tokens": 100}
        )

        params = config._get_model_params()
        assert params == {"temperature": 0.7, "max_tokens": 100}

    def test_get_model_params_without_params(self):
        """测试获取空模型参数"""
        config = PromptConfig(system="Test")

        params = config._get_model_params()
        assert params == {}

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """测试执行成功"""
        llm = MockLLM("Generated response")
        config = PromptConfig(
            system="You are helpful",
            user="Answer: {input}",
            model_params={"temperature": 0.5},
            llm=llm,
        )

        result = await config.execute({"input": "What is AI?"})

        assert result == "Generated response"
        assert len(llm.generate_calls) == 1

        call = llm.generate_calls[0]
        assert "You are helpful" in call["prompt"]
        assert "Answer: What is AI?" in call["prompt"]
        assert call["kwargs"]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_execute_without_llm(self):
        """测试没有LLM时执行失败"""
        config = PromptConfig(system="Test")

        with pytest.raises(ValueError, match="LLM not configured"):
            await config.execute()

    @pytest.mark.asyncio
    async def test_execute_with_additional_kwargs(self):
        """测试执行时传递额外参数"""
        llm = MockLLM()
        config = PromptConfig(system="Test", llm=llm)

        await config.execute({"input": "input"}, max_tokens=50, stop=["END"])

        call = llm.generate_calls[0]
        assert call["kwargs"]["max_tokens"] == 50
        assert call["kwargs"]["stop"] == ["END"]
