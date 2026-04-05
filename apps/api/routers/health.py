import inspect
import time

from fastapi import APIRouter, Depends

from bootstrap.runtime import AppRuntime, get_runtime
from config import settings
from infrastructure.background_tasks import get_task_stats
from infrastructure.database import check_database_connection, get_db
from infrastructure.redis_client import check_redis_connection, get_redis

router = APIRouter()


def get_optional_redis():
    """Return Redis when available, otherwise allow degraded health checks."""
    try:
        return get_redis()
    except Exception:
        return None


@router.get("/health")
async def health_check():
    """간단한 헬스체크"""
    return {"status": "healthy", "timestamp": time.time()}


@router.get("/health/detailed")
async def detailed_health_check(
    redis=Depends(get_optional_redis),
    db=Depends(get_db),
    runtime: AppRuntime = Depends(get_runtime),
):
    """의존성 상태를 포함한 상세 헬스체크"""
    db_ok = await check_database_connection(db)
    redis_ok = False
    try:
        if redis:
            if hasattr(redis, "ping"):
                try:
                    ping_result = redis.ping()
                    if inspect.isawaitable(ping_result):
                        await ping_result
                    redis_ok = True
                except Exception:
                    redis_ok = False
            else:
                redis_ok = True
        else:
            redis_ok = await check_redis_connection()
    except Exception:
        redis_ok = False

    background_stats = get_task_stats()
    return runtime.observability.build_health_snapshot(
        db_ok=db_ok,
        redis_ok=redis_ok,
        background_status=background_stats["status"],
        version=settings.version,
        now=time.time(),
    )
