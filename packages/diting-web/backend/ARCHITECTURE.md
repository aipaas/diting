# DiTing Web 后端架构设计

## 📐 分层架构

本项目采用**标准的三层架构**，遵循职责分离原则：

```
┌─────────────────────────────────────────────┐
│          API Layer (Controller)             │
│  - 请求验证（Pydantic）                      │
│  - 认证授权（JWT）                           │
│  - 调用Service                               │
│  - 返回响应                                  │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│          Service Layer (Business)           │
│  - 业务逻辑                                  │
│  - 数据验证                                  │
│  - 数据库操作                                │
│  - 事务管理                                  │
│  - 异常处理                                  │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│         Database Layer (ORM)                │
│  - SQLAlchemy Models                        │
│  - 数据库连接                                │
│  - 查询构建                                  │
└─────────────────────────────────────────────┘
```

## ✅ 重构后的正确做法

### API 层（Controller）

**职责**：
- ✅ 接收HTTP请求
- ✅ 验证请求参数（Pydantic自动验证）
- ✅ 认证和授权检查
- ✅ 调用Service层方法
- ✅ 构造HTTP响应
- ❌ **不直接操作数据库**

**示例**：

```python
# src/diting_web/api/v1/metrics.py

from diting_web.services import metric_service

@router.post("")
async def create_metric(
    metric_data: MetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> dict:
    """Create a new metric."""
    # ✅ 只负责调用Service，不直接操作数据库
    metric = await metric_service.create_metric(db, metric_data)
    
    return success_response(
        data=MetricResponse.model_validate(metric).model_dump(),
        code=201,
    )
```

### Service 层（Business Logic）

**职责**：
- ✅ 实现业务逻辑
- ✅ 执行数据库操作
- ✅ 管理事务
- ✅ 处理业务异常
- ✅ 数据转换和验证

**示例**：

```python
# src/diting_web/services/metric_service.py

async def create_metric(
    db: AsyncSession,
    metric_data: MetricCreate,
) -> Metric:
    """
    Create a new metric.
    
    Business logic:
    1. Check if metric name already exists
    2. Create new metric
    3. Commit transaction
    4. Log operation
    """
    # ✅ 业务逻辑：检查重复
    result = await db.execute(
        select(Metric).where(Metric.name == metric_data.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ResourceConflictError(
            f"Metric with name '{metric_data.name}' already exists"
        )

    # ✅ 数据库操作
    metric = Metric(**metric_data.model_dump())
    db.add(metric)
    await db.commit()
    await db.refresh(metric)

    # ✅ 日志记录
    logger.info("Metric created", metric_id=str(metric.id))
    
    return metric
```

## 🔄 重构对比

### ❌ 重构前（不推荐）

```python
# API层直接操作数据库 - 违反单一职责原则
@router.post("")
async def create_metric(
    metric_data: MetricCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # ❌ API层包含业务逻辑和数据库操作
    result = await db.execute(select(Metric).where(...))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(...)
    
    metric = Metric(**metric_data.model_dump())
    db.add(metric)
    await db.commit()
    return {"data": metric}
```

**问题**：
1. API层耦合了业务逻辑
2. 难以测试（需要Mock数据库）
3. 代码重复（多个API使用相同逻辑）
4. 难以维护和扩展

### ✅ 重构后（推荐）

```python
# API层：只负责HTTP交互
@router.post("")
async def create_metric(
    metric_data: MetricCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # ✅ 调用Service层
    metric = await metric_service.create_metric(db, metric_data)
    return success_response(data=...)

# Service层：包含业务逻辑
async def create_metric(db: AsyncSession, metric_data: MetricCreate) -> Metric:
    # ✅ 业务逻辑在这里
    # 检查重复、创建对象、提交事务
    ...
```

**优点**：
1. ✅ 职责清晰分离
2. ✅ 易于单元测试
3. ✅ 代码可复用
4. ✅ 易于维护

## 📁 目录结构

```
src/diting_web/
├── api/                    # API层（Controller）
│   └── v1/
│       ├── auth.py         # 认证API
│       ├── metrics.py      # ✅ 重构完成
│       ├── evaluators.py   # TODO: 待重构
│       ├── datasets.py     # TODO: 待重构
│       ├── tasks.py        # TODO: 待重构
│       └── statistics.py   # TODO: 待重构
│
├── services/               # Service层（Business Logic）
│   ├── metric_service.py   # ✅ Metrics业务逻辑
│   └── task_service.py     # 任务业务逻辑
│
├── models/                 # Database层（ORM Models）
│   ├── metric.py
│   ├── evaluator.py
│   ├── task.py
│   └── ...
│
├── schemas/                # 数据验证（Pydantic）
│   ├── metric.py
│   └── ...
│
└── db/                     # 数据库配置
    ├── base.py
    └── session.py
```

