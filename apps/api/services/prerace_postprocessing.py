"""Post-processing rules for prereace collection payloads."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT = _PROJECT_ROOT / "packages" / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from shared.entry_snapshot_metadata import (  # noqa: E402
    build_entry_snapshot_metadata,
    snapshot_meta_dict,
)

from adapters.kra_response_adapter import KRAResponseAdapter  # noqa: E402
from services.prerace_field_tagging import build_source_field_tags  # noqa: E402
from utils.prerace_entry_normalizer import normalize_prerace_horse_entry  # noqa: E402

SCHEMA_VERSION = "prerace-source-v1"
JOIN_TIMING_AUDIT_VERSION = "prerace-join-timing-audit-v1"

_ALLOWED_STATUS = frozenset({"success", "partial_failure"})
_REQUIRED_RACE_PLAN_FIELDS = ("rank", "budam", "rc_dist", "age_cond")
_OPTIONAL_RACE_PLAN_FIELDS = (
    "sex_cond",
    "sch_st_time",
    "chaksun1",
    "chaksun2",
    "chaksun3",
    "chaksun4",
    "chaksun5",
)
_REQUIRED_TRACK_FIELDS = ("weather", "track", "water_percent")
_OPTIONAL_TRACK_FIELDS = (
    "temperature",
    "humidity",
    "wind_direction",
    "wind_speed",
)
_REQUIRED_HORSE_FIELDS = (
    "chul_no",
    "hr_no",
    "hr_name",
    "jk_no",
    "jk_name",
    "tr_no",
    "tr_name",
    "ow_no",
    "ow_name",
    "age",
    "sex",
    "name",
    "rank",
    "rating",
    "wg_budam",
    "wg_budam_bigo",
    "wg_hr",
    "win_odds",
    "plc_odds",
)
_OPTIONAL_HORSE_FIELDS = ("ilsu", "hr_tool")
_HORSE_DETAIL_FIELDS = (
    "hrDetail",
    "jkDetail",
    "trDetail",
    "jkStats",
    "owDetail",
    "training",
)
_CANCELLED_ROW_ALIASES: dict[str, tuple[str, ...]] = {
    "race_date": ("race_date", "rcDate"),
    "race_no": ("race_no", "rcNo"),
    "meet": ("meet",),
    "chul_no": ("chul_no", "chulNo"),
}


def normalize_prerace_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize collected race payload into the canonical prereace schema."""

    entry_finalized_at_raw = payload.get("entry_finalized_at")
    entry_finalized_at = _parse_iso_datetime_or_none(entry_finalized_at_raw)
    join_timing_blocked_targets: list[dict[str, Any]] = []
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "race_date": _normalize_race_date(
            payload.get("race_date") or payload.get("date")
        ),
        "race_no": _safe_int_or_none(
            payload.get("race_no") or payload.get("race_number")
        ),
        "date": _normalize_race_date(payload.get("date") or payload.get("race_date")),
        "meet": _normalize_meet(payload.get("meet")),
        "race_number": _safe_int_or_none(
            payload.get("race_number") or payload.get("race_no")
        ),
        "race_info": _ensure_dict(payload.get("race_info")),
        "race_plan": _normalize_race_plan(payload.get("race_plan")),
        "track": _normalize_track(payload.get("track")),
        "cancelled_horses": _normalize_cancelled_horses(
            payload.get("cancelled_horses")
        ),
        "horses": _normalize_horses(
            payload.get("horses"),
            entry_finalized_at=entry_finalized_at,
            join_timing_blocked_targets=join_timing_blocked_targets,
        ),
        "failed_horses": _normalize_failed_horses(payload.get("failed_horses")),
        "status": _normalize_status(payload.get("status")),
        "collected_at": _normalize_iso_datetime(payload.get("collected_at")),
    }
    if entry_finalized_at_raw is not None or join_timing_blocked_targets:
        normalized["join_timing_audit"] = {
            "audit_version": JOIN_TIMING_AUDIT_VERSION,
            "entry_finalized_at": (
                entry_finalized_at.isoformat()
                if entry_finalized_at is not None
                else None
            ),
            "guard_applied": entry_finalized_at is not None,
            "guard_skipped_reason": (
                None
                if entry_finalized_at is not None
                or entry_finalized_at_raw in (None, "")
                else "invalid_entry_finalized_at"
            ),
            "blocked_target_count": len(join_timing_blocked_targets),
            "blocked_targets": join_timing_blocked_targets,
        }
    normalized["snapshot_meta"] = snapshot_meta_dict(
        build_entry_snapshot_metadata(
            race_date=normalized["race_date"],
            basic_data=normalized,
            row_collected_at=normalized["collected_at"],
            entry_finalized_at_override=entry_finalized_at,
        )
    )
    normalized["source_field_tags"] = build_source_field_tags(normalized)
    return normalized


