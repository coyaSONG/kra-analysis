"""
Celery 비동기 태스크 - 데이터 수집
백그라운드 데이터 수집 작업
"""

from typing import Dict, Any, List
from datetime import datetime
import asyncio
import structlog

from infrastructure.celery_app import celery_app
from infrastructure.database import async_session_maker
from services.kra_api_service import KRAAPIService
from services.collection_service import CollectionService
from models.database_models import Job, JobLog
from sqlalchemy import select

# Create AsyncSessionLocal alias for backward compatibility
AsyncSessionLocal = async_session_maker

logger = structlog.get_logger()


@celery_app.task(
    name="collect_race_data",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def collect_race_data_task(
    self,
    race_date: str,
    meet: int,
    race_no: int,
    job_id: int = None
) -> Dict[str, Any]:
    """
    경주 데이터 수집 태스크
    
    Args:
        race_date: 경주 날짜
        meet: 경마장 코드
        race_no: 경주 번호
        job_id: 작업 ID
        
    Returns:
        수집 결과
    """
    try:
        # 비동기 함수 실행
        result = asyncio.run(
            _collect_race_data_async(
                race_date, meet, race_no, job_id, self.request.id
            )
        )
        return result
        
    except Exception as e:
        logger.error(
            "Collection task failed",
            task_id=self.request.id,
            error=str(e)
        )
        
        # 재시도
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # 최종 실패
        if job_id:
            asyncio.run(_update_job_status(job_id, "failed", str(e)))
        
        raise


async def _collect_race_data_async(
    race_date: str,
    meet: int,
    race_no: int,
    job_id: int,
    task_id: str
) -> Dict[str, Any]:
    """비동기 수집 로직"""
    async with AsyncSessionLocal() as db:
        try:
            # 작업 상태 업데이트
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)
            
            # 서비스 초기화
            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)
            
            # 데이터 수집
            result = await collection_service.collect_race_data(
                race_date, meet, race_no, db
            )
            
            # 로그 기록
            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully collected race {race_no}",
                    {"race_no": race_no}
                )
            
            # KRA API 클라이언트 종료
            await kra_api.close()
            
            return {
                "status": "success",
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "data": result
            }
            
        except Exception as e:
            logger.error(
                "Async collection failed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                error=str(e)
            )
            
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to collect race {race_no}: {str(e)}",
                    {"race_no": race_no, "error": str(e)}
                )
            
            raise


@celery_app.task(
    name="preprocess_race_data",
    bind=True,
    max_retries=3
)
def preprocess_race_data_task(
    self,
    race_id: str,
    job_id: int = None
) -> Dict[str, Any]:
    """
    경주 데이터 전처리 태스크
    
    Args:
        race_id: 경주 ID
        job_id: 작업 ID
        
    Returns:
        전처리 결과
    """
    try:
        result = asyncio.run(
            _preprocess_race_data_async(
                race_id, job_id, self.request.id
            )
        )
        return result
        
    except Exception as e:
        logger.error(
            "Preprocessing task failed",
            task_id=self.request.id,
            race_id=race_id,
            error=str(e)
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        if job_id:
            asyncio.run(_update_job_status(job_id, "failed", str(e)))
        
        raise


async def _preprocess_race_data_async(
    race_id: str,
    job_id: int,
    task_id: str
) -> Dict[str, Any]:
    """비동기 전처리 로직"""
    async with AsyncSessionLocal() as db:
        try:
            # 작업 상태 업데이트
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)
            
            # 서비스 초기화
            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)
            
            # 전처리 수행
            result = await collection_service.preprocess_race_data(race_id, db)
            
            # 로그 기록
            if job_id:
                await _add_job_log(
                    job_id,
                    "info",
                    f"Successfully preprocessed race {race_id}",
                    {"race_id": race_id}
                )
            
            await kra_api.close()
            
            return {
                "status": "success",
                "race_id": race_id,
                "data": result
            }
            
        except Exception as e:
            logger.error(
                "Async preprocessing failed",
                race_id=race_id,
                error=str(e)
            )
            
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to preprocess race {race_id}: {str(e)}",
                    {"race_id": race_id, "error": str(e)}
                )
            
            raise


@celery_app.task(
    name="enrich_race_data",
    bind=True,
    max_retries=3
)
def enrich_race_data_task(
    self,
    race_id: str,
    job_id: int = None
) -> Dict[str, Any]:
    """
    경주 데이터 강화 태스크
    
    Args:
        race_id: 경주 ID
        job_id: 작업 ID
        
    Returns:
        강화 결과
    """
    try:
        result = asyncio.run(
            _enrich_race_data_async(
                race_id, job_id, self.request.id
            )
        )
        return result
        
    except Exception as e:
        logger.error(
            "Enrichment task failed",
            task_id=self.request.id,
            race_id=race_id,
            error=str(e)
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        if job_id:
            asyncio.run(_update_job_status(job_id, "failed", str(e)))
        
        raise


async def _enrich_race_data_async(
    race_id: str,
    job_id: int,
    task_id: str
) -> Dict[str, Any]:
    """비동기 강화 로직"""
    async with AsyncSessionLocal() as db:
        try:
            # 작업 상태 업데이트
            if job_id:
                await _update_job_status(job_id, "processing", task_id=task_id)
            
            # 서비스 초기화
            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)
            
            # 강화 수행
            result = await collection_service.enrich_race_data(race_id, db)
            
            # 로그 기록
            if job_id:
                await _add_job_log(
                    job_id,
                    "info", 
                    f"Successfully enriched race {race_id}",
                    {"race_id": race_id}
                )
            
            await kra_api.close()
            
            return {
                "status": "success",
                "race_id": race_id,
                "data": result
            }
            
        except Exception as e:
            logger.error(
                "Async enrichment failed",
                race_id=race_id,
                error=str(e)
            )
            
            if job_id:
                await _add_job_log(
                    job_id,
                    "error",
                    f"Failed to enrich race {race_id}: {str(e)}",
                    {"race_id": race_id, "error": str(e)}
                )
            
            raise


