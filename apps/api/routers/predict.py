"""삼복연승 top-3 예측 API 라우터.

leakage-free 챔피언 모델(autoresearch clean v2)을 사용한 단건 추론.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from config import settings
from dependencies.auth import AuthenticatedPrincipal, require_action
from models.predict_dto import (
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
)
from services.prediction_service import ModelNotLoadedError, PredictionService

logger = structlog.get_logger()

router = APIRouter(
    responses={
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
        503: {"description": "Model not available"},
    }
)

# 프로세스당 1개 인스턴스 (번들은 첫 호출 시 lazy-load)
prediction_service = PredictionService(bundle_path=settings.champion_model_path)


@router.post(
    "/",
    response_model=PredictResponse,
    summary="단일 경주 삼복연승 top-3 예측",
    description=(
        "prerace-canonical-v2 race payload를 받아 leakage-free 챔피언 LogReg "
        "모델로 top-3 chulNo와 score를 반환한다."
    ),
)
async def predict(
    request: PredictRequest,
    principal: AuthenticatedPrincipal = Depends(require_action("prediction.predict")),
) -> PredictResponse:
    try:
        result = prediction_service.predict(request.race)
    except ModelNotLoadedError as e:
        logger.warning("Prediction model unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ValueError as e:
        # build_alternative_ranking_rows_for_race 검증 실패 등
        logger.info("Invalid prediction payload", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid race payload: {e}",
        ) from e
    except Exception as e:
        logger.exception("Prediction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed",
        ) from e
    return PredictResponse(**result)


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="현재 로드된 챔피언 모델 메타데이터",
)
async def model_info(
    principal: AuthenticatedPrincipal = Depends(
        require_action("prediction.read_model_info")
    ),
) -> ModelInfoResponse:
    try:
        info = prediction_service.model_info()
    except ModelNotLoadedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    return ModelInfoResponse(**info)
