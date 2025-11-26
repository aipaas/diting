# Diting-Web 初始化脚本

本目录包含数据库初始化和数据迁移脚本。

---

## 📂 脚本列表

### `init_metrics.py`
初始化 6 个内置评估指标（builtin metrics）。

---

## 🚀 使用方法

### 初始化内置指标

**前提条件**：
- 已完成数据库迁移（`alembic upgrade head`）
- 数据库连接已配置（环境变量或配置文件）

**执行步骤**：

```bash
# 方法 1：直接运行脚本
cd diting/packages/diting-web/backend
python -m diting_web.scripts.init_metrics

# 方法 2：使用 Python 解释器
python src/diting_web/scripts/init_metrics.py
```

**预期输出**：
```
✅ Created metric: answer_correctness
✅ Created metric: answer_similarity
✅ Created metric: answer_relevancy
✅ Created metric: context_precision
✅ Created metric: context_recall
✅ Created metric: faithfulness

📊 统计:
   - 新创建: 6 个
   - 已更新: 0 个
   - 总计: 6 个内置指标

✅ 内置指标初始化完成！
```

**重复运行**：
脚本支持幂等操作，可以安全地多次运行：
- 已存在的指标会被更新（配置同步）
- 不存在的指标会被创建

```
🔄 Updated metric: answer_correctness
🔄 Updated metric: answer_similarity
...

📊 统计:
   - 新创建: 0 个
   - 已更新: 6 个
   - 总计: 6 个内置指标
```

---

## 📊 内置指标详情

### 1. answer_correctness（答案正确性）
- **描述**：评估生成答案与参考答案的事实一致性
- **必需字段**：
  - ✅ user_input
  - ✅ actual_output
  - ✅ expected_output
- **模型需求**：
  - ✅ LLM
  - ✅ Embedding

### 2. answer_similarity（答案相似度）
- **描述**：评估生成答案与参考答案的语义相似度
- **必需字段**：
  - ✅ actual_output
  - ✅ expected_output
- **模型需求**：
  - ✅ Embedding

### 3. answer_relevancy（答案相关性）
- **描述**：评估生成答案与问题的相关程度
- **必需字段**：
  - ✅ user_input
  - ✅ actual_output
- **模型需求**：
  - ✅ LLM

### 4. context_precision（上下文精确度）
- **描述**：评估检索内容的高价值信息排序质量
- **必需字段**：
  - ✅ user_input
  - ✅ expected_output
  - ✅ retrieval_context
- **模型需求**：
  - ✅ LLM

### 5. context_recall（上下文召回率）
- **描述**：评估检索系统的信息完整性
- **必需字段**：
  - ✅ user_input
  - ✅ expected_output
  - ✅ retrieval_context
- **模型需求**：
  - ✅ LLM

### 6. faithfulness（忠实度）
- **描述**：评估生成答案是否忠实于提供的上下文
- **必需字段**：
  - ✅ user_input
  - ✅ actual_output
  - ✅ retrieval_context
- **模型需求**：
  - ✅ LLM

---

## ⚙️ 数据库配置

脚本从以下位置读取数据库配置：

1. **环境变量**（优先级最高）
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/diting_web"
   ```

2. **配置文件**
   ```python
   # config/settings.py
   DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/diting_web"
   ```

---

## 🐛 故障排查

### 问题 1：找不到模块

**错误信息**：
```
ModuleNotFoundError: No module named 'diting_web'
```

**解决方法**：
```bash
# 确保在正确的目录
cd diting/packages/diting-web/backend

# 或者安装包（开发模式）
pip install -e .
```

### 问题 2：数据库连接失败

**错误信息**：
```
sqlalchemy.exc.OperationalError: connection refused
```

**解决方法**：
- 确认 PostgreSQL 服务正在运行
- 检查数据库连接字符串是否正确
- 验证用户名和密码

### 问题 3：表不存在

**错误信息**：
```
sqlalchemy.exc.ProgrammingError: relation "metrics" does not exist
```

**解决方法**：
```bash
# 运行数据库迁移
cd backend
alembic upgrade head
```

---

## 🔄 维护说明

### 添加新的内置指标

在 `init_metrics.py` 的 `BUILTIN_METRICS` 列表中添加新指标：

```python
BUILTIN_METRICS = [
    # ... 现有指标 ...
    {
        "name": "new_metric_name",
        "description": "指标描述",
        "type": MetricTypeEnum.BUILTIN,
        "prompt": None,
        "user_input_required": True,
        "actual_output_required": True,
        "expected_output_required": False,
        "context_required": False,
        "retrieval_context_required": False,
        "embedding_required": False,
        "llm_required": True,
    },
]
```

然后重新运行脚本即可。

### 更新指标配置

直接修改 `BUILTIN_METRICS` 中的指标配置，重新运行脚本会自动更新数据库。

---

## 📚 相关文档

- [Metric Model](../models/metric.py) - 指标模型定义
- [BACKEND_DESIGN.md](../../../../docs/BACKEND_DESIGN.md) - 后端设计文档
- [数据库表结构](../../../../docs/BACKEND_DESIGN.md#225-metrics-评估维度表-) - Metrics 表设计

---

**最后更新**: 2025-01-XX  
**维护者**: DiTing Team

