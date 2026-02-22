"""Job runner factory helpers."""

from functools import lru_cache

from config import settings
from infrastructure.background_tasks import get_runner_health
from infrastructure.job_runner.base import JobRunner
from infrastructure.job_runner.celery_runner import CeleryJobRunner
from infrastructure.job_runner.inprocess_runner import InProcessJobRunner


def create_job_runner(mode: str | None = None) -> JobRunner:
    selected_mode = (mode or settings.job_runner_mode).lower()
    if selected_mode == "celery":
        return CeleryJobRunner()
    return InProcessJobRunner()


@lru_cache(maxsize=1)
def get_job_runner() -> JobRunner:
    return create_job_runner()


def reset_job_runner_cache() -> None:
    get_job_runner.cache_clear()


def get_job_runner_health() -> dict[str, int | str]:
    runner = get_job_runner()
    if isinstance(runner, CeleryJobRunner):
        return runner.health()
    return get_runner_health()
