"""
Minimal runtime and observability facade for the API app.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from config import settings
from infrastructure.background_tasks import get_task_stats
from middleware.logging import get_request_count


@dataclass
class ObservabilityFacade:
    """Expose health and metrics rendering behind one object."""

    process_start_time: float = field(default_factory=time.time)

    def build_health_snapshot(
        self,
        *,
        db_ok: bool,
        redis_ok: bool,
        background_status: str,
        version: str,
        now: float | None = None,
    ) -> dict[str, Any]:
        timestamp = time.time() if now is None else now
        overall_status = (
            "healthy"
            if db_ok and redis_ok and background_status == "healthy"
            else "degraded"
        )
        return {
            "status": overall_status,
            "database": "healthy" if db_ok else "unhealthy",
            "redis": "healthy" if redis_ok else "unhealthy",
            "background_tasks": background_status,
            "timestamp": timestamp,
            "version": version,
        }

    def render_metrics(self, *, db_ok: bool, now: float | None = None) -> str:
        timestamp = time.time() if now is None else now
        uptime_seconds = max(0.0, timestamp - self.process_start_time)
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
        return "\n".join(lines) + "\n"


@dataclass
class AppRuntime:
    """Small runtime object for request handlers and tests."""

    settings: Any
    observability: ObservabilityFacade


_runtime: AppRuntime | None = None


def create_runtime() -> AppRuntime:
    return AppRuntime(settings=settings, observability=ObservabilityFacade())


def get_runtime() -> AppRuntime:
    global _runtime
    if _runtime is None:
        _runtime = create_runtime()
    return _runtime


def set_runtime_for_tests(runtime: AppRuntime | None) -> None:
    """Allow tests to replace the cached runtime."""
    global _runtime
    _runtime = runtime

