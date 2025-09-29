import pytest

from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService


class DummyKRA(KRAAPIService):
    def __init__(self):
        pass


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_weather_impact():
    svc = CollectionService(DummyKRA())
    heavy = svc._analyze_weather_impact({"track_condition": "heavy"})
    firm = svc._analyze_weather_impact({"track_condition": "firm"})
    default = svc._analyze_weather_impact({})
    assert heavy["track_speed_factor"] < 1 and heavy["stamina_importance"] > 1
    assert firm["track_speed_factor"] > 1 and firm["stamina_importance"] < 1
    assert default["track_speed_factor"] == 1


@pytest.mark.unit
def test_calculate_performance_stats_and_recent_form():
    from services.collection_service import CollectionService

    svc = CollectionService(DummyKRA())
    performances = [
        {"position": 1},
        {"position": 2},
        {"position": 3},
        {"position": 4},
        {"position": 5},
    ]
    stats = svc._calculate_performance_stats(performances)
    assert stats["total_races"] == 5
    assert 0 <= stats["win_rate"] <= 1
    # recent form is a normalized score
    assert 0 <= stats["recent_form"] <= 1
