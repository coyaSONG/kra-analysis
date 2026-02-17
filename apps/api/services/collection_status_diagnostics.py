"""
Collection status diagnostics helpers.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.database_models import Job
from services.collection_service import CollectionService


def _enum_to_str(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


async def gather_collection_diagnostics(
    db: AsyncSession, race_date: str | None = None, meet: int | None = None
) -> dict[str, Any]:
    """Gather database + collection status diagnostics for operators."""
    await db.execute(text("SELECT 1"))

    tables = {}
    for table_name in ("jobs", "races"):
        try:
            await db.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
            tables[table_name] = True
        except Exception:
            tables[table_name] = False

    job_rows = await db.execute(select(Job.status, func.count()).group_by(Job.status))
    job_status_counts = {
        _enum_to_str(status): int(count) for status, count in job_rows.all()
    }

    collection_status = None
    if race_date is not None and meet is not None:
        collection_status = await CollectionService.get_collection_status(
            db, race_date, meet
        )

    return {
        "db_ok": True,
        "checked_at": datetime.now(UTC).isoformat(),
        "tables": tables,
        "job_status_counts": job_status_counts,
        "collection_status": collection_status,
    }
