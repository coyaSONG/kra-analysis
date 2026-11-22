import pytest

from autoresearch.gate_training_source import (
    ASSISTANCE,
    DATE_BEFORE_OBSERVATION_DAY,
    PRACTICE,
    coverage,
    observation,
)

CAPTURE = "2026-11-18T15:02:00Z"
RACE = "20261121"


def decode(*lines):
    return observation("\n".join(lines), collected_at=CAPTURE, race_date=RACE)


def test_calendar_uses_seoul_and_preserves_literal_operands():
    result = decode(f"{PRACTICE}:261118(\ud2b8\ub799,\uc591\ud638)")
    assert result["state"] == DATE_BEFORE_OBSERVATION_DAY
    assert result["completed_calendar_days_before_observation"] == 1
    assert result["stated_day"] == "2026-11-18"
    assert result["stated_status"] == "\uc591\ud638"
    assert result["stated_rider"] == "\ud2b8\ub799"


@pytest.mark.parametrize(
    ("stamp", "state"),
    [
        ("261119", "same_collection_day_event_clock_unknown"),
        ("261120", "stated_day_after_collection_day"),
        ("261122", "stated_day_after_card_day"),
        ("261131", "invalid_stated_day"),
    ],
)
def test_other_literal_dates_are_not_earlier_day_operands(stamp, state):
    row = decode(f"{PRACTICE}:{stamp}(x,y)")
    assert row["state"] == state
    assert row["completed_calendar_days_before_observation"] is None


def test_source_misses_are_not_zero_or_assistance_or_duplicate():
    cases = [
        ([f"{ASSISTANCE}:261118(x,y)"], "routine_line_not_observed"),
        ([f"{PRACTICE}:"], "routine_line_printed_blank"),
        ([f"{PRACTICE}:261118(x"], "unreadable_practice_line"),
        ([f"261011-3R {PRACTICE}:261110(x,y)"], "routine_line_not_observed"),
        ([f"{PRACTICE}:261118(x,y)"] * 2, "conflicting_practice_lines"),
    ]
    for lines, status in cases:
        row = decode(*lines)
        assert row["state"] == status
        assert row["completed_calendar_days_before_observation"] is None
    assert decode(cases[0][0][0])["separate_assistance_lines"] == cases[0][0]


def test_coverage_keeps_unknown_runner_and_does_not_invent_tie_breaker():
    one = decode(f"{PRACTICE}:261117(x,)")
    same = decode(f"{PRACTICE}:261117(,y)")
    two = decode(f"{PRACTICE}:261118(x,y)")
    blank = decode(f"{PRACTICE}:")
    assert coverage([one, same, blank]) == {
        "retained_declarations": 3,
        "earlier_day_annotations": 2,
        "all_declarations_with_earlier_day": False,
        "at_least_two_distinct_earlier_days": False,
    }
    assert coverage([one, same, two]) == {
        "retained_declarations": 3,
        "earlier_day_annotations": 3,
        "all_declarations_with_earlier_day": True,
        "at_least_two_distinct_earlier_days": True,
    }
    assert one["stated_status"] is None
    assert same["stated_rider"] is None
