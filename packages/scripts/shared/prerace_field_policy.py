"""출전표 확정 시점 필드 플래그 해석과 공통 필터.

학습/추론 파이프라인이 문서상의 `train_inference_flag` 값을 동일하게 해석하도록
경로 패턴 기반 정책을 코드로 고정한다.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from evaluation.leakage_checks import _is_forbidden

from shared.prerace_field_metadata_schema import (
    FIELD_METADATA_RULES,
    TRAIN_INFERENCE_FLAGS,
    match_field_metadata_rule,
    normalize_field_path,
)

FIELD_POLICY_VERSION = "prerace-field-policy-v1"

ALLOW = "ALLOW"
ALLOW_SNAPSHOT_ONLY = "ALLOW_SNAPSHOT_ONLY"
ALLOW_STORED_ONLY = "ALLOW_STORED_ONLY"
HOLD = "HOLD"
BLOCK = "BLOCK"
LABEL_ONLY = "LABEL_ONLY"
META_ONLY = "META_ONLY"

ALLOWED_FLAGS = frozenset((ALLOW, ALLOW_SNAPSHOT_ONLY, ALLOW_STORED_ONLY))
OPERATIONAL_DATASET_BLOCKING_FLAGS = frozenset((HOLD, BLOCK, LABEL_ONLY, META_ONLY))

FINAL_HOLD_FIELD_PATHS = frozenset(
    rule.field_path
    for rule in FIELD_METADATA_RULES
    if rule.train_inference_flag == HOLD and rule.match_type == "exact"
)
FINAL_BLOCKED_LEAF_FIELDS = frozenset(
    rule.field_path
    for rule in FIELD_METADATA_RULES
    if rule.train_inference_flag == BLOCK and rule.match_type == "leaf"
)
FINAL_BLOCKED_PREFIX_PATHS = frozenset(
    rule.field_path
    for rule in FIELD_METADATA_RULES
    if rule.train_inference_flag == BLOCK and rule.match_type == "prefix"
)
FINAL_LABEL_ONLY_FIELD_PATHS = frozenset(
    rule.field_path
    for rule in FIELD_METADATA_RULES
    if rule.train_inference_flag == LABEL_ONLY and rule.match_type == "exact"
)
FINAL_LABEL_ONLY_PREFIX_PATHS = frozenset(
    rule.field_path
    for rule in FIELD_METADATA_RULES
    if rule.train_inference_flag == LABEL_ONLY and rule.match_type == "prefix"
)
FINAL_META_ONLY_PREFIX_PATHS = frozenset(
    rule.field_path
    for rule in FIELD_METADATA_RULES
    if rule.train_inference_flag == META_ONLY and rule.match_type == "prefix"
)

OPERATIONAL_DATASET_CHECKLIST: tuple[dict[str, str], ...] = (
    {
        "rule_id": "allow_only_runtime_feature_flags",
        "flag": "ALL",
        "description": "최종 운영 데이터셋은 ALLOW/ALLOW_SNAPSHOT_ONLY/ALLOW_STORED_ONLY 플래그만 남아야 한다.",
    },
    {
        "rule_id": "exclude_hold_fields",
        "flag": HOLD,
        "description": "공개 시점 미검증/odds 의존 HOLD 필드는 운영 데이터셋에서 제거돼야 한다.",
    },
    {
        "rule_id": "exclude_block_fields",
        "flag": BLOCK,
        "description": "사후/누수 BLOCK 필드는 운영 데이터셋에서 제거돼야 한다.",
    },
    {
        "rule_id": "exclude_label_only_fields",
        "flag": LABEL_ONLY,
        "description": "정답/평가 전용 LABEL_ONLY 필드는 운영 데이터셋에서 제거돼야 한다.",
    },
    {
        "rule_id": "exclude_meta_only_fields",
        "flag": META_ONLY,
        "description": "감사/운영 메타 전용 META_ONLY 필드는 운영 데이터셋에서 제거돼야 한다.",
    },
)


def resolve_train_inference_flag(path: str) -> str:
    """필드 경로를 `train_inference_flag` 값으로 해석한다."""

    metadata_rule = match_field_metadata_rule(path)
    if metadata_rule is not None:
        return metadata_rule.train_inference_flag

    normalized_path = normalize_field_path(path)
    leaf_key = normalized_path.rsplit(".", 1)[-1]
    if _is_forbidden(leaf_key):
        return BLOCK
    return ALLOW


def describe_flag(flag: str) -> str:
    descriptions = {
        ALLOW: "출전표 확정 시점 기준으로 바로 입력 허용",
        ALLOW_SNAPSHOT_ONLY: "cutoff 이전 snapshot에 잠긴 값만 입력 허용",
        ALLOW_STORED_ONLY: "사전 정보지만 당시 저장본만 입력 허용",
        HOLD: "raw 저장과 연구는 가능하지만 최종 학습/추론 입력에서는 제외",
        BLOCK: "사후/누수 필드라서 입력 금지",
        LABEL_ONLY: "라벨/정답 전용",
        META_ONLY: "감사/운영 메타데이터 전용",
    }
    return descriptions.get(flag, "정의되지 않은 플래그")


def flag_is_allowed(
    flag: str,
    *,
    include_hold: bool = False,
    include_label: bool = False,
    include_meta: bool = False,
) -> bool:
    if flag in ALLOWED_FLAGS:
        return True
    if flag == HOLD:
        return include_hold
    if flag == LABEL_ONLY:
        return include_label
    if flag == META_ONLY:
        return include_meta
    return False


def filter_prerace_payload(
    payload: dict[str, Any] | None,
    *,
    include_hold: bool = False,
    include_label: bool = False,
    include_meta: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """정책 플래그에 따라 payload를 공통 필터링한다."""

    if not payload:
        return {}, _build_policy_report(
            include_hold=include_hold,
            include_label=include_label,
            include_meta=include_meta,
            encountered_flag_counts={},
            removed_by_flag={},
        )

    encountered_flag_counts: dict[str, int] = {}
    removed_by_flag: dict[str, list[str]] = {}

    def _record(flag: str) -> None:
        encountered_flag_counts[flag] = encountered_flag_counts.get(flag, 0) + 1

    def _remove(path: str, flag: str) -> None:
        removed_by_flag.setdefault(flag, []).append(path)

    def _walk(node: Any, path: str) -> Any:
        if isinstance(node, dict):
            filtered: dict[str, Any] = {}
            for key, value in node.items():
                current_path = f"{path}.{key}" if path else key
                flag = resolve_train_inference_flag(current_path)
                _record(flag)
                if not flag_is_allowed(
                    flag,
                    include_hold=include_hold,
                    include_label=include_label,
                    include_meta=include_meta,
                ):
                    _remove(normalize_field_path(current_path), flag)
                    continue

                if isinstance(value, (dict, list)):
                    filtered[key] = _walk(value, current_path)
                else:
                    filtered[key] = deepcopy(value)
            return filtered

        if isinstance(node, list):
            filtered_list: list[Any] = []
            for idx, item in enumerate(node):
                current_path = f"{path}[{idx}]"
                if isinstance(item, (dict, list)):
                    filtered_list.append(_walk(item, current_path))
                else:
                    filtered_list.append(deepcopy(item))
            return filtered_list

        return deepcopy(node)

    filtered_payload = _walk(payload, "")
    return filtered_payload, _build_policy_report(
        include_hold=include_hold,
        include_label=include_label,
        include_meta=include_meta,
        encountered_flag_counts=encountered_flag_counts,
        removed_by_flag=removed_by_flag,
    )


def validate_operational_dataset_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """최종 운영 데이터셋 payload가 차단 규칙을 만족하는지 검사한다."""

    _filtered_payload, policy_report = filter_prerace_payload(payload)
    violations_by_flag = {
        flag: policy_report["removed_by_flag"][flag]
        for flag in OPERATIONAL_DATASET_BLOCKING_FLAGS
        if policy_report["removed_by_flag"].get(flag)
    }

    checklist: list[dict[str, Any]] = []
    for item in OPERATIONAL_DATASET_CHECKLIST:
        flag = item["flag"]
        if flag == "ALL":
            passed = not violations_by_flag
            violations = policy_report["removed_paths"]
        else:
            violations = policy_report["removed_by_flag"].get(flag, [])
            passed = not violations

        checklist.append(
            {
                **item,
                "passed": passed,
                "violations": violations,
            }
        )

    return {
        "passed": not violations_by_flag,
        "policy_version": FIELD_POLICY_VERSION,
        "allowed_flags": sorted(ALLOWED_FLAGS),
        "blocking_flags": sorted(OPERATIONAL_DATASET_BLOCKING_FLAGS),
        "violations_by_flag": violations_by_flag,
        "violating_paths": sorted(
            {path for paths in violations_by_flag.values() for path in paths}
        ),
        "checklist": checklist,
        "catalog": {
            "hold_exact_paths": sorted(FINAL_HOLD_FIELD_PATHS),
            "blocked_leaf_fields": sorted(FINAL_BLOCKED_LEAF_FIELDS),
            "blocked_prefix_paths": sorted(FINAL_BLOCKED_PREFIX_PATHS),
            "label_only_exact_paths": sorted(FINAL_LABEL_ONLY_FIELD_PATHS),
            "label_only_prefix_paths": sorted(FINAL_LABEL_ONLY_PREFIX_PATHS),
            "meta_only_prefix_paths": sorted(FINAL_META_ONLY_PREFIX_PATHS),
        },
        "policy_report": policy_report,
    }


def _build_policy_report(
    *,
    include_hold: bool,
    include_label: bool,
    include_meta: bool,
    encountered_flag_counts: dict[str, int],
    removed_by_flag: dict[str, list[str]],
) -> dict[str, Any]:
    normalized_counts = {
        flag: encountered_flag_counts.get(flag, 0) for flag in TRAIN_INFERENCE_FLAGS
    }
    normalized_removed = {
        flag: sorted(set(removed_by_flag.get(flag, [])))
        for flag in TRAIN_INFERENCE_FLAGS
    }
    return {
        "policy_version": FIELD_POLICY_VERSION,
        "include_hold": include_hold,
        "include_label": include_label,
        "include_meta": include_meta,
        "encountered_flag_counts": normalized_counts,
        "removed_by_flag": normalized_removed,
        "removed_paths": sorted(
            {path for paths in normalized_removed.values() for path in paths}
        ),
    }
