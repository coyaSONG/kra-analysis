"""Rule-table-backed normalization for prereace horse entries."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

HORSE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "chul_no": ("chul_no", "chulNo", "horse_no"),
    "hr_no": ("hr_no", "hrNo"),
    "hr_name": ("hr_name", "hrName", "horse_name"),
    "jk_no": ("jk_no", "jkNo"),
    "jk_name": ("jk_name", "jkName"),
    "tr_no": ("tr_no", "trNo"),
    "tr_name": ("tr_name", "trName"),
    "ow_no": ("ow_no", "owNo"),
    "ow_name": ("ow_name", "owName"),
    "age": ("age",),
    "sex": ("sex", "gender"),
    "name": ("name", "country"),
    "rank": ("rank", "class_rank"),
    "rating": ("rating",),
    "wg_budam": ("wg_budam", "wgBudam", "burden_weight"),
    "wg_budam_bigo": ("wg_budam_bigo", "wgBudamBigo"),
    "wg_hr": ("wg_hr", "wgHr"),
    "win_odds": ("win_odds", "winOdds"),
    "plc_odds": ("plc_odds", "plcOdds"),
    "ilsu": ("ilsu",),
    "hr_tool": ("hr_tool", "hrTool"),
}

DETAIL_FIELD_NAMES: tuple[str, ...] = (
    "hrDetail",
    "jkDetail",
    "trDetail",
    "jkStats",
    "owDetail",
    "training",
)

RATING_MAX_ALLOWED = 140
WG_BUDAM_MIN_ALLOWED = 40.0
WG_BUDAM_MAX_ALLOWED = 65.0
WEIGHT_MIN_ALLOWED = 200
WEIGHT_MAX_ALLOWED = 650
WEIGHT_DELTA_MIN_ALLOWED = -40
WEIGHT_DELTA_MAX_ALLOWED = 40
WIN_ODDS_MAX_ALLOWED = 300.0
PLC_ODDS_MAX_ALLOWED = 100.0

RULE_TABLE_FIELD_PATHS: frozenset[str] = frozenset(
    {
        "horses[].chul_no",
        "horses[].hr_no",
        "horses[].hr_name",
        "horses[].jk_no",
        "horses[].jk_name",
        "horses[].tr_no",
        "horses[].tr_name",
        "horses[].ow_no",
        "horses[].ow_name",
        "horses[].age",
        "horses[].sex",
        "horses[].name",
        "horses[].rank",
        "horses[].rating",
        "horses[].wg_budam",
        "horses[].wg_budam_bigo",
        "horses[].wg_hr",
        "horses[].win_odds",
        "horses[].plc_odds",
        "horses[].ilsu",
        "horses[].hr_tool",
        "horses[].weight",
        "horses[].weight_delta",
        "horses[].country",
        "horses[].hrDetail",
        "horses[].jkDetail",
        "horses[].trDetail",
        "horses[].jkStats",
        "horses[].owDetail",
        "horses[].training",
    }
)

_SENTINEL_NULL_STRINGS = frozenset({"-", "--", "없음", "미상", "n/a", "na"})
_MISSING_DETAIL_FLAGS: dict[str, str] = {
    "hrDetail": "hrdetail_missing",
    "jkDetail": "jkdetail_missing",
    "trDetail": "trdetail_missing",
    "jkStats": "jkstats_missing",
    "owDetail": "owdetail_missing",
    "training": "training_missing",
}
_JOIN_TIMING_META_KEYS: tuple[str, ...] = ("join_timing", "__join_timing__")
_SEX_BUCKETS: dict[str, str] = {
    "수": "수",
    "수컷": "수",
    "m": "수",
    "male": "수",
    "암": "암",
    "암컷": "암",
    "f": "암",
    "female": "암",
    "거": "거",
    "거세": "거",
    "g": "거",
    "gelding": "거",
}


def normalize_prerace_horse_entry(
    source: dict[str, Any],
    *,
    entry_finalized_at: datetime | None = None,
    join_timing_audit: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize one horse row into the canonical prereace schema."""

    working_source, join_timing_flags = _apply_join_timing_guard(
        source,
        entry_finalized_at=entry_finalized_at,
        audit=join_timing_audit,
    )
    normalized: dict[str, Any] = {}
    flags: set[str] = set(join_timing_flags)

    normalized["chul_no"] = _normalize_positive_int(
        _first_present_value(working_source, HORSE_FIELD_ALIASES["chul_no"])
    )
    if normalized["chul_no"] is None:
        flags.add("core_missing")

    for field in ("hr_no", "jk_no", "tr_no", "ow_no"):
        raw = _first_present_value(working_source, HORSE_FIELD_ALIASES[field])
        value = _normalize_identifier(raw)
        normalized[field] = value
        if value is None:
            flags.add("core_missing")
        elif raw is not None and str(raw).strip() != value:
            flags.add("id_normalized")

    for field in ("hr_name", "jk_name", "tr_name", "ow_name", "rank"):
        normalized[field] = _normalize_string(
            _first_present_value(working_source, HORSE_FIELD_ALIASES[field])
        )
        if normalized[field] is None:
            flags.add("core_missing")

    age = _normalize_positive_int(
        _first_present_value(working_source, HORSE_FIELD_ALIASES["age"])
    )
    normalized["age"] = age
    if age is None:
        flags.add("core_missing")
        if _first_present_value(working_source, HORSE_FIELD_ALIASES["age"]) not in (
            None,
            "",
        ):
            flags.add("age_invalid")

    sex_raw = _first_present_value(working_source, HORSE_FIELD_ALIASES["sex"])
    normalized["sex"] = _normalize_sex_bucket(sex_raw, flags)
    if normalized["sex"] is None:
        flags.add("core_missing")

    normalized["name"] = _normalize_string(
        _first_present_value(working_source, HORSE_FIELD_ALIASES["name"])
    )
    if normalized["name"] is None:
        flags.add("core_missing")
        normalized["country"] = None
        flags.add("country_missing")
    else:
        normalized["country"] = normalized["name"]

    rating_raw = _first_present_value(working_source, HORSE_FIELD_ALIASES["rating"])
    rating = _normalize_nonnegative_int(rating_raw)
    if rating is not None and rating > RATING_MAX_ALLOWED:
        rating = None
        flags.add("rating_outlier")
    normalized["rating"] = rating
    if rating is None and rating_raw not in (None, ""):
        if "rating_outlier" not in flags:
            flags.add("rating_parse_failed")
    if rating == 0:
        flags.add("rating_known_false")

    wg_budam_raw = _first_present_value(working_source, HORSE_FIELD_ALIASES["wg_budam"])
    wg_budam = _normalize_positive_float(wg_budam_raw)
    if wg_budam is not None and not (
        WG_BUDAM_MIN_ALLOWED <= wg_budam <= WG_BUDAM_MAX_ALLOWED
    ):
        wg_budam = None
        flags.add("wg_budam_outlier")
    normalized["wg_budam"] = wg_budam
    if wg_budam is None:
        flags.add("core_missing")
        if wg_budam_raw not in (None, ""):
            if "wg_budam_outlier" not in flags:
                flags.add("wg_budam_invalid")

    wg_budam_bigo = _normalize_string(
        _first_present_value(working_source, HORSE_FIELD_ALIASES["wg_budam_bigo"])
    )
    if wg_budam_bigo is not None and _is_sentinel(wg_budam_bigo):
        wg_budam_bigo = None
        flags.add("budam_note_missing")
    normalized["wg_budam_bigo"] = wg_budam_bigo

    wg_hr = _normalize_string(
        _first_present_value(working_source, HORSE_FIELD_ALIASES["wg_hr"])
    )
    if wg_hr is not None and _is_sentinel(wg_hr):
        wg_hr = None
    normalized["wg_hr"] = wg_hr

    explicit_weight = _normalize_positive_int(working_source.get("weight"))
    if explicit_weight is not None:
        normalized["weight"] = explicit_weight
    else:
        normalized["weight"] = parse_body_weight_from_wg_hr(wg_hr)
    if normalized["weight"] is not None and not (
        WEIGHT_MIN_ALLOWED <= normalized["weight"] <= WEIGHT_MAX_ALLOWED
    ):
        normalized["weight"] = None
        flags.add("weight_outlier")
    if normalized["weight"] is None:
        flags.add("weight_missing")
        if wg_hr not in (None, "") and "weight_outlier" not in flags:
            flags.add("wg_hr_parse_failed")

    normalized["weight_delta"] = parse_weight_delta_from_wg_hr(wg_hr)
    if normalized["weight_delta"] is not None and not (
        WEIGHT_DELTA_MIN_ALLOWED
        <= normalized["weight_delta"]
        <= WEIGHT_DELTA_MAX_ALLOWED
    ):
        normalized["weight_delta"] = None
        flags.add("weight_delta_outlier")
    if normalized["weight_delta"] is None:
        flags.add("weight_delta_missing")
        if (
            wg_hr not in (None, "")
            and "(" in str(wg_hr)
            and ")" in str(wg_hr)
            and "weight_delta_outlier" not in flags
        ):
            flags.add("weight_delta_parse_failed")

    for field in ("win_odds", "plc_odds"):
        raw = _first_present_value(working_source, HORSE_FIELD_ALIASES[field])
        odds_value = _normalize_market_odds(
            raw,
            flags,
            field_name=field,
            maximum=(
                WIN_ODDS_MAX_ALLOWED if field == "win_odds" else PLC_ODDS_MAX_ALLOWED
            ),
        )
        normalized[field] = odds_value

    ilsu_raw = _first_present_value(working_source, HORSE_FIELD_ALIASES["ilsu"])
    ilsu = _normalize_nonnegative_int(ilsu_raw)
    if ilsu is not None:
        normalized["ilsu"] = ilsu
    else:
        flags.add("ilsu_missing")
        if ilsu_raw not in (None, ""):
            flags.add("ilsu_parse_failed")

    hr_tool = _normalize_string(
        _first_present_value(working_source, HORSE_FIELD_ALIASES["hr_tool"])
    )
    if hr_tool is not None:
        normalized["hr_tool"] = hr_tool
    else:
        flags.add("hr_tool_missing")

    for detail_name in DETAIL_FIELD_NAMES:
        normalized[detail_name] = _normalize_detail_block(
            detail_name, working_source.get(detail_name), flags
        )

    normalized["normalization_flags"] = sorted(flags)
    return normalized


