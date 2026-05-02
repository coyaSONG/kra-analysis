"""홀드아웃 스냅샷 시각/필터 매니페스트 생성 helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any

from shared.entry_snapshot_metadata import (
    EntrySnapshotMetadata,
    derive_or_restore_entry_snapshot_metadata,
)
from shared.entry_snapshot_metadata import (
    parse_snapshot_datetime as _parse_datetime,
)
from shared.prediction_input_schema import build_alternative_ranking_dataset_metadata
from shared.prerace_source_schema import TOP_LEVEL_REQUIRED_FIELDS
from shared.read_contract import RaceSnapshot

DATASET_MANIFEST_VERSION = "holdout-dataset-manifest-v1"
_TOP_LEVEL_ALLOWED_KEYS = frozenset((*TOP_LEVEL_REQUIRED_FIELDS, "failed_horses"))
_AUDIT_REQUIRED_LOG_FIELDS = (
    "race_id",
    "source_filter_basis",
    "timestamp_source",
    "timestamp_confidence",
    "replay_status",
    "include_in_strict_dataset",
    "hard_required_sources_present",
    "late_reissue_after_cutoff",
    "cutoff_unbounded",
)
_AUDIT_TIMESTAMP_CONFIDENCE_BY_SOURCE = {
    "source_revision": "high",
    "snapshot_collected_at": "medium",
    "derived_from_schedule": "low",
    "fallback_collected_only": "low",
}
_AUDIT_EXCLUDED_REPLAY_STATUSES = frozenset(
    {"partial_snapshot", "late_snapshot_unusable", "missing_timestamp"}
)
_AUDIT_RULES = (
    {
        "rule_id": "basis_locked_to_entry_finalized_at",
        "description": "모든 홀드아웃 경주는 source_filter_basis가 entry_finalized_at 이어야 한다.",
    },
    {
        "rule_id": "included_races_require_prerace_inputs",
        "description": "include_in_strict_dataset=true 인 경주는 hard-required source와 entry_finalized_at 로그를 모두 가져야 한다.",
    },
    {
        "rule_id": "included_races_must_be_pre_cutoff",
        "description": "operational_cutoff_at 이 있는 경우 entry_finalized_at 은 cutoff 이하이어야 한다.",
    },
    {
        "rule_id": "excluded_statuses_cannot_be_included",
        "description": "partial_snapshot, late_snapshot_unusable, missing_timestamp 상태는 strict 집계에 포함되면 안 된다.",
    },
    {
        "rule_id": "timestamp_source_and_confidence_must_match",
        "description": "timestamp_source 와 timestamp_confidence 조합은 고정된 허용 매핑을 따라야 한다.",
    },
    {
        "rule_id": "snapshot_ready_log_required_for_snapshot_source",
        "description": "timestamp_source=snapshot_collected_at 이면 snapshot_ready_at 로그가 필수다.",
    },
)
_AUDIT_VIOLATION_CATALOG = {
    "missing_log_field": "필수 감사 로그 필드가 비어 있거나 누락됨",
    "unexpected_source_filter_basis": "source_filter_basis가 entry_finalized_at 이 아님",
    "strict_without_required_sources": "strict 집계 포함 경주에 hard-required source가 빠짐",
    "missing_entry_finalized_at": "strict 집계 포함 경주에 entry_finalized_at 로그가 없음",
    "missing_operational_cutoff_at": "cutoff_unbounded=false 인데 operational_cutoff_at 이 없음",
    "missing_scheduled_start_at": "cutoff_unbounded=false 인데 scheduled_start_at 이 없음",
    "post_cutoff_snapshot": "entry_finalized_at 이 operational_cutoff_at 이후임",
    "excluded_status_marked_included": "제외 대상 replay_status가 strict 집계에 포함됨",
    "timestamp_confidence_mismatch": "timestamp_source 와 timestamp_confidence 조합이 규칙과 다름",
    "missing_snapshot_ready_at": "snapshot_collected_at 기반인데 snapshot_ready_at 로그가 없음",
    "entry_snapshot_timestamp_mismatch": "snapshot_collected_at 기반인데 entry_finalized_at 과 snapshot_ready_at 이 다름",
}


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def select_allowed_basic_data(basic_data: dict[str, Any] | None) -> dict[str, Any]:
    if not basic_data:
        return {}
    filtered: dict[str, Any] = {}
    for key in _TOP_LEVEL_ALLOWED_KEYS:
        if key in basic_data:
            filtered[key] = deepcopy(basic_data[key])
    return filtered


def derive_snapshot_timing(snapshot: RaceSnapshot) -> EntrySnapshotMetadata:
    return derive_or_restore_entry_snapshot_metadata(
        race_date=snapshot.race_date,
        basic_data=snapshot.basic_data,
        raw_data=snapshot.raw_data,
        row_collected_at=snapshot.collected_at,
        row_updated_at=snapshot.updated_at,
    )


def build_dataset_manifest(
    mode: str,
    created_at: str,
    races: list[dict[str, Any]],
) -> dict[str, Any]:
    strict_count = sum(1 for race in races if race.get("include_in_strict_dataset"))
    status_counts: dict[str, int] = {}
    for race in races:
        status = str(race.get("replay_status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1

    content = {
        "format_version": DATASET_MANIFEST_VERSION,
        "dataset": mode,
        "created_at": created_at,
        "race_count": len(races),
        "strict_race_count": strict_count,
        "dataset_metadata": build_alternative_ranking_dataset_metadata(
            source="offline_evaluation_snapshot",
            dataset_name=mode,
            requested_limit=None,
            race_ids=[
                str(race.get("race_id")) for race in races if race.get("race_id")
            ],
            with_past_stats=False,
        ),
        "filter_policy": {
            "source_filter_basis": "entry_finalized_at",
            "required_pre_cutoff": True,
            "hard_required_sources": [
                "API214_1",
                "API72_2",
                "API189_1",
                "API9_1",
            ],
            "payload_shape": "legacy-race-array+snapshot_meta",
        },
        "replay_status_counts": status_counts,
        "audit": audit_snapshot_manifest_races(races),
        "candidate_selection_audit": audit_candidate_selection_traces(races),
        "races": races,
    }
    digest = sha256(
        json.dumps(content["races"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    content["manifest_sha256"] = digest
    return content


def snapshot_meta_dict(timing: EntrySnapshotMetadata) -> dict[str, Any]:
    return timing.to_dict()


def _append_audit_violation(
    violations: list[dict[str, str]],
    violation_counts: dict[str, int],
    *,
    race_id: str,
    code: str,
    rule_id: str,
    message: str,
    severity: str = "error",
) -> None:
    violations.append(
        {
            "race_id": race_id,
            "code": code,
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
        }
    )
    violation_counts[code] = violation_counts.get(code, 0) + 1


def audit_snapshot_manifest_races(races: list[dict[str, Any]]) -> dict[str, Any]:
    """홀드아웃 경주별 출전표 확정 시점 감사 로그를 검증한다."""

    violations: list[dict[str, str]] = []
    violation_counts: dict[str, int] = {}

    for race in races:
        race_id = str(race.get("race_id") or "unknown")
        for field in _AUDIT_REQUIRED_LOG_FIELDS:
            if _is_blank(race.get(field)):
                _append_audit_violation(
                    violations,
                    violation_counts,
                    race_id=race_id,
                    code="missing_log_field",
                    rule_id="basis_locked_to_entry_finalized_at",
                    message=f"{field} 로그가 비어 있거나 누락됨",
                )

        include_in_strict_dataset = bool(race.get("include_in_strict_dataset"))
        hard_required_sources_present = bool(race.get("hard_required_sources_present"))
        cutoff_unbounded = bool(race.get("cutoff_unbounded"))

        source_filter_basis = str(race.get("source_filter_basis") or "")
        if source_filter_basis != "entry_finalized_at":
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="unexpected_source_filter_basis",
                rule_id="basis_locked_to_entry_finalized_at",
                message=f"source_filter_basis={source_filter_basis!r}",
            )

        entry_finalized_at = _parse_datetime(race.get("entry_finalized_at"))
        operational_cutoff_at = _parse_datetime(race.get("operational_cutoff_at"))
        scheduled_start_at = _parse_datetime(race.get("scheduled_start_at"))
        snapshot_ready_at = _parse_datetime(race.get("snapshot_ready_at"))

        if include_in_strict_dataset and not hard_required_sources_present:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="strict_without_required_sources",
                rule_id="included_races_require_prerace_inputs",
                message="strict 집계 포함 경주에 hard_required_sources_present=false",
            )

        if include_in_strict_dataset and entry_finalized_at is None:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="missing_entry_finalized_at",
                rule_id="included_races_require_prerace_inputs",
                message="strict 집계 포함 경주에 entry_finalized_at 이 없음",
            )

        if not cutoff_unbounded and operational_cutoff_at is None:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="missing_operational_cutoff_at",
                rule_id="included_races_must_be_pre_cutoff",
                message="cutoff_unbounded=false 인데 operational_cutoff_at 이 없음",
            )

        if not cutoff_unbounded and scheduled_start_at is None:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="missing_scheduled_start_at",
                rule_id="included_races_must_be_pre_cutoff",
                message="cutoff_unbounded=false 인데 scheduled_start_at 이 없음",
            )

        if (
            include_in_strict_dataset
            and operational_cutoff_at is not None
            and entry_finalized_at is not None
            and entry_finalized_at > operational_cutoff_at
        ):
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="post_cutoff_snapshot",
                rule_id="included_races_must_be_pre_cutoff",
                message=(
                    f"entry_finalized_at={race.get('entry_finalized_at')} > "
                    f"operational_cutoff_at={race.get('operational_cutoff_at')}"
                ),
            )

        replay_status = str(race.get("replay_status") or "")
        if (
            include_in_strict_dataset
            and replay_status in _AUDIT_EXCLUDED_REPLAY_STATUSES
        ):
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="excluded_status_marked_included",
                rule_id="excluded_statuses_cannot_be_included",
                message=f"replay_status={replay_status!r} 인데 include_in_strict_dataset=true",
            )

        timestamp_source = str(race.get("timestamp_source") or "")
        timestamp_confidence = str(race.get("timestamp_confidence") or "")
        expected_confidence = _AUDIT_TIMESTAMP_CONFIDENCE_BY_SOURCE.get(
            timestamp_source
        )
        if (
            expected_confidence is not None
            and timestamp_confidence != expected_confidence
        ):
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="timestamp_confidence_mismatch",
                rule_id="timestamp_source_and_confidence_must_match",
                message=(
                    f"timestamp_source={timestamp_source!r}, "
                    f"timestamp_confidence={timestamp_confidence!r}, "
                    f"expected={expected_confidence!r}"
                ),
            )

        if timestamp_source == "snapshot_collected_at" and snapshot_ready_at is None:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="missing_snapshot_ready_at",
                rule_id="snapshot_ready_log_required_for_snapshot_source",
                message="snapshot_collected_at 기반인데 snapshot_ready_at 로그가 없음",
            )

        if (
            timestamp_source == "snapshot_collected_at"
            and snapshot_ready_at is not None
            and entry_finalized_at is not None
            and entry_finalized_at != snapshot_ready_at
        ):
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="entry_snapshot_timestamp_mismatch",
                rule_id="snapshot_ready_log_required_for_snapshot_source",
                message=(
                    f"entry_finalized_at={race.get('entry_finalized_at')} != "
                    f"snapshot_ready_at={race.get('snapshot_ready_at')}"
                ),
            )

    return {
        "passed": len(violations) == 0,
        "checked_races": len(races),
        "required_log_fields": list(_AUDIT_REQUIRED_LOG_FIELDS),
        "inspection_rules": list(_AUDIT_RULES),
        "violation_catalog": dict(_AUDIT_VIOLATION_CATALOG),
        "violation_counts": violation_counts,
        "violations": violations,
    }


def audit_candidate_selection_traces(races: list[dict[str, Any]]) -> dict[str, Any]:
    """후보 보완/폴백 이후 최소 3두 보장과 추적 필드 존재 여부를 검증한다."""

    violations: list[dict[str, str]] = []
    violation_counts: dict[str, int] = {}
    checked_races = 0

    for race in races:
        candidate_filter = race.get("candidate_filter")
        if not isinstance(candidate_filter, dict):
            snapshot_meta = race.get("snapshot_meta", {})
            if isinstance(snapshot_meta, dict):
                candidate_filter = snapshot_meta.get("candidate_filter")
        if not isinstance(candidate_filter, dict):
            continue

        checked_races += 1
        race_id = str(race.get("race_id") or "unknown")
        final_validation = candidate_filter.get("final_candidate_validation", {})
        race_trace = candidate_filter.get("race_trace", {})

        if not isinstance(final_validation, dict):
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="missing_candidate_validation",
                rule_id="candidate_traceability_required",
                message="final_candidate_validation 블록이 누락됨",
            )
            continue

        if not isinstance(race_trace, dict):
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="missing_candidate_trace",
                rule_id="candidate_traceability_required",
                message="race_trace 블록이 누락됨",
            )
            continue

        if final_validation.get("minimum_candidate_met") is not True:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="minimum_candidate_not_met",
                rule_id="candidate_traceability_required",
                message=(
                    "보완/폴백 이후에도 최소 3두 후보 조건을 만족하지 못함: "
                    f"{final_validation!r}"
                ),
            )

        final_candidate_count = final_validation.get("final_candidate_count")
        if race_trace.get("final_candidate_count") != final_candidate_count:
            _append_audit_violation(
                violations,
                violation_counts,
                race_id=race_id,
                code="candidate_count_trace_mismatch",
                rule_id="candidate_traceability_required",
                message=(
                    f"race_trace.final_candidate_count={race_trace.get('final_candidate_count')!r} "
                    f"!= final_candidate_validation.final_candidate_count={final_candidate_count!r}"
                ),
            )

        for field in (
            "applied_rule_ids",
            "reintroduced_targets",
            "final_candidates",
            "final_candidate_chul_nos",
        ):
            if field not in race_trace:
                _append_audit_violation(
                    violations,
                    violation_counts,
                    race_id=race_id,
                    code="missing_candidate_trace_field",
                    rule_id="candidate_traceability_required",
                    message=f"race_trace.{field} 필드가 누락됨",
                )

    return {
        "passed": len(violations) == 0,
        "checked_races": checked_races,
        "violation_counts": violation_counts,
        "violations": violations,
    }
