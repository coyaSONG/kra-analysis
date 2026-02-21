from datetime import UTC, datetime

import pytest

from models.database_models import DataStatus, Job, JobStatus, JobType, Race
from services.collection_status_diagnostics import gather_collection_diagnostics


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gather_collection_diagnostics_empty(db_session):
    diagnostics = await gather_collection_diagnostics(
        db_session, race_date="20240719", meet=1
    )

    assert diagnostics["db_ok"] is True
    assert diagnostics["tables"]["jobs"] is True
    assert diagnostics["tables"]["races"] is True
    assert diagnostics["job_status_counts"] == {}
    assert diagnostics["collection_status"]["total_races"] == 0
    assert diagnostics["collection_status"]["status"] == "pending"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_gather_collection_diagnostics_with_rows(db_session):
    db_session.add_all(
        [
            Job(
                type=JobType.COLLECTION,
                status=JobStatus.COMPLETED,
                created_by="tester",
                parameters={},
            ),
            Job(
                type=JobType.COLLECTION,
                status=JobStatus.FAILED,
                created_by="tester",
                parameters={},
            ),
            Race(
                race_id="20240719_1_1",
                date="20240719",
                meet=1,
                race_number=1,
                collection_status=DataStatus.COLLECTED,
                enrichment_status=DataStatus.PENDING,
                updated_at=datetime.now(UTC),
            ),
            Race(
                race_id="20240719_1_2",
                date="20240719",
                meet=1,
                race_number=2,
                collection_status=DataStatus.COLLECTED,
                enrichment_status=DataStatus.ENRICHED,
                updated_at=datetime.now(UTC),
            ),
        ]
    )
    await db_session.commit()

    diagnostics = await gather_collection_diagnostics(
        db_session, race_date="20240719", meet=1
    )

    assert diagnostics["job_status_counts"]["completed"] == 1
    assert diagnostics["job_status_counts"]["failed"] == 1
    assert diagnostics["collection_status"]["total_races"] == 2
    assert diagnostics["collection_status"]["collected_races"] == 2
    assert diagnostics["collection_status"]["enriched_races"] == 1
    assert diagnostics["collection_status"]["status"] == "running"
