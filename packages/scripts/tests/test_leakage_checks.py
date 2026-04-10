from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.leakage_checks import (
    FORBIDDEN_POST_RACE_FIELDS,
    FORBIDDEN_POST_RACE_SOURCE_TAGS,
    check_detailed_results_for_leakage,
)


def test_leakage_check_flags_forbidden_post_race_fields() -> None:
    detailed_results = [
        {
            "race_id": "race-1",
            "race_data": {
                "entries": [
                    {"horse_no": 1, "rank": 1, "win_odds": 2.5},
                    {"horse_no": 2, "rank": 5, "win_odds": 4.0},
                ]
            },
        }
    ]

    report = check_detailed_results_for_leakage(detailed_results)

    assert report["passed"] is False
    assert any("rank" in issue for issue in report["issues"])


def test_leakage_check_passes_when_no_forbidden_fields_exist() -> None:
    detailed_results = [
        {
            "race_id": "race-1",
            "race_data": {
                "entries": [
                    {"horse_no": 1, "win_odds": 2.5},
                    {"horse_no": 2, "win_odds": 4.0},
                ]
            },
        }
    ]

    report = check_detailed_results_for_leakage(detailed_results)

    assert report["passed"] is True
    assert report["issues"] == []


def test_raw_leakage_catalog_keeps_known_result_and_label_keys_blocked() -> None:
    assert {"rank", "top3", "actual_result"} <= FORBIDDEN_POST_RACE_FIELDS
    assert {
        "ord",
        "ordBigo",
        "diffUnit",
        "rankRise",
        "resultTime",
    } <= FORBIDDEN_POST_RACE_FIELDS
    assert {"race_odds", "dividend", "payout"} <= FORBIDDEN_POST_RACE_FIELDS
    assert FORBIDDEN_POST_RACE_SOURCE_TAGS == {"post_entry_only"}
