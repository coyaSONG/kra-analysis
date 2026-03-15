from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from models.database_models import DataStatus, Job, JobLog, JobStatus, JobType, Race
from tasks import async_tasks


@pytest.fixture
def patch_async_tasks_session_maker(monkeypatch, test_db_engine):
    session_maker = async_sessionmaker(
        test_db_engine,
        expire_on_commit=False,
    )
    monkeypatch.setattr(async_tasks, "async_session_maker", session_maker)
    return session_maker


async def _create_job(session_maker, job_id: str, job_type: JobType) -> None:
    async with session_maker() as session:
        session.add(
            Job(
                job_id=job_id,
                type=job_type,
                status=JobStatus.PENDING,
                created_by="tester",
                parameters={},
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()


class _FakeKRA:
    instances: list["_FakeKRA"] = []

    def __init__(self):
        self.closed = False
        self.__class__.instances.append(self)

    async def close(self):
        self.closed = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_race_data_updates_job_and_writes_log(
    patch_async_tasks_session_maker, monkeypatch
):
    await _create_job(
        patch_async_tasks_session_maker, "job-collect-success", JobType.COLLECTION
    )
    _FakeKRA.instances = []

    class FakeCollectionService:
        def __init__(self, kra_api):
            self.kra_api = kra_api

        async def collect_race_data(self, race_date, meet, race_no, db):
            return {
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "horses": [{"hr_no": "001"}],
            }

    monkeypatch.setattr(async_tasks, "KRAAPIService", _FakeKRA)
    monkeypatch.setattr(async_tasks, "CollectionService", FakeCollectionService)

    result = await async_tasks.collect_race_data(
        "20240719",
        1,
        3,
        job_id="job-collect-success",
        task_id="task-collect-success",
    )

    assert result["status"] == "success"
    assert result["data"]["race_no"] == 3

    async with patch_async_tasks_session_maker() as session:
        job = (
            await session.execute(
                select(Job).where(Job.job_id == "job-collect-success")
            )
        ).scalar_one()
        logs = (
            (
                await session.execute(
                    select(JobLog).where(JobLog.job_id == "job-collect-success")
                )
            )
            .scalars()
            .all()
        )

    assert job.status == JobStatus.COMPLETED
    assert job.task_id == "task-collect-success"
    assert job.result["status"] == "success"
    assert len(logs) == 1
    assert logs[0].level == "info"
    assert logs[0].log_metadata == {"race_no": 3}
    assert _FakeKRA.instances[0].closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_race_data_marks_job_failed_on_service_error(
    patch_async_tasks_session_maker, monkeypatch
):
    await _create_job(
        patch_async_tasks_session_maker, "job-collect-fail", JobType.COLLECTION
    )
    _FakeKRA.instances = []

    class FakeCollectionService:
        def __init__(self, kra_api):
            self.kra_api = kra_api

        async def collect_race_data(self, race_date, meet, race_no, db):
            raise RuntimeError("collection exploded")

    monkeypatch.setattr(async_tasks, "KRAAPIService", _FakeKRA)
    monkeypatch.setattr(async_tasks, "CollectionService", FakeCollectionService)

    with pytest.raises(RuntimeError, match="collection exploded"):
        await async_tasks.collect_race_data(
            "20240719",
            1,
            4,
            job_id="job-collect-fail",
            task_id="task-collect-fail",
        )

    async with patch_async_tasks_session_maker() as session:
        job = (
            await session.execute(select(Job).where(Job.job_id == "job-collect-fail"))
        ).scalar_one()
        logs = (
            (
                await session.execute(
                    select(JobLog).where(JobLog.job_id == "job-collect-fail")
                )
            )
            .scalars()
            .all()
        )

    assert job.status == JobStatus.FAILED
    assert job.error_message == "collection exploded"
    assert len(logs) == 1
    assert logs[0].level == "error"
    assert logs[0].log_metadata["race_no"] == 4
    assert logs[0].log_metadata["error"] == "collection exploded"
    assert _FakeKRA.instances[0].closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_collect_marks_job_completed_when_all_items_succeed(
    patch_async_tasks_session_maker, monkeypatch
):
    await _create_job(
        patch_async_tasks_session_maker, "job-batch-success", JobType.BATCH
    )
    calls = []

    async def fake_collect_race_data(
        race_date, meet, race_no, job_id=None, task_id=None, manage_job_status=True
    ):
        calls.append(
            {
                "race_date": race_date,
                "meet": meet,
                "race_no": race_no,
                "job_id": job_id,
                "task_id": task_id,
                "manage_job_status": manage_job_status,
            }
        )
        return {"status": "success", "race_no": race_no}

    monkeypatch.setattr(async_tasks, "collect_race_data", fake_collect_race_data)

    result = await async_tasks.batch_collect(
        "20240719",
        1,
        [1, 2, 3],
        job_id="job-batch-success",
        task_id="task-batch-success",
    )

    assert result["status"] == "completed"
    assert result["errors"] == []
    assert [item["race_no"] for item in result["results"]] == [1, 2, 3]
    assert all(call["manage_job_status"] is False for call in calls)

    async with patch_async_tasks_session_maker() as session:
        job = (
            await session.execute(select(Job).where(Job.job_id == "job-batch-success"))
        ).scalar_one()

    assert job.status == JobStatus.COMPLETED
    assert job.result["status"] == "completed"
    assert job.error_message is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_pipeline_runs_all_steps_and_updates_job(
    patch_async_tasks_session_maker, monkeypatch
):
    await _create_job(
        patch_async_tasks_session_maker, "job-pipeline-success", JobType.COLLECTION
    )
    _FakeKRA.instances = []
    step_calls = []

    class FakeCollectionService:
        def __init__(self, kra_api):
            self.kra_api = kra_api

        async def collect_race_data(self, race_date, meet, race_no, db):
            step_calls.append("collect")
            db.add(
                Race(
                    race_id="race-20240719-1-9",
                    date=race_date,
                    meet=meet,
                    race_number=race_no,
                    collection_status=DataStatus.COLLECTED,
                    basic_data={"race_no": race_no},
                )
            )
            await db.flush()

        async def preprocess_race_data(self, race_id, db):
            step_calls.append(("preprocess", race_id))
            return {"preprocessed": True}

        async def enrich_race_data(self, race_id, db):
            step_calls.append(("enrich", race_id))
            return {"enriched": True}

    monkeypatch.setattr(async_tasks, "KRAAPIService", _FakeKRA)
    monkeypatch.setattr(async_tasks, "CollectionService", FakeCollectionService)

    result = await async_tasks.full_pipeline(
        "20240719",
        1,
        9,
        job_id="job-pipeline-success",
        task_id="task-pipeline-success",
    )

    assert result["status"] == "success"
    assert result["race_id"] == "race-20240719-1-9"
    assert result["steps"] == {
        "collect": "completed",
        "preprocess": "completed",
        "enrich": "completed",
    }
    assert step_calls == [
        "collect",
        ("preprocess", "race-20240719-1-9"),
        ("enrich", "race-20240719-1-9"),
    ]

    async with patch_async_tasks_session_maker() as session:
        job = (
            await session.execute(
                select(Job).where(Job.job_id == "job-pipeline-success")
            )
        ).scalar_one()
        logs = (
            (
                await session.execute(
                    select(JobLog).where(JobLog.job_id == "job-pipeline-success")
                )
            )
            .scalars()
            .all()
        )

    assert job.status == JobStatus.COMPLETED
    assert job.result["race_id"] == "race-20240719-1-9"
    assert [log.message for log in logs] == [
        "Starting data collection",
        "Starting preprocessing",
        "Starting enrichment",
        "Pipeline completed successfully",
    ]
    assert _FakeKRA.instances[0].closed is True
