"""
Lightweight background task runner using asyncio.create_task()
Replaces Celery with in-process async task execution.
Task state is stored in Redis for observability.
"""

import asyncio
import json
import traceback
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Task state enum
# ---------------------------------------------------------------------------


class TaskState(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REDIS_KEY_PREFIX = "bgtask:"
_TASK_STATE_TTL = 3600  # 1 hour
_MAX_RETRIES = 3
_BASE_BACKOFF = 2  # seconds


# ---------------------------------------------------------------------------
# In-memory task registry (asyncio.Task handles)
# ---------------------------------------------------------------------------

_running_tasks: dict[str, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------


def _redis_key(task_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{task_id}"


async def _get_redis():
    """Get the global Redis client (lazy import to avoid circular deps)."""
    from infrastructure.redis_client import redis_client

    return redis_client


async def _save_state(
    task_id: str, state: TaskState, result: Any = None, error: str | None = None
) -> None:
    """Persist task state to Redis."""
    redis = await _get_redis()
    if redis is None:
        logger.warning("Redis unavailable; task state not persisted", task_id=task_id)
        return

    payload = {
        "task_id": task_id,
        "state": state.value,
        "result": result,
        "error": error,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    try:
        await redis.setex(
            _redis_key(task_id), _TASK_STATE_TTL, json.dumps(payload, default=str)
        )
    except Exception as exc:
        logger.warning(
            "Failed to save task state to Redis", task_id=task_id, error=str(exc)
        )


async def _load_state(task_id: str) -> dict[str, Any] | None:
    """Load task state from Redis."""
    redis = await _get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_redis_key(task_id))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(
            "Failed to load task state from Redis", task_id=task_id, error=str(exc)
        )
    return None


# ---------------------------------------------------------------------------
# Core task wrapper with retry logic
# ---------------------------------------------------------------------------


async def _run_with_retries(
    task_id: str,
    func: Callable[..., Coroutine],
    args: tuple,
    kwargs: dict,
) -> Any:
    """Execute *func* with exponential-backoff retries."""
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            await _save_state(task_id, TaskState.PROCESSING)
            logger.info("Task attempt started", task_id=task_id, attempt=attempt + 1)

            result = await func(*args, **kwargs)

            await _save_state(task_id, TaskState.COMPLETED, result=result)
            logger.info("Task completed", task_id=task_id)
            return result

        except asyncio.CancelledError:
            await _save_state(task_id, TaskState.CANCELLED)
            logger.info("Task cancelled", task_id=task_id)
            raise

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Task attempt failed",
                task_id=task_id,
                attempt=attempt + 1,
                error=str(exc),
            )
            if attempt < _MAX_RETRIES - 1:
                backoff = _BASE_BACKOFF ** (attempt + 1)
                await asyncio.sleep(backoff)

    # All retries exhausted
    tb = traceback.format_exception(type(last_exc), last_exc, last_exc.__traceback__)
    error_detail = "".join(tb)
    await _save_state(task_id, TaskState.FAILED, error=error_detail)
    logger.error("Task failed after retries", task_id=task_id, error=str(last_exc))
    raise last_exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def submit_task(
    func: Callable[..., Coroutine],
    *args: Any,
    **kwargs: Any,
) -> str:
    """
    Submit an async coroutine to run in the background.

    Returns:
        task_id (str): A UUID identifying the background task.
    """
    task_id = str(uuid.uuid4())

    async def _wrapper() -> None:
        try:
            await _run_with_retries(task_id, func, args, kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass  # state already saved by _run_with_retries
        finally:
            _running_tasks.pop(task_id, None)

    loop = asyncio.get_running_loop()
    asyncio_task = loop.create_task(_wrapper(), name=f"bgtask-{task_id}")
    _running_tasks[task_id] = asyncio_task

    # Fire-and-forget initial state save
    loop.create_task(_save_state(task_id, TaskState.PENDING))

    logger.info("Task submitted", task_id=task_id, func=func.__name__)
    return task_id


async def get_task_status(task_id: str) -> dict[str, Any] | None:
    """
    Get the current status of a background task.

    Returns:
        A dict with keys: task_id, state, result, error, updated_at
        or None if not found.
    """
    # Check in-memory handle first for live state
    asyncio_task = _running_tasks.get(task_id)

    # Load persisted state from Redis
    state = await _load_state(task_id)

    if state is not None:
        # Enrich with live info
        if asyncio_task is not None:
            state["alive"] = not asyncio_task.done()
        else:
            state["alive"] = False
        return state

    # Fallback: if only in memory (Redis write not yet flushed)
    if asyncio_task is not None:
        return {
            "task_id": task_id,
            "state": TaskState.PROCESSING.value
            if not asyncio_task.done()
            else TaskState.COMPLETED.value,
            "result": None,
            "error": None,
            "alive": not asyncio_task.done(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

    return None


async def cancel_task(task_id: str) -> bool:
    """
    Cancel a running background task.

    Returns:
        True if the task was found and cancellation was requested.
    """
    asyncio_task = _running_tasks.get(task_id)
    if asyncio_task is None:
        return False

    if asyncio_task.done():
        return False

    asyncio_task.cancel()
    await _save_state(task_id, TaskState.CANCELLED)
    logger.info("Task cancellation requested", task_id=task_id)
    return True


async def shutdown_all() -> None:
    """Cancel all running tasks. Call during app shutdown."""
    for task_id, asyncio_task in list(_running_tasks.items()):
        if not asyncio_task.done():
            asyncio_task.cancel()
            logger.info("Cancelling task on shutdown", task_id=task_id)

    # Wait briefly for tasks to finish
    if _running_tasks:
        await asyncio.gather(*_running_tasks.values(), return_exceptions=True)
    _running_tasks.clear()
