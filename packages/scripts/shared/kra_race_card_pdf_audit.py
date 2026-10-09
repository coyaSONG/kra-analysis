"""Fail-closed entry joins and cutoff checks for race-card PDF research rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from shared.entry_snapshot_metadata import KST
from shared.kra_race_card_pdf import normalize_horse_name
from shared.operational_cutoff import (
    classify_source_snapshot_for_t30,
    normalize_scheduled_start_time,
)

AUDIT_VERSION = "kra-race-card-pdf-audit-v1"


def _aware_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, (str, datetime)):
        return None
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _runner_number(value: Any) -> int | None:
    if type(value) is int:
        number = value
    elif isinstance(value, str) and value.isascii() and value.isdigit():
        number = int(value)
    else:
        return None
    return number if 1 <= number <= 20 else None


def audit_race_card_snapshot(
    parsed: dict[str, Any],
    *,
    collected_at: str | datetime | None,
    scheduled_start_time: str | int | None = None,
    entries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit feature rows only when parsing, both captures, and every join pass."""
    reasons: list[str] = []
    if parsed.get("parser_status") != "parsed":
        reasons.append("parser_not_validated")
    captured = _aware_timestamp(collected_at)
    cutoff = classify_source_snapshot_for_t30(
        race_date=parsed.get("race_date"),
        scheduled_start_time=scheduled_start_time,
        source_snapshot_at=captured,
    )
    if not cutoff.passed:
        reasons.append(cutoff.reason)
    schedule = normalize_scheduled_start_time(scheduled_start_time)
    pdf_schedule = parsed.get("scheduled_start_time_from_pdf")
    if not pdf_schedule:
        reasons.append("missing_pdf_schedule")
    elif schedule and pdf_schedule != schedule:
        reasons.append("schedule_mismatch")

    rows = parsed.get("rows") or []
    if not rows:
        reasons.append("no_pdf_rows")
    if captured:
        capture_date = captured.astimezone(KST).strftime("%Y%m%d")
        for row in rows:
            dates = [row.get("gate_training_date")]
            dates.extend(
                item.get("date") for item in row.get("recent_listed_treatments", [])
            )
            if any(date and date > capture_date for date in dates):
                reasons.append("event_after_capture_date")
    if any(row.get("issues") for row in rows):
        reasons.append("horse_panel_issues")

    entry_map: dict[int, dict[str, Any]] = {}
    entry_capture = None
    if not isinstance(entries, dict):
        reasons.append("missing_entry_snapshot")
    else:
        if any(
            entries.get(key) != parsed.get(key)
            for key in ("meet", "race_date", "race_no")
        ):
            reasons.append("entry_race_identity_mismatch")
        entry_schedule = normalize_scheduled_start_time(
            entries.get("scheduled_start_time")
        )
        if not entry_schedule:
            reasons.append("missing_entry_schedule")
        elif schedule and entry_schedule != schedule:
            reasons.append("entry_schedule_mismatch")
        entry_capture = _aware_timestamp(entries.get("collected_at"))
        entry_cutoff = classify_source_snapshot_for_t30(
            race_date=parsed.get("race_date"),
            scheduled_start_time=scheduled_start_time,
            source_snapshot_at=entry_capture,
        )
        if not entry_cutoff.passed:
            reasons.append(f"entry_{entry_cutoff.reason}")
        entry_rows = entries.get("entries")
        if not isinstance(entry_rows, list) or not entry_rows:
            reasons.append("missing_entry_rows")
        else:
            for entry in entry_rows:
                if not isinstance(entry, dict):
                    reasons.append("invalid_entry_identity")
                    continue
                number = _runner_number(entry.get("chulNo"))
                name = entry.get("hrName")
                if (
                    number is None
                    or not isinstance(name, str)
                    or not normalize_horse_name(name)
                ):
                    reasons.append("invalid_entry_identity")
                    continue
                if number in entry_map:
                    reasons.append("duplicate_entry_runner")
                entry_map[number] = entry

    horse_ids = [
        str(entry["hrNo"]) for entry in entry_map.values() if entry.get("hrNo")
    ]
    if len(horse_ids) != len(set(horse_ids)):
        reasons.append("duplicate_entry_horse_id")

    joined_rows = []
    seen_numbers: set[int] = set()
    name_mismatches: list[int] = []
    for row in rows:
        number = _runner_number(row.get("chulNo"))
        if number is None or number in seen_numbers:
            reasons.append("invalid_or_duplicate_pdf_runner")
            continue
        seen_numbers.add(number)
        entry = entry_map.get(number)
        if entry is None:
            continue
        if normalize_horse_name(str(row.get("hrName") or "")) != normalize_horse_name(
            entry["hrName"]
        ):
            name_mismatches.append(number)
            continue
        joined_rows.append({**row, "hrNo": entry.get("hrNo")})
    missing_pdf = sorted(set(entry_map) - seen_numbers)
    missing_entries = sorted(seen_numbers - set(entry_map))
    if missing_pdf or missing_entries or name_mismatches:
        reasons.append("incomplete_or_mismatched_entry_join")
    if len(joined_rows) != len(rows) or len(joined_rows) != len(entry_map):
        reasons.append("join_not_one_to_one_complete")
    reasons = sorted(set(reasons))
    available_at = (
        max(captured, entry_capture).isoformat() if captured and entry_capture else None
    )
    return {
        "audit_version": AUDIT_VERSION,
        "eligible_for_prerace_features": not reasons,
        "reasons": reasons,
        "pdf_timing": cutoff.to_dict(),
        "entry_collected_at": entry_capture.isoformat() if entry_capture else None,
        "features_available_at": available_at,
        "pdf_horse_count": len(rows),
        "entry_horse_count": len(entry_map),
        "joined_horse_count": len(joined_rows),
        "missing_pdf_runner_numbers": missing_pdf,
        "missing_entry_runner_numbers": missing_entries,
        "name_mismatch_runner_numbers": name_mismatches,
        "feature_rows": joined_rows if not reasons else [],
        "model_promoted": False,
    }