def validate_prerace_payload(payload: dict[str, Any]) -> list[str]:
    """Validate canonical prereace payload and return human-readable issues."""

    issues: list[str] = []

    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version must be prerace-source-v1")

    race_date = payload.get("race_date")
    if race_date is None:
        issues.append("race_date is required and must be YYYYMMDD")
    if payload.get("date") != race_date:
        issues.append("date must match race_date")

    race_no = payload.get("race_no")
    race_number = payload.get("race_number")
    if race_no is None or race_no <= 0:
        issues.append("race_no must be a positive integer")
    if race_number != race_no:
        issues.append("race_number must match race_no")

    meet = payload.get("meet")
    if meet is None or meet <= 0:
        issues.append("meet must be a positive integer")

    if not _looks_like_iso_datetime(payload.get("collected_at")):
        issues.append("collected_at must be an ISO-8601 datetime")

    if payload.get("status") not in _ALLOWED_STATUS:
        issues.append("status must be success or partial_failure")

    failed_horses = payload.get("failed_horses")
    if not isinstance(failed_horses, list):
        issues.append("failed_horses must be a list")
    elif failed_horses and payload.get("status") != "partial_failure":
        issues.append("status must be partial_failure when failed_horses is not empty")
    elif not failed_horses and payload.get("status") != "success":
        issues.append("status must be success when failed_horses is empty")

    race_info = payload.get("race_info")
    if not _has_items_envelope(race_info):
        issues.append("race_info must include response.body.items.item")
    else:
        metadata = KRAResponseAdapter.extract_race_metadata(race_info)
        if metadata.get("race_date") not in (None, race_date):
            issues.append("race_info race_date does not match top-level race_date")
        if metadata.get("race_no") not in (None, race_no):
            issues.append("race_info race_no does not match top-level race_no")
        if metadata.get("meet") not in (None, meet):
            issues.append("race_info meet does not match top-level meet")

    race_plan = payload.get("race_plan")
    if not isinstance(race_plan, dict):
        issues.append("race_plan must be an object")
    else:
        for field in _REQUIRED_RACE_PLAN_FIELDS:
            if race_plan.get(field) in (None, ""):
                issues.append(f"race_plan.{field} is required")

    track = payload.get("track")
    if not isinstance(track, dict):
        issues.append("track must be an object")
    else:
        for field in _REQUIRED_TRACK_FIELDS:
            if track.get(field) in (None, ""):
                issues.append(f"track.{field} is required")

    cancelled_horses = payload.get("cancelled_horses")
    if not isinstance(cancelled_horses, list):
        issues.append("cancelled_horses must be a list")

    horses = payload.get("horses")
    if not isinstance(horses, list) or not horses:
        issues.append("horses must be a non-empty list")
        return issues

    seen_chul_no: set[int] = set()
    for index, horse in enumerate(horses, start=1):
        prefix = f"horses[{index}]"
        if not isinstance(horse, dict):
            issues.append(f"{prefix} must be an object")
            continue

        required_core_fields = (
            "chul_no",
            "hr_no",
            "hr_name",
            "jk_no",
            "jk_name",
            "tr_no",
            "tr_name",
            "ow_no",
            "ow_name",
            "age",
            "sex",
            "name",
            "rank",
            "wg_budam",
        )
        for field in required_core_fields:
            if horse.get(field) in (None, ""):
                issues.append(f"{prefix}.{field} is required")

        chul_no = horse.get("chul_no")
        if not isinstance(chul_no, int) or chul_no <= 0:
            issues.append(f"{prefix}.chul_no must be a positive integer")
        elif chul_no in seen_chul_no:
            issues.append(f"{prefix}.chul_no duplicates another horse")
        else:
            seen_chul_no.add(chul_no)

        if horse.get("age") is not None and not isinstance(horse.get("age"), int):
            issues.append(f"{prefix}.age must be an integer")

        if horse.get("rating") is not None and not isinstance(horse.get("rating"), int):
            issues.append(f"{prefix}.rating must be an integer or null")

        for field in ("wg_budam",):
            value = horse.get(field)
            if not isinstance(value, (int, float)):
                issues.append(f"{prefix}.{field} must be numeric")
            elif value <= 0:
                issues.append(f"{prefix}.{field} must be greater than zero")

        for field in ("win_odds", "plc_odds"):
            value = horse.get(field)
            if value is not None and not isinstance(value, (int, float)):
                issues.append(f"{prefix}.{field} must be numeric or null")

        for field in (
            "hr_no",
            "hr_name",
            "jk_no",
            "jk_name",
            "tr_no",
            "tr_name",
            "ow_no",
            "ow_name",
            "sex",
            "name",
            "rank",
        ):
            value = horse.get(field)
            if not isinstance(value, str):
                issues.append(f"{prefix}.{field} must be a string")

        for field in ("wg_budam_bigo", "wg_hr"):
            value = horse.get(field)
            if value is not None and not isinstance(value, str):
                issues.append(f"{prefix}.{field} must be a string or null")

        if horse.get("weight") is not None and not isinstance(horse.get("weight"), int):
            issues.append(f"{prefix}.weight must be an integer or null")

        normalization_flags = horse.get("normalization_flags")
        if normalization_flags is not None and not (
            isinstance(normalization_flags, list)
            and all(isinstance(flag, str) for flag in normalization_flags)
        ):
            issues.append(f"{prefix}.normalization_flags must be a list of strings")

        for field in _HORSE_DETAIL_FIELDS:
            if not isinstance(horse.get(field), dict):
                issues.append(f"{prefix}.{field} must be an object")

    return issues


