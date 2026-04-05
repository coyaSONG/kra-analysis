import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation import data_loading


class FakeDBClient:
    def load_race_basic_data(self, race_id):
        assert race_id == "race-1"
        return {"raw": True}

    def get_past_top3_stats_for_race(self, hr_nos, race_date, lookback_days):
        assert hr_nos == ["001"]
        assert race_date == "20240719"
        assert lookback_days == 90
        return {"001": {"wins": 3}}


def test_load_race_data_builds_normalized_payload(monkeypatch):
    def fake_convert(_basic_data):
        return {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "chulNo": 1,
                                "hrName": "Alpha",
                                "hrNo": "001",
                                "jkName": "J One",
                                "jkNo": "J1",
                                "trName": "T One",
                                "trNo": "T1",
                                "winOdds": 2.5,
                                "plcOdds": 1.1,
                                "rating": 85,
                                "rank": "A",
                                "age": 4,
                                "sex": "M",
                                "rcDate": "20240719",
                                "rcNo": 7,
                                "rcDist": 1200,
                                "meet": 1,
                                "track": "dry",
                                "weather": "sunny",
                            },
                            {
                                "chulNo": 2,
                                "hrName": "Excluded",
                                "hrNo": "002",
                                "jkName": "J Two",
                                "jkNo": "J2",
                                "trName": "T Two",
                                "trNo": "T2",
                                "winOdds": 0,
                                "rcDate": "20240719",
                                "rcNo": 7,
                                "rcDist": 1200,
                                "meet": 1,
                            },
                        ]
                    }
                }
            }
        }

    def fake_features(horses):
        for horse in horses:
            horse["features_applied"] = True
        return horses

    monkeypatch.setattr(
        data_loading, "convert_basic_data_to_enriched_format", fake_convert
    )
    monkeypatch.setattr(data_loading, "compute_race_features", fake_features)

    loader = data_loading.RaceEvaluationDataLoader(FakeDBClient(), with_past_stats=True)
    payload = loader.load_race_data({"race_id": "race-1"})

    assert payload is not None
    assert payload["raceInfo"]["rcNo"] == 7
    assert payload["raceInfo"]["track"] == "dry"
    assert len(payload["horses"]) == 1
    horse = payload["horses"][0]
    assert horse["hrNo"] == "001"
    assert horse["past_stats"] == {"wins": 3}
    assert horse["features_applied"] is True


def test_build_v5_race_data():
    loader = data_loading.RaceEvaluationDataLoader(FakeDBClient())
    v5 = loader.build_v5_race_data(
        {
            "raceInfo": {"rcDate": "20240719"},
            "horses": [
                {
                    "chulNo": 1,
                    "winOdds": 2.5,
                    "jkName": "J One",
                    "jkDetail": {"winRate": 12.5},
                    "hrName": "Alpha",
                    "hrDetail": {"rcCntT": 3},
                }
            ],
        }
    )

    assert v5["entries"][0]["horse_no"] == 1
    assert v5["entries"][0]["jockey_winrate"] == 12.5


def test_build_dataset_metadata():
    loader = data_loading.RaceEvaluationDataLoader(FakeDBClient(), with_past_stats=True)

    metadata = loader.build_dataset_metadata(
        [{"race_id": "race-1"}, {"race_id": "race-2"}],
        limit=5,
    )

    assert metadata["source"] == "RaceDBClient.find_races_with_results"
    assert metadata["requested_limit"] == 5
    assert metadata["race_count"] == 2
    assert metadata["race_ids"] == ["race-1", "race-2"]
    assert metadata["feature_schema_version"] == "race-eval-v1"
    assert metadata["with_past_stats"] is True
