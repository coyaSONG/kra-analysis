"""T-30 release gate report helpers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from shared.t30_release_contract import t30_feature_names_by_bucket

T30_RELEASE_GATE_REPORT_VERSION = "t30-release-gate-report-v1"


def _payload_attr(payload: object, name: str, default: Any = None) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(name, default)
    return getattr(payload, name, default)


def _scan_key_paths(
    node: Any,
    target_keys: set[str],
    *,
    path: str = "",
) -> list[str]:
    paths: list[str] = []
    if isinstance(node, Mapping):
        for key, value in node.items():
            key_text = str(key)
            current_path = f"{path}.{key_text}" if path else key_text
            if key_text in target_keys:
                paths.append(current_path)
            paths.extend(_scan_key_paths(value, target_keys, path=current_path))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            current_path = f"{path}[{index}]"
            paths.extend(_scan_key_paths(item, target_keys, path=current_path))
    return paths


def _standard_payload(payload: object) -> Mapping[str, Any]:
    value = _payload_attr(payload, "standard_payload", payload)
    return value if isinstance(value, Mapping) else {}


def _race_id(payload: object) -> str:
    race_id = _payload_attr(payload, "race_id")
    if race_id:
        return str(race_id)
    standard = _standard_payload(payload)
    return str(standard.get("race_id") or "unknown")


def _freshness_status(payload: object) -> Mapping[str, Any]:
    status = _payload_attr(payload, "operational_cutoff_status", {})
    return status if isinstance(status, Mapping) else {}


def _entry_change_audit(payload: object) -> Mapping[str, Any]:
    audit = _payload_attr(payload, "entry_change_audit", {})
    return audit if isinstance(audit, Mapping) else {}


def build_t30_release_gate_report(
    payloads: Sequence[object],
) -> dict[str, Any]:
    """Build a deterministic safety-gate report for standardized T-30 payloads."""

    race_count = len(payloads)
    freshness_rows: list[dict[str, Any]] = []
    odds_paths_by_race: dict[str, list[str]] = {}
    audit_only_features = set(t30_feature_names_by_bucket("AUDIT_ONLY"))
    entry_source_counts: Counter[str] = Counter()
    changed_jockey_null_count = 0
    changed_jockey_horse_count = 0

    for payload in payloads:
        race_id = _race_id(payload)
        status = _freshness_status(payload)
        freshness_rows.append(
            {
                "race_id": race_id,
                "passed": status.get("passed") is True,
                "reason": status.get("reason"),
                "scheduled_start_at": status.get("scheduled_start_at"),
                "operational_cutoff_at": status.get("operational_cutoff_at"),
                "source_snapshot_at": status.get("source_snapshot_at"),
            }
        )

        standard = _standard_payload(payload)
        odds_paths = _scan_key_paths(standard, audit_only_features)
        if odds_paths:
            odds_paths_by_race[race_id] = odds_paths

        audit = _entry_change_audit(payload)
        source_key = "present" if audit.get("source_present") is True else "missing"
        entry_source_counts[source_key] += 1
        for horse in (
            standard.get("horses", []) if isinstance(standard, Mapping) else []
        ):
            if not isinstance(horse, Mapping) or "changed_jockey_flag" not in horse:
                continue
            changed_jockey_horse_count += 1
            if horse.get("changed_jockey_flag") is None:
                changed_jockey_null_count += 1

    freshness_failed = [row for row in freshness_rows if not row["passed"]]
    freshness_pass_rate = (
        (race_count - len(freshness_failed)) / race_count if race_count else 0.0
    )
    odds_path_count = sum(len(paths) for paths in odds_paths_by_race.values())

    return {
        "schema_version": T30_RELEASE_GATE_REPORT_VERSION,
        "race_count": race_count,
        "passed": race_count > 0 and not freshness_failed and odds_path_count == 0,
        "freshness": {
            "passed": race_count > 0 and not freshness_failed,
            "pass_rate": freshness_pass_rate,
            "failed_count": len(freshness_failed),
            "failed_races": freshness_failed,
        },
        "odds_exclusion": {
            "passed": odds_path_count == 0,
            "audit_only_features": sorted(audit_only_features),
            "violating_path_count": odds_path_count,
            "violating_paths_by_race": odds_paths_by_race,
        },
        "entry_change_coverage": {
            "source_present_race_count": entry_source_counts["present"],
            "source_missing_race_count": entry_source_counts["missing"],
            "changed_jockey_horse_count": changed_jockey_horse_count,
            "changed_jockey_null_count": changed_jockey_null_count,
            "changed_jockey_null_rate": (
                changed_jockey_null_count / changed_jockey_horse_count
                if changed_jockey_horse_count
                else 0.0
            ),
        },
    }
