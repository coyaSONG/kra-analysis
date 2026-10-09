"""Strict availability and complete horse joins, without reading race results."""

import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_race_card_pdf import parse_horse_panel
from shared.kra_race_card_pdf_audit import audit_race_card_snapshot

from autoresearch.tests.race_card_pdf_fixture import HORSE_NAME, PANEL_TEXT


@pytest.fixture
def parsed():
    return {
        "meet": 1,
        "race_date": "20260627",
        "race_no": 1,
        "parser_status": "parsed",
        "scheduled_start_time_from_pdf": "1035",
        "rows": [
            parse_horse_panel(
                chul_no=number,
                horse_name=HORSE_NAME + str(number),
                text=PANEL_TEXT,
                race_date="20260627",
            )
            for number in (1, 2, 3)
        ],
    }


@pytest.fixture
def entries():
    return {
        "meet": 1,
        "race_date": "20260627",
        "race_no": 1,
        "collected_at": "2026-06-27T09:30:00+09:00",
        "scheduled_start_time": "1035",
        "entries": [
            {
                "chulNo": str(number),
                "hrName": HORSE_NAME + str(number),
                "hrNo": f"hr-{number}",
            }
            for number in (1, 2, 3)
        ],
    }


def audit(parsed, entries, *, captured="2026-06-27T10:00:00+09:00", schedule="1035"):
    return audit_race_card_snapshot(
        parsed, collected_at=captured, scheduled_start_time=schedule, entries=entries
    )


def test_complete_pre_cutoff_join_emits_features_without_promoting_a_model(
    parsed, entries
):
    original = deepcopy(parsed)
    result = audit(parsed, entries)
    assert result["eligible_for_prerace_features"] is True
    assert result["joined_horse_count"] == 3
    assert result["feature_rows"][0]["hrNo"] == "hr-1"
    assert result["features_available_at"] == "2026-06-27T01:00:00+00:00"
    assert result["model_promoted"] is False
    assert parsed == original


@pytest.mark.parametrize(
    "captured,reason",
    [
        ("2026-06-27T10:05:01+09:00", "source_after_cutoff"),
        ("2026-10-10T00:00:00+09:00", "source_after_cutoff"),
        (None, "missing_source_snapshot_at"),
        ("2026-06-27T10:00:00", "missing_source_snapshot_at"),
        ("not-a-date", "missing_source_snapshot_at"),
    ],
)
def test_missing_naive_and_late_captures_never_emit_rows(
    parsed, entries, captured, reason
):
    result = audit(parsed, entries, captured=captured)
    assert not result["eligible_for_prerace_features"]
    assert reason in result["reasons"]
    assert result["feature_rows"] == []


def test_exact_cutoff_is_allowed(parsed, entries):
    assert audit(parsed, entries, captured="2026-06-27T10:05:00+09:00")[
        "eligible_for_prerace_features"
    ]


@pytest.mark.parametrize(
    "capture,reason",
    [
        (None, "entry_missing_source_snapshot_at"),
        ("2026-06-27T10:06:00+09:00", "entry_source_after_cutoff"),
    ],
)
def test_entry_snapshot_has_its_own_timing_guard(parsed, entries, capture, reason):
    entries["collected_at"] = capture
    result = audit(parsed, entries)
    assert reason in result["reasons"]
    assert not result["feature_rows"]


@pytest.mark.parametrize(
    "key,value", [("meet", 2), ("race_date", "20260628"), ("race_no", 2)]
)
def test_wrong_race_identity_is_blocked(parsed, entries, key, value):
    entries[key] = value
    assert "entry_race_identity_mismatch" in audit(parsed, entries)["reasons"]


@pytest.mark.parametrize(
    "schedule,reason",
    [
        (None, "missing_scheduled_start"),
        ("1036", "schedule_mismatch"),
        ("2500", "invalid_scheduled_start"),
    ],
)
def test_schedule_must_be_present_valid_and_consistent(
    parsed, entries, schedule, reason
):
    result = audit(parsed, entries, schedule=schedule)
    assert reason in result["reasons"]
    assert not result["feature_rows"]


def test_entry_schedule_cannot_be_overridden_by_cli_assumption(parsed, entries):
    entries["scheduled_start_time"] = "1030"
    assert "entry_schedule_mismatch" in audit(parsed, entries)["reasons"]


def test_missing_entry_schedule_blocks(parsed, entries):
    entries.pop("scheduled_start_time")
    assert "missing_entry_schedule" in audit(parsed, entries)["reasons"]


def test_name_only_join_is_not_accepted(parsed, entries):
    entries["entries"][0]["hrName"] = HORSE_NAME + "2"
    result = audit(parsed, entries)
    assert result["name_mismatch_runner_numbers"] == [1]
    assert not result["feature_rows"]


def test_normalized_spacing_is_accepted_on_matching_runner(parsed, entries):
    entries["entries"][0]["hrName"] = " ".join(HORSE_NAME + "1")
    assert audit(parsed, entries)["eligible_for_prerace_features"]


def test_missing_horse_is_not_dropped_to_improve_coverage(parsed, entries):
    parsed["rows"].pop()
    result = audit(parsed, entries)
    assert result["missing_pdf_runner_numbers"] == [3]
    assert not result["feature_rows"]


def test_pdf_has_an_unmatched_runner(parsed, entries):
    entries["entries"].pop()
    result = audit(parsed, entries)
    assert result["missing_entry_runner_numbers"] == [3]
    assert not result["feature_rows"]


@pytest.mark.parametrize(
    "entry",
    [None, {}, {"chulNo": True, "hrName": HORSE_NAME}, {"chulNo": 1, "hrName": ""}],
)
def test_malformed_entry_rows_block(parsed, entries, entry):
    entries["entries"][0] = entry
    assert "invalid_entry_identity" in audit(parsed, entries)["reasons"]


def test_duplicate_entry_number_blocks(parsed, entries):
    entries["entries"].append(entries["entries"][0])
    assert "duplicate_entry_runner" in audit(parsed, entries)["reasons"]


def test_duplicate_horse_id_blocks(parsed, entries):
    entries["entries"][1]["hrNo"] = "hr-1"
    assert "duplicate_entry_horse_id" in audit(parsed, entries)["reasons"]


def test_duplicate_pdf_number_blocks(parsed, entries):
    parsed["rows"].append(parsed["rows"][0])
    assert "invalid_or_duplicate_pdf_runner" in audit(parsed, entries)["reasons"]


def test_unknown_parser_layout_blocks(parsed, entries):
    parsed["parser_status"] = "blocked"
    assert "parser_not_validated" in audit(parsed, entries)["reasons"]


def test_an_event_not_yet_observed_at_capture_blocks(parsed, entries):
    parsed["rows"][0]["gate_training_date"] = "20260627"
    result = audit(parsed, entries, captured="2026-06-26T23:00:00+09:00")
    assert "event_after_capture_date" in result["reasons"]


def test_missing_entries_blocks(parsed):
    assert "missing_entry_snapshot" in audit(parsed, None)["reasons"]


def test_optional_persistent_horse_id_is_not_fabricated(parsed, entries):
    for entry in entries["entries"]:
        entry.pop("hrNo")
    result = audit(parsed, entries)
    assert result["eligible_for_prerace_features"]
    assert all(row["hrNo"] is None for row in result["feature_rows"])
