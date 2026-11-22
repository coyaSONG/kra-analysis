"""Describe literal routine starting-practice annotations on an isolated panel."""

import unicodedata
from datetime import date

from shared.entry_snapshot_metadata import KST
from shared.kra_race_card_pdf import GATE

from autoresearch.prerace_hash_witness import timestamp

PRACTICE = "\ucd9c\ubc1c\uc870\uad50"
ASSISTANCE = "\ucd9c\ubc1c\ubcf4\uc870"
DATE_BEFORE_OBSERVATION_DAY = "printed_day_before_collection_day"


def _printed_practice(lines):
    routine, assistance = [], []
    for line in lines:
        clean = " ".join(unicodedata.normalize("NFKC", line).split())
        if clean.startswith(PRACTICE):
            routine.append(clean)
        elif clean.startswith(ASSISTANCE):
            assistance.append(clean)
    return routine, assistance


def observation(panel_text, *, collected_at, race_date):
    """Record the literal source and calendar evidence, never a count or score."""
    capture_day = timestamp(collected_at).astimezone(KST).date()
    card_day = date.fromisoformat(race_date)
    lines, assistance = _printed_practice(panel_text.splitlines())
    record = {
        "routine_practice_lines": lines,
        "separate_assistance_lines": assistance,
        "stated_day": None,
        "stated_rider": None,
        "stated_status": None,
        "completed_calendar_days_before_observation": None,
    }
    if not lines:
        return {**record, "state": "routine_line_not_observed"}
    if len(lines) != 1:
        return {**record, "state": "conflicting_practice_lines"}
    if lines[0].replace(" ", "") == f"{PRACTICE}:":
        return {**record, "state": "routine_line_printed_blank"}
    match = GATE.fullmatch(lines[0])
    if match is None:
        return {**record, "state": "unreadable_practice_line"}
    try:
        day = date.fromisoformat(f"20{match[1]}")
    except ValueError:
        return {**record, "state": "invalid_stated_day"}
    record.update(
        stated_day=day.isoformat(),
        stated_rider=match[2].strip() or None,
        stated_status=match[3].strip() or None,
    )
    if day > card_day:
        state = "stated_day_after_card_day"
    elif day > capture_day:
        state = "stated_day_after_collection_day"
    elif day == capture_day:
        state = "same_collection_day_event_clock_unknown"
    else:
        state = DATE_BEFORE_OBSERVATION_DAY
        record["completed_calendar_days_before_observation"] = (capture_day - day).days
    return {**record, "state": state}


def coverage(states):
    """Report all declarations and whether dates distinguish any two runners."""
    if not states:
        raise ValueError("empty_original_field")
    days = [
        state["stated_day"]
        for state in states
        if state["state"] == DATE_BEFORE_OBSERVATION_DAY
    ]
    return {
        "retained_declarations": len(states),
        "earlier_day_annotations": len(days),
        "all_declarations_with_earlier_day": len(days) == len(states),
        "at_least_two_distinct_earlier_days": len(set(days)) >= 2,
    }
