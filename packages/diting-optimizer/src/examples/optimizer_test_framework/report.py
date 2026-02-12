"""
报告生成器 - 生成优化测试报告
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config import OptimizerTestConfig
from .logging_config import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "reports", format: str = "markdown"):
        self.output_dir = Path(output_dir)
        self.format = format

    def setup(self):
        """初始化报告目录"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_report(
        self,
        test_name: str,
        test_config: OptimizerTestConfig,
        results: List[Dict[str, Any]],
        timestamp: Optional[str] = None,
    ):
        """生成测试报告"""
        # 使用传入的时间戳或生成新的
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.format == "markdown":
            await self._generate_markdown_report(
                test_name, test_config, results, timestamp
            )
        elif self.format == "json":
            await self._generate_json_report(test_name, test_config, results, timestamp)
        elif self.format == "html":
            await self._generate_html_report(test_name, test_config, results, timestamp)

    async def _generate_markdown_report(
        self,
        test_name: str,
        test_config: OptimizerTestConfig,
        results: List[Dict[str, Any]],
        timestamp: str,
    ):
        """生成Markdown格式报告"""
        report_path = self.output_dir / f"{test_name}_report_{timestamp}.md"

        # 生成报告内容
        content = self._build_markdown_content(test_name, test_config, results)

        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Markdown报告已生成: {report_path}")

    def _build_markdown_content(
        self,
        test_name: str,
        test_config: OptimizerTestConfig,
        results: List[Dict[str, Any]],
    ) -> str:
        """构建Markdown报告内容"""
        lines = []

        # 标题
        lines.append(f"# {test_name} - 优化器测试报告")
        lines.append("")

        # 基本信息
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"- **测试名称**: {test_name}")
        lines.append(f"- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **任务数量**: {len(results)}")
        lines.append(f"- **执行模式**: {test_config.execution.execution_mode}")
        lines.append(f"- **最大并发数**: {test_config.execution.max_workers}")
        if test_config.description:
            lines.append(f"- **描述**: {test_config.description}")
        lines.append("")

        # 配置信息
        lines.append("## 配置信息")
        lines.append("")
        lines.append("### LLM配置")
        lines.append("")
        if test_config.generate_llm:
            lines.append(f"- **生成LLM**: {test_config.generate_llm.model}")
        if test_config.eval_llm:
            lines.append(f"- **评估LLM**: {test_config.eval_llm.model}")
        if test_config.optimize_llm:
            lines.append(f"- **优化LLM**: {test_config.optimize_llm.model}")
        if test_config.embedding:
            lines.append(f"- **Embedding**: {test_config.embedding.model}")
        lines.append("")

        # 测试结果汇总
        lines.append("## 测试结果汇总")
        lines.append("")
        lines.append(
            "| 任务名称 | 数据集 | 评估指标 | 最佳分数 | 迭代次数 | 耗时(秒) |"
        )
        lines.append("|---------|--------|----------|----------|----------|----------|")

        for result in results:
            if "error" not in result:
                lines.append(
                    f"| {result['task_name']} | {result['dataset']} | "
                    f"{result['metric']} | {result['best_score']:.4f} | "
                    f"{result['num_iterations']} | {result['duration_seconds']:.2f} |"
                )
            else:
                lines.append(f"| {result['task_name']} | - | - | - | - | - |")

        lines.append("")

        # 统计信息
        lines.append("## 统计信息")
        lines.append("")
        successful_results = [r for r in results if "error" not in r]

        if successful_results:
            scores = [r["best_score"] for r in successful_results]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)

            total_time = sum(r["duration_seconds"] for r in successful_results)
            total_iterations = sum(r["num_iterations"] for r in successful_results)

            lines.append(f"- **成功任务数**: {len(successful_results)}/{len(results)}")
            lines.append(f"- **平均分数**: {avg_score:.4f}")
            lines.append(f"- **最高分数**: {max_score:.4f}")
            lines.append(f"- **最低分数**: {min_score:.4f}")
            lines.append(f"- **总耗时**: {total_time:.2f}秒")
            lines.append(
                f"- **平均耗时**: {total_time / len(successful_results):.2f}秒"
            )
            lines.append(f"- **总迭代次数**: {total_iterations}")
            lines.append("")
        else:
            lines.append("- 所有任务执行失败")
            lines.append("")

        # 详细结果
        lines.append("## 详细结果")
        lines.append("")

        for i, result in enumerate(results, 1):
            lines.append(f"### {i}. {result['task_name']}")
            lines.append("")

            if "error" in result:
                lines.append(f"❌ **执行失败**: {result['error']}")
                lines.append("")
                continue

            lines.append(f"- **数据集**: {result['dataset']}")
            lines.append(f"- **评估指标**: {result['metric']}")
            lines.append(f"- **优化器**: {result['optimizer']}")
            lines.append(f"- **样本数**: {result['n_samples']}")
            lines.append(f"- **最佳分数**: {result['best_score']:.4f}")
            lines.append(f"- **迭代次数**: {result['num_iterations']}")
            lines.append(f"- **开始时间**: {result['start_time']}")
            lines.append(f"- **结束时间**: {result['end_time']}")
            lines.append(f"- **耗时**: {result['duration_seconds']:.2f}秒")
            lines.append("")

            # 优化历史（可选）
            if (
                hasattr(result["optimization_result"], "history")
                and result["optimization_result"].history
            ):
                lines.append("#### 优化历史")
                lines.append("")
                lines.append("| 迭代 | 分数 | 改进 |")
                lines.append("|------|------|------|")

                best_score = 0
                for j, record in enumerate(result["optimization_result"].history, 1):
                    score = record.score
                    improvement = "✅" if score > best_score else "➡️"
                    if score > best_score:
                        best_score = score
                    lines.append(f"| {j} | {score:.4f} | {improvement} |")

                lines.append("")

        return "\n".join(lines)

    async def _generate_json_report(
        self,
        test_name: str,
        test_config: OptimizerTestConfig,
        results: List[Dict[str, Any]],
        timestamp: str,
    ):
        """生成JSON格式报告"""
        report_path = self.output_dir / f"{test_name}_report_{timestamp}.json"

        # 准备报告数据
        report_data = {
            "test_name": test_name,
            "timestamp": timestamp,
            "config": test_config.to_dict(),
            "summary": {
                "total_tasks": len(results),
                "successful_tasks": len([r for r in results if "error" not in r]),
                "execution_mode": test_config.execution.execution_mode,
            },
            "results": [],
        }

        # 处理结果
        for result in results:
            result_data = {
                "task_name": result.get("task_name"),
                "dataset": result.get("dataset"),
                "metric": result.get("metric"),
                "optimizer": result.get("optimizer"),
                "n_samples": result.get("n_samples"),
                "best_score": result.get("best_score"),
                "num_iterations": result.get("num_iterations"),
                "duration_seconds": result.get("duration_seconds"),
                "start_time": result.get("start_time"),
                "end_time": result.get("end_time"),
                "error": result.get("error"),
            }
            report_data["results"].append(result_data)

        # 计算统计信息
        successful_results = [r for r in report_data["results"] if r["error"] is None]
        if successful_results:
            scores = [r["best_score"] for r in successful_results]
            report_data["statistics"] = {
                "average_score": sum(scores) / len(scores),
                "max_score": max(scores),
                "min_score": min(scores),
                "total_time": sum(r["duration_seconds"] for r in successful_results),
                "total_iterations": sum(
                    r["num_iterations"] for r in successful_results
                ),
            }

        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON报告已生成: {report_path}")

    async def _generate_html_report(
        self,
        test_name: str,
        test_config: OptimizerTestConfig,
        results: List[Dict[str, Any]],
        timestamp: str,
    ):
        """生成HTML格式报告"""
        report_path = self.output_dir / f"{test_name}_report_{timestamp}.html"

        # 生成Markdown内容
        md_content = self._build_markdown_content(test_name, test_config, results)

        # 简单的Markdown到HTML转换（不依赖外部库）
        html_content = self._simple_markdown_to_html(md_content)

        # 添加HTML样式
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{test_name} - 优化器测试报告</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                    font-weight: 600;
                }}
                h1, h2, h3 {{
                    color: #333;
                }}
                code {{
                    background-color: #f5f5f5;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 0;
                    padding-left: 20px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        logger.info(f"HTML报告已生成: {report_path}")

    def _simple_markdown_to_html(self, md_text: str) -> str:
        """简单的Markdown到HTML转换（无外部依赖）"""
        lines = md_text.split("\n")
        html_lines = []
        in_table = False
        table_headers = False

        for line in lines:
            # 标题
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            # 表格
            elif line.startswith("|") and line.endswith("|"):
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                if not in_table:
                    # 开始表格
                    html_lines.append("<table>")
                    in_table = True
                    table_headers = True
                    html_lines.append("<tr>")
                    for cell in cells:
                        html_lines.append(f"<th>{cell}</th>")
                    html_lines.append("</tr>")
                elif table_headers:
                    # 跳过分隔符行
                    table_headers = False
                else:
                    # 数据行
                    html_lines.append("<tr>")
                    for cell in cells:
                        html_lines.append(f"<td>{cell}</td>")
                    html_lines.append("</tr>")
            # 空行
            elif not line.strip() and in_table:
                html_lines.append("</table>")
                in_table = False
            elif not line.strip():
                html_lines.append("<br>")
            # 列表项
            elif line.strip().startswith("- "):
                html_lines.append(f"<li>{line.strip()[2:]}</li>")
            # 普通段落
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")

        # 关闭未闭合的表格
        if in_table:
            html_lines.append("</table>")

        return "\n".join(html_lines)
