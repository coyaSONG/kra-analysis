"""
Celery 애플리케이션 설정
비동기 작업 큐 관리
"""

from celery import Celery
from celery.schedules import crontab
import structlog

from config import settings

logger = structlog.get_logger()

# Celery 앱 생성
celery_app = Celery(
    "kra_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "tasks.collection_tasks",
        "tasks.analysis_tasks",
        "tasks.prediction_tasks"
    ]
)

# Celery 설정
celery_app.conf.update(
    # 작업 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    
    # 작업 큐 설정
    task_default_queue=settings.celery_task_default_queue,
    task_acks_late=settings.celery_task_acks_late,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    
    # 결과 백엔드 설정
    result_expires=3600,  # 1시간
    result_persistent=True,
    
    # 작업 실행 설정
    task_soft_time_limit=600,  # 10분
    task_time_limit=900,  # 15분
    
    # 작업 재시도 설정
    task_autoretry_for=(Exception,),
    task_retry_kwargs={
        "max_retries": 3,
        "countdown": 60,  # 1분 후 재시도
    },
    
    # 로깅 설정
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    
    # 성능 설정
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
)

# Beat 스케줄 설정 (정기 작업)
celery_app.conf.beat_schedule = {
    # 매일 오전 6시 전날 데이터 수집
    "daily-collection": {
        "task": "tasks.collection_tasks.daily_collection_task",
        "schedule": crontab(hour=6, minute=0),
        "options": {
            "queue": "scheduled",
            "priority": 5,
        }
    },
    
    # 매시간 캐시 정리
    "hourly-cache-cleanup": {
        "task": "tasks.maintenance.cleanup_old_cache",
        "schedule": crontab(minute=0),
        "options": {
            "queue": "maintenance",
            "priority": 1,
        }
    },
    
    # 매주 월요일 오전 9시 주간 분석
    "weekly-analysis": {
        "task": "tasks.analysis_tasks.weekly_performance_analysis",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
        "options": {
            "queue": "analysis",
            "priority": 3,
        }
    },
    
    # 매일 자정 작업 상태 정리
    "daily-job-cleanup": {
        "task": "tasks.maintenance.cleanup_old_jobs",
        "schedule": crontab(hour=0, minute=0),
        "options": {
            "queue": "maintenance",
            "priority": 1,
        }
    },
}

# 라우팅 설정 (작업별 큐 분배)
celery_app.conf.task_routes = {
    "tasks.collection_tasks.*": {"queue": "collection"},
    "tasks.analysis_tasks.*": {"queue": "analysis"},
    "tasks.prediction_tasks.*": {"queue": "prediction"},
    "tasks.maintenance.*": {"queue": "maintenance"},
}


# Celery 시그널 핸들러
@celery_app.task(bind=True)
def debug_task(self):
    """디버그용 작업"""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}


# 작업 실행 전 후크
from celery.signals import task_prerun, task_postrun, task_failure

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    """작업 실행 전 로깅"""
    logger.info(
        "Task starting",
        task_name=task.name,
        task_id=task_id
    )


# 작업 성공 후크
@task_postrun.connect
def task_success_handler(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
    """작업 완료 시 로깅"""
    if state == "SUCCESS":
        logger.info(
            "Task completed successfully",
            task_name=task.name,
            task_id=task_id
        )


# 작업 실패 후크
@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, task=None, **kwargs):
    """작업 실패 시 로깅"""
    logger.error(
        "Task failed",
        task_name=task.name if task else "unknown",
        task_id=task_id,
        error=str(exception)
    )


# 필요한 경우 추가 시그널 핸들러를 여기에 추가
# Celery 5.x에서는 task_retry 시그널이 제거되었습니다