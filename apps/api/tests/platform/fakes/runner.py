"""
Deterministic background task runners for tests.
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from infrastructure.background_tasks import TaskState


class _BaseTaskRunner:
    def __init__(self):
        self._states: dict[str, dict[str, Any]] = {}
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

    def _make_state(
        self,
        task_id: str,
        state: TaskState,
        *,
        result: Any = None,
        error: str | None = None,
        alive: bool = False,
    ) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "state": state.value,
            "result": result,
            "error": error,
            "alive": alive,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        return self._states.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        state = self._states.get(task_id)
        if state is None or state["state"] in {
            TaskState.COMPLETED.value,
            TaskState.FAILED.value,
            TaskState.CANCELLED.value,
        }:
            return False
        self._stats["cancelled"] += 1
        self._states[task_id] = self._make_state(task_id, TaskState.CANCELLED)
        return True

    def get_task_stats(self) -> dict[str, Any]:
        active_tasks = sum(
            1
            for state in self._states.values()
            if state["state"] in {TaskState.PENDING.value, TaskState.PROCESSING.value}
        )
        return {
            "active_tasks": active_tasks,
            "alive_tasks": active_tasks,
            "stuck_tasks": 0,
            "submitted_tasks": self._stats["submitted"],
            "completed_tasks": self._stats["completed"],
            "failed_tasks": self._stats["failed"],
            "cancelled_tasks": self._stats["cancelled"],
            "status": "healthy",
        }


class InlineTaskRunner(_BaseTaskRunner):
    """Execute tasks immediately in the current event loop."""

    def __init__(self):
        super().__init__()
        self._handles: dict[str, asyncio.Task] = {}

    def submit_task(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> str:
        task_id = str(uuid.uuid4())
        self._stats["submitted"] += 1
        self._states[task_id] = self._make_state(task_id, TaskState.PENDING, alive=True)

        async def _run() -> None:
            self._states[task_id] = self._make_state(
                task_id, TaskState.PROCESSING, alive=True
            )
            try:
                result = await func(*args, **kwargs)
            except asyncio.CancelledError:
                self._stats["cancelled"] += 1
                self._states[task_id] = self._make_state(task_id, TaskState.CANCELLED)
                raise
            except Exception as exc:
                self._stats["failed"] += 1
                error_detail = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
                self._states[task_id] = self._make_state(
                    task_id, TaskState.FAILED, error=error_detail
                )
            else:
                self._stats["completed"] += 1
                self._states[task_id] = self._make_state(
                    task_id, TaskState.COMPLETED, result=result
                )

        self._handles[task_id] = asyncio.create_task(_run())
        return task_id

    async def wait_all(self) -> None:
        if self._handles:
            await asyncio.gather(*self._handles.values(), return_exceptions=True)


class ControlledTaskRunner(_BaseTaskRunner):
    """Queue tasks until the test explicitly drains them."""

    def __init__(self):
        super().__init__()
        self._queue: list[tuple[str, Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]] = []

    def submit_task(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> str:
        task_id = str(uuid.uuid4())
        self._stats["submitted"] += 1
        self._states[task_id] = self._make_state(task_id, TaskState.PENDING, alive=True)
        self._queue.append((task_id, func, args, kwargs))
        return task_id

    async def drain_one(self) -> str | None:
        if not self._queue:
            return None
        task_id, func, args, kwargs = self._queue.pop(0)
        current = self._states.get(task_id)
        if current and current["state"] == TaskState.CANCELLED.value:
            return task_id
        self._states[task_id] = self._make_state(
            task_id, TaskState.PROCESSING, alive=True
        )
        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            self._stats["failed"] += 1
            error_detail = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            self._states[task_id] = self._make_state(
                task_id, TaskState.FAILED, error=error_detail
            )
        else:
            self._stats["completed"] += 1
            self._states[task_id] = self._make_state(
                task_id, TaskState.COMPLETED, result=result
            )
        return task_id

    async def drain_all(self) -> list[str]:
        drained: list[str] = []
        while self._queue:
            task_id = await self.drain_one()
            if task_id is not None:
                drained.append(task_id)
        return drained
