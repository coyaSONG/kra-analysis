from types import SimpleNamespace
from unittest.mock import patch

import pytest

from services.job_service import JobService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_uses_dispatch_table_for_supported_type():
    service = JobService()

    with patch(
        "services.job_service.submit_task", return_value="task-id"
    ) as mock_submit:
        job = SimpleNamespace(
            type="collect_race",
            parameters={"race_date": "20240719", "meet": 1, "race_no": 3},
            job_id="job-1",
        )

        result = await service._dispatch_task(job)

    assert result == "task-id"
    submitted_args = mock_submit.call_args.args
    assert submitted_args[1:] == ("20240719", 1, 3, "job-1")


@pytest.mark.unit
def test_normalize_dispatch_job_type_accepts_batch_alias():
    service = JobService()

    assert service._normalize_dispatch_job_type("batch") == "batch_collect"
    assert service._normalize_dispatch_job_type("batch_collect") == "batch_collect"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_task_raises_for_unknown_type():
    service = JobService()
    job = SimpleNamespace(type="unknown", parameters={}, job_id="job-1")

    with pytest.raises(ValueError, match="Unknown job type: unknown"):
        await service._dispatch_task(job)
