"""
데이터 수집 API 라우터 v2
경주 데이터 수집, 전처리, 강화, 결과 수집 엔드포인트
"""

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from dependencies.auth import require_api_key
from infrastructure.database import get_db
from models.collection_dto import (
    CollectionRequest,
    CollectionResponse,
    CollectionStatus,
    ResultCollectionRequest,
)
from models.database_models import DataStatus, Race
from services.collection_service import CollectionService
from services.job_service import JobService
from services.kra_api_service import KRAAPIService, get_kra_api_service

logger = structlog.get_logger()

router = APIRouter(
    responses={
        404: {"description": "Not found"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    }
)

# JobService 인스턴스
job_service = JobService()


@router.post(
    "/",
    response_model=CollectionResponse,
    summary="경주 데이터 수집",
    description="KRA API에서 경주 데이터를 수집합니다.",
)
async def collect_race_data(
    request: CollectionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
    kra_api: KRAAPIService = Depends(get_kra_api_service),
):
    """경주 데이터 수집"""
    try:
        # CollectionService 사용
        collection_service = CollectionService(kra_api)

        # 경주 번호가 지정되지 않았으면 1-15 전체
        race_numbers = request.race_numbers or list(range(1, 16))

        results = []
        logger.info(
            f"Collecting races for {request.date}, meet {request.meet}, races: {race_numbers}"
        )

        for race_no in race_numbers:
            try:
                result = await collection_service.collect_race_data(
                    request.date,
                    request.meet,
                    race_no,
                    db,  # Pass as integer
                )
                results.append(result)
                logger.info(f"Successfully collected race {race_no}")
            except Exception as e:
                logger.error(f"Failed to collect race {race_no}: {e}", exc_info=True)

        return CollectionResponse(
            status="success", message=f"Collected {len(results)} races", data=results
        )

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/async",
    response_model=CollectionResponse,
    summary="경주 데이터 수집 (비동기)",
    description="KRA API에서 경주 데이터를 비동기로 수집합니다.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def collect_race_data_async(
    request: CollectionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """경주 데이터 비동기 수집"""
    try:
        _ = str(uuid.uuid4())
        race_numbers = request.race_numbers or list(range(1, 16))
        parameters = {
            "race_date": request.date,
            "meet": request.meet,
            "race_numbers": race_numbers,
        }

        job = await job_service.create_job(
            job_type="batch",
            parameters=parameters,
            user_id=api_key,
            db=db,
        )
        await job_service.start_job(job.job_id, db)

        return CollectionResponse(
            job_id=job.job_id,
            status="accepted",
            message="Collection job started",
            webhook_url=f"/api/v2/jobs/{job.job_id}",
            data=None,
            estimated_time=5,
        )
    except Exception as e:
        logger.error(f"Async collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/status",
    response_model=CollectionStatus,
    summary="수집 상태 조회",
    description="데이터 수집 상태를 조회합니다.",
)
async def get_collection_status(
    date: str,
    meet: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """수집 상태 조회"""
    try:
        status_data = await CollectionService.get_collection_status(db, date, meet)
        return CollectionStatus(**status_data)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/result",
    response_model=CollectionResponse,
    summary="경주 결과 수집",
    description="KRA API에서 경주 결과(1-3위)를 수집하여 DB에 저장합니다.",
)
async def collect_race_result(
    request: ResultCollectionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
    kra_api: KRAAPIService = Depends(get_kra_api_service),
):
    """경주 결과 수집 - KRA API에서 결과를 가져와 races.result_data에 저장"""
    try:
        # KRA API에서 경주 결과 조회
        result_response = await kra_api.get_race_result(
            request.date, str(request.meet), request.race_number
        )

        if not KRAResponseAdapter.is_successful_response(result_response):
            raise HTTPException(
                status_code=404,
                detail=f"경주 결과를 찾을 수 없습니다: {request.date} {request.meet}경마장 {request.race_number}R",
            )

        # items에서 top3 추출
        items = KRAResponseAdapter.extract_items(result_response)
        if not items:
            raise HTTPException(
                status_code=404, detail="경주 결과 데이터가 비어있습니다"
            )

        # ord 필드로 정렬하여 1-3위 추출
        sorted_items = sorted(
            [item for item in items if item.get("ord") and int(item["ord"]) > 0],
            key=lambda x: int(x["ord"]),
        )
        top3 = [int(item["chulNo"]) for item in sorted_items[:3]]

        if len(top3) < 3:
            raise HTTPException(
                status_code=404,
                detail=f"1-3위 결과가 부족합니다 (찾은 수: {len(top3)})",
            )

        # DB에서 해당 경주 찾기
        race_id = f"{request.date}_{request.meet}_{request.race_number}"
        result = await db.execute(select(Race).where(Race.race_id == race_id))
        race = result.scalar_one_or_none()

        if not race:
            raise HTTPException(
                status_code=404, detail=f"경주를 찾을 수 없습니다: {race_id}"
            )

        # 결과 저장
        race.result_data = top3
        race.result_status = DataStatus.COLLECTED
        race.result_collected_at = datetime.utcnow()
        race.updated_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Race result collected: {race_id} -> top3={top3}")

        return CollectionResponse(
            status="success",
            message=f"결과 수집 완료: {race_id}",
            data=[{"race_id": race_id, "top3": top3}],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Result collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