## 🎯 最佳实践

### 1. API层职责

```python
# ✅ DO: 简洁的API函数
@router.get("/{id}")
async def get_metric(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> dict:
    metric = await metric_service.get_metric_by_id(db, id)
    return success_response(data=MetricResponse.model_validate(metric).model_dump())

# ❌ DON'T: 在API中写业务逻辑
@router.get("/{id}")
async def get_metric(id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Metric).where(Metric.id == id))
    metric = result.scalar_one_or_none()
    if not metric:
        raise HTTPException(404)
    # 更多业务逻辑...
```

### 2. Service层职责

```python
# ✅ DO: 完整的业务逻辑
async def update_metric(
    db: AsyncSession,
    metric_id: UUID,
    metric_data: MetricUpdate,
) -> Metric:
    """Update metric with business rules."""
    # 1. 获取对象
    metric = await get_metric_by_id(db, metric_id)
    
    # 2. 业务规则验证
    if metric.is_builtin:
        raise ResourceConflictError("Cannot modify builtin metric")
    
    # 3. 更新数据
    for field, value in metric_data.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)
    
    # 4. 保存
    await db.commit()
    await db.refresh(metric)
    
    # 5. 日志
    logger.info("Metric updated", metric_id=str(metric_id))
    
    return metric
```

### 3. 异常处理

```python
# ✅ Service层抛出业务异常
async def create_metric(db: AsyncSession, data: MetricCreate) -> Metric:
    if await _metric_exists(db, data.name):
        raise ResourceConflictError(f"Metric '{data.name}' exists")
    # ...

# ✅ API层只需要处理Service异常
@router.post("")
async def create_metric(data: MetricCreate, db: AsyncSession = Depends(get_db)):
    try:
        metric = await metric_service.create_metric(db, data)
        return success_response(data=...)
    except ResourceConflictError as e:
        # 全局异常处理器会自动处理
        raise
```

## 📊 重构进度

| 模块 | 状态 | 说明 |
|------|------|------|
| metrics | ✅ 完成 | 已重构，数据库操作在service层 |
| evaluators | ⏳ 待重构 | 需要创建evaluator_service.py |
| datasets | ⏳ 待重构 | 需要创建dataset_service.py |
| tasks | ⏳ 待重构 | 需要创建或完善task_service.py |
| statistics | ⏳ 待重构 | 需要创建statistics_service.py |

## 🧪 测试策略

### Service层测试（单元测试）

```python
# 测试Service层更容易，可以Mock数据库
async def test_create_metric():
    # Mock database
    mock_db = Mock(AsyncSession)
    
    # 调用Service
    metric = await metric_service.create_metric(
        mock_db,
        MetricCreate(name="test", display_name="Test")
    )
    
    # 验证
    assert metric.name == "test"
```

### API层测试（集成测试）

```python
# 测试API层，使用TestClient
def test_create_metric_api(client: TestClient):
    response = client.post(
        "/api/v1/metrics",
        json={"name": "test", "display_name": "Test"}
    )
    assert response.status_code == 201
```

## 🔧 重构步骤

如需重构其他API：

1. **创建Service文件**
   ```bash
   touch src/diting_web/services/xxx_service.py
   ```

2. **移动业务逻辑**
   - 从API文件复制数据库操作代码
   - 创建Service函数
   - 添加异常处理和日志

3. **更新API文件**
   - 导入Service
   - 调用Service方法
   - 简化API函数

4. **更新__init__.py**
   ```python
   from . import xxx_service
   __all__ = [..., "xxx_service"]
   ```

## 💡 架构优势

1. **可维护性** ⬆️
   - 代码组织清晰
   - 易于定位问题

2. **可测试性** ⬆️
   - Service层独立测试
   - API层集成测试

3. **可复用性** ⬆️
   - Service可被多个API使用
   - 避免代码重复

4. **扩展性** ⬆️
   - 易于添加新功能
   - 不影响现有代码

## 📚 参考资料

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)

---

**最后更新**: 2025-10-24
**维护者**: DiTing Team

