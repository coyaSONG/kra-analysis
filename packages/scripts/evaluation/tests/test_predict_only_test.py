from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation import predict_only_test
from evaluation.predict_only_test import PredictionTester
from shared.prerace_standard_loader import StandardizedPreracePayload
from shared.read_contract import RaceKey, RaceSnapshot


class FakeClaudeClient:
    def __init__(self, output: str) -> None:
        self.output = output

    def predict_sync(self, *_args, **_kwargs) -> str:
        return self.output


def _build_prediction_tester(tmp_path: Path, *, output: str) -> PredictionTester:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("PROMPT\n\n{{RACE_DATA}}", encoding="utf-8")

    tester = PredictionTester.__new__(PredictionTester)
    tester.prompt_path = str(prompt_path)
    tester.predictions_dir = tmp_path / "prediction_tests"
    tester.predictions_dir.mkdir(parents=True, exist_ok=True)
    tester.client = FakeClaudeClient(output)
    tester.db_client = None
    return tester


class FakeSnapshotDBClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def load_race_basic_data(self, race_id: str, *, lookup):
        self.calls.append((race_id, lookup))
        return {"raw": True, "cancelled_horses": [{"chulNo": 9, "reason": "출전취소"}]}


def test_load_race_data_reuses_snapshot_lookup_and_common_builder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tester = _build_prediction_tester(tmp_path, output="{}")
    tester.db_client = FakeSnapshotDBClient()

    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-77", race_date="20250719", meet=1, race_number=7),
        basic_data={
            "race_info": {"response": {"body": {"items": {"item": []}}}},
            "cancelled_horses": [],
        },
        raw_data={
            "snapshot_meta": {
                "entry_finalized_at": "2025-07-19T10:35:00+09:00",
                "replay_status": "strict",
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
            }
        },
        collected_at="2025-07-19T10:35:00+09:00",
        updated_at="2025-07-19T10:36:00+09:00",
    )

    captured: dict[str, object] = {}

    def fake_loader(race_record, *, query_port):
        captured["race_record"] = race_record
        captured["query_port"] = query_port
        return StandardizedPreracePayload(
            race_id="race-77",
            race_date="20250719",
            meet="서울",
            lookup=tester.db_client.calls[0][1] if tester.db_client.calls else None,
            basic_data={"cancelled_horses": [{"chulNo": 9, "reason": "출전취소"}]},
            enriched_data={},
            standard_payload={
                "race_id": "race-77",
                "race_date": "20250719",
                "race_info": {
                    "rcDate": "20250719",
                    "rcNo": 7,
                    "rcDist": 1200,
                    "track": "건조",
                    "weather": "맑음",
                    "meet": "서울",
                },
                "horses": [
                    {
                        "chulNo": 1,
                        "hrName": "알파",
                        "jkName": "기수1",
                        "rating": 80,
                        "class_rank": "국6",
                        "hrDetail": {
                            "rcCntT": 5,
                            "ord1CntT": 1,
                            "ord2CntT": 1,
                            "ord3CntT": 1,
                        },
                        "jkDetail": {"rcCntT": 10, "ord1CntT": 2},
                        "computed_features": {"rating_rank": 1},
                    }
                ],
                "candidate_filter": {"status_counts": {"normal": 1}},
                "input_schema": {"schema_version": "alternative-ranking-input-v1"},
            },
            candidate_filter={"status_counts": {"normal": 1}},
            field_policy={
                "removed_paths": [],
                "policy_version": "prerace-field-policy-v1",
            },
            removed_post_race_paths=(),
            entry_resolution_audit=None,
        )

    monkeypatch.setattr(
        predict_only_test,
        "load_standardized_prerace_payload",
        fake_loader,
    )

    loaded = tester.load_race_data(snapshot)

    assert loaded is not None
    assert captured["race_record"] is snapshot
    assert captured["query_port"] is tester.db_client
    assert (
        loaded["prompt_payload"]["input_schema"]["schema_version"]
        == "alternative-ranking-input-v1"
    )
    assert loaded["analysis_payload"]["source_lookup"] == {}
    assert loaded["analysis_payload"]["candidate_filter"] == {
        "status_counts": {"normal": 1}
    }


def test_analyze_prediction_uses_schema_safe_selection_rank(tmp_path: Path) -> None:
    tester = _build_prediction_tester(tmp_path, output="{}")

    analysis = tester.analyze_prediction(
        {
            "race_id": "race-55",
            "predicted": [2, 1, 3],
            "confidence": 74,
            "execution_time": 1.2,
        },
        {
            "horses": [
                {
                    "chulNo": 1,
                    "hrName": "말1",
                    "jkName": "기수1",
                    "computed_features": {"rating_rank": 2},
                },
                {
                    "chulNo": 2,
                    "hrName": "말2",
                    "jkName": "기수2",
                    "computed_features": {"rating_rank": 1},
                },
                {
                    "chulNo": 3,
                    "hrName": "말3",
                    "jkName": "기수3",
                    "computed_features": {"horse_skill_rank": 3},
                },
            ]
        },
    )

    assert [horse["selectionRank"] for horse in analysis["predicted_horses"]] == [
        1,
        2,
        3,
    ]
    assert analysis["predicted_horses"][0]["selectionRankBasis"] == "rating_rank"
    assert analysis["prediction_strategy"] == "상위 지표 중심"
    assert analysis["confidence_level"] == "높음"