def normalize_and_validate_prerace_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a payload and raise when hard schema issues remain."""

    normalized = normalize_prerace_payload(payload)
    issues = validate_prerace_payload(normalized)
    if issues:
        raise ValueError("Invalid prereace payload: " + "; ".join(issues))
    return normalized


def _normalize_race_plan(source: Any) -> dict[str, Any]:
    data = _ensure_dict(source)
    normalized: dict[str, Any] = {
        "rank": _normalize_string(data.get("rank")),
        "budam": _normalize_string(data.get("budam")),
        "rc_dist": _safe_int_or_none(data.get("rc_dist") or data.get("rcDist")),
        "age_cond": _normalize_string(data.get("age_cond") or data.get("ageCond")),
    }
    optional_pairs = {
        "sex_cond": data.get("sex_cond") or data.get("sexCond"),
        "sch_st_time": data.get("sch_st_time") or data.get("schStTime"),
        "chaksun1": data.get("chaksun1"),
        "chaksun2": data.get("chaksun2"),
        "chaksun3": data.get("chaksun3"),
        "chaksun4": data.get("chaksun4"),
        "chaksun5": data.get("chaksun5"),
    }
    for field in _OPTIONAL_RACE_PLAN_FIELDS:
        value = optional_pairs.get(field)
        if value not in (None, ""):
            normalized[field] = _normalize_scalar(value)
    return normalized


def _normalize_track(source: Any) -> dict[str, Any]:
    data = _ensure_dict(source)
    normalized: dict[str, Any] = {
        "weather": _normalize_string(data.get("weather")),
        "track": _normalize_string(data.get("track")),
        "water_percent": _safe_int_or_none(
            data.get("water_percent") or data.get("waterPercent")
        ),
    }
    optional_pairs = {
        "temperature": data.get("temperature"),
        "humidity": data.get("humidity"),
        "wind_direction": data.get("wind_direction") or data.get("windDirection"),
        "wind_speed": data.get("wind_speed") or data.get("windSpeed"),
    }
    for field in _OPTIONAL_TRACK_FIELDS:
        value = optional_pairs.get(field)
        if value not in (None, ""):
            normalized[field] = _normalize_scalar(value)
    return normalized


def _normalize_cancelled_horses(source: Any) -> list[dict[str, Any]]:
    if not isinstance(source, list):
        return []

    normalized_rows: list[dict[str, Any]] = []
    for row in source:
        if not isinstance(row, dict):
            continue
        normalized = {**row}
        for field, aliases in _CANCELLED_ROW_ALIASES.items():
            value = _first_present_value(row, aliases)
            parsed: Any
            if field in {"race_no", "chul_no"}:
                parsed = _safe_int_or_none(value)
            elif field == "race_date":
                parsed = _normalize_race_date(value)
            elif field == "meet":
                parsed = _normalize_meet(value)
            else:
                parsed = value
            if parsed is not None:
                normalized[field] = parsed
        normalized_rows.append(normalized)

    return sorted(
        normalized_rows,
        key=lambda row: (
            row.get("chul_no") is None,
            row.get("chul_no") if row.get("chul_no") is not None else 999,
        ),
    )


def _normalize_horses(
    source: Any,
    *,
    entry_finalized_at: datetime | None = None,
    join_timing_blocked_targets: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(source, list):
        return []

    horses: list[dict[str, Any]] = []
    for horse in source:
        if not isinstance(horse, dict):
            continue
        horses.append(
            normalize_prerace_horse_entry(
                horse,
                entry_finalized_at=entry_finalized_at,
                join_timing_audit=join_timing_blocked_targets,
            )
        )

    return sorted(
        horses,
        key=lambda horse: (
            horse.get("chul_no") is None,
            horse.get("chul_no") if horse.get("chul_no") is not None else 999,
            horse.get("hr_no") or "",
        ),
    )


def _normalize_failed_horses(source: Any) -> list[dict[str, Any]]:
    if not isinstance(source, list):
        return []

    failures: list[dict[str, Any]] = []
    for failure in source:
        if not isinstance(failure, dict):
            continue
        failures.append(
            {
                "horse_no": _normalize_identifier(
                    failure.get("horse_no") or failure.get("horseNo")
                ),
                "horse_name": _normalize_string(
                    failure.get("horse_name") or failure.get("horseName")
                ),
                "error": _normalize_string(failure.get("error")) or "unknown_error",
            }
        )
    return failures


def _normalize_status(value: Any) -> str:
    normalized = _normalize_string(value)
    if normalized in _ALLOWED_STATUS:
        return normalized
    return "partial_failure" if normalized == "failed" else "success"


def _normalize_iso_datetime(value: Any) -> str:
    if value in (None, ""):
        return datetime.utcnow().isoformat()
    text = str(value).strip()
    if not text:
        return datetime.utcnow().isoformat()
    return text


def _parse_iso_datetime_or_none(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _looks_like_iso_datetime(value: Any) -> bool:
    if value in (None, ""):
        return False
    text = str(value).strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def _has_items_envelope(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        items = value["response"]["body"]["items"]["item"]
    except (KeyError, TypeError):
        return False
    return isinstance(items, list) or isinstance(items, dict)


def _ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_present_value(source: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in source and source[alias] not in (None, ""):
            return source[alias]
    for alias in aliases:
        if alias in source:
            return source[alias]
    return None


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_identifier(value: Any) -> str | None:
    normalized = _normalize_string(value)
    if normalized is None:
        return None
    if normalized.endswith(".0"):
        stripped = normalized[:-2]
        return stripped or None
    return normalized


def _normalize_race_date(value: Any) -> str | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    return digits if len(digits) == 8 else None


def _normalize_meet(value: Any) -> int | None:
    return KRAResponseAdapter._normalize_meet(value)


def _safe_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_body_weight(value: Any) -> int | None:
    if value is None:
        return None
    digits: list[str] = []
    for char in str(value).strip():
        if char.isdigit():
            digits.append(char)
            continue
        if digits:
            break
    return int("".join(digits)) if digits else None


def _normalize_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return value
