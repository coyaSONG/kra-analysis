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
async def test_enrich_race_data_with_stats(monkeypatch, db_session):
    svc = CollectionService(DummyKRA())
    # Seed race with basic_data containing two horses
    race_id = "20240719_1_7"
    basic = {
        "race_date": "20240719",
        "meet": 1,
        "race_number": 7,
        "horses": [
            {"hr_no": "H001", "jk_no": "J001", "tr_no": "T001"},
            {"hr_no": "H002"},
        ],
        "weather": {"track_condition": "soft"},
    }
    r = Race(
        race_id=race_id,
        date="20240719",
        race_date="20240719",
        meet=1,
        race_number=7,
        race_no=7,
        basic_data=basic,
        status=DataStatus.COLLECTED,
    )
    db_session.add(r)
    await db_session.commit()

    # Patch helpers
    async def fake_past(horse_no, race_date, db):
        return [{"position": 1}] if horse_no == "H001" else []

    async def fake_jk(jk_no, race_date, db):
        return {"recent_win_rate": 0.1}

    async def fake_tr(tr_no, race_date, db):
        return {"career_win_rate": 0.2}

    monkeypatch.setattr(svc, "_get_horse_past_performances", fake_past)
    monkeypatch.setattr(svc, "_get_jockey_stats", fake_jk)
    monkeypatch.setattr(svc, "_get_trainer_stats", fake_tr)

    enriched = await svc.enrich_race_data(race_id, db_session)
    assert "weather_impact" in enriched
    horses = enriched["horses"]
    # First horse got past_stats from performance; second got default
    assert horses[0]["past_stats"]["wins"] >= 0
    assert "past_stats" in horses[1]
    # Jockey/trainer stats attached
    assert "jockey_stats" in horses[0]
    assert "trainer_stats" in horses[0]


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_enrich_race_data_not_found_raises(db_session):
    svc = CollectionService(DummyKRA())
    with pytest.raises(ValueError):
        await svc.enrich_race_data("non-existent", db_session)
