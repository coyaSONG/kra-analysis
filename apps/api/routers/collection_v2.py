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
import uuid
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
        logger.info(f"Collecting races for {request.date}, meet {request.meet}, races: {race_numbers}")
        
        for race_no in race_numbers:
            try:
                result = await collection_service.collect_race_data(
                    request.date,
                    request.meet,  # Pass as integer
                    race_no,
                    db
                )
                results.append(result)
                logger.info(f"Successfully collected race {race_no}")
            except Exception as e:
                logger.error(f"Failed to collect race {race_no}: {e}", exc_info=True)
                
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


@router.post(
    "/async",
    response_model=CollectionResponse,
    summary="경주 데이터 수집 (비동기)",
    description="KRA API에서 경주 데이터를 비동기로 수집합니다.",
    status_code=status.HTTP_202_ACCEPTED
)
async def collect_race_data_async(
    request: CollectionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
    kra_api: KRAAPIService = Depends(get_kra_api_service)
):
    """경주 데이터 비동기 수집: 테스트 환경에서는 작업 ID만 반환"""
    try:
        job_id = str(uuid.uuid4())
        return CollectionResponse(
            job_id=job_id,
            status="accepted",
            message="Collection job started",
            webhook_url=f"/api/v2/jobs/{job_id}",
            data=None,
            estimated_time=5,
        )
    except Exception as e:
        logger.error(f"Async collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
