"""
Celery 애플리케이션 설정
비동기 작업 큐 관리
"""

import structlog
from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun
from kombu import Exchange, Queue

from config import settings

logger = structlog.get_logger()

# Celery 앱 생성
celery_app = Celery(
    "kra_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "tasks.collection_tasks",
    ],
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
    # 로깅 설정
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    # 성능 설정
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
)

# Beat 스케줄 설정 (정기 작업)
# Beat 스케줄 설정 (정기 작업)
# 현재 저장소에 존재하지 않는 태스크 참조를 제거했습니다.
# 필요한 주기 작업이 준비되면 아래 딕셔너리에 추가하세요.
celery_app.conf.beat_schedule = {}

# 큐/익스체인지 설정 (우선순위 지원)
default_exchange = Exchange("default", type="direct")
celery_app.conf.task_queues = (
    Queue(
        settings.celery_task_default_queue,
        default_exchange,
        routing_key=settings.celery_task_default_queue,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "collection",
        default_exchange,
        routing_key="collection",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "analysis",
        default_exchange,
        routing_key="analysis",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "prediction",
        default_exchange,
        routing_key="prediction",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "maintenance",
        default_exchange,
        routing_key="maintenance",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "scheduled",
        default_exchange,
        routing_key="scheduled",
        queue_arguments={"x-max-priority": 10},
    ),
)
celery_app.conf.task_default_queue = settings.celery_task_default_queue
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = settings.celery_task_default_queue

# 라우팅 설정 (작업별 큐 분배)
# 모든 태스크를 기본 큐로 라우팅하여 워커가 확실히 소비하도록 설정합니다.
celery_app.conf.task_routes = {
    "tasks.collection_tasks.*": {"queue": "collection", "routing_key": "collection"},
    # 향후 다른 모듈이 추가되면 아래 매핑을 확장
    "tasks.analysis_tasks.*": {"queue": "analysis", "routing_key": "analysis"},
    "tasks.prediction_tasks.*": {"queue": "prediction", "routing_key": "prediction"},
    "tasks.maintenance.*": {"queue": "maintenance", "routing_key": "maintenance"},
}


# Celery 시그널 핸들러
@celery_app.task(bind=True)
def debug_task(self):
    """디버그용 작업"""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}


# 작업 실행 전 후크
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    """작업 실행 전 로깅"""
    logger.info("Task starting", task_name=task.name, task_id=task_id)


# 작업 성공 후크
@task_postrun.connect
def task_success_handler(
    sender=None, task_id=None, task=None, retval=None, state=None, **kwargs
):
    """작업 완료 시 로깅"""
    if state == "SUCCESS":
        logger.info("Task completed successfully", task_name=task.name, task_id=task_id)


# 작업 실패 후크
@task_failure.connect
def task_failure_handler(
    sender=None, task_id=None, exception=None, task=None, **kwargs
):
    """작업 실패 시 로깅"""
    logger.error(
        "Task failed",
        task_name=task.name if task else "unknown",
        task_id=task_id,
        error=str(exception),
    )


# 필요한 경우 추가 시그널 핸들러를 여기에 추가
# Celery 5.x에서는 task_retry 시그널이 제거되었습니다
