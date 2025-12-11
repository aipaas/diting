#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基于文本生成问题列表的功能
"""
import asyncio
import json
from diting_server.apis.v1.synthesis.data_models import (
    QuestionListRequest,
    ModelConfig
)
from diting_server.services.synthesis.synthesis_service import SynthesizerService


async def test_question_generation():
    """测试问题生成功能"""
    
    # 创建测试请求
    test_text = """
    人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
    机器学习是人工智能的一个子领域，专注于开发能够从数据中学习和改进的算法。
    深度学习是机器学习的一个分支，使用人工神经网络来模拟人脑的工作方式。
    自然语言处理（NLP）是人工智能的另一个重要领域，专注于让计算机理解和生成人类语言。
    """
    
    request = QuestionListRequest(
        text=test_text.strip(),
        llm_config=ModelConfig(
            name="gpt-3.5-turbo",  # 或者你配置的其他模型名称
            base_url="https://api.openai.com/v1",
            api_key="your-api-key-here",  # 需要替换为实际的API密钥
            timeout=30
        ),
        max_questions=3,
        themes=["人工智能", "机器学习"]
    )
    
    # 创建服务实例
    service = SynthesizerService()
    
    try:
        # 调用生成方法
        result = await service.generate_questions_from_text(request, "test-request-123")
        
        # 打印结果
        print("=== 测试结果 ===")
        print(f"请求ID: {result.request_id}")
        print(f"状态: {result.status}")
        print(f"错误信息: {result.error}")
        print(f"生成的问题数量: {len(result.data) if result.data else 0}")
        
        if result.data:
            print("\n=== 生成的问题列表 ===")
            for i, question_item in enumerate(result.data, 1):
                print(f"{i}. 问题: {question_item.question}")
                if question_item.score:
                    print(f"   评分: {question_item.score}")
                if question_item.reason:
                    print(f"   理由: {question_item.reason}")
                print()
        
        if result.usages:
            print("=== Token使用情况 ===")
            for usage in result.usages:
                print(f"模型: {getattr(usage, 'model', 'N/A')}")
                print(f"输入Token: {getattr(usage, 'input_tokens', 'N/A')}")
                print(f"输出Token: {getattr(usage, 'output_tokens', 'N/A')}")
                print(f"总计Token: {getattr(usage, 'total_tokens', 'N/A')}")
        
        if result.metadata:
            print(f"\n=== 元数据 ===")
            print(json.dumps(result.metadata, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("开始测试基于文本生成问题列表功能...")
    asyncio.run(test_question_generation())
    print("测试完成!")