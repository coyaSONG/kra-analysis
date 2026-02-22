"""Job runner abstraction used by JobService."""

from abc import ABC, abstractmethod
from typing import Any

from models.database_models import Job


class JobRunner(ABC):
    """Background job execution abstraction."""

    @abstractmethod
    def submit(self, job: Job) -> str:
        """Submit a job and return a runner task id."""

    @abstractmethod
    async def status(self, task_id: str) -> dict[str, Any] | None:
        """Get task status from the runner backend."""

    @abstractmethod
    async def cancel(self, task_id: str) -> bool:
        """Cancel a task in the runner backend."""
