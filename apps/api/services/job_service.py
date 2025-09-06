"""
작업 관리 서비스
비동기 작업 생성, 모니터링, 관리
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from celery.result import AsyncResult

from models.database_models import Job, JobLog
from infrastructure.celery_app import celery_app
from tasks.collection_tasks import (
    collect_race_data_task,
    preprocess_race_data_task,
    enrich_race_data_task,
    batch_collect_races_task,
    full_pipeline_task
)

logger = structlog.get_logger()


class JobService:
    """작업 관리 서비스"""
    
    async def create_job(
        self,
        job_type: str,
        parameters: Dict[str, Any],
        user_id: str,
        db: AsyncSession
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
                created_by=user_id
            )
            
            db.add(job)
            await db.commit()
            await db.refresh(job)
            
            logger.info(
                "Job created",
                job_id=job.job_id,
                job_type=job_type,
                user_id=user_id
            )
            
            return job
            
        except Exception as e:
            logger.error("Failed to create job", error=str(e))
            await db.rollback()
            raise
    
    async def start_job(
        self,
        job_id: str,
        db: AsyncSession
    ) -> str:
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
            result = await db.execute(
                select(Job).where(Job.job_id == job_id)
            )
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
            
            logger.info(
                "Job started",
                job_id=job_id,
                task_id=task_result.id
            )
            
            return task_result.id
            
        except Exception as e:
            logger.error("Failed to start job", job_id=job_id, error=str(e))
            await db.rollback()
            raise
    
    async def _dispatch_task(self, job: Job) -> AsyncResult:
        """작업 유형에 따라 Celery 태스크 디스패치"""
        params = job.parameters
        
        if job.type == "collect_race":
            return collect_race_data_task.delay(
                params["race_date"],
                params["meet"],
                params["race_no"],
                job.job_id
            )
        
        elif job.type == "preprocess_race":
            return preprocess_race_data_task.delay(
                params["race_id"],
                job.job_id
            )
        
        elif job.type == "enrich_race":
            return enrich_race_data_task.delay(
                params["race_id"],
                job.job_id
            )
        
        elif job.type == "batch_collect":
            return batch_collect_races_task.delay(
                params["race_date"],
                params["meet"],
                params["race_numbers"],
                job.job_id
            )
        
        elif job.type == "full_pipeline":
            return full_pipeline_task.delay(
                params["race_date"],
                params["meet"],
                params["race_no"],
                job.job_id
            )
        
        else:
            raise ValueError(f"Unknown job type: {job.type}")
    
    async def get_job(
        self,
        job_id: str,
        db: AsyncSession
    ) -> Optional[Job]:
        """작업 조회"""
        result = await db.execute(
            select(Job).where(Job.job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_job_status(
        self,
        job_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
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
        
        # Celery 태스크 상태 확인
        celery_status = None
        if job.task_id:
            try:
                task_result = AsyncResult(job.task_id, app=celery_app)
                celery_status = {
                    "state": task_result.state,
                    "info": task_result.info if isinstance(task_result.info, dict) else str(task_result.info),
                    "ready": task_result.ready(),
                    "successful": task_result.successful() if task_result.ready() else None
                }
            except Exception as e:
                logger.warning(f"Failed to get Celery status: {e}")
        
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
            "error": job.error,
            "celery_status": celery_status,
            "parameters": job.parameters
        }
    
    def _calculate_progress(
        self,
        job: Job,
        celery_status: Optional[Dict[str, Any]]
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
                        completed = sum(1 for v in info["steps"].values() if v == "completed")
                        return 10 + (completed * 30)  # 10-100%
            return 50  # 기본값
        
        return 0
    
    async def get_job_logs(
        self,
        job_id: str,
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[JobLog]:
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
        data: Dict[str, Any],
        db: AsyncSession
    ) -> JobLog:
        """작업 로그 추가"""
        try:
            log = JobLog(
                job_id=job_id,
                level=level,
                message=message,
                log_metadata=data
            )
            
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
        user_id: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Job]:
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
    
    async def cancel_job(
        self,
        job_id: str,
        db: AsyncSession
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
            job = await self.get_job(job_id, db)
            
            if not job:
                return False
            
            if str(job.status) in ["completed", "failed", "cancelled"] or (
                hasattr(job.status, "value") and job.status.value in ["completed", "failed", "cancelled"]
            ):
                return False
            
            # Celery 태스크 취소
            task_id = getattr(job, "task_id", None)
            if task_id:
                try:
                    celery_app.control.revoke(task_id, terminate=True)
                except Exception as e:
                    logger.warning(f"Failed to revoke Celery task: {e}")
            
            # 상태 업데이트
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()
            
            await db.commit()
            
            # 로그 추가
            await self.add_job_log(
                job_id, "warning", "Job cancelled", {}, db
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            await db.rollback()
            return False
    
    async def cleanup_old_jobs(
        self,
        db: AsyncSession,
        days: int = 7
    ) -> int:
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
                        Job.created_at < cutoff_date
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
        self,
        db: AsyncSession,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
            for status in ["pending", "queued", "processing", "completed", "failed", "cancelled"]:
                result = await db.execute(
                    base_query.where(Job.status == status)
                )
                status_counts[status] = len(result.scalars().all())
            
            # 작업 유형별 수
            type_counts = {}
            for job_type in ["collect_race", "preprocess_race", "enrich_race", "batch_collect", "full_pipeline"]:
                result = await db.execute(
                    base_query.where(Job.type == job_type)
                )
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get job statistics", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
