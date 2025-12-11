#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Any, List, Dict, Optional


class QA(BaseModel):
    question: str
    answer: str


class QAPairs(BaseModel):
    qa_pairs: list[QA]


class QAWithScore(BaseModel):
    QA: QA
    score: float
    reason: str

class QAviewpoints(BaseModel):
    shared_key_term: str
    question1: str
    question2: str
    answer: str

class QuestionPairs(BaseModel):
    summary_within_20_words: str
    five_QAstyle_viewpoints: list[QAviewpoints]


class FineTuneSample(BaseModel):
    """微调样本数据结构"""
    query: str
    positive: List[str]
    negatives: List[str]
    source_id: str
    collection_id: str
    original_q: Optional[str]
    original_a: Optional[str]
    metadata: Dict[str, Any]


class PrecomputedData(BaseModel):
    """预计算数据结构，提升性能"""
    all_questions: List[str]  # 所有问题列表，用于随机采样
    question_to_items: Dict[str, List[str]]  # 问题到数据项ID的映射
    question_to_collection: Dict[str, str]  # 问题到知识库的映射
    collection_questions: Dict[str, List[str]]  # 知识库到问题列表的映射
    question_index_map: Dict[str, int]  # 问题到索引的映射，用于排除
