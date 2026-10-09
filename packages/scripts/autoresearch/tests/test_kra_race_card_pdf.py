"""Parser tests for supported layouts and exclusion of historical columns."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_race_card_pdf import (
    NUMERIC_FIELDS,
    normalize_horse_name,
    parse_horse_panel,
    parse_race_card_pdf,
    race_card_url,
)

from autoresearch.tests.race_card_pdf_fixture import (
    GATE_TEXT,
    HORSE_NAME,
    PANEL_TEXT,
    TRAINING_TEXT,
    make_card_pdf,
)


@pytest.mark.parametrize(
    "meet,directory,prefix", [(1, "seoul", "s"), (2, "jeju", "j"), (3, "busan", "b")]
)
def test_urls_have_the_official_meeting_prefix(meet, directory, prefix):
    assert (
        race_card_url(meet, "20260627", 1)
        == f"https://race.kra.co.kr/down/pdf/{directory}/chulma/{prefix}_run_hr_260627_01.pdf"
    )


@pytest.mark.parametrize(
    "meet,date,number",
    [
        (0, "20260627", 1),
        (True, "20260627", 1),
        (1, "20260230", 1),
        (1, "260627", 1),
        (1, "19990627", 1),
        (1, "20260627", 0),
        (1, "20260627", 21),
        (1, "20260627", True),
    ],
)
def test_invalid_identifiers_are_rejected(meet, date, number):
    with pytest.raises(ValueError):
        race_card_url(meet, date, number)


def panel(text=PANEL_TEXT):
    return parse_horse_panel(
        chul_no=1, horse_name=HORSE_NAME, text=text, race_date="20260627"
    )


def test_training_counts_and_explicit_swimming_zero():
    row = panel()
    assert row["training_count"] == 16
    assert row["training_minutes"] == 242
    assert row["training_gu_count"] == 18
    assert row["training_seup_count"] == 1
    assert row["swimming_count"] == row["swimming_laps"] == 0
    assert row["trainer_wins"] == 52
    assert row["trainer_win_rate"] == pytest.approx(0.083)
    assert row["training_window_days"] is None
    assert row["gate_training_date"] == "20260501"
    assert row["recent_listed_treatments"][0]["printed_count"] == 1
    assert row["hrNo"] is None
    assert not row["issues"]


def test_jeju_window_is_explicit_and_unprinted_fields_stay_missing():
    row = panel(
        "2\uc8fc\uc870\uad50: 7\ud68c 108\ubd84(\uad00/\uc870)\n260503\uc815\uce58"
    )
    assert row["training_window_days"] == 14
    assert row["training_count"] == 7
    assert row["training_riders"] == ["\uad00", "\uc870"]
    assert row["training_gu_count"] is None
    assert row["swimming_count"] is None
    assert row["recent_listed_treatments"][0]["printed_count"] is None


def test_missing_fields_are_not_fabricated_as_zero():
    row = panel(GATE_TEXT)
    assert all(row[key] is None for key in NUMERIC_FIELDS)
    assert row["recent_listed_treatments"] == []


def test_truncated_training_keeps_only_the_complete_numeric_prefix():
    row = panel("2\uc8fc\uc870\uad50: 7\ud68c 96\ubd84(\uad00/\uc870/\ub2e4\uc601")
    assert row["training_count"] == 7
    assert row["training_minutes"] == 96
    assert row["training_window_days"] == 14
    assert row["training_summary_truncated"] is True
    assert row["training_riders"] is None
    assert row["training_gu_count"] is None
    assert not row["issues"]


def test_duplicate_summary_is_not_silently_selected():
    assert "ambiguous_training" in panel(TRAINING_TEXT + "\n" + TRAINING_TEXT)["issues"]


@pytest.mark.parametrize(
    "date,reason",
    [("260630", "event_after_race_date"), ("260231", "invalid_event_date")],
)
def test_bad_event_dates_block_the_panel(date, reason):
    assert (
        reason in panel(TRAINING_TEXT + "\n" + date + "\uc0b0\ud1b11\ud68c")["issues"]
    )


@pytest.mark.parametrize(
    "history",
    ["\u2460 1\ud14c\uc2a4\ud2b8 1:03.2", "260617-2R \uc8fc\ud589\uc2ec\uc0ac"],
)
def test_accidental_history_in_current_panel_is_detected(history):
    assert "history_in_current_panel" in panel(TRAINING_TEXT + "\n" + history)["issues"]


def test_name_normalization_only_changes_unicode_form_and_spacing():
    assert normalize_horse_name(" \ud14c \uc2a4 \ud2b8 \ub9c8 ") == HORSE_NAME
    assert normalize_horse_name("A-B") == "A-B"


@pytest.mark.parametrize("meet", [1, 2, 3])
def test_real_pdf_round_trip_excludes_history(meet):
    pytest.importorskip("pdfplumber")
    result = parse_race_card_pdf(
        make_card_pdf(meet=meet), meet=meet, race_date="20260627", race_no=1
    )
    assert result["parser_status"] == "parsed", result["issues"]
    assert result["horse_count"] == 2
    assert result["scheduled_start_time_from_pdf"] == "1035"
    assert result["rows"][0]["hrName"] == HORSE_NAME
    assert result["rows"][0]["training_count"] == (7 if meet == 2 else 16)
    assert result["rows"][0]["recent_listed_treatments"][0]["printed_count"] == 1
    assert len(result["rows"][0]["recent_listed_treatments"]) == 1
    assert result["treatment_history_is_exhaustive"] is False
    assert result["current_race_results_extracted"] is False


def test_stale_or_wrong_race_pdf_has_no_usable_rows():
    pytest.importorskip("pdfplumber")
    result = parse_race_card_pdf(
        make_card_pdf(), meet=1, race_date="20260628", race_no=1
    )
    assert result["parser_status"] == "blocked"
    assert result["rows"] == []
    assert "document_identity_mismatch_or_missing" in result["issues"]


@pytest.mark.parametrize("meet", [1, 2, 3])
def test_two_digit_runner_numbers_joined_to_names_are_not_missed(meet):
    pytest.importorskip("pdfplumber")
    result = parse_race_card_pdf(
        make_card_pdf(meet=meet, horse_numbers=(10, 11), joined_headers=True),
        meet=meet,
        race_date="20260627",
        race_no=1,
    )
    assert result["parser_status"] == "parsed", result["issues"]
    assert [row["chulNo"] for row in result["rows"]] == [10, 11]
    assert all(row["hrName"] == HORSE_NAME for row in result["rows"])


def test_duplicate_pdf_runner_is_blocked():
    pytest.importorskip("pdfplumber")
    result = parse_race_card_pdf(
        make_card_pdf(horse_numbers=(1, 1)), meet=1, race_date="20260627", race_no=1
    )
    assert "duplicate_runner_numbers" in result["issues"]


def test_html_masquerading_as_pdf_is_rejected():
    with pytest.raises(ValueError, match="invalid_pdf_bytes"):
        parse_race_card_pdf(
            b"<html>error</html>", meet=1, race_date="20260627", race_no=1
        )
