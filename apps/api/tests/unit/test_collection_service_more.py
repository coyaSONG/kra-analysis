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
async def test_preprocess_data_various_values():
    svc = CollectionService(DummyKRA())
    raw = {
        "horses": [
            {"win_odds": "0", "weight": "500", "rating": "80"},
            {"win_odds": "5.5", "weight": "510", "rating": "82"},
            {"win_odds": "abc", "weight": "bad", "rating": None},
        ]
    }
    out = await svc._preprocess_data(raw)
    assert "preprocessing_timestamp" in out
    audit = out["preprocessing_audit"]
    assert audit["rule_schema_version"].startswith(
        "prerace-entry-preprocessing-rules-v1"
    )
    # All entries lack core identifiers (chul_no/hr_no/etc.) so they are excluded.
    assert out["horses"] == []
    assert out["excluded_horses"] == 3


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_race_data_update_path(db_session):
    svc = CollectionService(DummyKRA())
    # Insert initial race
    r = Race(
        race_id="20240719_1_1",
        date="20240719",
        race_date="20240719",
        meet=1,
        race_number=1,
        race_no=1,
        basic_data={"init": True},
        status=DataStatus.PENDING,
        collection_status=DataStatus.PENDING,
    )
    db_session.add(r)
    await db_session.commit()

    data = {
        "date": "20240719",
        "meet": 1,
        "race_number": 1,
        "race_date": "20240719",
        "race_no": 1,
    }
    await svc._save_race_data(data, db_session)

    # Verify updated
    from sqlalchemy import select

    res = await db_session.execute(select(Race).where(Race.race_id == "20240719_1_1"))
    race = res.scalar_one()
    assert race.status == DataStatus.COLLECTED
    assert race.collection_status == DataStatus.COLLECTED
