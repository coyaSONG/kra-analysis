import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from config import settings
from infrastructure.background_tasks import get_task_stats
from infrastructure.database import check_database_connection, get_db
from middleware.logging import get_request_count

router = APIRouter()

_PROCESS_START_TIME = time.time()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(db=Depends(get_db)):
    """Prometheus text format metrics endpoint."""
    if not settings.prometheus_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled",
        )

    uptime_seconds = max(0.0, time.time() - _PROCESS_START_TIME)
    db_ok = await check_database_connection(db)
    task_stats = get_task_stats()

    lines = [
        "# HELP kra_requests_total Total HTTP requests processed",
        "# TYPE kra_requests_total counter",
        f"kra_requests_total {get_request_count()}",
        "# HELP kra_background_tasks_active Current active background tasks",
        "# TYPE kra_background_tasks_active gauge",
        f"kra_background_tasks_active {task_stats['active_tasks']}",
        "# HELP kra_background_tasks_failed_total Total failed background tasks",
        "# TYPE kra_background_tasks_failed_total counter",
        f"kra_background_tasks_failed_total {task_stats['failed_tasks']}",
        "# HELP kra_database_up Database connectivity status",
        "# TYPE kra_database_up gauge",
        f"kra_database_up {1 if db_ok else 0}",
        "# HELP kra_uptime_seconds Process uptime in seconds",
        "# TYPE kra_uptime_seconds gauge",
        f"kra_uptime_seconds {uptime_seconds:.2f}",
    ]

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")