def _apply_join_timing_guard(
    source: dict[str, Any],
    *,
    entry_finalized_at: datetime | None,
    audit: list[dict[str, Any]] | None,
) -> tuple[dict[str, Any], set[str]]:
    if entry_finalized_at is None:
        return source, set()

    timing_meta = _extract_join_timing_meta(source)
    if not timing_meta:
        return source, set()

    guarded = {**source}
    flags: set[str] = set()
    record_key = (
        _normalize_positive_int(
            _first_present_value(source, HORSE_FIELD_ALIASES["chul_no"])
        )
        or _normalize_identifier(
            _first_present_value(source, HORSE_FIELD_ALIASES["hr_no"])
        )
        or "unknown"
    )

    for detail_name in DETAIL_FIELD_NAMES:
        block_meta = timing_meta.get(detail_name)
        block_value = guarded.get(detail_name)
        if not isinstance(block_meta, dict) or not isinstance(block_value, dict):
            continue

        row_created_at = _parse_iso_datetime(
            block_meta.get("row_created_at") or block_meta.get("basis_at")
        )
        if row_created_at is not None and row_created_at > entry_finalized_at:
            guarded[detail_name] = {}
            flags.add(f"{detail_name.lower()}_blocked_post_entry")
            if audit is not None:
                audit.append(
                    {
                        "record_key": str(record_key),
                        "target_path": f"horses[].{detail_name}",
                        "action": "block_row",
                        "reason_code": "join_row_after_entry_finalized_at",
                        "basis_at": row_created_at.isoformat(),
                        "entry_finalized_at": entry_finalized_at.isoformat(),
                    }
                )
            continue

        field_created_at = block_meta.get("field_created_at")
        if not isinstance(field_created_at, dict):
            continue

        blocked_fields = sorted(
            field_name
            for field_name, raw_timestamp in field_created_at.items()
            if field_name in block_value
            and (parsed_timestamp := _parse_iso_datetime(raw_timestamp)) is not None
            and parsed_timestamp > entry_finalized_at
        )
        if not blocked_fields:
            continue

        guarded_block = {**block_value}
        for field_name in blocked_fields:
            guarded_block.pop(field_name, None)
        guarded[detail_name] = guarded_block
        flags.add(f"{detail_name.lower()}_fields_blocked_post_entry")
        if audit is not None:
            audit.append(
                {
                    "record_key": str(record_key),
                    "target_path": f"horses[].{detail_name}",
                    "action": "block_fields",
                    "reason_code": "join_fields_after_entry_finalized_at",
                    "blocked_fields": blocked_fields,
                    "entry_finalized_at": entry_finalized_at.isoformat(),
                }
            )

    return guarded, flags


