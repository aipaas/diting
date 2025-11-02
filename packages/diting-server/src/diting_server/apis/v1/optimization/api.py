#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from diting_server.apis.v1.optimization.data_models import (
    OptimizationRequest,
    OptimizationResponse,
)
from diting_server.common.logging_config.config import get_logger
from diting_server.middleware.request_tracking import get_request_id_from_scope
from diting_server.services.optimization.optimization_service import (
    rag_optimization_service,
)

router = APIRouter(prefix="/api/v1/optimizations", tags=["optimizations"])
logger = get_logger(__name__)


@router.post("/rag", response_model=OptimizationResponse)
async def optimize_rag(
    request: OptimizationRequest, http_request: Request
) -> OptimizationResponse:
    request_id = get_request_id_from_scope(http_request.scope)
    try:
        return await rag_optimization_service.run_optimization(request, request_id)
    except ValueError as exc:
        logger.warning(
            "Invalid optimization request",
            request_id=request_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error during optimization",
            request_id=request_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(exc)}",
        ) from exc
