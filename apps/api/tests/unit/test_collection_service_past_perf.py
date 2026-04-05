from datetime import UTC, datetime, timedelta

import pytest

from models.database_models import DataStatus, Race
from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService


class DummyKRA(KRAAPIService):
    def __init__(self):
        pass


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_horse_past_performances(db_session):
    svc = CollectionService(DummyKRA())
    # insert past race within 3 months
    race_date = (datetime.now(UTC) - timedelta(days=20)).strftime("%Y%m%d")
    r = Race(
        race_id=f"{race_date}_1_1",
        date=race_date,
        race_date=race_date,
        meet=1,
        race_number=1,
        race_no=1,
        status=DataStatus.COLLECTED,
        result_status=DataStatus.COLLECTED,
        result_data={
            "horses": [
                {
                    "hr_no": "H001",
                    "ord": 1,
                    "win_odds": 2.8,
                    "rating": 80,
                    "weight": 500,
                }
            ]
        },
    )
    db_session.add(r)
    await db_session.commit()

    # Query past performances for this horse
    today = datetime.now(UTC).strftime("%Y%m%d")
    perfs = await svc._get_horse_past_performances("H001", today, db_session)
    assert len(perfs) >= 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_horse_past_performances_accepts_canonical_projection(db_session):
    svc = CollectionService(DummyKRA())
    race_date = (datetime.now(UTC) - timedelta(days=20)).strftime("%Y%m%d")
    r = Race(
        race_id=f"{race_date}_1_2",
        date=race_date,
        race_date=race_date,
        meet=1,
        race_number=2,
        race_no=2,
        status=DataStatus.COLLECTED,
        result_status=DataStatus.COLLECTED,
        result_data={
            "schema_version": 1,
            "top3": [1, 2, 3],
            "horses": [
                {"ord": 1, "chulNo": 1, "hr_no": "H001", "win_odds": 2.8},
                {"ord": 2, "chulNo": 2, "hr_no": "H002", "win_odds": 4.1},
            ],
        },
    )
    db_session.add(r)
    await db_session.commit()

    today = datetime.now(UTC).strftime("%Y%m%d")
    perfs = await svc._get_horse_past_performances("H001", today, db_session)
    assert len(perfs) >= 1
    assert perfs[0]["position"] == 1
