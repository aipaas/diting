#!/usr/bin/env python3
"""测试 OptimizationResult 的新方法"""

import os
import pytest
from datetime import datetime, timezone
from diting_optimizer.optimization_result import OptimizationResult, HistoryRecord
from diting_optimizer.target.prompt_config import PromptConfig


class TestOptimizationResultOutput:
    """测试 OptimizationResult 的输出方法"""

    @pytest.fixture
    def temp_files(self, tmp_path):
        """创建临时文件路径"""
        json_file = tmp_path / "test_result.json"
        md_file = tmp_path / "test_result.md"
        return str(json_file), str(md_file)

    def test_to_json_and_to_markdown(self):
        """测试 to_json 和 to_markdown 方法"""

        # 创建一个简单的 PromptConfig
        config = PromptConfig(
            system="你是一个有用的助手。",
            user="请回答：{question}",
            model_params={"temperature": 0.7, "max_tokens": 100},
        )

        # 创建一个简单的实验结果字典（满足 pydantic 验证）
        exp_result_dict1 = {"experiment_name": "test_exp_1", "test_results": []}

        exp_result_dict2 = {"experiment_name": "test_exp_2", "test_results": []}

        # 创建历史记录
        history1 = HistoryRecord(
            iteration=0,
            stage="initial",
            timestamp=datetime.now(timezone.utc),
            score=0.5,
            optimizer_name="test_optimizer",
            metric_name="accuracy",
            config=config,
            experiment_result=exp_result_dict1,
            metadata={"test": "data"},
        )

        history2 = HistoryRecord(
            iteration=1,
            stage="optimized",
            timestamp=datetime.now(timezone.utc),
            score=0.8,
            optimizer_name="test_optimizer",
            metric_name="accuracy",
            config=config,
            experiment_result=exp_result_dict2,
            metadata={"test": "data"},
        )

        # 创建优化结果
        result = OptimizationResult(
            optimizer_name="test_optimizer",
            metric_name="accuracy",
            best_config=config,
            best_score=0.8,
            initial_config=config,
            initial_score=0.5,
            histories=[history1, history2],
            total_llm_calls=10,
            iterations=2,
            details={
                "optimized_parameters": {"temperature": 0.7},
                "parameter_importance": {"temperature": 0.5},
            },
        )

        # 测试 to_json 方法
        json_output = result.to_json()

        # 验证 JSON 输出
        assert json_output is not None
        assert isinstance(json_output, str)
        assert "test_optimizer" in json_output
        assert "0.8" in json_output
        assert "histories" in json_output

        # 测试 to_markdown 方法
        markdown_output = result.to_markdown()

        # 验证 Markdown 输出
        assert markdown_output is not None
        assert isinstance(markdown_output, str)
        assert "# 优化结果报告" in markdown_output
        assert "test_optimizer" in markdown_output
        assert "0.8" in markdown_output
        assert "## 优化历史" in markdown_output

        # 验证 markdown 包含关键信息
        assert "基本信息" in markdown_output
        assert "性能指标" in markdown_output
        assert "最佳配置" in markdown_output
        assert "系统提示" in markdown_output
        assert "用户提示" in markdown_output
        assert "改进幅度" in markdown_output

        # 验证包含历史记录表格
        assert "| 迭代 | 阶段 | 分数 | 时间戳 | 优化器 | 配置摘要 |" in markdown_output
        assert "| 0 | initial |" in markdown_output
        assert "| 1 | optimized |" in markdown_output

        # 验证包含历史统计
        assert "历史统计" in markdown_output
        assert "平均分数" in markdown_output

    def test_to_json_and_to_markdown_with_file_output(self, temp_files):
        """测试 to_json 和 to_markdown 方法的文件写入功能"""
        json_file, md_file = temp_files

        # 创建一个简单的 PromptConfig
        config = PromptConfig(
            system="你是一个有用的助手。",
            user="请回答：{question}",
            model_params={"temperature": 0.7, "max_tokens": 100},
        )

        # 创建实验结果字典
        exp_result_dict = {"experiment_name": "test_exp", "test_results": []}

        # 创建历史记录
        history = HistoryRecord(
            iteration=0,
            stage="initial",
            timestamp=datetime.now(timezone.utc),
            score=0.8,
            optimizer_name="test_optimizer",
            metric_name="accuracy",
            config=config,
            experiment_result=exp_result_dict,
            metadata={"test": "data"},
        )

        # 创建优化结果
        result = OptimizationResult(
            optimizer_name="test_optimizer",
            metric_name="accuracy",
            best_config=config,
            best_score=0.8,
            histories=[history],
            iterations=1,
        )

        # 测试 to_json 文件写入
        json_output = result.to_json(file_path=json_file)

        # 验证文件已创建
        assert os.path.exists(json_file)

        # 验证文件内容
        with open(json_file, "r", encoding="utf-8") as f:
            file_content = f.read()
        assert file_content == json_output
        assert "test_optimizer" in file_content

        # 测试 to_markdown 文件写入
        markdown_output = result.to_markdown(file_path=md_file)

        # 验证文件已创建
        assert os.path.exists(md_file)

        # 验证文件内容
        with open(md_file, "r", encoding="utf-8") as f:
            file_content = f.read()
        assert file_content == markdown_output
        assert "# 优化结果报告" in file_content
        assert "test_optimizer" in file_content
