"""Initialize builtin metrics script.

根据 diting-core 的内置指标配置初始化评估维度。
"""

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.db.session import AsyncSessionLocal
from diting_web.models.metric import Metric, MetricTypeEnum

# Builtin metrics from diting-core
# 数据来源：diting-core 内置指标配置
BUILTIN_METRICS = [
    {
        "name": "answer_correctness",
        "description": "Evaluates the factual consistency between the generated answer and the reference answer, evaluating whether it is accurate and error-free.",
        "type": MetricTypeEnum.BUILTIN,
        "is_global": True,  # 系统内置维度，所有用户可见
        "created_by": None,  # 系统内置维度，无创建者
        "prompt": None,  # 内置指标的 prompt 在 diting-core 中定义
        "user_input_required": True,
        "actual_output_required": True,
        "expected_output_required": True,
        "context_required": False,
        "retrieval_context_required": False,
        "embedding_required": True,
        "llm_required": True,
    },
    {
        "name": "answer_similarity",
        "description": "Evaluates the semantic alignment between the generated answer and the reference answer, determining whether they convey the same core information.",
        "type": MetricTypeEnum.BUILTIN,
        "is_global": True,  # 系统内置维度，所有用户可见
        "created_by": None,  # 系统内置维度，无创建者
        "prompt": None,
        "user_input_required": False,
        "actual_output_required": True,
        "expected_output_required": True,
        "context_required": False,
        "retrieval_context_required": False,
        "embedding_required": True,
        "llm_required": False,
    },
    {
        "name": "answer_relevancy",
        "description": "Evaluates how well the generated answer aligns with the question, judging whether the response directly addresses the query.",
        "type": MetricTypeEnum.BUILTIN,
        "is_global": True,  # 系统内置维度，所有用户可见
        "created_by": None,  # 系统内置维度，无创建者
        "prompt": None,
        "user_input_required": True,
        "actual_output_required": True,
        "expected_output_required": False,
        "context_required": False,
        "retrieval_context_required": False,
        "embedding_required": False,
        "llm_required": True,
    },
    {
        "name": "context_precision",
        "description": "Evaluates whether high-value information is prioritized in the retrieved content, reflecting the quality of ranking and information density.",
        "type": MetricTypeEnum.BUILTIN,
        "is_global": True,  # 系统内置维度，所有用户可见
        "created_by": None,  # 系统内置维度，无创建者
        "prompt": None,
        "user_input_required": True,
        "actual_output_required": False,
        "expected_output_required": True,
        "context_required": False,
        "retrieval_context_required": True,
        "embedding_required": False,
        "llm_required": True,
    },
    {
        "name": "context_recall",
        "description": "Evaluates whether the retrieval system successfully retrieves all key information necessary for formulating the answer, assessing the completeness of retrieval.",
        "type": MetricTypeEnum.BUILTIN,
        "is_global": True,  # 系统内置维度，所有用户可见
        "created_by": None,  # 系统内置维度，无创建者
        "prompt": None,
        "user_input_required": True,
        "actual_output_required": False,
        "expected_output_required": True,
        "context_required": False,
        "retrieval_context_required": True,
        "embedding_required": False,
        "llm_required": True,
    },
    {
        "name": "faithfulness",
        "description": "Evaluates whether the generated answer remains faithful to the provided context, determining whether it contains fabricated or inaccurate content.",
        "type": MetricTypeEnum.BUILTIN,
        "is_global": True,  # 系统内置维度，所有用户可见
        "created_by": None,  # 系统内置维度，无创建者
        "prompt": None,
        "user_input_required": True,
        "actual_output_required": True,
        "expected_output_required": False,
        "context_required": False,
        "retrieval_context_required": True,
        "embedding_required": False,
        "llm_required": True,
    },
]


async def ensure_enum_value_exists(db: AsyncSession) -> None:
    """Ensure 'builtin' and 'custom' values exist in metrictypeenum.
    
    This function checks if the enum values exist and adds them if missing.
    This is necessary because the database enum might have been created before
    these values were added to the Python enum definition.
    """
    enum_values = ['builtin', 'custom']
    
    for enum_value in enum_values:
        try:
            # Check if enum value exists
            result = await db.execute(
                text("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM pg_enum 
                        WHERE enumlabel = :enum_value
                        AND enumtypid = (
                            SELECT oid 
                            FROM pg_type 
                            WHERE typname = 'metrictypeenum'
                        )
                    )
                """),
                {"enum_value": enum_value}
            )
            exists = result.scalar()
            
            if not exists:
                # Add enum value
                await db.execute(
                    text(f"ALTER TYPE metrictypeenum ADD VALUE '{enum_value}'")
                )
                await db.commit()
                print(f"✅ Added '{enum_value}' value to metrictypeenum")
            else:
                print(f"ℹ️  '{enum_value}' value already exists in metrictypeenum")
        except Exception as e:
            # If the enum doesn't exist at all, that's a different issue
            # In that case, the table creation should handle it
            print(f"⚠️  Warning: Could not check/add '{enum_value}' enum value: {e}")
            await db.rollback()


async def init_builtin_metrics() -> None:
    """Initialize builtin metrics.
    
    支持幂等操作：
    - 如果指标不存在，则创建
    - 如果指标已存在，则更新其配置
    """
    async with AsyncSessionLocal() as db:
        # Ensure the enum value exists before creating metrics
        await ensure_enum_value_exists(db)
        
        # Recreate session to ensure clean state after enum modification
        # (PostgreSQL enum modifications require a new transaction)
    async with AsyncSessionLocal() as db:
        created_count = 0
        updated_count = 0
        
        for metric_data in BUILTIN_METRICS:
            # Check if metric exists
            result = await db.execute(
                select(Metric).where(Metric.name == metric_data["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 更新现有指标的配置
                for key, value in metric_data.items():
                    if key != "name":  # name 不可修改
                        setattr(existing, key, value)
                updated_count += 1
                print(f"🔄 Updated metric: {metric_data['name']}")
            else:
                # 创建新指标
                metric = Metric(**metric_data)
                db.add(metric)
                created_count += 1
                print(f"✅ Created metric: {metric_data['name']}")

        await db.commit()
        print(f"\n📊 统计:")
        print(f"   - 新创建: {created_count} 个")
        print(f"   - 已更新: {updated_count} 个")
        print(f"   - 总计: {len(BUILTIN_METRICS)} 个内置指标")
        print(f"\n✅ 内置指标初始化完成！")


if __name__ == "__main__":
    asyncio.run(init_builtin_metrics())

