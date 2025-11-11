"""
统一的配置管理系统
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import yaml


@dataclass
class LLMConfig:
    """LLM配置"""

    model: str
    base_url: str
    api_key: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }


@dataclass
class EmbeddingConfig:
    """Embedding配置"""

    model: str
    base_url: str
    api_key: str
    timeout: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "timeout": self.timeout,
        }


@dataclass
class DatasetConfig:
    """数据集配置"""

    name: str
    module_path: str
    function_name: str
    description: Optional[str] = None
    size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "module_path": self.module_path,
            "function_name": self.function_name,
            "description": self.description,
            "size": self.size,
        }


@dataclass
class MetricConfig:
    """评估指标配置"""

    name: str
    module_path: str
    class_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "params": self.params,
            "description": self.description,
        }


@dataclass
class OptimizerConfig:
    """优化器配置"""

    name: str
    module_path: str
    class_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "params": self.params,
            "description": self.description,
        }


@dataclass
class TestTaskConfig:
    """单个测试任务配置"""

    name: str
    dataset: DatasetConfig
    metric: MetricConfig
    optimizer: OptimizerConfig
    prompt_template: str
    n_samples: int = 10
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "dataset": self.dataset.to_dict(),
            "metric": self.metric.to_dict(),
            "optimizer": self.optimizer.to_dict(),
            "prompt_template": self.prompt_template,
            "n_samples": self.n_samples,
            "description": self.description,
        }


@dataclass
class ExecutionConfig:
    """执行配置"""

    execution_mode: str = "sequential"  # sequential | parallel | batch
    max_workers: int = 4
    save_reports: bool = True
    report_dir: str = "reports"
    report_format: str = "markdown"  # markdown | json | html
    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR
    verbose_http: bool = False  # 是否显示HTTP请求日志

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_mode": self.execution_mode,
            "max_workers": self.max_workers,
            "save_reports": self.save_reports,
            "report_dir": self.report_dir,
            "report_format": self.report_format,
            "log_level": self.log_level,
            "verbose_http": self.verbose_http,
        }


@dataclass
class OptimizerTestConfig:
    """完整的优化器测试配置"""

    name: str
    description: Optional[str] = None

    # LLM配置
    generate_llm: LLMConfig = field(default_factory=lambda: None)  # type: ignore
    eval_llm: LLMConfig = field(default_factory=lambda: None)  # type: ignore
    optimize_llm: LLMConfig = field(default_factory=lambda: None)  # type: ignore
    embedding: Optional[EmbeddingConfig] = None

    # 测试任务列表
    tasks: List[TestTaskConfig] = field(default_factory=list)

    # 执行配置
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "execution": self.execution.to_dict(),
            "tasks": [task.to_dict() for task in self.tasks],
        }

        if self.generate_llm:
            result["generate_llm"] = self.generate_llm.to_dict()
        if self.eval_llm:
            result["eval_llm"] = self.eval_llm.to_dict()
        if self.optimize_llm:
            result["optimize_llm"] = self.optimize_llm.to_dict()
        if self.embedding:
            result["embedding"] = self.embedding.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizerTestConfig":
        """从字典创建配置"""
        config = cls(name=data["name"], description=data.get("description"))

        # 解析LLM配置
        if "generate_llm" in data:
            config.generate_llm = LLMConfig(**data["generate_llm"])
        if "eval_llm" in data:
            config.eval_llm = LLMConfig(**data["eval_llm"])
        if "optimize_llm" in data:
            config.optimize_llm = LLMConfig(**data["optimize_llm"])
        if "embedding" in data:
            config.embedding = EmbeddingConfig(**data["embedding"])

        # 解析执行配置
        if "execution" in data:
            config.execution = ExecutionConfig(**data["execution"])

        # 解析任务配置
        for task_data in data.get("tasks", []):
            task = TestTaskConfig(
                name=task_data["name"],
                dataset=DatasetConfig(**task_data["dataset"]),
                metric=MetricConfig(**task_data["metric"]),
                optimizer=OptimizerConfig(**task_data["optimizer"]),
                prompt_template=task_data["prompt_template"],
                n_samples=task_data.get("n_samples", 10),
                description=task_data.get("description"),
            )
            config.tasks.append(task)

        return config

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "OptimizerTestConfig":
        """从文件加载配置（支持JSON和YAML）"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        return cls.from_dict(data)

    def save_to_file(self, file_path: Union[str, Path]):
        """保存配置到文件"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = self.to_dict()

        with open(file_path, "w", encoding="utf-8") as f:
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                yaml.dump(
                    data, f, default_flow_style=False, allow_unicode=True, indent=2
                )
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
