"""
작업 관리 API 라우터 v2
비동기 작업 모니터링 및 관리
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from dependencies.auth import require_api_key
from infrastructure.database import get_db
from services.job_service import JobService
from models.job_dto import (
    Job,
    JobDetailResponse,
    JobListResponse,
    JobStatus,
    JobType
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


@router.get(
    "/",
    response_model=JobListResponse,
    summary="작업 목록 조회",
    description="작업 목록을 조회합니다."
)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="작업 상태 필터"),
    job_type: Optional[JobType] = Query(None, description="작업 유형 필터"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """작업 목록 조회"""
    try:
        jobs = await job_service.list_jobs(
            db=db,
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset
        )
        
        return JobListResponse(
            jobs=jobs,
            total=len(jobs),
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="작업 상세 조회",
    description="특정 작업의 상세 정보를 조회합니다."
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """작업 상세 조회"""
    try:
        job = await job_service.get_job(job_id, db)
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )
            
        logs = await job_service.get_job_logs(job_id, db)
        
        return JobDetailResponse(
            job=job,
            logs=logs
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/{job_id}/cancel",
    response_model=Job,
    summary="작업 취소",
    description="진행 중인 작업을 취소합니다."
)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key)
):
    """작업 취소"""
    try:
        job = await job_service.cancel_job(job_id, db)
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )