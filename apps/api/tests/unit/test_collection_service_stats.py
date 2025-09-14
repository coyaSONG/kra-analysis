import pytest

from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService


class DummyKRA(KRAAPIService):
    def __init__(self, jockey_payload=None, trainer_payload=None):
        self._j = jockey_payload
        self._t = trainer_payload

    async def get_jockey_info(self, jk_no: str, use_cache: bool = False):
        return self._j

    async def get_trainer_info(self, tr_no: str, use_cache: bool = False):
        return self._t


@pytest.mark.asyncio
async def test_get_jockey_stats_success():
    payload = {
        "response": {
            "body": {
                "items": {
                    "item": {
                        "winRateY": 10,
                        "winRateT": 20,
                        "ord1CntT": 7,
                        "rcCntT": 70,
                        "rcCntY": 12,
                    }
                }
            }
        }
    }
    svc = CollectionService(DummyKRA(jockey_payload=payload))
    stats = await svc._get_jockey_stats("080405", "20240719", None)
    assert stats["recent_win_rate"] == 0.10
    assert stats["career_win_rate"] == 0.20
    assert stats["total_wins"] == 7
    assert stats["total_races"] == 70
    assert stats["recent_races"] == 12


@pytest.mark.asyncio
async def test_get_trainer_stats_success():
    payload = {
        "response": {
            "body": {
                "items": {
                    "item": {
                        "winRateY": 12,
                        "winRateT": 30,
                        "ord1CntT": 9,
                        "rcCntT": 90,
                        "rcCntY": 14,
                        "plcRateT": 40,
                        "meet": "서울",
                    }
                }
            }
        }
    }
    svc = CollectionService(DummyKRA(trainer_payload=payload))
    stats = await svc._get_trainer_stats("070180", "20240719", None)
    assert stats["recent_win_rate"] == 0.12
    assert stats["career_win_rate"] == 0.30
    assert stats["plc_rate"] == 0.40
    assert stats["meet"] == "서울"


@pytest.mark.asyncio
async def test_collect_batch_races_mixed(monkeypatch):
    svc = CollectionService(DummyKRA())

    async def ok(date, meet, no, db):
        return {"race_no": no}

    async def fail(date, meet, no, db):
        raise RuntimeError("boom")

    # patch method on instance
    monkeypatch.setattr(svc, "collect_race_data", ok)
    res1 = await svc.collect_batch_races("20240719", 1, [1], None)
    assert res1[1]["status"] == "success"

    monkeypatch.setattr(svc, "collect_race_data", fail)
    res2 = await svc.collect_batch_races("20240719", 1, [2], None)
    assert res2[2]["status"] == "error"
