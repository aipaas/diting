import asyncio
import numpy as np
import csv
import hashlib
import os
import json
import logging
from typing import List, Dict, Any, TypedDict

from diting_core.cases.llm_case import LLMCase
from diting_core.metrics import BaseMetric, CompositeMetric, ContextRecall
from diting_core.metrics.context_precision.context_precision import ContextPrecision
from diting_core.models.embeddings.factory import embedding_factory
from diting_core.models.llms.factory import llm_factory
from diting_core.optimization.datasets import InMemoryDataset
from diting_core.optimization.retrieval.semantic_search import SemanticSearchExhaustiveOptimizer
from diting_core.optimization.target import BaseSemanticRetriever, SemanticSearchConfig


class Document(TypedDict):
    """文档类型声明"""
    id: str
    content: str


class DemoSemanticRetriever(BaseSemanticRetriever):
    """演示用语义检索器"""
    
    def __init__(self, embedding_model):
        # 使用通过factory创建的embedding模型
        super().__init__(embeddings=embedding_model)
        # 从CSV文件加载文档数据
        self.documents: List[Document] = self._load_documents_from_csv()
        
        # 文档embeddings将在首次检索时计算
        self.document_embeddings = None
        
        # embedding缓存文件路径
        self.embedding_cache_file = "D:/diting/packages/diting-core/src/diting_core/optimization/datasets/retrieval_data/embeddings_旅游.json"
        
        # 缓存文件的内容，避免重复读取
        self._cached_embedding_data = None
    
    def _load_documents_from_csv(self):
        """从CSV文件加载文档数据"""
        documents = []
        try:
            with open('D:/diting/packages/diting-core/src/diting_core/optimization/datasets/retrieval_data/旅游人工标注分片.csv', 
                      'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for i, row in enumerate(reader):
                    # 使用csv文件中的contents列作为内容，doc_id作为id
                    documents.append({
                        "id": row['doc_id'],
                        "content": row['contents']
                    })
                    # 限制文档数量以避免处理时间过长
                    # if i >= 19:  # 只加载前20个文档，减少处理时间
                    #     break
        except FileNotFoundError:
            print("警告: 未找到CSV文件，使用默认文档")
            documents = [
                {"id": "doc_1", "content": "人工智能是计算机科学的一个分支，致力于创建智能机器。"},
                {"id": "doc_2", "content": "机器学习是人工智能的一个子集，专注于算法和统计模型。"},
                {"id": "doc_3", "content": "深度学习使用神经网络来模拟人脑处理信息的方式。"},
                {"id": "doc_4", "content": "自然语言处理让计算机能够理解和生成人类语言。"},
                {"id": "doc_5", "content": "计算机视觉使机器能够识别和理解图像和视频内容。"},
            ]
        return documents
    
    def _generate_cache_key(self, contents):
        """为文档内容生成唯一标识符"""
        # 使用内容的哈希值作为唯一标识符
        content_str = "|".join(contents)
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def _save_embeddings_to_cache(self, cache_key, embeddings):
        """将embedding保存到缓存文件"""
        try:
            # 如果缓存文件存在，加载现有数据
            if os.path.exists(self.embedding_cache_file):
                with open(self.embedding_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {}
            
            # 添加新的embedding数据
            cache_data[cache_key] = embeddings
            
            # 保存到文件
            with open(self.embedding_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 更新内存中的缓存数据
            self._cached_embedding_data = cache_data
            
            print(f"Embedding已保存到缓存，键值: {cache_key}")
        except Exception as e:
            print(f"保存embedding到缓存时出错: {e}")
    
    def _load_embeddings_from_cache(self, cache_key):
        """从缓存文件加载embedding"""
        try:
            # 如果还没有加载缓存数据，则从文件加载
            if self._cached_embedding_data is None and os.path.exists(self.embedding_cache_file):
                with open(self.embedding_cache_file, 'r', encoding='utf-8') as f:
                    self._cached_embedding_data = json.load(f)
            
            # 从内存中获取数据
            if self._cached_embedding_data and cache_key in self._cached_embedding_data:
                return self._cached_embedding_data[cache_key]
        except Exception as e:
            print(f"从缓存加载embedding时出错: {e}")
        
        return None
    
    async def _ensure_document_embeddings(self):
        """确保文档embeddings已计算"""
        if self.document_embeddings is None:
            # 为每个文档单独处理embedding缓存
            cached_embeddings = []
            documents_to_embed = []
            indices_to_embed = []
            
            for i, doc in enumerate(self.documents):
                # 使用文档的id作为缓存键
                doc_cache_key = doc["id"]
                cached_embedding = self._load_embeddings_from_cache(doc_cache_key)
                
                if cached_embedding is not None:
                    # 如果从缓存加载成功，直接使用缓存的embedding
                    cached_embeddings.append(cached_embedding)
                else:
                    # 如果缓存中没有，需要重新计算
                    documents_to_embed.append(doc["content"])
                    indices_to_embed.append(i)
                    # 添加占位符以保持索引一致性
                    cached_embeddings.append(None)
            
            # 如果有需要计算embedding的文档
            if documents_to_embed:
                # 逐条计算这些文档的embeddings，并每100个保存一次到缓存
                batch_count = 0
                batch_size = 100
                temp_embeddings_cache = {}
                try:
                    for idx, (doc_index, doc_content) in enumerate(zip(indices_to_embed, documents_to_embed)):
                        # 逐条调用embedding计算，避免批量处理导致上下文过长
                        doc_embedding = await self.embeddings.aembed_query(doc_content)
                        
                        # 计算完一个就先保存到临时缓存
                        doc_id = self.documents[doc_index]["id"]
                        temp_embeddings_cache[doc_id] = doc_embedding
                        cached_embeddings[doc_index] = doc_embedding
                        
                        # 每100个embedding保存一次到磁盘
                        batch_count += 1
                        if batch_count % batch_size == 0:
                            self._save_embeddings_batch_to_cache(temp_embeddings_cache)
                            temp_embeddings_cache = {}  # 清空临时缓存
                            print(f"已保存 {batch_count} 个embedding到缓存")
                    
                    # 保存剩余的embedding到缓存
                    if temp_embeddings_cache:
                        self._save_embeddings_batch_to_cache(temp_embeddings_cache)
                        print(f"已保存最后 {len(temp_embeddings_cache)} 个embedding到缓存")
                        
                except Exception as e:
                    print(f"计算文档embeddings时出错: {e}")
                    raise e
            
            self.document_embeddings = cached_embeddings

    def _save_embeddings_batch_to_cache(self, embeddings_batch):
        """批量保存embedding到缓存文件"""
        try:
            # 如果缓存文件存在，加载现有数据
            if os.path.exists(self.embedding_cache_file):
                with open(self.embedding_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {}
            
            # 添加新的embedding数据
            cache_data.update(embeddings_batch)
            
            # 保存到文件
            with open(self.embedding_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 更新内存中的缓存数据
            self._cached_embedding_data = cache_data
            
            print(f"批量保存了 {len(embeddings_batch)} 个embedding到缓存")
        except Exception as e:
            print(f"批量保存embedding到缓存时出错: {e}")
    
    async def retrieve(self, query: str, top_k: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """基于余弦相似度的实际检索方法"""
        # 确保文档embeddings已计算
        await self._ensure_document_embeddings()
        
        # 生成查询的embedding
        query_embedding = await self.embeddings.aembed_query(query)
        
        # 计算查询与所有文档的余弦相似度
        similarities = []
        for doc_embedding in self.document_embeddings:
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            similarities.append(similarity)
        
        # 获取top_k个最相似的结果
        top_indices = sorted(
            range(len(similarities)), 
            key=lambda i: similarities[i], 
            reverse=True
        )[:min(top_k, len(self.documents))]
        
        # 构造结果
        results = []
        for i in top_indices:
            results.append({
                "content": self.documents[i]["content"],
                "id": self.documents[i]["id"],
                "similarity": similarities[i]
            })
        # print(f"召回结果:{results}")
        return results
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        # 转换为numpy数组
        a = np.array(a)
        b = np.array(b)
        
        # 计算点积
        dot_product = np.dot(a, b)
        
        # 计算范数
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        # 避免除零错误
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        # 计算余弦相似度
        return dot_product / (norm_a * norm_b)


async def main():
    """主函数 - 演示语义搜索优化器使用"""
    print("=== 语义搜索参数穷举优化演示 ===\n")
    
    # 配置日志级别和格式，确保可以看到INFO级别的日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("diting_core").setLevel(logging.INFO)
    logging.getLogger("diting_core.metrics.composite").setLevel(logging.INFO)
    
    # 1. 创建embedding模型 (使用factory)
    print("1. 初始化embedding模型...")
    try:
        # 这里使用模拟的embedding模型
        embedding_model = embedding_factory(
            model="BAAI/bge-m3",
            base_url="https://api.siliconflow.cn/v1/",
            api_key="sk-pdfifkpjdlxvyvgkerbluaotktpznsmpbcvskjauotenxgvz"  # 请替换为有效密钥
        )
    except Exception as e:
        print(f"警告: 无法初始化真实embedding模型，使用模拟模型: {e}")
    # 2. 创建语义检索器
    print("2. 初始化语义检索器...")
    retriever = DemoSemanticRetriever(embedding_model)
    
    # 3. 创建测试数据集 - 使用eval.csv中的数据
    print("3. 准备测试数据集...")
    test_queries = []
    try:
        with open('D:/diting/packages/diting-core/src/diting_core/optimization/datasets/retrieval_data/旅游人工标注.csv', 
                  'r', encoding='utf-8') as csvfile:
            import csv as csv_module
            reader = csv_module.DictReader(csvfile)
            for i, row in enumerate(reader):
                # 跳过第一行标题行
                if i == 0:
                    continue
                test_queries.append({
                    "user_input": row['query'],
                    "expected_output": row['generation_gt'],
                    "response": row['actual_output'],
                    "retrieved_contexts": row['retrieval_context'],
                    "id": i
                })
                # 限制查询数量以避免处理时间过长
                # if i >= 9:  # 只加载前10个查询
                #     break
    except FileNotFoundError:
        print("警告: 未找到eval.csv文件，使用默认查询")
        test_queries = [
            {"user_input": "人工智能和机器学习有什么区别?", "expected_output": "人工智能是计算机科学的一个分支，机器学习是人工智能的一个子集。", "id": "q1"},
            {"user_input": "深度学习在自然语言处理中的应用", "expected_output": "深度学习在自然语言处理中用于机器翻译、文本摘要、问答系统等任务。", "id": "q2"},
            {"user_input": "计算机视觉技术的发展现状", "expected_output": "计算机视觉技术广泛应用于图像识别、目标检测、人脸识别等领域。", "id": "q3"},
        ]
    
    dataset = InMemoryDataset("demo_dataset", test_queries)
    
    # 4. 创建评估指标 - 使用复合指标
    print("4. 初始化评估指标...")
    try:
        # 创建LLM模型用于context_precision和context_recall
        llm_model = llm_factory(
            model="qwen/qwen3-next-80b-a3b-instruct",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"  # 请替换为有效密钥
        )
        
        # 创建context_precision和context_recall实例
        context_precision = ContextPrecision(model=llm_model)
        context_recall = ContextRecall(model=llm_model)
        
        # 使用CompositeMetric组合它们，权重各自0.5
        metric = CompositeMetric(
            metrics=[context_precision, context_recall],
            weights=[0.5, 0.5]  # 各自0.5权重
        )
    except Exception as e:
        print(f"警告: 无法初始化基于LLM的复合指标，使用简化指标: {e}")
        class SimpleRetrievalMetric(BaseMetric):
            async def _compute(self, test_case: LLMCase, *args, **kwargs) -> float:
                if hasattr(test_case, 'retrieval_context') and test_case.retrieval_context:
                    # 简单评分：返回检索结果数量的归一化值(最多10个结果)
                    score = min(len(test_case.retrieval_context) / 10.0, 1.0)
                    return score
                return 0.5  # 默认评分
        metric = SimpleRetrievalMetric()
    
    # 5. 创建优化器 (减小参数范围以避免错误)
    print("5. 初始化穷举优化器...")
    optimizer = SemanticSearchExhaustiveOptimizer(
        similarity_threshold_range=(0.1, 0.8),  # 缩小范围
        similarity_threshold_step=0.1,          # 增大步长以减少组合数
        context_recall_tokens_range=(1500, 4000),  # 合法范围
        context_recall_tokens_step=500,        # 增大步长
        max_workers=10  # 减少并发数以避免API限制
    )
    
    # 6. 显示参数空间信息
    print("6. 参数空间信息:")
    space_summary = optimizer.get_parameter_space_summary()
    print(f"   相似度阈值候选: {space_summary['similarity_threshold']['candidates']}")
    print(f"   Token数候选: {space_summary['context_recall_max_tokens']['candidates']}")
    print(f"   总组合数: {space_summary['total_combinations']}")
    
    # 7. 执行优化
    print("7. 开始优化过程...")
    # 创建初始配置
    initial_config = SemanticSearchConfig.create_default(retriever)

    try:
        result = await optimizer.optimize(
            config=initial_config,
            dataset=dataset,
            metric=metric,
            n_samples=100,  # 减少样本数以加快执行速度
            verbose=True
        )
        
        # 8. 显示结果
        print("\n=== 优化结果 ===")
        print(f"最佳评分: {result.best_score:.4f}")
        print(f"初始评分: {result.initial_score:.4f}")
        improvement = result.improvement
        print(f"性能提升: {improvement:.2%}")
        best_params = result.details.get("best_params", {})
        print(f"最佳参数: {best_params}")
        total_combinations = result.details.get("total_combinations", 0)
        print(f"总组合数: {total_combinations}")
        execution_time = result.details.get("execution_time", 0)
        print(f"执行时间: {execution_time:.2f}秒")
        
        # 保存所有评估结果到CSV文件
        print("\n=== 保存评估结果 ===")
        import csv as csv_module
        import json
        from datetime import datetime
        from typing import Any
        
        # 定义一个函数来处理不能直接序列化的对象
        def json_serializer(obj):
            """处理不能直接序列化的对象"""
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return str(obj)
        
        # 生成基于时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"optimization_results_{timestamp}.csv"
        
        # 准备CSV字段
        fieldnames = [
            "iteration", "type", "score", "similarity_threshold", "context_recall_max_tokens", 
            "success", "avg_retrieval_count", "total_samples", "document_ids", "run_logs",
            "per_item_metrics"
        ]
        
        try:
            # 使用utf-8-sig编码来解决Excel打开CSV文件中文乱码问题
            with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv_module.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # 写入baseline记录
                initial_config = SemanticSearchConfig.create_default(retriever)
                # 评估初始配置以获取详细信息
                initial_score_result = await optimizer._evaluate_config(initial_config, dataset, metric, n_samples=3)
                initial_score = initial_score_result if isinstance(initial_score_result, (int, float)) else initial_score_result[0]
                initial_run_log = {} if isinstance(initial_score_result, (int, float)) else initial_score_result[1]
                
                baseline_record = {
                    "iteration": 0,
                    "type": "baseline",
                    "score": initial_score, # 使用实际评估得到的分数
                    "similarity_threshold": initial_config.similarity_threshold,
                    "context_recall_max_tokens": initial_config.context_recall_max_tokens,
                    "success": True,
                    "avg_retrieval_count": initial_run_log.get("avg_retrieval_count", "N/A"),
                    "total_samples": initial_run_log.get("total_samples", "N/A"),
                    "document_ids": "N/A",
                    "run_logs": "N/A",
                    "per_item_metrics": "N/A"
                }
                
                # 收集baseline的document_ids
                document_ids_list = []
                for log_entry in initial_run_log.get("run_logs", []):
                    if "document_ids" in log_entry:
                        document_ids_list.extend(log_entry["document_ids"])
                
                # 将document_ids转换为JSON字符串
                try:
                    baseline_record["document_ids"] = json.dumps(document_ids_list, 
                                                                ensure_ascii=False, 
                                                                default=json_serializer)
                except Exception as e:
                    baseline_record["document_ids"] = f"序列化错误: {str(e)}"
                
                # 将run_logs转换为JSON字符串
                try:
                    baseline_record["run_logs"] = json.dumps(initial_run_log.get("run_logs", []), 
                                                            ensure_ascii=False, 
                                                            default=json_serializer)
                except Exception as e:
                    baseline_record["run_logs"] = f"序列化错误: {str(e)}"
                
                # 添加每个数据项的指标分数
                try:
                    per_item_metrics = []
                    for log_entry in initial_run_log.get("run_logs", []):
                        sample_id = log_entry.get("sample_id", "unknown")
                        score = log_entry.get("score", 0.0)
                        retrieval_count = log_entry.get("retrieval_count", 0)
                        
                        # 提取各个指标的分数
                        metrics_scores = {}
                        if "run_logs" in log_entry:
                            run_logs = log_entry["run_logs"]
                            if isinstance(run_logs, dict):
                                for metric_name, metric_data in run_logs.items():
                                    if isinstance(metric_data, dict):
                                        # 处理context_precision等指标
                                        if "verdicts" in metric_data:
                                            verdicts = metric_data["verdicts"]
                                            if isinstance(verdicts, list):
                                                # 对于context_precision，提取每个verdict的值
                                                metrics_scores[metric_name] = [v.get("verdict", 0) for v in verdicts if isinstance(v, dict)]
                                            elif isinstance(verdicts, dict) and "verdicts" in verdicts:
                                                # 处理嵌套的情况
                                                inner_verdicts = verdicts["verdicts"]
                                                if isinstance(inner_verdicts, list):
                                                    metrics_scores[metric_name] = [v.get("verdict", 0) for v in inner_verdicts if isinstance(v, dict)]
                                        elif "score" in metric_data:
                                            # 直接包含分数的指标
                                            metrics_scores[metric_name] = metric_data["score"]
                                        else:
                                            # 如果没有verdicts或score字段，尝试查找其他可能的分数表示
                                            for key, value in metric_data.items():
                                                if key == "score" or (isinstance(key, str) and "score" in key.lower()):
                                                    metrics_scores[metric_name] = value
                                                    break
                                    # 处理复合指标中的嵌套结构
                                    elif isinstance(metric_data, list) and len(metric_data) > 0:
                                        # 如果metric_data是一个列表，尝试提取其中的verdicts
                                        for item in metric_data:
                                            if isinstance(item, dict) and "verdicts" in item:
                                                verdicts = item["verdicts"]
                                                if isinstance(verdicts, list):
                                                    metrics_scores[metric_name] = [v.get("verdict", 0) for v in verdicts if isinstance(v, dict)]
                                                break
                                            # 如果仍然没有提取到指标分数，尝试直接从metric_value中获取score
                                            if metric_name not in metrics_scores and isinstance(metric_data, dict):
                                                if "score" in metric_data:
                                                    metrics_scores[metric_name] = metric_data["score"]
                                                elif "verdicts" in metric_data and isinstance(metric_data["verdicts"], dict) and "score" in metric_data["verdicts"]:
                                                    metrics_scores[metric_name] = metric_data["verdicts"]["score"]
                                                # 特殊处理context_recall，它返回的是Verdicts对象
                                                elif "verdicts" in metric_data and isinstance(metric_data["verdicts"], dict):
                                                    verdicts_data = metric_data["verdicts"]
                                                    if "verdicts" in verdicts_data and isinstance(verdicts_data["verdicts"], list):
                                                        # 对于context_recall，提取每个attributed的值
                                                        metrics_scores[metric_name] = [v.get("attributed", 0) for v in verdicts_data["verdicts"] if isinstance(v, dict)]
                        
                        per_item_metrics.append({
                            "sample_id": sample_id,
                            "retrieval_count": retrieval_count,
                            "metrics": metrics_scores
                        })
                    
                    baseline_record["per_item_metrics"] = json.dumps(per_item_metrics, 
                                                                    ensure_ascii=False, 
                                                                    default=json_serializer)
                except Exception as e:
                    baseline_record["per_item_metrics"] = f"序列化错误: {str(e)}"
                
                writer.writerow(baseline_record)
                
                # 写入所有评估记录
                for record in result.history:
                    if record["type"] == "evaluation":
                        row_data = {
                            "iteration": record["iteration"],
                            "type": record["type"],
                            "score": record.get("score", "N/A"),
                            "similarity_threshold": record["params"].get("similarity_threshold", "N/A"),
                            "context_recall_max_tokens": record["params"].get("context_recall_max_tokens", "N/A"),
                            "success": record.get("success", "N/A"),
                            "avg_retrieval_count": "N/A",
                            "total_samples": "N/A",
                            "document_ids": "N/A",
                            "run_logs": "N/A",
                            "per_item_metrics": "N/A"
                        }
                        
                        # 添加运行日志信息
                        if "run_log" in record:
                            run_log = record["run_log"]
                            row_data["avg_retrieval_count"] = run_log.get("avg_retrieval_count", "N/A")
                            row_data["total_samples"] = run_log.get("total_samples", "N/A")
                            
                            # 收集所有document_ids
                            document_ids_list = []
                            for log_entry in run_log.get("run_logs", []):
                                if "document_ids" in log_entry:
                                    document_ids_list.extend(log_entry["document_ids"])
                            
                            # 将document_ids转换为JSON字符串
                            try:
                                row_data["document_ids"] = json.dumps(document_ids_list, 
                                                                    ensure_ascii=False, 
                                                                    default=json_serializer)
                            except Exception as e:
                                row_data["document_ids"] = f"序列化错误: {str(e)}"
                            
                            # 将run_logs转换为JSON字符串
                            try:
                                row_data["run_logs"] = json.dumps(run_log.get("run_logs", []), 
                                                                ensure_ascii=False, 
                                                                default=json_serializer)
                            except Exception as e:
                                row_data["run_logs"] = f"序列化错误: {str(e)}"
                            
                            # 添加每个数据项的指标分数
                            try:
                                per_item_metrics = []
                                for log_entry in run_log.get("run_logs", []):
                                    sample_id = log_entry.get("sample_id", "unknown")
                                    score = log_entry.get("score", 0.0)
                                    retrieval_count = log_entry.get("retrieval_count", 0)
                                    
                                    # 提取各个指标的分数
                                    metrics_scores = {}
                                    if "run_logs" in log_entry:
                                        run_logs = log_entry["run_logs"]
                                        if isinstance(run_logs, dict):
                                            for metric_name, metric_data in run_logs.items():
                                                if isinstance(metric_data, dict):
                                                    # 处理context_precision等指标
                                                    if "verdicts" in metric_data:
                                                        verdicts = metric_data["verdicts"]
                                                        if isinstance(verdicts, list):
                                                            # 对于context_precision，提取每个verdict的值
                                                            metrics_scores[metric_name] = [v.get("verdict", 0) for v in verdicts if isinstance(v, dict)]
                                                        elif isinstance(verdicts, dict) and "verdicts" in verdicts:
                                                            # 处理嵌套的情况
                                                            inner_verdicts = verdicts["verdicts"]
                                                            if isinstance(inner_verdicts, list):
                                                                metrics_scores[metric_name] = [v.get("verdict", 0) for v in inner_verdicts if isinstance(v, dict)]
                                                    elif "score" in metric_data:
                                                        # 直接包含分数的指标
                                                        metrics_scores[metric_name] = metric_data["score"]
                                                    else:
                                                        # 如果没有verdicts或score字段，尝试查找其他可能的分数表示
                                                        for key, value in metric_data.items():
                                                            if key == "score" or (isinstance(key, str) and "score" in key.lower()):
                                                                metrics_scores[metric_name] = value
                                                                break
                                                # 处理复合指标中的嵌套结构
                                                elif isinstance(metric_data, list) and len(metric_data) > 0:
                                                    # 如果metric_data是一个列表，尝试提取其中的verdicts
                                                    for item in metric_data:
                                                        if isinstance(item, dict) and "verdicts" in item:
                                                            verdicts = item["verdicts"]
                                                            if isinstance(verdicts, list):
                                                                metrics_scores[metric_name] = [v.get("verdict", 0) for v in verdicts if isinstance(v, dict)]
                                                            break
                                            # 如果仍然没有提取到指标分数，尝试直接从metric_value中获取score
                                            if metric_name not in metrics_scores and isinstance(metric_data, dict):
                                                if "score" in metric_data:
                                                    metrics_scores[metric_name] = metric_data["score"]
                                                elif "verdicts" in metric_data and isinstance(metric_data["verdicts"], dict) and "score" in metric_data["verdicts"]:
                                                    metrics_scores[metric_name] = metric_data["verdicts"]["score"]
                                                # 特殊处理context_recall，它返回的是Verdicts对象
                                                elif "verdicts" in metric_data and isinstance(metric_data["verdicts"], dict):
                                                    verdicts_data = metric_data["verdicts"]
                                                    if "verdicts" in verdicts_data and isinstance(verdicts_data["verdicts"], list):
                                                        # 对于context_recall，提取每个attributed的值
                                                        metrics_scores[metric_name] = [v.get("attributed", 0) for v in verdicts_data["verdicts"] if isinstance(v, dict)]
                                    
                                    per_item_metrics.append({
                                        "sample_id": sample_id,
                                        "retrieval_count": retrieval_count,
                                        "metrics": metrics_scores
                                    })
                                
                                row_data["per_item_metrics"] = json.dumps(per_item_metrics, 
                                                                        ensure_ascii=False, 
                                                                        default=json_serializer)
                            except Exception as e:
                                row_data["per_item_metrics"] = f"序列化错误: {str(e)}"
                        
                        writer.writerow(row_data)
            
            print(f"评估结果已保存到: {csv_filename}")
        except Exception as e:
            print(f"保存评估结果到CSV文件时出错: {e}")
        
        # 显示所有参数组合的执行结果
        print("\n=== 各参数组合执行结果 ===")
        all_results = result.details.get("all_results", [])
        valid_results = [r for r in all_results if r["success"]]
        sorted_results = sorted(valid_results, key=lambda x: x["score"], reverse=True)
        
        print("排名\t相似度阈值\tToken限制\t评分")
        print("-" * 45)
        for i, res in enumerate(sorted_results[:5], 1):  # 显示前5个最佳结果
            params = res["params"]
            print(f"{i}\t{params['similarity_threshold']}\t\t{params['context_recall_max_tokens']}\t\t{res['score']:.4f}")
        
        failed_results = [r for r in all_results if not r["success"]]
        if failed_results:
            print(f"\n注意: 有 {len(failed_results)} 个参数组合执行失败")
        
        # 显示优化历史
        if result.history:
            print("\n=== 优化历史记录 ===")
            print("迭代\t类型\t\t评分\t\t相似度阈值\tToken限制\t平均检索条数")
            print("-" * 80)
            for record in result.history[:10]:  # 显示前10条记录
                iteration = record["iteration"]
                type_ = record["type"]
                score = record.get("score", 0)
                params = record.get("params", {})
                threshold = params.get("similarity_threshold", "N/A")
                tokens = params.get("context_recall_max_tokens", "N/A")
                
                # 获取平均检索条数信息
                avg_retrieval_count = "N/A"
                if "run_log" in record and "avg_retrieval_count" in record["run_log"]:
                    avg_retrieval_count = f"{record['run_log']['avg_retrieval_count']:.2f}"
                
                print(f"{iteration}\t{type_}\t\t{score:.4f}\t\t{threshold}\t\t{tokens}\t\t{avg_retrieval_count}")
            
            if len(result.history) > 10:
                print(f"... 还有 {len(result.history) - 10} 条记录未显示")
        
        # 9. 演示使用最佳参数
        print("\n=== 使用最佳参数进行检索演示 ===")
        best_threshold = best_params.get("similarity_threshold", 0.7)  # 使用默认值0.7以防万一
        best_tokens = best_params.get("context_recall_max_tokens", 2000)  # 使用默认值2000以防万一
        
        print(f"使用最佳配置:")
        print(f"  - 相似度阈值: {best_threshold}")
        print(f"  - Token限制: {best_tokens} tokens")
        
        # 创建使用最佳参数的配置
        best_config = SemanticSearchConfig.create_with_threshold(
            semantic_retriever=retriever,
            similarity_threshold=best_threshold,
            context_recall_max_tokens=best_tokens
        )
        
        test_query = "人工智能技术在医疗领域的应用"
        print(f"\n查询: {test_query}")
        
        results = await best_config.execute(dataset_item={"query": test_query})
        print(f"检索到 {len(results)} 个结果:")
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. 相似度: {result['similarity']:.3f}")
            print(f"     内容: {result['content'][:50]}...")
            print()
            
    except Exception as e:
        print(f"优化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        print("可能的原因:")
        print("1. API密钥或URL配置不正确")
        print("2. 网络连接问题")
        print("3. 参数范围超出了允许的范围")
        print("4. API调用频率限制")
        print("\n建议:")
        print("- 检查并替换示例中的API密钥和URL为有效的值")
        print("- 如果没有有效的API密钥，可以使用本地模型或模拟模型")
        print("- 减小参数搜索范围和步长以减少组合数")


if __name__ == "__main__":
    asyncio.run(main())