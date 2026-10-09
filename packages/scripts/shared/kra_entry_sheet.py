"""Strict normalization of pre-race API26 entry-sheet observations."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from shared.kra_race_card_pdf import normalize_horse_name, validate_identity
from shared.operational_cutoff import normalize_scheduled_start_time

SOURCE_ID = "kra_api26_2_entry_sheet"
MEET_NAMES = {
    "\uc11c\uc6b8": 1,
    "\uc81c\uc8fc": 2,
    "\ubd80\uacbd": 3,
    "\ubd80\uc0b0\uacbd\ub0a8": 3,
}
START_TIME = re.compile(r"^(?:\ucd9c\ubc1c\s*:\s*)?(?:\d{3,4}|\d{1,2}:\d{2})$")


def _integer(value: Any, *, minimum: int, maximum: int) -> int:
    if type(value) is int:
        number = value
    elif isinstance(value, str) and value.isascii() and value.isdigit():
        number = int(value)
    else:
        raise ValueError("invalid_entry_integer")
    if not minimum <= number <= maximum:
        raise ValueError("entry_integer_out_of_range")
    return number


def parse_entry_sheet_page(
    payload: Any, *, page_no: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    """Require a complete page and the requested pagination metadata."""
    response = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(response, dict):
        raise ValueError("invalid_entry_response")
    header, body = response.get("header"), response.get("body")
    if not isinstance(header, dict) or header.get("resultCode") != "00":
        raise ValueError("entry_api_unsuccessful")
    if not isinstance(body, dict):
        raise ValueError("invalid_entry_body")
    total = _integer(body.get("totalCount"), minimum=0, maximum=10_000)
    if (
        _integer(body.get("pageNo"), minimum=1, maximum=100) != page_no
        or _integer(body.get("numOfRows"), minimum=1, maximum=1000) != page_size
    ):
        raise ValueError("entry_pagination_mismatch")
    items = body.get("items")
    rows = items.get("item") if isinstance(items, dict) else None
    if rows is None and total == 0 and items in (None, "", {}):
        rows = []
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("invalid_entry_items")
    expected = min(page_size, max(0, total - (page_no - 1) * page_size))
    if len(rows) != expected:
        raise ValueError("incomplete_entry_page")
    return rows, total


def build_entry_snapshot(
    rows: list[dict[str, Any]],
    *,
    meet: int,
    race_date: str,
    race_no: int,
    collected_at: datetime,
) -> dict[str, Any]:
    """Filter response identities, not the API's unreliable rc_no parameter."""
    validate_identity(meet, race_date, race_no)
    if collected_at.tzinfo is None or collected_at.utcoffset() is None:
        raise ValueError("entry_capture_requires_timezone")
    selected = []
    for row in rows:
        raw_meet = row.get("meet")
        meeting = MEET_NAMES.get(raw_meet) if isinstance(raw_meet, str) else None
        if meeting is None:
            meeting = _integer(raw_meet, minimum=1, maximum=3)
        date = str(_integer(row.get("rcDate"), minimum=20000101, maximum=20991231))
        number = _integer(row.get("rcNo"), minimum=1, maximum=20)
        if meeting != meet or date != race_date:
            raise ValueError("entry_date_or_meeting_mismatch")
        if number == race_no:
            selected.append(row)
    if not selected:
        raise ValueError("no_entries_for_requested_race")

    schedules: set[str] = set()
    declared_counts: set[int] = set()
    entries = []
    for row in selected:
        number = _integer(row.get("chulNo"), minimum=1, maximum=20)
        name, horse_id = row.get("hrName"), row.get("hrNo")
        if not isinstance(name, str) or not normalize_horse_name(name):
            raise ValueError("missing_entry_horse_name")
        if type(horse_id) is int and horse_id > 0:
            horse_id = str(horse_id)
        if (
            not isinstance(horse_id, str)
            or not re.fullmatch(r"[0-9]+", horse_id)
            or int(horse_id) == 0
        ):
            raise ValueError("invalid_entry_horse_id")
        start = str(row.get("stTime", "")).strip()
        schedule = normalize_scheduled_start_time(start)
        if not START_TIME.fullmatch(start) or not schedule:
            raise ValueError("invalid_entry_start_time")
        schedules.add(schedule)
        declared_counts.add(_integer(row.get("dusu"), minimum=1, maximum=20))
        entries.append({"chulNo": number, "hrName": name, "hrNo": horse_id})
    if len(schedules) != 1:
        raise ValueError("inconsistent_entry_start_times")
    if declared_counts != {len(entries)}:
        raise ValueError("incomplete_entry_field")
    if len({entry["chulNo"] for entry in entries}) != len(entries):
        raise ValueError("duplicate_entry_runner")
    if len({entry["hrNo"] for entry in entries}) != len(entries):
        raise ValueError("duplicate_entry_horse_id")
    return {
        "source_id": SOURCE_ID,
        "meet": meet,
        "race_date": race_date,
        "race_no": race_no,
        "collected_at": collected_at.astimezone(UTC).isoformat(),
        "scheduled_start_time": next(iter(schedules)),
        "declared_horse_count": len(entries),
        "entries": sorted(entries, key=lambda entry: entry["chulNo"]),
    }
