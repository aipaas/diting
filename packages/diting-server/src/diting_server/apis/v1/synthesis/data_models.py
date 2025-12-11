from pydantic import Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from diting_server.common.schema import Usage, StatusEnum, BaseSchema, ModelConfig


class Metadata(BaseSchema):
    chunk_id: Optional[str] = Field(None, description="分片ID")
    total_chunks: Optional[int] = Field(None, description="总分片数")
    project_name: Optional[str] = Field(None, description="项目名称")
    created_at: Optional[str] = Field(None, description="创建时间")


class SynthesizerConfig(BaseSchema):
    synthesizer_name: str = Field(..., description="合成器名称")
    config: Optional[Dict[str, Any]] = Field(None, description="算法配置参数")


class SynthesizerDefinition(BaseSchema):
    name: str = Field(..., description="Unique identifier for the synthesizer")
    description: str = Field(
        ..., description="Human-readable description of what the synthesizer measures"
    )
    required_input: List[str] = Field(
        ..., description="List of required input fields for this synthesizer"
    )


class InputData(BaseSchema):
    context: Optional[list[str]] = Field(None, description="上下文")
    themes: Optional[List[str]] = Field(None, description="主题列表")


class DatasetSynthesisRequest(BaseSchema):
    llm_config: ModelConfig = Field(..., description="数据生成LLM模型配置")
    embedding_config: Optional[ModelConfig] = Field(
        None, description="数据生成embedding模型配置"
    )
    synthesizer_config: SynthesizerConfig = Field(..., description="数据生成算法配置")
    input_data: InputData = Field(..., description="数据生成输入数据")
    metadata: Optional[Metadata] = Field(None, description="分片信息")


class QAPair(BaseSchema):
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")


class SyntheticQAResult(BaseSchema):
    qa_pair: QAPair = Field(..., description="生成的问答对列表")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="生成过程的元信息，如模型版本、时间、分片ID等"
    )


class DatasetSynthesisResponse(BaseSchema):
    request_id: str = Field(..., description="请求唯一标识符")
    status: StatusEnum = Field(..., description="数据合成状态")
    data: Optional[SyntheticQAResult] = Field(None, description="生成的数据结果")
    usages: Optional[List[Usage]] = Field(None, description="使用token情况")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据信息")
    error: Optional[str] = Field(None, description="错误信息")


class QuestionList(BaseSchema):
    """单个问题的模型"""
    questions: List[str] = Field(..., description="生成的问题列表")


class QuestionListResponse(BaseSchema):
    """基于文本生成问题列表的响应模型"""
    request_id: str = Field(..., description="请求唯一标识符")
    status: StatusEnum = Field(..., description="生成状态")
    data: Optional[QuestionList] = Field(None, description="生成的问题列表")
    usages: Optional[List[Usage]] = Field(None, description="使用token情况")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据信息")
    error: Optional[str] = Field(None, description="错误信息")


class FineTuneDataItem(BaseSchema):
    """微调数据项 - 对应输入数据结构"""
    dataId: str
    collectionId: str
    q: str
    a: str
    indexes: List[List[str]]  # [[question1, question2], ...]


class FineTuneSample(BaseSchema):
    """微调样本 - 输出数据结构"""
    query: str
    positive: List[str] = Field(default_factory=list)
    negatives: List[str] = Field(default_factory=list)
    source_id: str  # 原始数据的_id
    collection_id: str
    original_q: Optional[str] = None
    original_a: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FineTuneDataRequest(BaseSchema):
    """微调数据构建请求"""
    items: List[FineTuneDataItem]
    min_negative_samples: int = Field(default=1, ge=1, description="最小负样本数")
    max_negative_samples: int = Field(default=10, ge=1, description="最大负样本数")
    include_original_q: bool = Field(default=True, description="是否包含原始q作为查询")
    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "dataId": "item_001",
                        "collectionId": "collection_001",
                        "q": "什么是人工智能？",
                        "a": "人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。",
                        "indexes": [
                            ["什么是AI？", "AI的定义"]
                        ]
                    },
                    {
                        "dataId": "item_002",
                        "collectionId": "collection_001",
                        "q": "机器学习是什么？",
                        "a": "机器学习是一门多领域交叉学科，专门研究计算机怎样模拟或实现人类的学习行为，以获取新的知识或技能。",
                        "indexes": [
                            ["ML定义", "机器学习概念"],
                            ["什么是机器学习", "机器学习解释"]
                        ]
                    }
                ],
                "min_negative_samples": 1,
                "max_negative_samples": 5,
                "include_original_q": True,            
            }
        }


class FineTuneDataResponse(BaseSchema):
    """微调数据响应"""
    request_id: str
    total_items: int
    total_samples: int
    positive_samples: int
    negative_samples: int
    processing_time: float
    samples: List[FineTuneSample]
    statistics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)