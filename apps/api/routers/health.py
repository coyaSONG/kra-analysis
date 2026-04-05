import inspect
import time

from fastapi import APIRouter, Depends

from bootstrap.runtime import AppRuntime, get_runtime
from config import settings
from infrastructure.database import check_database_connection, get_db
from infrastructure.redis_client import get_redis

router = APIRouter()


def get_optional_redis():
    """Return Redis when available, otherwise allow degraded health checks."""
    try:
        return get_redis()
    except RuntimeError:
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
    redis_status = "unavailable"
    if redis is not None and hasattr(redis, "ping"):
        try:
            ping_result = redis.ping()
            if inspect.isawaitable(ping_result):
                await ping_result
            redis_status = "healthy"
        except Exception:
            redis_status = "error"

    background_stats = runtime.observability.get_task_stats()
    return runtime.observability.build_health_snapshot(
        db_ok=db_ok,
        redis_status=redis_status,
        background_status=background_stats["status"],
        version=settings.version,
        now=time.time(),
    )