def _extract_join_timing_meta(source: dict[str, Any]) -> dict[str, Any]:
    for key in _JOIN_TIMING_META_KEYS:
        value = source.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_detail_block(name: str, value: Any, flags: set[str]) -> dict[str, Any]:
    data = _ensure_dict(value)
    if not data:
        flags.add(_MISSING_DETAIL_FLAGS[name])
        return {}

    normalized = _normalize_trimmed_dict(data)
    if name == "jkDetail":
        for key in ("birthday", "debut", "sp_date"):
            if key in normalized:
                normalized[key] = _normalize_date_like(normalized.get(key))
    elif name == "trDetail":
        if "birthday" in normalized:
            normalized["birthday"] = _normalize_date_like(normalized.get("birthday"))
        if "age" in normalized:
            normalized["age"] = _normalize_nonnegative_int(normalized.get("age"))
    elif name == "jkStats":
        normalized = _normalize_numeric_dict(normalized)
        if not normalized:
            flags.add("jkstats_parse_failed")
            return {}
    elif name == "owDetail":
        for key in ("ow_no", "owner_no"):
            if key in normalized:
                normalized[key] = _normalize_identifier(normalized.get(key))

    return normalized


def _normalize_numeric_dict(data: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            normalized[key] = _normalize_numeric_dict(value)
            continue
        if isinstance(value, list):
            normalized[key] = value
            continue
        if value in (None, ""):
            normalized[key] = None
            continue
        if isinstance(value, (int, float)) and value >= 0:
            normalized[key] = value
            continue
        text = _normalize_string(value)
        if text is None:
            normalized[key] = None
            continue
        number = _parse_nonnegative_number(text)
        normalized[key] = number if number is not None else text
    return normalized


def _normalize_trimmed_dict(data: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            normalized[key] = _normalize_trimmed_dict(value)
        elif isinstance(value, list):
            normalized[key] = [
                _normalize_trimmed_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            normalized[key] = (
                _normalize_string(value) if isinstance(value, str) else value
            )
    return normalized


def _normalize_market_odds(
    value: Any,
    flags: set[str],
    *,
    field_name: str,
    maximum: float,
) -> float | None:
    parsed = _safe_float_or_none(value)
    if parsed is None:
        if value not in (None, ""):
            flags.add("odds_parse_failed")
        flags.add("market_signal_missing")
        if field_name == "win_odds":
            flags.add("popularity_unusable")
        return None
    if parsed <= 0:
        flags.add("market_signal_missing")
        if field_name == "win_odds":
            flags.add("popularity_unusable")
        return None
    if parsed > maximum:
        flags.add(f"{field_name}_outlier")
        flags.add("market_signal_missing")
        if field_name == "win_odds":
            flags.add("popularity_unusable")
        return None
    return parsed


def _normalize_sex_bucket(value: Any, flags: set[str]) -> str | None:
    normalized = _normalize_string(value)
    if normalized is None:
        return None
    bucket = _SEX_BUCKETS.get(normalized.lower(), _SEX_BUCKETS.get(normalized))
    if bucket is None:
        flags.add("sex_bucketed")
        return "기타"
    if bucket != normalized:
        flags.add("sex_bucketed")
    return bucket


def _normalize_identifier(value: Any) -> str | None:
    normalized = _normalize_string(value)
    if normalized is None:
        return None
    if normalized.endswith(".0"):
        stripped = normalized[:-2]
        return stripped or None
    return normalized


def _normalize_positive_int(value: Any) -> int | None:
    normalized = _safe_int_or_none(value)
    if normalized is None or normalized <= 0:
        return None
    return normalized


def _normalize_nonnegative_int(value: Any) -> int | None:
    normalized = _safe_int_or_none(value)
    if normalized is None or normalized < 0:
        return None
    return normalized


def _normalize_positive_float(value: Any) -> float | None:
    normalized = _safe_float_or_none(value)
    if normalized is None or normalized <= 0:
        return None
    return normalized


def _normalize_date_like(value: Any) -> str | None:
    normalized = _normalize_string(value)
    if normalized is None or _is_sentinel(normalized):
        return None
    digits = "".join(ch for ch in normalized if ch.isdigit())
    return digits if len(digits) == 8 else None


def parse_body_weight_from_wg_hr(value: Any) -> int | None:
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


def parse_weight_delta_from_wg_hr(value: Any) -> int | None:
    normalized = _normalize_string(value)
    if normalized is None:
        return None
    match = re.search(r"\(([+-]?\d+)\)", normalized)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _parse_nonnegative_number(value: str) -> int | float | None:
    if any(char in value for char in (".", "%")):
        try:
            parsed_float = float(value.replace("%", ""))
        except ValueError:
            return None
        return parsed_float if parsed_float >= 0 else None
    if value.isdigit():
        return int(value)
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return int(parsed) if parsed.is_integer() else parsed


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


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _is_sentinel(value: str) -> bool:
    return value.strip().lower() in _SENTINEL_NULL_STRINGS


def _first_present_value(source: dict[str, Any], aliases: Iterable[str]) -> Any:
    for alias in aliases:
        if alias in source and source[alias] not in (None, ""):
            return source[alias]
    for alias in aliases:
        if alias in source:
            return source[alias]
    return None


def _ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
