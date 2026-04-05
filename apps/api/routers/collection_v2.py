"""
데이터 수집 API 라우터 v2
경주 데이터 수집, 전처리, 강화, 결과 수집 엔드포인트
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import AuthenticatedPrincipal, require_action
from infrastructure.database import get_db
from models.collection_dto import (
    CollectionRequest,
    CollectionResponse,
    CollectionStatus,
    ResultCollectionRequest,
)
from services.collection_service import CollectionService
from services.collection_workflow import CollectionWorkflow
from services.job_service import JobService
from services.kra_api_service import KRAAPIService, get_kra_api_service
from services.result_collection_service import (
    ResultCollectionService,
    ResultNotFoundError,
)

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
collection_workflow = CollectionWorkflow(job_service)
result_collection_service = ResultCollectionService()


@router.post(
    "/",
    response_model=CollectionResponse,
    summary="경주 데이터 수집",
    description="KRA API에서 경주 데이터를 수집합니다.",
)
async def collect_race_data(
    request: CollectionRequest,
    db: AsyncSession = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_action("collection.collect")),
    kra_api: KRAAPIService = Depends(get_kra_api_service),
):
    """경주 데이터 수집"""
    try:
        plan = collection_workflow.build_batch_plan(request)
        outcome = await collection_workflow.collect_batch(plan, db, kra_api)

        if outcome.status == "error":
            raise HTTPException(
                status_code=502,
                detail={"message": outcome.message, "errors": outcome.errors},
            )

        return outcome.to_response()

    except HTTPException:
        raise
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
    principal: AuthenticatedPrincipal = Depends(
        require_action("collection.collect_async")
    ),
):
    """경주 데이터 비동기 수집"""
    try:
        plan = collection_workflow.build_batch_plan(request)
        return await collection_workflow.submit_batch_job(
            plan,
            owner_ref=principal.owner_ref,
            db=db,
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
    principal: AuthenticatedPrincipal = Depends(
        require_action("collection.status.read")
    ),
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
    principal: AuthenticatedPrincipal = Depends(
        require_action("collection.result.collect")
    ),
    kra_api: KRAAPIService = Depends(get_kra_api_service),
):
    """경주 결과 수집 - KRA API에서 결과를 가져와 races.result_data에 저장"""
    try:
        result_data = await result_collection_service.collect_result(
            race_date=request.date,
            meet=request.meet,
            race_number=request.race_number,
            db=db,
            kra_api=kra_api,
        )

        return CollectionResponse(
            job_id=None,
            status="success",
            message=f"결과 수집 완료: {result_data['race_id']}",
            estimated_time=None,
            webhook_url=None,
            data=[result_data],
        )
    except ResultNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Result collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
