from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.report_schema import build_report_v2, validate_report_v2
from shared.prediction_input_schema import build_alternative_ranking_dataset_metadata


def test_validate_report_v2_rejects_missing_keys() -> None:
    ok, errors = validate_report_v2({"prompt_version": "v1.0"})

    assert ok is False
    assert errors


def test_validate_report_v2_accepts_complete_report() -> None:
    report = build_report_v2(
        prompt_version="v1.0",
        summary={
            "prompt_version": "v1.0",
            "total_races": 2,
            "valid_predictions": 2,
            "successful_predictions": 1,
            "success_rate": 50.0,
            "average_correct_horses": 1.0,
            "avg_execution_time": 1.2,
            "error_stats": {},
            "detailed_results": [],
            "dataset_metadata": build_alternative_ranking_dataset_metadata(
                source="RaceDBClient.find_races",
                dataset_name="report_test_dataset",
                requested_limit=None,
                race_ids=["race-1", "race-2"],
                with_past_stats=False,
            ),
            "feature_schema_version": "alternative-ranking-input-v1",
        },
        metrics={
            "log_loss": 0.5,
            "brier": 0.2,
            "ece": 0.1,
            "topk": {"top_1": 0.5, "top_3": 0.5},
            "roi": {"avg_roi": 0.0, "bets": 0, "wins": 0},
            "coverage": 1.0,
            "deferred_count": 0,
            "samples": 2,
            "prediction_coverage": 1.0,
            "expected_race_count": 2,
            "predicted_race_count": 2,
            "missing_prediction_count": 0,
            "missing_prediction_race_ids": [],
            "unexpected_prediction_count": 0,
            "unexpected_prediction_race_ids": [],
            "json_valid_rate": 1.0,
            "race_hit_count": 1,
            "race_hit_rate": 0.5,
            "ordered_race_hit_count": 0,
            "ordered_race_hit_rate": 0.0,
        },
        leakage={"passed": True, "issues": []},
    )

    ok, errors = validate_report_v2(report)

    assert ok is True
    assert errors == []
    assert report["dataset_metadata"]["race_count"] == 2
    assert report["feature_schema_version"] == "alternative-ranking-input-v1"
    assert report["metrics_v2"]["race_hit_count"] == 1
    assert report["metrics_v2"]["race_hit_rate"] == 0.5
    assert report["metrics_v2"]["ordered_race_hit_count"] == 0
    assert report["metrics_v2"]["ordered_race_hit_rate"] == 0.0
    assert report["metrics_v2"]["missing_prediction_count"] == 0
    assert report["metrics_v2"]["missing_prediction_race_ids"] == []
