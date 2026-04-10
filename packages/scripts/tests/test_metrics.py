from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.metrics import compute_prediction_quality_metrics


def _sample_results() -> list[dict]:
    return [
        {
            "race_id": "r1",
            "predicted": [1, 2, 3],
            "actual": [1, 5, 6],
            "reward": {"correct_count": 1},
            "confidence": 80,
            "race_data": {
                "entries": [
                    {"horse_no": 1, "win_odds": 2.5},
                    {"horse_no": 2, "win_odds": 3.8},
                    {"horse_no": 3, "win_odds": 5.0},
                ]
            },
        },
        {
            "race_id": "r2",
            "predicted": [2, 3, 4],
            "actual": [5, 2, 7],
            "reward": {"correct_count": 1},
            "confidence": 60,
            "race_data": {
                "entries": [
                    {"horse_no": 2, "win_odds": 4.2},
                    {"horse_no": 3, "win_odds": 6.5},
                    {"horse_no": 4, "win_odds": 7.1},
                    {"horse_no": 5, "win_odds": 3.1},
                ]
            },
        },
    ]


def test_compute_prediction_quality_metrics_basic_values() -> None:
    report = compute_prediction_quality_metrics(
        _sample_results(), topk_values=(1, 3), ece_bins=5
    )

    assert report["samples"] == 2
    assert report["topk"]["top_1"] == 0.5
    assert report["topk"]["top_3"] == 0.5
    assert report["coverage"] == 1.0
    assert report["prediction_coverage"] == 1.0
    assert report["expected_race_count"] == 2
    assert report["predicted_race_count"] == 2
    assert report["missing_prediction_count"] == 0
    assert report["missing_prediction_race_ids"] == []
    assert round(report["roi"]["avg_roi"], 3) == 0.25
    assert report["log_loss"] > 0
    assert report["brier"] >= 0
    assert report["ece"] >= 0
    assert report["race_hit_count"] == 0
    assert report["race_hit_rate"] == 0.0


def test_compute_prediction_quality_metrics_defer_threshold_changes_coverage() -> None:
    report = compute_prediction_quality_metrics(
        _sample_results(),
        topk_values=(1, 3),
        ece_bins=5,
        defer_threshold=0.7,
    )

    assert report["coverage"] == 0.5
    assert report["deferred_count"] == 1


def test_compute_prediction_quality_metrics_reports_missing_prediction_race_ids() -> (
    None
):
    results = [
        {
            "race_id": "r1",
            "predicted": [1, 2, 3],
            "actual": [1, 2, 3],
            "prediction": {"selected_horses": [{"chulNo": 1}]},
            "reward": {"correct_count": 3},
            "hit": True,
        },
        {
            "race_id": "r2",
            "prediction": None,
            "reward": {"status": "error", "correct_count": 0},
            "hit": False,
        },
    ]

    report = compute_prediction_quality_metrics(
        results,
        topk_values=(1, 3),
        reference_race_ids=["r1", "r2"],
    )

    assert report["prediction_coverage"] == 0.5
    assert report["expected_race_count"] == 2
    assert report["predicted_race_count"] == 1
    assert report["missing_prediction_count"] == 1
    assert report["missing_prediction_race_ids"] == ["r2"]
    assert report["unexpected_prediction_count"] == 0
    assert report["unexpected_prediction_race_ids"] == []


def test_set_match_score_perfect():
    from evaluation.metrics import _set_match_score

    assert _set_match_score([1, 2, 3], [1, 2, 3]) == 1.0


def test_set_match_score_partial():
    from evaluation.metrics import _set_match_score

    assert abs(_set_match_score([1, 2, 3], [1, 5, 6]) - 1 / 3) < 0.01


def test_set_match_score_none():
    from evaluation.metrics import _set_match_score

    assert _set_match_score([1, 2, 3], [4, 5, 6]) == 0.0


def test_is_unordered_topk_exact_match_ignores_order():
    from evaluation.metrics import is_unordered_topk_exact_match

    assert is_unordered_topk_exact_match([3, 1, 2], [1, 2, 3]) is True


