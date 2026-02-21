import pytest

from services import collection_enrichment as ce


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enrich_data_skips_past_fetch_when_horse_number_missing():
    async def fail_if_called(horse_no, race_date, db):
        raise AssertionError("get_horse_past_performances should not be called")

    async def fake_jockey_stats(jockey_no, race_date, db):
        return {"recent_win_rate": 0.1}

    async def fake_trainer_stats(trainer_no, race_date, db):
        return {"career_win_rate": 0.2}

    data = {
        "race_date": "20240719",
        "horses": [{"jk_no": "J001", "tr_no": "T001"}],
        "weather": {"track_condition": "firm"},
    }

    out = await ce.enrich_data(
        data,
        db=None,
        get_horse_past_performances=fail_if_called,
        calculate_performance_stats_fn=ce.calculate_performance_stats,
        get_default_stats_fn=ce.get_default_stats,
        get_jockey_stats=fake_jockey_stats,
        get_trainer_stats=fake_trainer_stats,
        analyze_weather_impact_fn=ce.analyze_weather_impact,
    )

    horse = out["horses"][0]
    assert horse["past_stats"]["total_races"] == 0
    assert horse["jockey_stats"]["recent_win_rate"] == 0.1
    assert horse["trainer_stats"]["career_win_rate"] == 0.2
    assert out["weather_impact"]["track_speed_factor"] == 1.05
