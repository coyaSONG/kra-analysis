"""
작업 관리 API 라우터 v2
비동기 작업 모니터링 및 관리
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import require_api_key
from infrastructure.database import get_db
from models.job_dto import (
    Job,
    JobDetailResponse,
    JobListResponse,
    JobStatus,
    JobType,
)
from models.job_dto import (
    JobLog as JobLogDTO,
)
from services.job_service import JobService

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


@router.get(
    "/",
    response_model=JobListResponse,
    summary="작업 목록 조회",
    description="작업 목록을 조회합니다.",
)
async def list_jobs(
    status: JobStatus | None = Query(None, description="작업 상태 필터"),
    job_type: JobType | None = Query(None, description="작업 유형 필터"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """작업 목록 조회"""
    try:
        jobs, total_count = await job_service.list_jobs_with_total(
            db=db,
            user_id=api_key,
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset,
        )

        # Convert SQLAlchemy models to DTOs
        dto_jobs = [
            Job(
                job_id=j.job_id,
                type=JobType(j.type.value if hasattr(j.type, "value") else str(j.type)),
                status=JobStatus(
                    j.status.value if hasattr(j.status, "value") else str(j.status)
                ),
                created_at=j.created_at or datetime.now(UTC),
                started_at=j.started_at,
                completed_at=j.completed_at,
                progress=j.progress or 0,
                current_step=j.current_step,
                total_steps=j.total_steps,
                result=j.result,
                error_message=j.error_message,
                retry_count=j.retry_count or 0,
                parameters=j.parameters,
                created_by=j.created_by,
                tags=j.tags or [],
            )
            for j in jobs
        ]

        return JobListResponse(
            jobs=dto_jobs,
            total=total_count,
            limit=limit,
            offset=offset,
            pagination=None,
        )
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="작업 상세 조회",
    description="특정 작업의 상세 정보를 조회합니다.",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(
        require_api_key
    ),  # Keep for now, will implement resource access later
):
    """작업 상세 조회"""
    try:
        job = await job_service.get_job(job_id, db, user_id=api_key)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        logs = await job_service.get_job_logs(job_id, db)
        dto_logs = [
            JobLogDTO(
                timestamp=log.timestamp or datetime.now(UTC),
                level=log.level or "INFO",
                message=log.message or "",
                metadata=log.log_metadata,
            )
            for log in (logs or [])
        ]

        dto_job = Job(
            job_id=job.job_id,
            type=JobType(
                job.type.value if hasattr(job.type, "value") else str(job.type)
            ),
            status=JobStatus(
                job.status.value if hasattr(job.status, "value") else str(job.status)
            ),
            created_at=job.created_at or datetime.now(UTC),
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress=job.progress or 0,
            current_step=job.current_step,
            total_steps=job.total_steps,
            result=job.result,
            error_message=job.error_message,
            retry_count=job.retry_count or 0,
            parameters=job.parameters,
            created_by=job.created_by,
            tags=job.tags or [],
        )

        return JobDetailResponse(
            job=dto_job,
            logs=dto_logs,
            estimated_completion=None,
            duration_seconds=None,
            resource_usage=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/{job_id}/cancel", summary="작업 취소", description="진행 중인 작업을 취소합니다."
)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """작업 취소"""
    try:
        success = await job_service.cancel_job(job_id, db, user_id=api_key)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"message": "Job cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