def test_is_unordered_topk_exact_match_uses_only_top3_window():
    from evaluation.metrics import is_unordered_topk_exact_match

    assert is_unordered_topk_exact_match([1, 2, 4, 3], [1, 2, 3]) is False


def test_is_ordered_topk_exact_match_requires_exact_order():
    from evaluation.metrics import is_ordered_topk_exact_match

    assert is_ordered_topk_exact_match([1, 2, 3], [1, 2, 3]) is True
    assert is_ordered_topk_exact_match([3, 1, 2], [1, 2, 3]) is False


def test_ndcg_at_k_perfect():
    from evaluation.metrics import _ndcg_at_k

    score = _ndcg_at_k([1, 2, 3], [1, 2, 3])
    assert score == 1.0


def test_ndcg_at_k_partial():
    from evaluation.metrics import _ndcg_at_k

    score = _ndcg_at_k([1, 4, 5], [1, 2, 3])
    assert 0 < score < 1.0


def test_compute_metrics_includes_new_fields():
    report = compute_prediction_quality_metrics(_sample_results(), topk_values=(1, 3))
    assert "set_match_rate" in report
    assert "ndcg3" in report
    assert "brier_set" in report
    assert "prediction_coverage" in report
    assert "missing_prediction_count" in report
    assert "missing_prediction_race_ids" in report
    assert "race_hit_count" in report
    assert "race_hit_rate" in report
    assert "ordered_race_hit_count" in report
    assert "ordered_race_hit_rate" in report
    assert report["set_match_rate"] >= 0
    assert report["ndcg3"] >= 0


def test_compute_prediction_quality_metrics_aggregates_race_hits_over_all_races() -> (
    None
):
    results = [
        {
            "race_id": "r1",
            "predicted": [1, 2, 3],
            "actual": [3, 1, 2],
            "prediction": {"selected_horses": [{"chulNo": 1}]},
            "reward": {
                "unordered_top3_exact_match": True,
                "ordered_top3_exact_match": False,
                "correct_count": 3,
            },
            "hit": True,
            "ordered_hit": False,
        },
        {
            "race_id": "r2",
            "predicted": [1, 2, 3],
            "actual": [1, 2, 3],
            "prediction": {"selected_horses": [{"chulNo": 1}]},
            "reward": {
                "unordered_top3_exact_match": True,
                "ordered_top3_exact_match": True,
                "correct_count": 3,
            },
            "hit": True,
            "ordered_hit": True,
        },
        {
            "race_id": "r3",
            "prediction": None,
            "reward": {"status": "error", "correct_count": 0},
            "hit": False,
            "ordered_hit": False,
        },
    ]

    report = compute_prediction_quality_metrics(results, topk_values=(1, 3))

    assert report["samples"] == 2
    assert report["prediction_coverage"] == 2 / 3
    assert report["expected_race_count"] == 3
    assert report["predicted_race_count"] == 2
    assert report["missing_prediction_count"] == 1
    assert report["missing_prediction_race_ids"] == ["r3"]
    assert report["race_hit_count"] == 2
    assert abs(report["race_hit_rate"] - (2 / 3)) < 1e-9
    assert report["ordered_race_hit_count"] == 1
    assert abs(report["ordered_race_hit_rate"] - (1 / 3)) < 1e-9


def test_compute_stratified_metrics():
    from evaluation.metrics import compute_stratified_metrics

    results = [
        {
            "predicted": [1, 2, 3],
            "actual": [1, 5, 6],
            "race_data": {
                "raceInfo": {"rcDist": 1400, "meet": "서울"},
                "horses": [{"horse_no": i} for i in range(1, 11)],
            },
        },
        {
            "predicted": [2, 3, 4],
            "actual": [2, 3, 7],
            "race_data": {
                "raceInfo": {"rcDist": 1800, "meet": "부산"},
                "horses": [{"horse_no": i} for i in range(1, 9)],
            },
        },
    ]
    strat = compute_stratified_metrics(results)
    assert "distance" in strat
    assert "field_size" in strat
    assert "meet" in strat
