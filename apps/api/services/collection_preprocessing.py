"""Collection preprocessing helpers backed by the prereace rule engine."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

import structlog

from utils.prerace_entry_normalizer import normalize_prerace_horse_entry

logger = structlog.get_logger()

RULE_SCHEMA_VERSION = "prerace-entry-preprocessing-rules-v1"

_OPTIONAL_HORSE_FIELDS: tuple[str, ...] = ("ilsu", "hr_tool")


def preprocess_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Apply rule-engine-based preprocessing to collected race data."""
    horses_in = raw_data.get("horses", [])

    normalized_horses = [_normalize_horse(horse) for horse in horses_in]
    chul_no_counts: Counter[int] = Counter(
        horse["chul_no"]
        for horse in normalized_horses
        if horse.get("chul_no") is not None
    )

    active_horses, excluded_entries = _partition_horses(
        normalized_horses, chul_no_counts
    )
    audit = _build_preprocessing_audit(excluded_entries)

    return {
        **raw_data,
        "horses": active_horses,
        "excluded_horses": len(excluded_entries),
        "preprocessing_timestamp": datetime.now(UTC).isoformat(),
        "preprocessing_audit": audit,
    }


def _normalize_horse(horse: Any) -> dict[str, Any]:
    if not isinstance(horse, dict):
        return {"normalization_flags": ["core_missing"]}
    try:
        return normalize_prerace_horse_entry(horse)
    except Exception as exc:
        logger.warning("Horse normalization failed", error=str(exc))
        return {"normalization_flags": ["core_missing"]}


def _partition_horses(
    normalized_horses: list[dict[str, Any]],
    chul_no_counts: Counter[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for horse in normalized_horses:
        flags = list(horse.get("normalization_flags", []))
        reasons = _exclusion_reasons(horse, flags, chul_no_counts)

        body = _shape_horse_for_output(horse, flags)

        if reasons:
            excluded.append(
                {
                    "hr_no": horse.get("hr_no"),
                    "chul_no": horse.get("chul_no"),
                    "reasons": reasons,
                }
            )
        else:
            active.append(body)

    return active, excluded


def _exclusion_reasons(
    horse: dict[str, Any],
    flags: list[str],
    chul_no_counts: Counter[int],
) -> list[str]:
    reasons: list[str] = []
    chul_no = horse.get("chul_no")
    if isinstance(chul_no, int) and chul_no_counts.get(chul_no, 0) > 1:
        reasons.append("chul_no_duplicate")
    if "age_invalid" in flags:
        reasons.append("age_invalid")
    if "wg_budam_outlier" in flags:
        reasons.append("wg_budam_outlier")
    if not reasons and "core_missing" in flags:
        reasons.append("core_missing")
    return reasons


def _shape_horse_for_output(horse: dict[str, Any], flags: list[str]) -> dict[str, Any]:
    body = {key: value for key, value in horse.items() if key != "normalization_flags"}
    for field in _OPTIONAL_HORSE_FIELDS:
        body.setdefault(field, None)
    body["preprocessing"] = {"flags": flags}
    return body


def _build_preprocessing_audit(
    excluded_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    reason_counts: Counter[str] = Counter()
    for entry in excluded_entries:
        reason_counts.update(entry["reasons"])

    return {
        "rule_schema_version": RULE_SCHEMA_VERSION,
        "excluded_entries": excluded_entries,
        "reason_counts": dict(reason_counts),
    }
