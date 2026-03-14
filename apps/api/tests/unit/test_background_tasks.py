import asyncio
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from infrastructure import background_tasks


@pytest_asyncio.fixture(autouse=True)
async def cleanup_background_tasks():
    background_tasks._running_tasks.clear()
    yield
    tasks = list(background_tasks._running_tasks.values())
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    background_tasks._running_tasks.clear()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_task_registers_task_and_saves_states(monkeypatch):
    task_id = "task-submit-123"
    save_state = AsyncMock()
    started = asyncio.Event()
    finished = asyncio.Event()

    async def worker(value):
        started.set()
        await finished.wait()
        return value * 2

    monkeypatch.setattr(background_tasks.uuid, "uuid4", lambda: task_id)
    monkeypatch.setattr(background_tasks, "_save_state", save_state)

    submitted_task_id = background_tasks.submit_task(worker, 21)
    assert submitted_task_id == task_id
    assert task_id in background_tasks._running_tasks

    wrapper_task = background_tasks._running_tasks[task_id]
    await started.wait()
    finished.set()
    await wrapper_task

    saved_states = [call.args[1] for call in save_state.await_args_list]
    assert background_tasks.TaskState.PENDING in saved_states
    assert background_tasks.TaskState.PROCESSING in saved_states
    assert any(
        call.args[:2] == (task_id, background_tasks.TaskState.COMPLETED)
        and call.kwargs["result"] == 42
        for call in save_state.await_args_list
    )
    assert task_id not in background_tasks._running_tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_status_returns_persisted_state_with_alive_flag(monkeypatch):
    wait_forever = asyncio.Event()
    task = asyncio.create_task(wait_forever.wait())
    background_tasks._running_tasks["task-status-live"] = task

    monkeypatch.setattr(
        background_tasks,
        "_load_state",
        AsyncMock(
            return_value={
                "task_id": "task-status-live",
                "state": background_tasks.TaskState.PROCESSING.value,
                "result": None,
                "error": None,
                "updated_at": "2026-03-14T00:00:00+00:00",
            }
        ),
    )

    status = await background_tasks.get_task_status("task-status-live")

    assert status == {
        "task_id": "task-status-live",
        "state": "processing",
        "result": None,
        "error": None,
        "updated_at": "2026-03-14T00:00:00+00:00",
        "alive": True,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_status_falls_back_to_in_memory_state(monkeypatch):
    wait_forever = asyncio.Event()
    task = asyncio.create_task(wait_forever.wait())
    background_tasks._running_tasks["task-memory-only"] = task

    monkeypatch.setattr(background_tasks, "_load_state", AsyncMock(return_value=None))

    status = await background_tasks.get_task_status("task-memory-only")

    assert status is not None
    assert status["task_id"] == "task-memory-only"
    assert status["state"] == background_tasks.TaskState.PROCESSING.value
    assert status["alive"] is True
    assert status["result"] is None
    assert status["error"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_cancels_running_task_and_persists_state(monkeypatch):
    save_state = AsyncMock()

    async def worker():
        await asyncio.Event().wait()

    task = asyncio.create_task(worker())
    await asyncio.sleep(0)
    background_tasks._running_tasks["task-cancel-live"] = task

    monkeypatch.setattr(background_tasks, "_save_state", save_state)

    cancelled = await background_tasks.cancel_task("task-cancel-live")

    assert cancelled is True
    with pytest.raises(asyncio.CancelledError):
        await task
    save_state.assert_awaited_once_with(
        "task-cancel-live", background_tasks.TaskState.CANCELLED
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_returns_false_for_missing_or_completed_tasks(monkeypatch):
    save_state = AsyncMock()
    monkeypatch.setattr(background_tasks, "_save_state", save_state)

    assert await background_tasks.cancel_task("missing-task") is False

    completed_task = asyncio.create_task(asyncio.sleep(0))
    await completed_task
    background_tasks._running_tasks["done-task"] = completed_task

    assert await background_tasks.cancel_task("done-task") is False
    save_state.assert_not_awaited()
