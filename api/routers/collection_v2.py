"""
데이터 수집 API 라우터 v2
경주 데이터 수집, 전처리, 강화 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from dependencies.auth import require_api_key
from infrastructure.database import get_db
from services.job_service import JobService
from services.kra_api_service import get_kra_api_service, KRAAPIService
from services.collection_service import CollectionService
from models.collection_dto import (
    CollectionRequest,
    CollectionResponse,
    CollectionStatus
)

logger = structlog.get_logger()

router = APIRouter(
    responses={
        404: {"description": "Not found"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)

# JobService 인스턴스
job_service = JobService()


@router.post(
    "/",
    response_model=CollectionResponse,
    summary="경주 데이터 수집",
    description="KRA API에서 경주 데이터를 수집합니다."
)
async def collect_race_data(
    request: CollectionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
    kra_api: KRAAPIService = Depends(get_kra_api_service)
):
    """경주 데이터 수집"""
    try:
        # CollectionService 사용
        collection_service = CollectionService(kra_api)
        
        # 경주 번호가 지정되지 않았으면 1-15 전체
        race_numbers = request.race_numbers or list(range(1, 16))
        
        results = []
        for race_no in race_numbers:
            try:
                result = await collection_service.collect_race_data(
                    request.date,
                    str(request.meet),  # Convert to string as expected by service
                    race_no,
                    db
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to collect race {race_no}: {e}")
                
        return CollectionResponse(
            status="success",
            message=f"Collected {len(results)} races",
            data=results
        )
        
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/status",
    response_model=CollectionStatus,
    summary="수집 상태 조회",
    description="데이터 수집 상태를 조회합니다."
)
async def get_collection_status(
    date: str,
    meet: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """수집 상태 조회"""
    try:
        # TODO: 실제 상태 조회 구현
        return CollectionStatus(
            date=date,
            meet=meet,
            total_races=15,
            collected_races=0,
            enriched_races=0,
            status="pending"
        )
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )