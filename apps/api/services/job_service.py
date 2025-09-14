"""
작업 관리 서비스
비동기 작업 생성, 모니터링, 관리
"""

import importlib
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database_models import Job, JobLog

# Optional globals for test-time injection
AsyncResult = None  # type: ignore
celery_app = None  # type: ignore

logger = structlog.get_logger()


class JobService:
    """작업 관리 서비스"""

    @staticmethod
    def _get_celery_components():
        """
        Celery 사용 컴포넌트를 지연 임포트합니다.
        Celery 미설치/미구성 환경에서도 ImportError로 모듈 로드가 실패하지 않도록 가드합니다.

        Returns:
            tuple(celery_app | None, AsyncResult | None)
        """
        # 우선 모듈 전역으로 주입된 값 사용(테스트 호환)
        injected_app = globals().get("celery_app")
        injected_async_result = globals().get("AsyncResult")

        app = None
        ar = None

        if injected_app is not None:
            app = injected_app
        else:
            try:
                infra = importlib.import_module("infrastructure.celery_app")
                app = getattr(infra, "celery_app", None)
            except Exception as e:
                logger.debug("Celery app unavailable", error=str(e))
                app = None

        if injected_async_result is not None:
            ar = injected_async_result
        else:
            try:
                celery_result_mod = importlib.import_module("celery.result")
                ar = getattr(celery_result_mod, "AsyncResult", None)
            except Exception as e:
                logger.debug("Celery AsyncResult unavailable", error=str(e))
                ar = None

        return app, ar

    @staticmethod
    def _get_collection_tasks_module():
        """
        Celery 태스크 모듈(tasks.collection_tasks)을 지연 임포트합니다.
        Celery가 설치되지 않았거나 설정되지 않은 경우 None을 반환합니다.
        """
        try:
            return importlib.import_module("tasks.collection_tasks")
        except Exception as e:
            logger.debug("collection_tasks module unavailable", error=str(e))
            return None

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
            Celery 태스크 ID
        """
        try:
            # 작업 조회
            result = await db.execute(select(Job).where(Job.job_id == job_id))
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job not found: {job_id}")

            if job.status != "pending":
                raise ValueError(f"Job already started: {job.status}")

            # 작업 유형에 따라 Celery 태스크 실행
            task_result = await self._dispatch_task(job)

            # 상태 업데이트
            job.status = "queued"
            job.task_id = task_result.id
            job.started_at = datetime.utcnow()

            await db.commit()

            # 로그 추가
            await self.add_job_log(
                job_id, "info", "Job started", {"task_id": task_result.id}, db
            )

            logger.info("Job started", job_id=job_id, task_id=task_result.id)

            return task_result.id

        except Exception as e:
            logger.error("Failed to start job", job_id=job_id, error=str(e))
            await db.rollback()
            raise

    async def _dispatch_task(self, job: Job) -> AsyncResult:
        """작업 유형에 따라 Celery 태스크 디스패치"""
        params = job.parameters

        celery_app, _ = self._get_celery_components()
        tasks_mod = self._get_collection_tasks_module()
        if not celery_app or not tasks_mod:
            raise RuntimeError(
                "Celery가 설치/구성되지 않아 작업을 큐에 넣을 수 없습니다. "
                "환경 변수 및 브로커 설정을 확인하세요."
            )

        if job.type == "collect_race":
            return tasks_mod.collect_race_data_task.delay(
                params["race_date"], params["meet"], params["race_no"], job.job_id
            )
        elif job.type == "preprocess_race":
            return tasks_mod.preprocess_race_data_task.delay(
                params["race_id"], job.job_id
            )
        elif job.type == "enrich_race":
            return tasks_mod.enrich_race_data_task.delay(params["race_id"], job.job_id)
        elif job.type == "batch_collect":
            return tasks_mod.batch_collect_races_task.delay(
                params["race_date"], params["meet"], params["race_numbers"], job.job_id
            )
        elif job.type == "full_pipeline":
            return tasks_mod.full_pipeline_task.delay(
                params["race_date"], params["meet"], params["race_no"], job.job_id
            )
        else:
            raise ValueError(f"Unknown job type: {job.type}")

    async def get_job(self, job_id: str, db: AsyncSession) -> Job | None:
        """작업 조회"""
        result = await db.execute(select(Job).where(Job.job_id == job_id))
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

        # Celery 태스크 상태 확인 (선택적)
        celery_status: dict[str, Any] | None = None
        if job.task_id:
            celery_app, AsyncResult = self._get_celery_components()
            if celery_app and AsyncResult:
                try:
                    task_result = AsyncResult(job.task_id, app=celery_app)
                    celery_status = {
                        "state": task_result.state,
                        "info": (
                            task_result.info
                            if isinstance(task_result.info, dict)
                            else str(task_result.info)
                        ),
                        "ready": task_result.ready(),
                        "successful": (
                            task_result.successful() if task_result.ready() else None
                        ),
                    }
                except Exception as e:
                    logger.warning(f"Failed to get Celery status: {e}")
            else:
                logger.debug("Celery not available; skipping status fetch")

        # 작업 진행률 계산
        progress = self._calculate_progress(job, celery_status)

        return {
            "job_id": job.job_id,
            "type": job.type,
            "status": job.status,
            "progress": progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": getattr(job, "error_message", None),
            "celery_status": celery_status,
            "parameters": job.parameters,
        }

    def _calculate_progress(
        self, job: Job, celery_status: dict[str, Any] | None
    ) -> int:
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
                if celery_status and "info" in celery_status:
                    info = celery_status["info"]
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
        return result.scalars().all()

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
        query = select(Job)

        # 필터 적용
        filters = []
        if user_id:
            filters.append(Job.created_by == user_id)
        if job_type:
            filters.append(Job.type == job_type)
        if status:
            filters.append(Job.status == status)

        if filters:
            query = query.where(and_(*filters))

        # 정렬 및 페이징
        query = query.order_by(desc(Job.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def cancel_job(self, job_id: str, db: AsyncSession) -> bool:
        """
        작업 취소

        Args:
            job_id: 작업 ID
            db: 데이터베이스 세션

        Returns:
            성공 여부
        """
        try:
            job = await self.get_job(job_id, db)

            if not job:
                return False

            if str(job.status) in ["completed", "failed", "cancelled"] or (
                hasattr(job.status, "value")
                and job.status.value in ["completed", "failed", "cancelled"]
            ):
                return False

            # Celery 태스크 취소
            task_id = getattr(job, "task_id", None)
            if task_id:
                celery_app, _ = self._get_celery_components()
                if celery_app:
                    try:
                        celery_app.control.revoke(task_id, terminate=True)
                    except Exception as e:
                        logger.warning(f"Failed to revoke Celery task: {e}")
                else:
                    logger.debug("Celery not available; skipping revoke")

            # 상태 업데이트
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()

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
            cutoff_date = datetime.utcnow() - timedelta(days=days)

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
                db.delete(job)

            await db.commit()

            logger.info(f"Cleaned up {count} old jobs")

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
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_result = await db.execute(
                base_query.where(Job.created_at >= yesterday)
            )
            recent_jobs = len(recent_result.scalars().all())

            return {
                "total_jobs": total_jobs,
                "status_counts": status_counts,
                "type_counts": type_counts,
                "recent_jobs_24h": recent_jobs,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get job statistics", error=str(e))
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
