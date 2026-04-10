import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation import data_loading
from shared.prediction_input_schema import ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
from shared.prerace_standard_loader import StandardizedPreracePayload


class FakeDBClient:
    def load_race_basic_data(self, race_id, *, lookup):
        assert race_id == "race-1"
        assert lookup.race_id == "race-1"
        assert lookup.race_date == "20240719"
        assert lookup.entry_snapshot_at == "2024-07-19T10:00:00+09:00"
        return {"raw": True, "cancelled_horses": []}

    def get_past_top3_stats_for_race(self, hr_nos, *, lookup, lookback_days):
        assert hr_nos == ["001", "002"]
        assert lookup.race_id == "race-1"
        assert lookup.race_date == "20240719"
        assert lookup.entry_snapshot_at == "2024-07-19T10:00:00+09:00"
        assert lookback_days == 90
        return {"001": {"wins": 3}}


def test_load_race_data_builds_normalized_payload(monkeypatch):
    def fake_loader(race_info, *, query_port, horse_preprocessor):
        assert query_port is not None
        assert race_info["race_id"] == "race-1"
        horses = horse_preprocessor(
            [
                {
                    "chulNo": 1,
                    "hrNo": "001",
                    "class_rank": "A",
                    "past_stats": {},
                },
                {
                    "chulNo": 2,
                    "hrNo": "002",
                    "class_rank": "A",
                },
            ]
        )
        horses[0]["features_applied"] = True
        return StandardizedPreracePayload(
            race_id="race-1",
            race_date="20240719",
            meet=1,
            lookup=None,
            basic_data={"cancelled_horses": []},
            enriched_data={},
            standard_payload={
                "race_id": "race-1",
                "race_date": "20240719",
                "race_info": {
                    "rcDate": "20240719",
                    "rcNo": 7,
                    "track": "dry",
                },
                "horses": horses,
                "candidate_filter": {
                    "status_counts": {"normal": 1, "scratched": 1},
                    "exclusion_rule_counts": {},
                    "initial_exclusion_rule_counts": {"zero_market_signal": 1},
                    "reinclusion_rule_counts": {"zero_market_signal": 1},
                    "flag_counts": {"market_signal_missing": 1},
                    "race_diagnostics": {
                        "minimum_prediction_candidates": 3,
                        "total_runner_count": 2,
                        "initial_eligible_runner_count": 1,
                        "initial_excluded_runner_count": 1,
                        "initial_candidate_shortage_count": 2,
                        "reincluded_runner_count": 1,
                        "reinclusion_applied": True,
                        "eligible_runner_count": 2,
                        "excluded_runner_count": 0,
                        "candidate_shortage_count": 1,
                        "has_candidate_shortage": True,
                        "shortage_reason_counts": {},
                        "shortage_reason_classification": "raw_field_too_small",
                        "primary_shortage_reason": None,
                    },
                },
                "input_schema": {
                    "schema_version": "alternative-ranking-input-v1",
                    "row_count": 2,
                    "canonical_path_mismatches": [],
                },
            },
            candidate_filter={
                "status_counts": {"normal": 1, "scratched": 1},
                "exclusion_rule_counts": {},
                "initial_exclusion_rule_counts": {"zero_market_signal": 1},
                "reinclusion_rule_counts": {"zero_market_signal": 1},
                "flag_counts": {"market_signal_missing": 1},
                "race_diagnostics": {
                    "minimum_prediction_candidates": 3,
                    "total_runner_count": 2,
                    "initial_eligible_runner_count": 1,
                    "initial_excluded_runner_count": 1,
                    "initial_candidate_shortage_count": 2,
                    "reincluded_runner_count": 1,
                    "reinclusion_applied": True,
                    "eligible_runner_count": 2,
                    "excluded_runner_count": 0,
                    "candidate_shortage_count": 1,
                    "has_candidate_shortage": True,
                    "shortage_reason_counts": {},
                    "shortage_reason_classification": "raw_field_too_small",
                    "primary_shortage_reason": None,
                },
            },
            field_policy={},
            removed_post_race_paths=(),
            entry_resolution_audit=None,
        )

    monkeypatch.setattr(data_loading, "load_standardized_prerace_payload", fake_loader)

    loader = data_loading.RaceEvaluationDataLoader(FakeDBClient(), with_past_stats=True)
    payload = loader.load_race_data(
        {
            "race_id": "race-1",
            "race_date": "20240719",
            "entry_snapshot_at": "2024-07-19T10:00:00+09:00",
        }
    )

    assert payload is not None
    assert payload["race_info"]["rcNo"] == 7
    assert payload["race_info"]["track"] == "dry"
    assert len(payload["horses"]) == 2
    assert payload["candidate_filter"]["status_counts"] == {
        "normal": 1,
        "scratched": 1,
    }
    assert payload["candidate_filter"]["exclusion_rule_counts"] == {}
    assert payload["candidate_filter"]["initial_exclusion_rule_counts"] == {
        "zero_market_signal": 1
    }
    assert payload["candidate_filter"]["reinclusion_rule_counts"] == {
        "zero_market_signal": 1
    }
    assert payload["candidate_filter"]["flag_counts"]["market_signal_missing"] == 1
    assert payload["candidate_filter"]["race_diagnostics"] == {
        "minimum_prediction_candidates": 3,
        "total_runner_count": 2,
        "initial_eligible_runner_count": 1,
        "initial_excluded_runner_count": 1,
        "initial_candidate_shortage_count": 2,
        "reincluded_runner_count": 1,
        "reinclusion_applied": True,
        "eligible_runner_count": 2,
        "excluded_runner_count": 0,
        "candidate_shortage_count": 1,
        "has_candidate_shortage": True,
        "shortage_reason_counts": {},
        "shortage_reason_classification": "raw_field_too_small",
        "primary_shortage_reason": None,
    }
    horse = payload["horses"][0]
    assert horse["hrNo"] == "001"
    assert horse["class_rank"] == "A"
    assert "rank" not in horse
    assert "winOdds" not in horse
    assert "plcOdds" not in horse
    assert horse["past_stats"] == {"wins": 3}
    assert horse["features_applied"] is True
    assert payload["input_schema"]["schema_version"] == "alternative-ranking-input-v1"
    assert payload["input_schema"]["row_count"] == 2
    assert payload["input_schema"]["canonical_path_mismatches"] == []


