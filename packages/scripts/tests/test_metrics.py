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
    assert round(report["roi"]["avg_roi"], 3) == 0.25
    assert report["log_loss"] > 0
    assert report["brier"] >= 0
    assert report["ece"] >= 0


def test_compute_prediction_quality_metrics_defer_threshold_changes_coverage() -> None:
    report = compute_prediction_quality_metrics(
        _sample_results(),
        topk_values=(1, 3),
        ece_bins=5,
        defer_threshold=0.7,
    )

    assert report["coverage"] == 0.5
    assert report["deferred_count"] == 1


def test_set_match_score_perfect():
    from evaluation.metrics import _set_match_score

    assert _set_match_score([1, 2, 3], [1, 2, 3]) == 1.0


def test_set_match_score_partial():
    from evaluation.metrics import _set_match_score

    assert abs(_set_match_score([1, 2, 3], [1, 5, 6]) - 1 / 3) < 0.01


def test_set_match_score_none():
    from evaluation.metrics import _set_match_score

    assert _set_match_score([1, 2, 3], [4, 5, 6]) == 0.0


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
    assert report["set_match_rate"] >= 0
    assert report["ndcg3"] >= 0


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
