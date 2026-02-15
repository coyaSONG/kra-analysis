"""Leakage checks for post-race fields in evaluation inputs."""

from __future__ import annotations

from typing import Any

FORBIDDEN_POST_RACE_FIELDS = {
    "rank",
    "ord",
    "rcTime",
    "result",
    "resultTime",
    "finish_position",
    "top3",
    "actual_result",
    "dividend",
    "payout",
}


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _scan_forbidden_fields(obj: Any, path: str, issues: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_POST_RACE_FIELDS and _is_meaningful(value):
                issues.add(current_path)
            _scan_forbidden_fields(value, current_path, issues)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _scan_forbidden_fields(item, f"{path}[{idx}]", issues)


def check_detailed_results_for_leakage(detailed_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Check detailed evaluation records for post-race leakage fields."""

    issues: set[str] = set()
    for row in detailed_results:
        race_id = row.get("race_id", "unknown")
        race_data = row.get("race_data") or {}
        _scan_forbidden_fields(race_data, f"{race_id}.race_data", issues)

    sorted_issues = sorted(issues)
    return {
        "passed": len(sorted_issues) == 0,
        "issues": sorted_issues,
        "checked_races": len(detailed_results),
        "forbidden_fields": sorted(FORBIDDEN_POST_RACE_FIELDS),
    }
