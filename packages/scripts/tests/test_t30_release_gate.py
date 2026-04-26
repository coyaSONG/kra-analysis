from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.t30_release_gate import (  # noqa: E402
    T30_RELEASE_GATE_REPORT_VERSION,
    build_t30_release_gate_report,
)


def _payload(
    *,
    race_id: str = "race-1",
    freshness_passed: bool = True,
    include_odds: bool = False,
    entry_source_present: bool = True,
    changed_jockey_flag: float | None = 0.0,
) -> dict[str, object]:
    horse = {
        "chulNo": 1,
        "hrNo": "001",
        "changed_jockey_flag": changed_jockey_flag,
    }
    if include_odds:
        horse["winOdds"] = 2.5
    return {
        "race_id": race_id,
        "operational_cutoff_status": {
            "passed": freshness_passed,
            "reason": "ok" if freshness_passed else "source_after_cutoff",
            "scheduled_start_at": "2025-01-01T11:00:00+09:00",
            "operational_cutoff_at": "2025-01-01T10:30:00+09:00",
            "source_snapshot_at": "2025-01-01T10:00:00+09:00",
        },
        "entry_change_audit": {"source_present": entry_source_present},
        "standard_payload": {
            "race_id": race_id,
            "race_date": "20250101",
            "horses": [horse],
        },
    }


def test_build_t30_release_gate_report_passes_safe_payloads() -> None:
    report = build_t30_release_gate_report([_payload()])

    assert report["schema_version"] == T30_RELEASE_GATE_REPORT_VERSION
    assert report["passed"] is True
    assert report["freshness"]["passed"] is True
    assert report["freshness"]["pass_rate"] == 1.0
    assert report["odds_exclusion"]["passed"] is True
    assert report["entry_change_coverage"]["source_present_race_count"] == 1
    assert report["entry_change_coverage"]["changed_jockey_null_rate"] == 0.0


def test_build_t30_release_gate_report_blocks_late_snapshots_and_odds() -> None:
    report = build_t30_release_gate_report(
        [
            _payload(race_id="race-1", freshness_passed=False),
            _payload(race_id="race-2", include_odds=True),
        ]
    )

    assert report["passed"] is False
    assert report["freshness"]["passed"] is False
    assert report["freshness"]["failed_races"][0]["race_id"] == "race-1"
    assert report["freshness"]["failed_races"][0]["reason"] == "source_after_cutoff"
    assert report["odds_exclusion"]["passed"] is False
    assert report["odds_exclusion"]["violating_paths_by_race"] == {
        "race-2": ["horses[0].winOdds"]
    }


def test_build_t30_release_gate_report_tracks_missing_change_source_nulls() -> None:
    report = build_t30_release_gate_report(
        [
            _payload(
                entry_source_present=False,
                changed_jockey_flag=None,
            )
        ]
    )

    coverage = report["entry_change_coverage"]
    assert coverage["source_missing_race_count"] == 1
    assert coverage["changed_jockey_horse_count"] == 1
    assert coverage["changed_jockey_null_count"] == 1
    assert coverage["changed_jockey_null_rate"] == 1.0
