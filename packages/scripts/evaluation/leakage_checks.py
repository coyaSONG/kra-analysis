"""Leakage checks for post-race fields in evaluation inputs."""

from __future__ import annotations

import re
from typing import Any

# --- 구간 통과 데이터 필드 자동 생성 ---
# 패턴: {prefix}G{1-8}f{suffix}, {prefix}S1f{suffix}, {prefix}_{1-4}c{suffix}
# prefix: sj(서울지방), bu(부산경남), se(서울)
# suffix: Ord(순위), AccTime(누적시간), GTime(구간시간)
_PREFIXES = ("sj", "bu", "se")
_GATES = tuple(f"G{i}f" for i in range(1, 9)) + ("S1f",)
_CORNERS = tuple(f"_{i}c" for i in range(1, 5))
_SUFFIXES = ("Ord", "AccTime", "GTime")

_SECTIONAL_FIELDS = frozenset(
    f"{prefix}{segment}{suffix}"
    for prefix in _PREFIXES
    for segment in (*_GATES, *_CORNERS)
    for suffix in _SUFFIXES
)

# 경주 결과/사후 확정 필드
_RESULT_FIELDS = frozenset(
    {
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
        "diffUnit",
        "rankRise",
    }
)

FORBIDDEN_POST_RACE_FIELDS = _RESULT_FIELDS | _SECTIONAL_FIELDS

# 패턴 기반 2차 검증 (명시적 목록에 없는 필드도 감지)
_SECTIONAL_PATTERN = re.compile(
    r"^(sj|bu|se)(G[1-8]f|S[12]f|_[1-4]c)(Ord|AccTime|GTime)$"
)


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _is_forbidden(key: str) -> bool:
    """명시적 목록 + 패턴 기반 2차 검증."""
    if key in FORBIDDEN_POST_RACE_FIELDS:
        return True
    return bool(_SECTIONAL_PATTERN.match(key))


def _scan_forbidden_fields(obj: Any, path: str, issues: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if _is_forbidden(key) and _is_meaningful(value):
                issues.add(current_path)
            _scan_forbidden_fields(value, current_path, issues)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _scan_forbidden_fields(item, f"{path}[{idx}]", issues)


def check_detailed_results_for_leakage(
    detailed_results: list[dict[str, Any]],
) -> dict[str, Any]:
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
