"""Normalize observed official results without guessing exceptional start codes."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from shared.kra_race_identity import MEET_NAMES, validate_race_identity

SOURCE_ID = "kra_api214_1_result_observation"


def _integer(value: Any, minimum: int, maximum: int) -> int:
    if type(value) is int:
        result = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        result = int(value)
    else:
        raise ValueError("invalid_result_integer")
    if not minimum <= result <= maximum:
        raise ValueError("result_integer_out_of_range")
    return result


def normalize_result_rows(
    rows: list[dict[str, Any]],
    *,
    meet: int,
    race_date: str,
    entry_rosters: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    validate_race_identity(meet, race_date, 1)
    records, gates, horses = [], set(), set()
    for row in rows:
        raw_meet = row.get("meet")
        physical = MEET_NAMES.get(raw_meet) if isinstance(raw_meet, str) else None
        missing_venue = raw_meet in (None, "")
        if missing_venue:
            if entry_rosters is None:
                raise ValueError("missing_result_venue")
            physical = meet
        elif physical is None:
            physical = _integer(raw_meet, 1, 4)
        day = str(_integer(row.get("rcDate"), 20000101, 20991231))
        race_no = _integer(row.get("rcNo"), 1, 20)
        if physical != meet or day != race_date:
            raise ValueError("result_date_or_venue_mismatch")
        number = _integer(row.get("chulNo"), 1, 20)
        horse_id = str(_integer(row.get("hrNo"), 1, 99_999_999))
        race_id = f"{day}_{physical}_{race_no}"
        if (race_id, number) in gates or (race_id, horse_id) in horses:
            raise ValueError("duplicate_result_runner_or_horse")
        gates.add((race_id, number))
        horses.add((race_id, horse_id))
        rank, elapsed = row.get("ord"), row.get("rcTime")
        note = row.get("ordBigo")
        if note is not None and not isinstance(note, str):
            raise ValueError("invalid_result_note_type")
        if any(type(v) not in (str, int, float, type(None)) for v in (rank, elapsed)):
            raise ValueError("invalid_result_status_type")
        if any(isinstance(v, float) and not math.isfinite(v) for v in (rank, elapsed)):
            raise ValueError("nonfinite_result_status")
        try:
            ranked = _integer(rank, 1, 20)
        except ValueError:
            ranked = None
        try:
            seconds = float(elapsed)
        except (TypeError, ValueError):
            seconds = None
        finished = (
            ranked is not None
            and seconds is not None
            and math.isfinite(seconds)
            and seconds > 0
            and note in (None, "", "-")
        )
        records.append(
            {
                "race_id": race_id,
                "chul_no": number,
                "horse_id": horse_id,
                "raw_horse_id": row["hrNo"],
                "raw_meet": raw_meet,
                "venue_identity_basis": "api26_full_day_roster"
                if missing_venue
                else "api214_row",
                "raw_ord": rank,
                "raw_rc_time": elapsed,
                "raw_ord_bigo": note,
                "evidence": "ranked_finish_observed" if finished else "unresolved",
            }
        )
    records.sort(key=lambda row: (int(row["race_id"].split("_")[2]), row["chul_no"]))
    if entry_rosters is not None:
        actual = {(r["race_id"], r["chul_no"], r["horse_id"]) for r in records}
        expected = set()
        for race_id, entries in entry_rosters.items():
            for entry in entries:
                key = (
                    race_id,
                    _integer(entry["chulNo"], 1, 20),
                    str(_integer(entry["hrNo"], 1, 99_999_999)),
                )
                if key in expected:
                    raise ValueError("duplicate_result_binding_entry")
                expected.add(key)
        if not actual or actual != expected:
            raise ValueError("result_entry_roster_mismatch")
    return {
        "source_id": SOURCE_ID,
        "row_count": len(records),
        "race_counts": dict(sorted(Counter(row["race_id"] for row in records).items())),
        "evidence_counts": dict(Counter(row["evidence"] for row in records)),
        "population_status": "api_reported_rows" if records else "empty_unconfirmed",
        "complete_actual_start_history_verified": False,
        "historical_pre_race_availability_verified": False,
        "records": records,
    }
