from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch.random_split_result_collector import (  # noqa: E402
    collect_detailed_records_from_ralph_runs,
)
from autoresearch.seed_summary_report import build_seed_summary_report  # noqa: E402

from .fixtures.multi_seed_result_cases import (  # noqa: E402
    EXPECTED_REPORT_SUMMARY,
    build_execution_journal_from_detailed_records,
    write_multi_seed_random_split_case,
)


def test_build_seed_summary_report_matches_multi_seed_fixture_aggregates(
    tmp_path: Path,
) -> None:
    run_paths = write_multi_seed_random_split_case(tmp_path / "ralph")
    collected = collect_detailed_records_from_ralph_runs(tuple(reversed(run_paths)))
    journal = build_execution_journal_from_detailed_records(collected)

    report = build_seed_summary_report(
        journal,
        journal_path=tmp_path / "holdout_execution_journal.json",
        generated_at="2026-04-11T12:00:00+09:00",
    )

    expected = EXPECTED_REPORT_SUMMARY
    overall = report["aggregates"]["overall_holdout_hit_rate"]
    normalized_overall = report["normalized_metrics"]["metrics"][
        "overall_holdout_hit_rate"
    ]["summary"]
    normalized_dev_gap = report["normalized_metrics"]["metrics"]["dev_test_gap"][
        "summary"
    ]

    assert report["gate"]["actual"] == expected["gate_actual"]
    assert report["gate"]["passed"] is expected["gate_passed"]
    assert report["verification_verdict"]["status"] == expected["verification_status"]
    assert (
        report["verification_verdict"]["blockers"] == expected["verification_blockers"]
    )
    assert report["worst_completed_run"]["run_id"] == expected["worst_completed_run_id"]
    assert overall["count"] == expected["overall_distribution"]["count"]
    assert overall["min"] == expected["overall_distribution"]["min"]
    assert overall["max"] == expected["overall_distribution"]["max"]
    assert overall["mean"] == pytest.approx(expected["overall_distribution"]["mean"])
    assert overall["median"] == pytest.approx(
        expected["overall_distribution"]["median"]
    )
    assert overall["stddev"] == pytest.approx(
        expected["overall_distribution"]["stddev"]
    )
    assert overall["quantiles"] == expected["overall_distribution"]["quantiles"]
    assert (
        len(overall["outlier_analysis"]["outlier_run_ids"])
        == expected["overall_distribution"]["outlier_count"]
    )
    assert (
        normalized_overall["row_count"]
        == expected["normalized_overall_summary"]["row_count"]
    )
    assert (
        normalized_overall["ok_count"]
        == expected["normalized_overall_summary"]["ok_count"]
    )
    assert normalized_overall["normalized_mean"] == pytest.approx(
        expected["normalized_overall_summary"]["normalized_mean"]
    )
    assert normalized_overall["normalized_median"] == pytest.approx(
        expected["normalized_overall_summary"]["normalized_median"]
    )
    assert normalized_overall["normalized_stddev"] == pytest.approx(
        expected["normalized_overall_summary"]["normalized_stddev"]
    )
    assert normalized_overall["comparable_mean"] == pytest.approx(
        expected["normalized_overall_summary"]["comparable_mean"]
    )
    assert normalized_overall["comparable_median"] == pytest.approx(
        expected["normalized_overall_summary"]["comparable_median"]
    )
    assert normalized_overall["comparable_stddev"] == pytest.approx(
        expected["normalized_overall_summary"]["comparable_stddev"]
    )
    assert (
        len(normalized_overall["outlier_analysis"]["outlier_run_ids"])
        == expected["normalized_overall_summary"]["outlier_count"]
    )
    assert (
        normalized_dev_gap["row_count"]
        == expected["normalized_dev_gap_summary"]["row_count"]
    )
    assert (
        normalized_dev_gap["ok_count"]
        == expected["normalized_dev_gap_summary"]["ok_count"]
    )
    assert normalized_dev_gap["comparable_mean"] == pytest.approx(
        expected["normalized_dev_gap_summary"]["comparable_mean"]
    )
    rows_by_run_id = {
        row["run_id"]: row["overall_holdout_hit_rate_source"]
        for row in report["seed_hit_rate_rows"]
    }
    for run_id, source in expected["fallback_sources_by_run_id"].items():
        assert rows_by_run_id[run_id] == source