def test_run_prediction_and_save_results_keep_same_corrected_top3_for_overfilled_output(
    tmp_path: Path,
) -> None:
    tester = _build_prediction_tester(
        tmp_path,
        output="""{
  "selected_horses": [
    {"chulNo": 5},
    {"chulNo": 5},
    {"chulNo": 0},
    {"chulNo": 4},
    {"chulNo": 3},
    {"chulNo": 2},
    {"chulNo": "bad"}
  ],
  "predictions": [
    {"chulNo": 5, "win_probability": 0.95},
    {"chulNo": 4, "win_probability": 0.89},
    {"chulNo": 2, "win_probability": 0.84},
    {"chulNo": 3, "win_probability": 0.35}
  ],
  "confidence": 80
}""",
    )
    race_data = {
        "horses": [
            {"chulNo": 2},
            {"chulNo": 3},
            {"chulNo": 4},
            {"chulNo": 5},
        ]
    }

    prediction = tester.run_prediction(race_data, "race-corrected-top3")

    assert prediction is not None
    assert prediction["predicted"] == [5, 4, 2]
    assert prediction["top3"] == [5, 4, 2]
    assert prediction["selected_horses"] == [
        {"chulNo": 5},
        {"chulNo": 4},
        {"chulNo": 2},
    ]
    assert prediction["prediction_output_format"] == {
        "version": "unordered-top3-unique-v1",
        "predicted_count": 3,
        "is_unique": True,
    }

    tester.save_results([prediction], analyses=[], date_filter="20260411")

    saved_files = list(tester.predictions_dir.glob("prediction_test_20260411_*.json"))
    assert len(saved_files) == 1

    saved_payload = json.loads(saved_files[0].read_text(encoding="utf-8"))
    saved_prediction = saved_payload["predictions"][0]
    assert saved_prediction["predicted"] == [5, 4, 2]
    assert saved_prediction["top3"] == [5, 4, 2]
    assert saved_prediction["selected_horses"] == [
        {"chulNo": 5},
        {"chulNo": 4},
        {"chulNo": 2},
    ]
    assert saved_prediction["full_output"]
    assert saved_prediction["prediction_validation"]["issue_codes"] == []
    assert saved_prediction["prediction_correction"]["repair_action_codes"] == []
    assert saved_prediction["prediction_validation"]["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 5,
            "score": 0.95,
            "hrName": None,
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 2,
            "chulNo": 4,
            "score": 0.89,
            "hrName": None,
            "source_field": "selected_horses",
            "raw_index": 2,
        },
        {
            "rank": 3,
            "chulNo": 2,
            "score": 0.84,
            "hrName": None,
            "source_field": "selected_horses",
            "raw_index": 3,
        },
    ]


def test_run_prediction_and_save_results_fill_missing_slot_from_race_card(
    tmp_path: Path,
) -> None:
    tester = _build_prediction_tester(
        tmp_path,
        output="""{
  "selected_horses": [
    {"chulNo": 1},
    {"chulNo": "bad"},
    {"chulNo": 2}
  ],
  "confidence": 80
}""",
    )
    race_data = {
        "horses": [
            {"chulNo": 1},
            {"chulNo": 2},
            {"chulNo": 3},
        ]
    }

    prediction = tester.run_prediction(race_data, "race-underfilled-top3")

    assert prediction is not None
    assert prediction["predicted"] == [1, 2, 3]
    assert prediction["top3"] == [1, 2, 3]
    assert prediction["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert prediction["prediction_output_format"] == {
        "version": "unordered-top3-unique-v1",
        "predicted_count": 3,
        "is_unique": True,
    }

    tester.save_results([prediction], analyses=[], date_filter="20260411")

    saved_files = list(tester.predictions_dir.glob("prediction_test_20260411_*.json"))
    assert len(saved_files) == 1

    saved_payload = json.loads(saved_files[0].read_text(encoding="utf-8"))
    saved_prediction = saved_payload["predictions"][0]
    assert saved_prediction["predicted"] == [1, 2, 3]
    assert saved_prediction["top3"] == [1, 2, 3]
    assert saved_prediction["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert saved_prediction["prediction_validation"]["issue_codes"] == []
    assert saved_prediction["prediction_correction"]["repair_action_codes"] == []
