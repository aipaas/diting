#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 FineTuneDataSynthesizer 重构后的功能
"""

import sys
import os
from pathlib import Path

import asyncio
from typing import List


# 模拟数据类
class MockFineTuneDataItem:
    def __init__(self, dataId: str, collectionId: str, q: str, a: str, indexes: List[List[str]]):
        self.dataId = dataId
        self.collectionId = collectionId
        self.q = q
        self.a = a
        self.indexes = indexes

class MockFineTuneSample:
    def __init__(self, query: str, positive: str, negatives: list, source_id: str, collection_id: str, original_q=None, original_a=None, metadata=None):
        self.query = query
        self.positive = positive
        self.negatives = negatives
        self.source_id = source_id
        self.collection_id = collection_id
        self.original_q = original_q
        self.original_a = original_a
        self.metadata = metadata or {}

async def test_fine_tune_synthesizer():
    """测试 FineTuneDataSynthesizer"""
    try:
        # 导入必要的模块
        from diting_core.synthesis.qa.fine_tune_data_synthesizer import FineTuneDataSynthesizer
        from diting_core.synthesis.base_corpus import BaseCorpus
        
        print("✅ 成功导入 FineTuneDataSynthesizer")
        
        # 创建测试数据
        test_items = [
            MockFineTuneDataItem(
                dataId="item_001",
                collectionId="collection_001",
                q="什么是人工智能？",
                a="人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。",
                indexes=[
                    ["什么是AI？", "AI的定义"],
                    ["人工智能概念", "AI的含义"]
                ]
            ),
            MockFineTuneDataItem(
                dataId="item_002",
                collectionId="collection_001",
                q="机器学习是什么？",
                a="机器学习是一门多领域交叉学科，专门研究计算机怎样模拟或实现人类的学习行为，以获取新的知识或技能。",
                indexes=[
                    ["ML定义", "机器学习概念"],
                    ["什么是机器学习", "机器学习解释"]
                ]
            ),
            MockFineTuneDataItem(
                dataId="item_003",
                collectionId="collection_002",
                q="深度学习是什么？",
                a="深度学习是机器学习的一个子领域，它基于人工神经网络的学习算法。",
                indexes=[
                    ["深度学习定义", "DL概念"],
                    ["什么是DL", "深度学习解释"]
                ]
            )
        ]
        
        print("✅ 创建测试数据完成")
        
        # 创建 synthesizer 实例
        synthesizer = FineTuneDataSynthesizer()
        print("✅ 创建 FineTuneDataSynthesizer 实例成功")
        
        # 创建 corpus
        corpus = BaseCorpus()
        corpus.fine_tune_items = test_items
        corpus.min_negative_samples = 1
        corpus.max_negative_samples = 3
        corpus.include_original_q = True
        corpus.request_id = "test_001"
        
        print("✅ 创建 corpus 对象成功")
        
        # 应用 synthesizer
        llm_case = await synthesizer.apply(corpus=corpus)
        print("✅ 成功应用 synthesizer")
        
        # 获取结果
        result = llm_case.metadata.get("result", {})
        
        print(f"✅ 测试完成！")
        print(f"   - 总项目数: {result.get('total_items', 0)}")
        print(f"   - 总样本数: {result.get('total_samples', 0)}")
        print(f"   - 正样本数: {result.get('positive_samples', 0)}")
        print(f"   - 负样本数: {result.get('negative_samples', 0)}")
        print(f"   - 处理时间: {result.get('processing_time', 0):.3f}s")
        
        # 显示样本详情
        samples = result.get('samples', [])
        if samples:
            print(f"   - 样本示例:")
            for i, sample in enumerate(samples[:2]):  # 只显示前2个样本
                if hasattr(sample, 'query'):
                    print(f"     样本 {i+1}: {sample.query} -> {sample.positive} (负样本: {len(sample.negatives)})")
                else:
                    print(f"     样本 {i+1}: {sample['query']} -> {sample['positive']} (负样本: {len(sample['negatives'])})")
        
        # 测试统计信息
        statistics = result.get('statistics', {})
        if statistics:
            print(f"   - 知识库数量: {statistics.get('total_collections', 0)}")
            print(f"   - 唯一问题数: {statistics.get('unique_questions', 0)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_synthesizer_discovery():
    """测试 synthesizer 发现功能"""
    try:
        from diting_server.services.synthesis.synthesizers import SynthesizerFactory
        
        factory = SynthesizerFactory()
        synthesizers = factory.synthesizers
        
        print("✅ 可用的 synthesizers:")
        for name, cls in synthesizers.items():
            print(f"   - {name}: {cls.__name__}")
        
        # 检查我们的新 synthesizer 是否被发现
        if "fine_tune_data_synthesizer" in synthesizers:
            print("✅ FineTuneDataSynthesizer 已被成功发现")
        else:
            print("❌ FineTuneDataSynthesizer 未被发现")
            print(f"   可用的 synthesizers: {list(synthesizers.keys())}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入 SynthesizerFactory 失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试 synthesizer 发现失败: {e}")
        return False

async def test_service_integration():
    """测试与 SynthesizerService 的集成"""
    try:
        from diting_server.services.synthesis.synthesis_service import SynthesizerService
        
        service = SynthesizerService()
        
        # 创建测试数据
        test_items = [
            MockFineTuneDataItem(
                dataId="item_001",
                collectionId="collection_001",
                q="什么是人工智能？",
                a="人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。",
                indexes=[["什么是AI？", "AI的定义"]]
            )
        ]
        
        print("✅ 创建 SynthesizerService 实例成功")
        
        # 调用重构后的方法
        result = await service.build_fine_tune_data(
            items=test_items,
            min_negative_samples=1,
            max_negative_samples=2,
            include_original_q=True,
            request_id="test_service"
        )
        
        print("✅ 成功调用重构后的 build_fine_tune_data 方法")
        print(f"   - 总样本数: {result.get('total_samples', 0)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入 SynthesizerService 失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试服务集成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始测试重构后的 FineTuneDataSynthesizer")
    print("=" * 60)
    
    # 测试 1: 基本功能测试
    print("\n📋 测试 1: 基本 synthesizer 功能")
    test1_result = await test_fine_tune_synthesizer()
    
    # 测试 2: synthesizer 发现测试
    print("\n📋 测试 2: synthesizer 发现功能")
    test2_result = await test_synthesizer_discovery()
    
    # 测试 3: 服务集成测试
    print("\n📋 测试 3: 服务集成测试")
    test3_result = await test_service_integration()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"   基本功能测试: {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"   发现功能测试: {'✅ 通过' if test2_result else '❌ 失败'}")
    print(f"   服务集成测试: {'✅ 通过' if test3_result else '❌ 失败'}")
    
    if all([test1_result, test2_result, test3_result]):
        print("\n🎉 所有测试通过！重构成功！")
        return True
    else:
        print("\n❌ 部分测试失败，需要进一步调试")
        return False

if __name__ == "__main__":
    asyncio.run(main())