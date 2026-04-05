import pytest

from infrastructure.background_tasks import TaskState
from tests.platform.fakes import ControlledTaskRunner, InlineTaskRunner


@pytest.mark.asyncio
async def test_inline_task_runner_completes_tasks():
    runner = InlineTaskRunner()

    async def worker(value: int) -> int:
        return value + 1

    task_id = runner.submit_task(worker, 41)
    await runner.wait_all()

    status = await runner.get_task_status(task_id)
    assert status is not None
    assert status["state"] == TaskState.COMPLETED.value
    assert status["result"] == 42


@pytest.mark.asyncio
async def test_controlled_task_runner_exposes_pending_then_completed():
    runner = ControlledTaskRunner()

    async def worker() -> str:
        return "ok"

    task_id = runner.submit_task(worker)
    pending = await runner.get_task_status(task_id)
    assert pending is not None
    assert pending["state"] == TaskState.PENDING.value

    await runner.drain_one()
    completed = await runner.get_task_status(task_id)
    assert completed is not None
    assert completed["state"] == TaskState.COMPLETED.value
    assert completed["result"] == "ok"
