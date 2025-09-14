import pytest

from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService


class DummyKRA(KRAAPIService):
    def __init__(self, raise_j=False):
        self.raise_j = raise_j

    async def get_jockey_info(self, *a, **k):
        if self.raise_j:
            raise RuntimeError("jk err")
        return {}

    async def get_trainer_info(self, *a, **k):
        return {"response": {"body": {"items": {}}}}


@pytest.mark.asyncio
async def test_get_horse_past_performances_bad_date(db_session):
    svc = CollectionService(DummyKRA())
    out = await svc._get_horse_past_performances("H001", "BADDATE", db_session)
    assert out == []


@pytest.mark.asyncio
async def test_get_jockey_stats_exception_path():
    svc = CollectionService(DummyKRA(raise_j=True))
    stats = await svc._get_jockey_stats("J001", "20240719", None)
    assert stats["recent_win_rate"] == 0.15


@pytest.mark.asyncio
async def test_get_trainer_stats_default_path():
    svc = CollectionService(DummyKRA())
    stats = await svc._get_trainer_stats("T001", "20240719", None)
    # payload had no items -> defaults
    assert stats["career_win_rate"] == 0.16


@pytest.mark.asyncio
async def test_enrich_data_empty_horses():
    svc = CollectionService(DummyKRA())
    data = {"race_date": "20240719", "meet": 1, "horses": [], "weather": {}}
    out = await svc._enrich_data(data, None)
    assert out["horses"] == [] and "weather_impact" in out
