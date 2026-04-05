import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from bootstrap.runtime import AppRuntime, get_runtime
from config import settings
from infrastructure.database import check_database_connection, get_db

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(db=Depends(get_db), runtime: AppRuntime = Depends(get_runtime)):
    """Prometheus text format metrics endpoint."""
    if not settings.prometheus_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled",
        )

    db_ok = await check_database_connection(db)
    rendered = runtime.observability.render_metrics(db_ok=db_ok, now=time.time())
    return PlainTextResponse(rendered, media_type="text/plain")
