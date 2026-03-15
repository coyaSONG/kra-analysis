import time

from fastapi import APIRouter, Depends

from config import settings
from infrastructure.background_tasks import get_task_stats
from infrastructure.database import check_database_connection, get_db
from infrastructure.redis_client import check_redis_connection, get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """간단한 헬스체크"""
    return {"status": "healthy", "timestamp": time.time()}


@router.get("/health/detailed")
async def detailed_health_check(redis=Depends(get_redis), db=Depends(get_db)):
    """의존성 상태를 포함한 상세 헬스체크"""
    db_ok = await check_database_connection(db)
    redis_ok = False
    try:
        if redis:
            if hasattr(redis, "ping"):
                try:
                    await redis.ping()
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
    background_status = background_stats["status"]

    if db_ok and redis_ok and background_status == "healthy":
        overall_status = "healthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "database": "healthy" if db_ok else "unhealthy",
        "redis": "healthy" if redis_ok else "unhealthy",
        "background_tasks": background_status,
        "timestamp": time.time(),
        "version": settings.version,
    }
