from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prediction_output_guard import guard_prediction_output


def test_guard_prediction_output_fills_missing_slot_from_race_card() -> None:
    report = guard_prediction_output(
        {
            "selected_horses": [
                {"chulNo": 1},
                {"chulNo": 0},
                {"chulNo": 2},
            ]
        },
        valid_chul_nos=[1, 2, 3, 4],
    )

    assert report["accepted"] is True
    assert report["repairable"] is True
    assert report["final_predicted"] == [1, 2, 3]
    assert report["final_selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert report["blocking_issue_codes"] == []
    assert report["repair_action_codes"] == [
        "deduped_or_trimmed_candidates",
        "discarded_invalid_format_candidates",
        "filled_from_race_card",
    ]


def test_guard_prediction_output_rejects_blocking_race_card_violation() -> None:
    report = guard_prediction_output(
        {
            "selected_horses": [
                {"chulNo": 1},
                {"chulNo": 2},
                {"chulNo": 9},
            ]
        },
        valid_chul_nos=[1, 2, 3],
    )

    assert report["accepted"] is False
    assert report["repairable"] is False
    assert report["blocking_issue_codes"] == ["horse_number_not_in_race_card"]
    assert report["final_predicted"] == [1, 2]


def test_guard_prediction_output_marks_duplicate_cleanup_as_repaired() -> None:
    report = guard_prediction_output(
        {
            "selected_horses": [
                {"chulNo": 2},
                {"chulNo": 2},
                {"chulNo": 1},
                {"chulNo": 3},
            ]
        },
        valid_chul_nos=[1, 2, 3],
    )

    assert report["accepted"] is True
    assert report["repaired"] is True
    assert report["final_predicted"] == [2, 1, 3]
    assert report["repair_action_codes"] == ["deduped_or_trimmed_candidates"]
