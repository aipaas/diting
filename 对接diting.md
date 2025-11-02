## RAG 参数调优对接方案

### 一、总览
- 目标：让外部 RAG 系统按统一规范把检索 / 生成等阶段的可调参数传入 diting，使用内置优化器完成逐阶段调优，回收最优组合。
- 关键机制：顶部 `stage_sequence` 定义调优顺序，diting 按马尔可夫式贪心策略逐阶段固定当前最优，再搜索下一阶段。
- 输出：每阶段最优参数、得分提升、调优历史与外部回传的运行日志。

### 二、参数声明 Schema
- 文件建议：`rag_parameter_schema.yaml`（或 JSON），字段：
  - `schema_id` / `version`：唯一标识规范版本，例如 `rag.parameters.v1`。
  - `parameters`：数组，元素包含：
    - `name`：内部参数名，例如 `retrieval.similarity_threshold`。
    - `stage`：所属阶段（如 `retrieval.semantic_search`、`generator.llm`）。
    - `type`：`float` / `int` / `categorical`。
    - `min`、`max`、`step`（或 `choices`）。
    - `default`、`scale`（`linear` / `log`）和 `description`。
    - `target`：映射到对接协议中的键路径（例如 `parameters.similarity_threshold`）。
    - 可选：`dependencies`、`transform`、`tags`。
- Schema 示意：
```yaml
schema_id: rag.parameters.v1
version: 1.0.0
parameters:
  - name: retrieval.similarity_threshold
    stage: retrieval.semantic_search
    type: float
    min: 0.2
    max: 0.8
    step: 0.05
    default: 0.4
    scale: linear
    target: parameters.similarity_threshold
    description: 过滤召回文档的相似度阈值
  - name: retrieval.context_recall_tokens
    stage: retrieval.semantic_search
    type: int
    min: 1000
    max: 8000
    step: 500
    default: 3000
    scale: linear
    target: parameters.context_recall_max_tokens
    description: 单次检索可拼接的上下文 token 上限
  - name: generator.temperature
    stage: generator.llm
    type: float
    min: 0.0
    max: 1.0
    step: 0.05
    default: 0.2
    target: model_params.temperature
    description: 模型生成温度
```

### 三、diting 接口定义
- **Endpoint**
  - `POST /api/v1/rag/optimization/run`
  - Header：`Authorization: Bearer <token>`；`Content-Type: application/json`
- **请求结构**
```jsonc
{
  "schema_id": "rag.parameters.v1",
  "run_id": "opt-2025-11-02-001",
  "stage_sequence": [
    "retrieval.semantic_search",
    "generator.llm",
    "reranker.cross_encoder"
  ],
  "stages": [
    {
      "name": "retrieval.semantic_search",
      "parameters": {
        "similarity_threshold": 0.45,
        "context_recall_max_tokens": 4000
      },
      "override": {
        "max_trials": 100,
        "optimizer": "semantic_search_exhaustive"
      }
    },
    {
      "name": "generator.llm",
      "parameters": {
        "temperature": 0.2,
        "top_p": 0.9
      },
      "override": {
        "max_trials": 30,
        "optimizer": "prompt_parameter_optuna"
      }
    }
  ],
  "global_context": {
    "dataset_name": "qa_eval_set",
    "metric": "composite@context_recall+precision",
    "n_samples": 50
  },
  "callback": {
    "result_webhook": "https://caller.example.com/rag/optimization/callback"
  }
}
```
- 字段说明：
  - `schema_id`：用于加载参数声明。
  - `run_id`：调用方任务 ID，便于幂等和追踪。
  - `stage_sequence`：定义调优顺序，diting 按此列表逐阶段执行。
  - `stages`：每个阶段的初始参数与优化器覆盖项：
    - `parameters`：外部希望探索的初值或范围提示。
    - `override`：可选，覆盖默认 trial 数、优化算法等。
  - `global_context`：共享评估上下文（数据集、指标、采样量等）。
  - `callback`：可选，调优完成后回调地址。

- **响应示例**
```jsonc
{
  "run_id": "opt-2025-11-02-001",
  "status": "completed",
  "schema_id": "rag.parameters.v1",
  "stages": [
    {
      "name": "retrieval.semantic_search",
      "best_score": 0.74,
      "best_params": {
        "similarity_threshold": 0.55,
        "context_recall_max_tokens": 4500
      }
    },
    {
      "name": "generator.llm",
      "best_score": 0.79,
      "best_params": {
        "temperature": 0.18,
        "top_p": 0.92
      }
    }
  ],
  "final_score": 0.81,
  "history": [...],
  "details": {
    "stage_results": {...},
    "total_duration_seconds": 185.4
  }
}
```

### 四、diting 内部执行流程
1. **Schema 装载与校验**：根据 `schema_id` 构建内部参数空间，校验 `stage_sequence`。
2. **阶段调优**：
   - 按 `stage_sequence` 迭代执行。
   - 检索阶段：调用 `SemanticSearchExhaustiveOptimizer` 组合遍历。
   - 生成阶段：使用 `ParameterOptimizer`（Optuna/TPE）调 `model_params`。
   - 其他阶段可按需接入对应优化器。
3. **马尔可夫式贪心策略**：
   - 每个阶段结束后，固定该阶段最优参数，将其注入下一个阶段配置。
   - 记录阶段得分、改进百分比和参数快照。
4. **结果汇总**：输出 `OptimizationResult`，包含阶段信息、`details.stage_results`、全程 `history`，并按需回调。

### 五、外部系统接入要点
- 按 schema 组织参数并调用接口，无需关心内部优化细节。
- 同一 `run_id` 可重复调用实现幂等；stage 级别迭代由 diting 负责。
- 若需分阶段运行，允许仅提交片段 `stage_sequence`（例如先检索后生成）。
- 所有传参必须符合 schema `min/max/choices`，diting 会返回 `INVALID_PARAMETER` 错误以提示修正。
- 回调 payload 与响应格式一致，便于调用方统一处理。

### 六、后续扩展
- Schema 版本升级：通过新的 `schema_id` 扩展参数，不破坏现有接入。
- 支持更多优化器：在 `override.optimizer` 中加入如 `bayesian`, `grid_search` 等。
- 加强日志与监控：结合 `run_id`、阶段信息接入可视化面板，追踪调优收敛情况。
