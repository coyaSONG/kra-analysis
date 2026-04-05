"""
데이터 수집 API 라우터 v2
경주 데이터 수집, 전처리, 강화, 결과 수집 엔드포인트
"""

from dataclasses import asdict

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
from services.kra_collection_module import (
    BatchCollectInput,
    KRACollectionModule,
    ResultCollectInput,
)
from services.result_collection_service import (
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

collection_module = KRACollectionModule()


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
):
    """경주 데이터 수집"""
    try:
        outcome = await collection_module.commands.collect_batch(
            BatchCollectInput(
                race_date=request.date,
                meet=request.meet,
                race_numbers=request.race_numbers,
            ),
            db=db,
        )

        if outcome.status == "error":
            raise HTTPException(
                status_code=502,
                detail={"message": outcome.message, "errors": outcome.errors},
            )

        return CollectionResponse(
            job_id=None,
            status=outcome.status,
            message=outcome.message,
            estimated_time=None,
            webhook_url=None,
            data=outcome.data,
        )

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
        receipt = await collection_module.jobs.submit_batch_collect(
            BatchCollectInput(
                race_date=request.date,
                meet=request.meet,
                race_numbers=request.race_numbers,
            ),
            owner_ref=principal.owner_ref,
            db=db,
        )
        return CollectionResponse(
            job_id=receipt.job_id,
            status=receipt.status,
            message=receipt.message,
            estimated_time=receipt.estimated_time,
            webhook_url=receipt.webhook_url,
            data=None,
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
        status_data = await collection_module.queries.get_status(
            race_date=date,
            meet=meet,
            db=db,
        )
        return CollectionStatus(**asdict(status_data))
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
):
    """경주 결과 수집 - KRA API에서 결과를 가져와 races.result_data에 저장"""
    try:
        result_data = await collection_module.commands.collect_result(
            ResultCollectInput(
                race_date=request.date,
                meet=request.meet,
                race_number=request.race_number,
            ),
            db=db,
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
