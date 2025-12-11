#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, status, Request
from diting_server.common.logging_config.config import get_logger
from diting_server.apis.v1.synthesis.data_models import (
    DatasetSynthesisRequest,
    DatasetSynthesisResponse,
    QuestionListResponse,
    FineTuneDataRequest,
    FineTuneDataResponse,

)
from diting_server.services.synthesis.synthesis_service import synthesizer_service
from diting_server.middleware.request_tracking import get_request_id_from_scope

router = APIRouter(prefix="/api/v1/dataset-synthesis", tags=["dataset-synthesis"])
logger = get_logger(__name__)


@router.post("/runs", response_model=DatasetSynthesisResponse | QuestionListResponse)
async def run_synthesis(
    request: DatasetSynthesisRequest, http_request: Request
) -> DatasetSynthesisResponse | QuestionListResponse:
    request_id = get_request_id_from_scope(http_request.scope)

    try:
        result = await synthesizer_service.run_synthesizer(request, request_id)
        return result
    except Exception as e:
        logger.error("Synthesis failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthesis task execution failed: {str(e)}",
        )



@router.post("/build-fine-tune-data", response_model=FineTuneDataResponse)
async def build_fine_tune_data(
    request: FineTuneDataRequest, 
    http_request: Request
) -> FineTuneDataResponse:
    """
    构建微调数据接口
    从输入的几千条数据中构建正负样本对用于模型微调
    
    正样本：indexes中的每一个[q1, q2]对
    负样本：其他indexes中的其他问题
    """
    request_id = get_request_id_from_scope(http_request.scope)
    
    logger.info(
        "Building fine-tune data",
        request_id=request_id,
        total_items=len(request.items)
    )
    
    try:
        # 调用synthesizer_service中的方法构建微调数据
        result = await synthesizer_service.build_fine_tune_data(
            items=request.items,
            min_negative_samples=request.min_negative_samples,
            max_negative_samples=request.max_negative_samples,
            include_original_q=request.include_original_q,
            request_id=request_id
        )
        
        logger.info(
            "Fine-tune data built successfully",
            request_id=request_id,
            total_samples=result["total_samples"],
            processing_time=result["processing_time"]
        )
        
        # 构建响应
        response = FineTuneDataResponse(
            request_id=request_id,
            total_items=result["total_items"],
            total_samples=result["total_samples"],
            positive_samples=result["positive_samples"],
            negative_samples=result["negative_samples"],
            processing_time=result["processing_time"],
            samples=result["samples"],
            statistics=result.get("statistics", {})
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to build fine-tune data",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build fine-tune data: {str(e)}",
        )