def test_load_race_data_excludes_cancelled_rows_even_when_market_signal_is_positive(
    monkeypatch,
):
    class CancelledHorseDBClient(FakeDBClient):
        pass

    def fake_loader(_race_info, *, query_port, horse_preprocessor):
        horses = horse_preprocessor([{"chulNo": 2, "hrNo": "002", "class_rank": "A"}])
        return StandardizedPreracePayload(
            race_id="race-1",
            race_date="20240719",
            meet=1,
            lookup=None,
            basic_data={"cancelled_horses": [{"chulNo": 1, "reason": "출전취소"}]},
            enriched_data={},
            standard_payload={
                "horses": horses,
                "input_schema": {"row_count": 1},
                "candidate_filter": {
                    "exclusion_rule_counts": {"cancelled": 1},
                    "reinclusion_rule_counts": {},
                    "race_diagnostics": {
                        "has_candidate_shortage": True,
                        "shortage_reason_classification": "raw_field_too_small",
                    },
                },
            },
            candidate_filter={
                "exclusion_rule_counts": {"cancelled": 1},
                "reinclusion_rule_counts": {},
                "race_diagnostics": {
                    "has_candidate_shortage": True,
                    "shortage_reason_classification": "raw_field_too_small",
                },
            },
            field_policy={},
            removed_post_race_paths=(),
            entry_resolution_audit=None,
        )

    monkeypatch.setattr(data_loading, "load_standardized_prerace_payload", fake_loader)

    loader = data_loading.RaceEvaluationDataLoader(
        CancelledHorseDBClient(),
        with_past_stats=False,
    )
    payload = loader.load_race_data(
        {
            "race_id": "race-1",
            "race_date": "20240719",
            "entry_snapshot_at": "2024-07-19T10:00:00+09:00",
        }
    )

    assert payload is not None
    assert [horse["chulNo"] for horse in payload["horses"]] == [2]
    assert "winOdds" not in payload["horses"][0]
    assert payload["input_schema"]["row_count"] == 1
    assert payload["candidate_filter"]["exclusion_rule_counts"] == {"cancelled": 1}
    assert payload["candidate_filter"]["reinclusion_rule_counts"] == {}
    assert (
        payload["candidate_filter"]["race_diagnostics"]["has_candidate_shortage"]
        is True
    )
    assert (
        payload["candidate_filter"]["race_diagnostics"][
            "shortage_reason_classification"
        ]
        == "raw_field_too_small"
    )


def test_load_race_data_delegates_payload_build_to_shared_builder(monkeypatch):
    calls: list[dict] = []

    def fake_loader(race_info, *, query_port, horse_preprocessor):
        calls.append({"race_info": race_info, "query_port": query_port})
        processed = horse_preprocessor([{"hrNo": "001"}, {"hrNo": "002"}])
        return StandardizedPreracePayload(
            race_id="race-1",
            race_date="20240719",
            meet=1,
            lookup=None,
            basic_data={"cancelled_horses": []},
            enriched_data={},
            standard_payload={
                "race_id": race_info["race_id"],
                "race_date": race_info["race_date"],
                "race_info": {
                    "rcDate": "20240719",
                    "rcNo": 7,
                    "rcDist": 1200,
                    "track": "dry",
                    "weather": "sunny",
                    "meet": 1,
                },
                "horses": processed,
                "candidate_filter": {"status_counts": {"normal": 1}},
                "input_schema": {"schema_version": "alternative-ranking-input-v1"},
            },
            candidate_filter={"status_counts": {"normal": 1}},
            field_policy={"blocked_paths": []},
            removed_post_race_paths=(),
            entry_resolution_audit=None,
        )

    monkeypatch.setattr(data_loading, "load_standardized_prerace_payload", fake_loader)

    loader = data_loading.RaceEvaluationDataLoader(FakeDBClient(), with_past_stats=True)
    payload = loader.load_race_data(
        {
            "race_id": "race-1",
            "race_date": "20240719",
            "entry_snapshot_at": "2024-07-19T10:00:00+09:00",
        }
    )

    assert payload is not None
    assert calls[0]["race_info"]["race_id"] == "race-1"
    assert calls[0]["race_info"]["race_date"] == "20240719"
    assert payload["horses"][0]["past_stats"] == {"wins": 3}


def test_build_v5_race_data():
    loader = data_loading.RaceEvaluationDataLoader(FakeDBClient())
    v5 = loader.build_v5_race_data(
        {
            "race_info": {"rcDate": "20240719"},
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
    assert (
        metadata["feature_schema_version"] == ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
    )
    assert (
        metadata["dataset_metadata_version"]
        == "alternative-ranking-dataset-metadata-v1"
    )
    assert (
        metadata["input_schema_contract"]["schema_version"]
        == ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
    )
    assert metadata["with_past_stats"] is True


def test_load_race_data_requires_entry_snapshot_at():
    loader = data_loading.RaceEvaluationDataLoader(
        FakeDBClient(), with_past_stats=False
    )

    payload = loader.load_race_data({"race_id": "race-1", "race_date": "20240719"})

    assert payload is None