@celery_app.task(
    name="batch_collect_races",
    bind=True
)
def batch_collect_races_task(
    self,
    race_date: str,
    meet: int,
    race_numbers: List[int],
    job_id: int = None
) -> Dict[str, Any]:
    """
    여러 경주 일괄 수집 태스크
    
    Args:
        race_date: 경주 날짜
        meet: 경마장 코드
        race_numbers: 경주 번호 리스트
        job_id: 작업 ID
        
    Returns:
        수집 결과
    """
    try:
        # 개별 태스크 생성
        tasks = []
        for race_no in race_numbers:
            task = collect_race_data_task.delay(
                race_date, meet, race_no, job_id
            )
            tasks.append({
                "race_no": race_no,
                "task_id": task.id
            })
        
        return {
            "status": "started",
            "race_date": race_date,
            "meet": meet,
            "tasks": tasks
        }
        
    except Exception as e:
        logger.error(
            "Batch collection task failed",
            error=str(e)
        )
        
        if job_id:
            asyncio.run(_update_job_status(job_id, "failed", str(e)))
        
        raise


@celery_app.task(
    name="full_pipeline",
    bind=True
)
def full_pipeline_task(
    self,
    race_date: str,
    meet: int,
    race_no: int,
    job_id: int = None
) -> Dict[str, Any]:
    """
    전체 파이프라인 실행 태스크
    (수집 → 전처리 → 강화)
    
    Args:
        race_date: 경주 날짜
        meet: 경마장 코드
        race_no: 경주 번호
        job_id: 작업 ID
        
    Returns:
        파이프라인 실행 결과
    """
    try:
        result = asyncio.run(
            _full_pipeline_async(
                race_date, meet, race_no, job_id, self.request.id
            )
        )
        return result
        
    except Exception as e:
        logger.error(
            "Full pipeline failed",
            task_id=self.request.id,
            error=str(e)
        )
        
        if job_id:
            asyncio.run(_update_job_status(job_id, "failed", str(e)))
        
        raise


async def _full_pipeline_async(
    race_date: str,
    meet: int,
    race_no: int,
    job_id: int,
    task_id: str
) -> Dict[str, Any]:
    """비동기 전체 파이프라인"""
    async with AsyncSessionLocal() as db:
        try:
            # 서비스 초기화
            kra_api = KRAAPIService()
            collection_service = CollectionService(kra_api)
            
            # 1. 수집
            if job_id:
                await _add_job_log(
                    job_id, "info", "Starting data collection", {"step": "collect"}
                )
            
            collect_result = await collection_service.collect_race_data(
                race_date, meet, race_no, db
            )
            
            # race_id 찾기
            from sqlalchemy import and_
            from models.database_models import Race
            
            result = await db.execute(
                select(Race).where(
                    and_(
                        Race.race_date == race_date,
                        Race.meet == meet,
                        Race.race_no == race_no
                    )
                )
            )
            race = result.scalar_one_or_none()
            
            if not race:
                raise ValueError("Race not found after collection")
            
            race_id = race.id
            
            # 2. 전처리
            if job_id:
                await _add_job_log(
                    job_id, "info", "Starting preprocessing", {"step": "preprocess"}
                )
            
            preprocess_result = await collection_service.preprocess_race_data(
                race_id, db
            )
            
            # 3. 강화
            if job_id:
                await _add_job_log(
                    job_id, "info", "Starting enrichment", {"step": "enrich"}
                )
            
            enrich_result = await collection_service.enrich_race_data(
                race_id, db
            )
            
            # 완료
            if job_id:
                await _update_job_status(job_id, "completed")
                await _add_job_log(
                    job_id, "info", "Pipeline completed successfully", 
                    {"race_id": race_id}
                )
            
            await kra_api.close()
            
            return {
                "status": "success",
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "race_id": race_id,
                "steps": {
                    "collect": "completed",
                    "preprocess": "completed",
                    "enrich": "completed"
                }
            }
            
        except Exception as e:
            logger.error(
                "Full pipeline async failed",
                error=str(e)
            )
            
            if job_id:
                await _add_job_log(
                    job_id, "error", f"Pipeline failed: {str(e)}", 
                    {"error": str(e)}
                )
            
            raise


# 헬퍼 함수들
async def _update_job_status(
    job_id: int,
    status: str,
    error: str = None,
    task_id: str = None
):
    """작업 상태 업데이트"""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                job.status = status
                job.updated_at = datetime.utcnow()
                
                if error:
                    job.error = error
                if task_id:
                    job.task_id = task_id
                if status == "completed":
                    job.completed_at = datetime.utcnow()
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")


async def _add_job_log(
    job_id: int,
    level: str,
    message: str,
    data: Dict[str, Any] = None
):
    """작업 로그 추가"""
    async with AsyncSessionLocal() as db:
        try:
            log = JobLog(
                job_id=job_id,
                level=level,
                message=message,
                data=data or {}
            )
            db.add(log)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to add job log: {e}")