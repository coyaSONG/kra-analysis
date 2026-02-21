"""
작업 관리 서비스
비동기 작업 생성, 모니터링, 관리
Uses in-process background task runner (infrastructure.background_tasks).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.background_tasks import (
    cancel_task,
    get_task_status,
    submit_task,
)
from models.database_models import Job, JobLog

logger = structlog.get_logger()


class JobService:
    """작업 관리 서비스"""

    @staticmethod
    def _to_filter_value(value: Any) -> str:
        """Enum/문자열 필터 값을 DB 비교 가능한 문자열로 정규화."""
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    async def create_job(
        self, job_type: str, parameters: dict[str, Any], user_id: str, db: AsyncSession
    ) -> Job:
        """
        새 작업 생성

        Args:
            job_type: 작업 유형
            parameters: 작업 파라미터
            user_id: 사용자 ID
            db: 데이터베이스 세션

        Returns:
            생성된 작업 객체
        """
        try:
            # 작업 생성
            job = Job(
                type=job_type,
                parameters=parameters,
                status="pending",
                created_by=user_id,
            )

            db.add(job)
            await db.commit()
            await db.refresh(job)

            logger.info(
                "Job created", job_id=job.job_id, job_type=job_type, user_id=user_id
            )

            return job

        except Exception as e:
            logger.error("Failed to create job", error=str(e))
            await db.rollback()
            raise

    async def start_job(self, job_id: str, db: AsyncSession) -> str:
        """
        작업 시작

        Args:
            job_id: 작업 ID
            db: 데이터베이스 세션

        Returns:
            Background task ID
        """
        try:
            # 작업 조회
            result = await db.execute(select(Job).where(Job.job_id == job_id))
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job not found: {job_id}")

            if job.status != "pending":
                raise ValueError(f"Job already started: {job.status}")

            # 작업 유형에 따라 background task 실행
            task_id = await self._dispatch_task(job)

            # 상태 업데이트
            job.status = "queued"  # type: ignore[assignment]
            job.task_id = task_id  # type: ignore[assignment]
            job.started_at = datetime.now(UTC)  # type: ignore[assignment]

            await db.commit()

            # 로그 추가
            await self.add_job_log(
                job_id, "info", "Job started", {"task_id": task_id}, db
            )

            logger.info("Job started", job_id=job_id, task_id=task_id)

            return task_id

        except Exception as e:
            logger.error("Failed to start job", job_id=job_id, error=str(e))
            await db.rollback()
            raise

    async def _dispatch_task(self, job: Job) -> str:
        """작업 유형에 따라 background task 디스패치. Returns task_id."""
        from tasks.async_tasks import (
            batch_collect,
            collect_race_data,
            enrich_race_data,
            full_pipeline,
            preprocess_race_data,
        )

        params = job.parameters

        job_type = job.type.value if hasattr(job.type, "value") else str(job.type)

        if job_type == "collect_race":
            task_id = submit_task(
                collect_race_data,
                params["race_date"],
                params["meet"],
                params["race_no"],
                job.job_id,
            )
        elif job_type == "preprocess_race":
            task_id = submit_task(
                preprocess_race_data,
                params["race_id"],
                job.job_id,
            )
        elif job_type == "enrich_race":
            task_id = submit_task(
                enrich_race_data,
                params["race_id"],
                job.job_id,
            )
        elif job_type in ("batch_collect", "batch"):
            task_id = submit_task(
                batch_collect,
                params["race_date"],
                params["meet"],
                params["race_numbers"],
                job.job_id,
            )
        elif job_type == "full_pipeline":
            task_id = submit_task(
                full_pipeline,
                params["race_date"],
                params["meet"],
                params["race_no"],
                job.job_id,
            )
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        return task_id

    async def get_job(
        self, job_id: str, db: AsyncSession, user_id: str | None = None
    ) -> Job | None:
        """작업 조회"""
        query = select(Job).where(Job.job_id == job_id)
        if user_id:
            query = query.where(Job.created_by == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_job_status(self, job_id: str, db: AsyncSession) -> dict[str, Any]:
        """
        작업 상태 조회

        Args:
            job_id: 작업 ID
            db: 데이터베이스 세션

        Returns:
            상태 정보
        """
        job = await self.get_job(job_id, db)

        if not job:
            return None

        # Background task 상태 확인 (선택적)
        bg_status: dict[str, Any] | None = None
        if job.task_id:
            try:
                bg_status = await get_task_status(job.task_id)
            except Exception as e:
                logger.warning("Failed to get background task status", error=str(e))

        # 작업 진행률 계산
        progress = self._calculate_progress(job, bg_status)

        return {
            "job_id": job.job_id,
            "type": job.type,
            "status": job.status,
            "progress": progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": getattr(job, "error_message", None),
            "task_status": bg_status,
            "parameters": job.parameters,
        }

    def _calculate_progress(self, job: Job, task_status: dict[str, Any] | None) -> int:
        """작업 진행률 계산 (0-100)"""
        if job.status == "completed":
            return 100
        elif job.status == "failed":
            return 0
        elif job.status == "pending":
            return 0
        elif job.status == "queued":
            return 5
        elif job.status == "processing":
            # 작업 유형에 따라 진행률 계산
            if job.type == "full_pipeline":
                # 3단계 파이프라인
                if task_status and "result" in task_status:
                    info = task_status["result"]
                    if isinstance(info, dict) and "steps" in info:
                        completed = sum(
                            1 for v in info["steps"].values() if v == "completed"
                        )
                        return 10 + (completed * 30)  # 10-100%
            return 50  # 기본값

        return 0

    async def get_job_logs(
        self, job_id: str, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[JobLog]:
        """작업 로그 조회"""
        result = await db.execute(
            select(JobLog)
            .where(JobLog.job_id == job_id)
            .order_by(desc(JobLog.timestamp))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def add_job_log(
        self,
        job_id: str,
        level: str,
        message: str,
        data: dict[str, Any],
        db: AsyncSession,
    ) -> JobLog:
        """작업 로그 추가"""
        try:
            log = JobLog(job_id=job_id, level=level, message=message, log_metadata=data)

            db.add(log)
            await db.commit()
            await db.refresh(log)

            return log

        except Exception as e:
            logger.error("Failed to add job log", error=str(e))
            await db.rollback()
            raise

    async def list_jobs(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Job]:
        """
        작업 목록 조회

        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID (필터)
            job_type: 작업 유형 (필터)
            status: 상태 (필터)
            limit: 조회 개수
            offset: 오프셋

        Returns:
            작업 목록
        """
        jobs, _ = await self.list_jobs_with_total(
            db=db,
            user_id=user_id,
            job_type=job_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        return jobs

    async def list_jobs_with_total(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """작업 목록과 전체 개수를 함께 조회."""
        filters = []
        if user_id:
            filters.append(Job.created_by == user_id)
        if job_type:
            filters.append(Job.type == self._to_filter_value(job_type))
        if status:
            filters.append(Job.status == self._to_filter_value(status))

        list_query = select(Job)
        count_query = select(func.count()).select_from(Job)

        if filters:
            condition = and_(*filters)
            list_query = list_query.where(condition)
            count_query = count_query.where(condition)

        list_query = (
            list_query.order_by(desc(Job.created_at)).limit(limit).offset(offset)
        )

        list_result = await db.execute(list_query)
        count_result = await db.execute(count_query)

        return list(list_result.scalars().all()), count_result.scalar_one()

    async def cancel_job(
        self, job_id: str, db: AsyncSession, user_id: str | None = None
    ) -> bool:
        """
        작업 취소

        Args:
            job_id: 작업 ID
            db: 데이터베이스 세션

        Returns:
            성공 여부
        """
        try:
            job = await self.get_job(job_id, db, user_id=user_id)

            if not job:
                return False

            if str(job.status) in ["completed", "failed", "cancelled"] or (
                hasattr(job.status, "value")
                and job.status.value in ["completed", "failed", "cancelled"]
            ):
                return False

            # Background task 취소
            task_id = getattr(job, "task_id", None)
            if task_id:
                try:
                    await cancel_task(task_id)
                except Exception as e:
                    logger.warning("Failed to cancel background task", error=str(e))

            # 상태 업데이트
            job.status = "cancelled"  # type: ignore[assignment]
            job.completed_at = datetime.now(UTC)  # type: ignore[assignment]

            await db.commit()

            # 로그 추가
            await self.add_job_log(job_id, "warning", "Job cancelled", {}, db)

            return True

        except Exception as e:
            logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            await db.rollback()
            return False

    async def cleanup_old_jobs(self, db: AsyncSession, days: int = 7) -> int:
        """
        오래된 작업 정리

        Args:
            db: 데이터베이스 세션
            days: 보관 일수

        Returns:
            삭제된 작업 수
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            # 완료된 오래된 작업 조회
            result = await db.execute(
                select(Job).where(
                    and_(
                        Job.status.in_(["completed", "failed", "cancelled"]),
                        Job.created_at < cutoff_date,
                    )
                )
            )

            jobs = result.scalars().all()
            count = len(jobs)

            # 삭제
            for job in jobs:
                await db.delete(job)

            await db.commit()

            logger.info("Cleaned up old jobs", count=count)

            return count

        except Exception as e:
            logger.error("Failed to cleanup old jobs", error=str(e))
            await db.rollback()
            return 0

    async def get_job_statistics(
        self, db: AsyncSession, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        작업 통계 조회

        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID (필터)

        Returns:
            통계 정보
        """
        try:
            # 기본 쿼리
            base_query = select(Job)
            if user_id:
                base_query = base_query.where(Job.created_by == user_id)

            # 전체 작업 수
            total_result = await db.execute(base_query)
            total_jobs = len(total_result.scalars().all())

            # 상태별 작업 수
            status_counts = {}
            for status in [
                "pending",
                "queued",
                "processing",
                "completed",
                "failed",
                "cancelled",
            ]:
                result = await db.execute(base_query.where(Job.status == status))
                status_counts[status] = len(result.scalars().all())

            # 작업 유형별 수
            type_counts = {}
            for job_type in [
                "collect_race",
                "preprocess_race",
                "enrich_race",
                "batch_collect",
                "full_pipeline",
            ]:
                result = await db.execute(base_query.where(Job.type == job_type))
                type_counts[job_type] = len(result.scalars().all())

            # 최근 24시간 작업 수
            yesterday = datetime.now(UTC) - timedelta(days=1)
            recent_result = await db.execute(
                base_query.where(Job.created_at >= yesterday)
            )
            recent_jobs = len(recent_result.scalars().all())

            return {
                "total_jobs": total_jobs,
                "status_counts": status_counts,
                "type_counts": type_counts,
                "recent_jobs_24h": recent_jobs,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get job statistics", error=str(e))
            return {"error": str(e), "timestamp": datetime.now(UTC).isoformat()}
