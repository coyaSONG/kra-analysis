from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.seed_performance_aggregation import (  # noqa: E402
    build_seed_metric_aggregate,
    standardize_seed_metric_rows,
    summarize_seed_metric_distribution,
)


def test_summarize_seed_metric_distribution_exposes_quantiles_and_iqr_bounds() -> None:
    summary = summarize_seed_metric_distribution([0.67, 0.69, 0.72, 0.79])

    assert summary["sample_count"] == 4
    assert summary["mean"] == 0.7175
    assert summary["median"] == 0.705
    assert summary["stddev"] == 0.045484
    assert summary["quantiles"] == {
        "p10": 0.676,
        "p25": 0.685,
        "p50": 0.705,
        "p75": 0.7375,
        "p90": 0.769,
    }
    assert summary["iqr"] == 0.0525
    assert summary["lower_fence"] == 0.60625
    assert summary["upper_fence"] == 0.81625


def test_standardize_seed_metric_rows_normalizes_aliases_and_value_sources() -> None:
    rows = standardize_seed_metric_rows(
        [
            {
                "runId": "seed_02_rs17",
                "seedIndex": 2,
                "seed": 17,
                "status": "completed",
                "overall_holdout_hit_rate": "71%",
                "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
            }
        ],
        metric_name="overall_holdout_hit_rate",
        value_source_key="overall_holdout_hit_rate_source",
    )

    assert rows == [
        {
            "format_version": "seed-performance-row-v1",
            "metric_name": "overall_holdout_hit_rate",
            "run_id": "seed_02_rs17",
            "seed_index": 2,
            "model_random_state": 17,
            "run_status": "completed",
            "value_source": "summary.overfit_safe_exact_rate",
            "direction": "maximize",
            "raw_value": "71%",
            "normalized_value": 0.71,
            "comparable_value": 0.71,
            "status": "ok",
            "issue_code": None,
            "scale_applied": "percent_string",
        }
    ]


def test_build_seed_metric_aggregate_flags_iqr_outlier_rows() -> None:
    aggregate = build_seed_metric_aggregate(
        [
            {
                "run_id": "seed_01_rs11",
                "seed_index": 1,
                "model_random_state": 11,
                "status": "completed",
                "overall_holdout_hit_rate": 0.70,
                "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
            },
            {
                "run_id": "seed_02_rs17",
                "seed_index": 2,
                "model_random_state": 17,
                "status": "completed",
                "overall_holdout_hit_rate": 0.71,
                "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
            },
            {
                "run_id": "seed_03_rs23",
                "seed_index": 3,
                "model_random_state": 23,
                "status": "completed",
                "overall_holdout_hit_rate": 0.72,
                "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
            },
            {
                "run_id": "seed_04_rs31",
                "seed_index": 4,
                "model_random_state": 31,
                "status": "completed",
                "overall_holdout_hit_rate": 0.95,
                "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
            },
        ],
        metric_name="overall_holdout_hit_rate",
        value_source_key="overall_holdout_hit_rate_source",
    )

    assert aggregate["summary"]["normalized_value_aggregate"]["quantiles"] == {
        "p10": 0.703,
        "p25": 0.7075,
        "p50": 0.715,
        "p75": 0.7775,
        "p90": 0.881,
    }
    assert aggregate["summary"]["outlier_analysis"]["high_outlier_run_ids"] == (
        "seed_04_rs31",
    )
    assert aggregate["summary"]["outlier_analysis"]["low_outlier_run_ids"] == ()
    outlier_rows = {row["run_id"]: row["outlier_label"] for row in aggregate["rows"]}
    assert outlier_rows["seed_04_rs31"] == "high"
    assert outlier_rows["seed_01_rs11"] is None
