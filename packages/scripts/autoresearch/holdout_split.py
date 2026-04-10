"""최근 기간 홀드아웃/mini_val 분할 선택과 manifest 저장."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from evaluation.leakage_checks import check_detailed_results_for_leakage
from shared.batch_race_selection_policy import (
    BATCH_RACE_SELECTION_POLICY_VERSION,
    DEFAULT_BATCH_RACE_SELECTION_POLICY,
)
from shared.data_adapter import convert_basic_data_to_enriched_format
from shared.execution_matrix import (
    DEFAULT_EVALUATION_SEEDS,
    DEFAULT_LEAKAGE_POLICY_VERSION,
    ExecutionMatrix,
    build_execution_matrix,
    build_holdout_manifest_parameters,
)
from shared.holdout_split_manifest_schema import (
    DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
    DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
    HoldoutSplitManifest,
)
from shared.prerace_field_policy import filter_prerace_payload
from shared.read_contract import RaceSnapshot, normalize_result_data
from shared.runner_status import select_prediction_candidates

from .holdout_dataset import derive_snapshot_timing, select_allowed_basic_data

KST = ZoneInfo("Asia/Seoul")
DEFAULT_HOLDOUT_MINIMUM_RACE_COUNT = 500
DEFAULT_MINI_VAL_MINIMUM_RACE_COUNT = 200
DEFAULT_SPLIT_OUTPUT_DIR = Path(".ralph") / "outputs"
DEFAULT_SPLIT_OUTPUT_FILENAMES = {
    "holdout": "holdout_split_manifest.json",
    "mini_val": "mini_val_split_manifest.json",
}
DEFAULT_SPLIT_DATASETS = tuple(DEFAULT_SPLIT_OUTPUT_FILENAMES)
_OFFICIAL_EXCLUSION_STATUSES = frozenset({"cancelled", "withdrawn", "excluded"})


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if value in ("", None):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(KST)


def _normalize_manifest_created_at(
    value: datetime | str | None,
) -> datetime:
    normalized = _parse_datetime(value)
    if normalized is not None:
        return normalized
    return datetime.now(KST)


def _parse_race_date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _iter_enriched_items(enriched: dict[str, Any]) -> list[dict[str, Any]]:
    items = enriched["response"]["body"]["items"]["item"]
    if not isinstance(items, list):
        return [items]
    return items


def _normalize_item_chul_no(item: dict[str, Any]) -> int | None:
    try:
        return int(item.get("chulNo"))
    except (TypeError, ValueError):
        return None


def _has_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _extract_active_items(
    enriched: dict[str, Any],
    *,
    cancelled_horses: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    items = _iter_enriched_items(enriched)
    candidate_selection = select_prediction_candidates(
        items,
        cancelled_horses=cancelled_horses,
    )
    return candidate_selection.eligible_runners


def _payload_passes_leakage_check(
    race_id: str,
    active_items: list[dict[str, Any]],
) -> bool:
    filtered_payload, _ = filter_prerace_payload(
        {
            "race_info": active_items[0],
            "horses": active_items,
        }
    )
    result = check_detailed_results_for_leakage(
        [{"race_id": race_id, "race_data": filtered_payload}]
    )
    return bool(result.get("passed"))


@dataclass(frozen=True, slots=True)
class RaceSplitAssessment:
    snapshot: RaceSnapshot
    race_date: date
    included: bool
    exclusion_reason: str | None
    entry_finalized_at: datetime | None
    data_timestamp: datetime | None

    @property
    def race_id(self) -> str:
        return self.snapshot.race_id

    @property
    def sort_key(self) -> tuple[date, int, int, str]:
        return (
            self.race_date,
            self.snapshot.meet,
            self.snapshot.race_number,
            self.snapshot.race_id,
        )


@dataclass(frozen=True, slots=True)
class ExpectedRaceIdSelection:
    """고정 기준을 통과해 실행이 반드시 포함해야 하는 대상 경주 식별자 집합."""

    dataset: str
    minimum_race_count: int
    start_date: date
    end_date: date
    latest_complete_race_date: date
    selected_race_dates: tuple[date, ...]
    expected_race_ids: tuple[str, ...]
    included_rows: tuple[RaceSplitAssessment, ...]
    excluded_race_dates: tuple[date, ...]
    exclusion_reason_counts: dict[str, int]


def _select_target_scope_snapshots(
    snapshots: list[RaceSnapshot],
) -> tuple[RaceSnapshot, ...]:
    """정책 범위에 속하는 KRA 경주만 selection 후보로 남긴다."""

    selection_policy = DEFAULT_BATCH_RACE_SELECTION_POLICY
    return tuple(
        snapshot
        for snapshot in snapshots
        if snapshot.meet in selection_policy.allowed_meets
    )


def assess_race_for_recent_holdout(snapshot: RaceSnapshot) -> RaceSplitAssessment:
    selection_policy = DEFAULT_BATCH_RACE_SELECTION_POLICY
    race_date = _parse_race_date(snapshot.race_date)
    timing = derive_snapshot_timing(snapshot)
    data_timestamp = (
        _parse_datetime(snapshot.updated_at)
        or _parse_datetime(snapshot.collected_at)
        or _parse_datetime(timing.entry_finalized_at)
    )
    entry_finalized_at = _parse_datetime(timing.entry_finalized_at)

    if snapshot.result_status != selection_policy.required_result_status:
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="missing_result_data",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    if not snapshot.basic_data:
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="missing_basic_data",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    if not timing.include_in_strict_dataset:
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason=timing.replay_status,
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    basic_data = select_allowed_basic_data(snapshot.basic_data)
    enriched = convert_basic_data_to_enriched_format(basic_data)
    if selection_policy.require_payload_conversion and not enriched:
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="payload_conversion_failed",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    active_items = _extract_active_items(
        enriched,
        cancelled_horses=(snapshot.basic_data or {}).get("cancelled_horses"),
    )
    if len(active_items) < selection_policy.minimum_active_runners:
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="insufficient_active_runners",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    top3 = normalize_result_data(snapshot.result_data)
    if len(top3) != selection_policy.require_exact_top3_label_count or (
        selection_policy.require_unique_top3_label
        and len(set(top3)) != selection_policy.require_exact_top3_label_count
    ):
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="invalid_top3_result",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    active_numbers: set[int] = set()
    for item in active_items:
        try:
            active_numbers.add(int(item["chulNo"]))
        except (KeyError, TypeError, ValueError):
            continue
    if selection_policy.require_top3_subset_of_active_runners and not set(
        top3
    ).issubset(active_numbers):
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="top3_not_in_active_runners",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    if (
        selection_policy.require_leakage_check_pass
        and not _payload_passes_leakage_check(snapshot.race_id, active_items)
    ):
        return RaceSplitAssessment(
            snapshot=snapshot,
            race_date=race_date,
            included=False,
            exclusion_reason="leakage_violation",
            entry_finalized_at=entry_finalized_at,
            data_timestamp=data_timestamp,
        )

    return RaceSplitAssessment(
        snapshot=snapshot,
        race_date=race_date,
        included=True,
        exclusion_reason=None,
        entry_finalized_at=entry_finalized_at,
        data_timestamp=data_timestamp,
    )


def _group_assessments_by_date(
    assessments: list[RaceSplitAssessment],
) -> dict[date, list[RaceSplitAssessment]]:
    grouped: dict[date, list[RaceSplitAssessment]] = defaultdict(list)
    for assessment in sorted(assessments, key=lambda item: item.sort_key):
        grouped[assessment.race_date].append(assessment)
    return dict(grouped)


def _complete_dates(grouped: dict[date, list[RaceSplitAssessment]]) -> tuple[date, ...]:
    return tuple(
        race_date
        for race_date, rows in grouped.items()
        if rows and all(row.included for row in rows)
    )


def _build_snapshot_metadata(
    included_rows: list[RaceSplitAssessment],
    *,
    manifest_created_at: datetime,
) -> dict[str, datetime]:
    entry_snapshot_as_of = max(
        (row.entry_finalized_at for row in included_rows if row.entry_finalized_at),
        default=manifest_created_at,
    )
    data_as_of = max(
        (
            timestamp
            for timestamp in (
                *(row.data_timestamp for row in included_rows),
                entry_snapshot_as_of,
            )
            if timestamp is not None
        ),
        default=entry_snapshot_as_of,
    )
    results_as_of = max(manifest_created_at, data_as_of)
    return {
        "entry_snapshot_as_of": entry_snapshot_as_of,
        "data_as_of": data_as_of,
        "results_as_of": results_as_of,
    }


def _snapshot_timestamp_basis(
    snapshot: RaceSnapshot,
    *,
    timing: Any,
) -> tuple[str, datetime | None]:
    selected_timestamp_field = str(
        getattr(timing, "selected_timestamp_field", "") or ""
    )
    selected_timestamp_value = _parse_datetime(
        getattr(timing, "selected_timestamp_value", None)
    )
    if selected_timestamp_field:
        return (selected_timestamp_field, selected_timestamp_value)

    basic_data = snapshot.basic_data or {}
    basic_collected_at = _parse_datetime(basic_data.get("collected_at"))
    row_collected_at = _parse_datetime(snapshot.collected_at)
    row_updated_at = _parse_datetime(snapshot.updated_at)
    entry_finalized_at = _parse_datetime(timing.entry_finalized_at)

    if basic_collected_at is not None:
        return ("basic_data.collected_at", basic_collected_at)
    if row_collected_at is not None:
        return ("races.collected_at", row_collected_at)
    if row_updated_at is not None:
        return ("races.updated_at", row_updated_at)
    if timing.timestamp_source == "derived_from_schedule":
        return ("race_plan.sch_st_time_minus_10m", entry_finalized_at)
    return ("unresolved_timestamp_basis", entry_finalized_at)


def _build_race_input_snapshot_reference(
    snapshot: RaceSnapshot,
) -> dict[str, Any]:
    timing = derive_snapshot_timing(snapshot)
    selected_timestamp_field, selected_timestamp_value = _snapshot_timestamp_basis(
        snapshot,
        timing=timing,
    )
    filtered_basic_data = select_allowed_basic_data(snapshot.basic_data)
    snapshot_signature = {
        "race_id": snapshot.race_id,
        "basic_data": filtered_basic_data,
        "result_status": snapshot.result_status,
        "collected_at": str(snapshot.collected_at)
        if snapshot.collected_at is not None
        else None,
        "updated_at": str(snapshot.updated_at)
        if snapshot.updated_at is not None
        else None,
        "selected_timestamp_field": selected_timestamp_field,
        "selected_timestamp_value": (
            selected_timestamp_value.isoformat()
            if selected_timestamp_value is not None
            else None
        ),
    }
    snapshot_id = (
        "holdout-input-v1:"
        + sha256(
            json.dumps(
                snapshot_signature,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()[:16]
    )
    return {
        "snapshot_id": snapshot_id,
        "snapshot_generation_basis": {
            "source_filter_basis": timing.source_filter_basis,
            "timestamp_source": timing.timestamp_source,
            "selected_timestamp_field": selected_timestamp_field,
            "selected_timestamp_value": selected_timestamp_value,
            "snapshot_ready_at": _parse_datetime(timing.snapshot_ready_at),
            "entry_finalized_at": _parse_datetime(timing.entry_finalized_at),
        },
    }


def _attach_manifest_sha(manifest: HoldoutSplitManifest) -> HoldoutSplitManifest:
    payload = manifest.model_dump(mode="json")
    payload_without_sha = {**payload, "manifest_sha256": None}
    digest = sha256(
        json.dumps(payload_without_sha, ensure_ascii=False, sort_keys=True).encode(
            "utf-8"
        )
    ).hexdigest()
    return manifest.model_copy(update={"manifest_sha256": digest})


def serialize_split_manifest(manifest: HoldoutSplitManifest) -> str:
    """manifest를 byte-level 비교 가능한 canonical JSON 문자열로 직렬화한다."""

    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _ordered_snapshot_ids(manifest: HoldoutSplitManifest) -> tuple[str, ...]:
    return tuple(
        manifest.race_input_snapshot_map[race_id].snapshot_id
        for race_id in manifest.included_race_ids
    )


def _sequence_digest(values: tuple[str, ...]) -> str:
    return sha256(
        json.dumps(values, ensure_ascii=False, sort_keys=False).encode("utf-8")
    ).hexdigest()


def _sequence_mismatch_details(
    reference: tuple[str, ...],
    regenerated: tuple[str, ...],
) -> dict[str, Any] | None:
    if reference == regenerated:
        return None

    mismatch_index: int | None = None
    for idx, (left, right) in enumerate(zip(reference, regenerated, strict=False)):
        if left != right:
            mismatch_index = idx
            break

    if mismatch_index is None and len(reference) != len(regenerated):
        mismatch_index = min(len(reference), len(regenerated))

    return {
        "reference_count": len(reference),
        "regenerated_count": len(regenerated),
        "first_mismatch_index": mismatch_index,
        "reference_value": (
            reference[mismatch_index]
            if mismatch_index is not None and mismatch_index < len(reference)
            else None
        ),
        "regenerated_value": (
            regenerated[mismatch_index]
            if mismatch_index is not None and mismatch_index < len(regenerated)
            else None
        ),
    }


def select_expected_race_ids_for_dataset(
    assessments: list[RaceSplitAssessment],
    *,
    dataset: str,
    minimum_race_count: int,
    end_date: date | None = None,
) -> ExpectedRaceIdSelection:
    """문서화된 기준을 적용해 dataset별 기대 race_id 목록을 확정한다."""

    grouped = _group_assessments_by_date(assessments)
    candidate_dates = sorted(
        race_date for race_date in grouped if end_date is None or race_date <= end_date
    )
    if not candidate_dates:
        raise ValueError(f"{dataset} 분할에 사용할 경주 날짜가 없습니다.")

    selected_dates_desc: list[date] = []
    skipped_dates_desc: list[date] = []
    latest_complete_date: date | None = None
    included_rows: list[RaceSplitAssessment] = []
    included_count = 0

    for race_date in reversed(candidate_dates):
        rows = grouped[race_date]
        date_is_complete = rows and all(row.included for row in rows)
        if date_is_complete:
            if latest_complete_date is None:
                latest_complete_date = race_date
            selected_dates_desc.append(race_date)
            included_rows.extend(rows)
            included_count += len(rows)
            if included_count >= minimum_race_count:
                break
        else:
            skipped_dates_desc.append(race_date)

    if latest_complete_date is None:
        raise ValueError(f"{dataset} 분할에 사용할 완결 평가일이 없습니다.")
    if included_count < minimum_race_count:
        raise ValueError(
            f"{dataset} 분할 후보가 부족합니다: need>={minimum_race_count}, got={included_count}"
        )

    selected_dates = tuple(sorted(selected_dates_desc))
    included_rows_sorted = tuple(sorted(included_rows, key=lambda item: item.sort_key))
    expected_race_ids = tuple(row.race_id for row in included_rows_sorted)

    start_date = selected_dates[0]
    end_selected_date = selected_dates[-1]
    excluded_dates = tuple(sorted(skipped_dates_desc))

    exclusion_reason_counts: dict[str, int] = {}
    for race_date in excluded_dates:
        for row in grouped[race_date]:
            reason = row.exclusion_reason or "incomplete_race_date"
            exclusion_reason_counts[reason] = exclusion_reason_counts.get(reason, 0) + 1

    return ExpectedRaceIdSelection(
        dataset=dataset,
        minimum_race_count=minimum_race_count,
        start_date=start_date,
        end_date=end_selected_date,
        latest_complete_race_date=latest_complete_date,
        selected_race_dates=selected_dates,
        expected_race_ids=expected_race_ids,
        included_rows=included_rows_sorted,
        excluded_race_dates=excluded_dates,
        exclusion_reason_counts=exclusion_reason_counts,
    )


def _build_manifest_from_expected_race_ids(
    selection: ExpectedRaceIdSelection,
    *,
    manifest_created_at: datetime,
    execution_matrix: ExecutionMatrix,
) -> HoldoutSplitManifest:
    race_input_snapshot_map = {
        row.race_id: _build_race_input_snapshot_reference(row.snapshot)
        for row in selection.included_rows
    }
    snapshot_meta = _build_snapshot_metadata(
        list(selection.included_rows),
        manifest_created_at=manifest_created_at,
    )
    manifest = HoldoutSplitManifest.model_validate(
        {
            "parameters": build_holdout_manifest_parameters(
                dataset=selection.dataset,
                minimum_race_count=selection.minimum_race_count,
                execution_matrix=execution_matrix,
            ),
            "metadata": {
                "manifest_created_at": manifest_created_at,
                "period": {
                    "start_date": selection.start_date,
                    "end_date": selection.end_date,
                    "latest_complete_race_date": selection.latest_complete_race_date,
                    "race_count": len(selection.expected_race_ids),
                    "race_date_count": len(selection.selected_race_dates),
                },
                "seed": {
                    "selection_seed": None,
                    "selection_seed_invariant": execution_matrix.holdout.selection_seed_invariant,
                    "evaluation_seeds": execution_matrix.evaluation_seeds,
                },
                "data_snapshot": snapshot_meta,
                "rule": {
                    "rule_version": DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
                    "rule_path": "docs/recent-holdout-split-rule.md",
                    "entry_finalization_rule_version": DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
                    "batch_race_selection_policy_version": BATCH_RACE_SELECTION_POLICY_VERSION,
                },
            },
            "included_race_ids": selection.expected_race_ids,
            "race_input_snapshot_map": race_input_snapshot_map,
            "excluded_race_dates": selection.excluded_race_dates,
            "exclusion_reason_counts": selection.exclusion_reason_counts,
        }
    )
    return _attach_manifest_sha(manifest)


def _plan_recent_holdout_selections_unchecked(
    snapshots: list[RaceSnapshot],
    *,
    holdout_minimum_race_count: int,
    mini_val_minimum_race_count: int,
) -> dict[str, ExpectedRaceIdSelection]:
    scoped_snapshots = _select_target_scope_snapshots(snapshots)
    assessments = [
        assess_race_for_recent_holdout(snapshot) for snapshot in scoped_snapshots
    ]

    holdout_selection = select_expected_race_ids_for_dataset(
        assessments,
        dataset="holdout",
        minimum_race_count=holdout_minimum_race_count,
    )

    grouped = _group_assessments_by_date(assessments)
    complete_dates = _complete_dates(grouped)
    previous_complete_dates = [
        race_date
        for race_date in complete_dates
        if race_date < holdout_selection.start_date
    ]
    if not previous_complete_dates:
        raise ValueError("mini_val 종료일을 결정할 직전 완결 평가일이 없습니다.")

    mini_val_selection = select_expected_race_ids_for_dataset(
        assessments,
        dataset="mini_val",
        minimum_race_count=mini_val_minimum_race_count,
        end_date=previous_complete_dates[-1],
    )

    overlap = set(holdout_selection.expected_race_ids) & set(
        mini_val_selection.expected_race_ids
    )
    if overlap:
        raise ValueError(f"holdout/mini_val 경주가 겹칩니다: {sorted(overlap)[:5]}")

    return {
        "holdout": holdout_selection,
        "mini_val": mini_val_selection,
    }


def plan_recent_holdout_selections(
    snapshots: list[RaceSnapshot],
    *,
    holdout_minimum_race_count: int = DEFAULT_HOLDOUT_MINIMUM_RACE_COUNT,
    mini_val_minimum_race_count: int = DEFAULT_MINI_VAL_MINIMUM_RACE_COUNT,
) -> dict[str, ExpectedRaceIdSelection]:
    """실행마다 고정돼야 하는 holdout/mini_val 기대 race_id 목록을 계산한다."""

    return _plan_recent_holdout_selections_unchecked(
        snapshots,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
    )


def plan_recent_holdout_manifests(
    snapshots: list[RaceSnapshot],
    *,
    manifest_created_at: datetime | str | None = None,
    holdout_minimum_race_count: int = DEFAULT_HOLDOUT_MINIMUM_RACE_COUNT,
    mini_val_minimum_race_count: int = DEFAULT_MINI_VAL_MINIMUM_RACE_COUNT,
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS,
    leakage_policy_version: str = DEFAULT_LEAKAGE_POLICY_VERSION,
) -> dict[str, HoldoutSplitManifest]:
    normalized_created_at = _normalize_manifest_created_at(manifest_created_at)
    execution_matrix = build_execution_matrix(
        evaluation_seeds=evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
    )
    manifests = _plan_recent_holdout_manifests_unchecked(
        snapshots,
        manifest_created_at=normalized_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        execution_matrix=execution_matrix,
    )
    reproducibility_report = check_manifest_reproducibility(
        snapshots,
        manifest_created_at=normalized_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        evaluation_seeds=evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
        reference_manifests=manifests,
    )
    if not reproducibility_report["passed"]:
        raise ValueError(
            "홀드아웃 분할 재생성 검증에 실패했습니다. "
            f"details={json.dumps(reproducibility_report['datasets'], ensure_ascii=False, sort_keys=True)}"
        )
    return manifests


def _plan_recent_holdout_manifests_unchecked(
    snapshots: list[RaceSnapshot],
    *,
    manifest_created_at: datetime,
    holdout_minimum_race_count: int,
    mini_val_minimum_race_count: int,
    execution_matrix: ExecutionMatrix,
) -> dict[str, HoldoutSplitManifest]:
    selections = _plan_recent_holdout_selections_unchecked(
        snapshots,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
    )

    holdout_manifest = _build_manifest_from_expected_race_ids(
        selections["holdout"],
        manifest_created_at=manifest_created_at,
        execution_matrix=execution_matrix,
    )
    mini_val_manifest = _build_manifest_from_expected_race_ids(
        selections["mini_val"],
        manifest_created_at=manifest_created_at,
        execution_matrix=execution_matrix,
    )

    overlap = set(holdout_manifest.included_race_ids) & set(
        mini_val_manifest.included_race_ids
    )
    if overlap:
        raise ValueError(f"holdout/mini_val 경주가 겹칩니다: {sorted(overlap)[:5]}")

    return {
        "holdout": holdout_manifest,
        "mini_val": mini_val_manifest,
    }


def check_manifest_reproducibility(
    snapshots: list[RaceSnapshot],
    *,
    manifest_created_at: datetime | str | None = None,
    holdout_minimum_race_count: int = DEFAULT_HOLDOUT_MINIMUM_RACE_COUNT,
    mini_val_minimum_race_count: int = DEFAULT_MINI_VAL_MINIMUM_RACE_COUNT,
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS,
    leakage_policy_version: str = DEFAULT_LEAKAGE_POLICY_VERSION,
    reference_manifests: dict[str, HoldoutSplitManifest] | None = None,
) -> dict[str, Any]:
    """동일 원천 데이터/규칙으로 manifest를 재생성했을 때 내용이 동일한지 검증한다."""

    execution_matrix = build_execution_matrix(
        evaluation_seeds=evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
    )
    normalized_created_at = _normalize_manifest_created_at(
        manifest_created_at
        or (
            next(iter(reference_manifests.values())).metadata.manifest_created_at
            if reference_manifests
            else None
        )
    )
    reference = reference_manifests or _plan_recent_holdout_manifests_unchecked(
        snapshots,
        manifest_created_at=normalized_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        execution_matrix=execution_matrix,
    )
    regenerated = _plan_recent_holdout_manifests_unchecked(
        snapshots,
        manifest_created_at=normalized_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        execution_matrix=execution_matrix,
    )

    dataset_results: dict[str, Any] = {}
    for dataset in DEFAULT_SPLIT_DATASETS:
        reference_text = serialize_split_manifest(reference[dataset])
        regenerated_text = serialize_split_manifest(regenerated[dataset])
        reference_race_ids = tuple(reference[dataset].included_race_ids)
        regenerated_race_ids = tuple(regenerated[dataset].included_race_ids)
        reference_snapshot_ids = _ordered_snapshot_ids(reference[dataset])
        regenerated_snapshot_ids = _ordered_snapshot_ids(regenerated[dataset])
        race_ids_match = reference_race_ids == regenerated_race_ids
        snapshot_ids_match = reference_snapshot_ids == regenerated_snapshot_ids
        payload_match = reference_text == regenerated_text
        dataset_results[dataset] = {
            "passed": payload_match and race_ids_match and snapshot_ids_match,
            "sample_composition_match": race_ids_match,
            "sample_identifier_match": snapshot_ids_match,
            "canonical_payload_match": payload_match,
            "reference_manifest_sha256": reference[dataset].manifest_sha256,
            "regenerated_manifest_sha256": regenerated[dataset].manifest_sha256,
            "canonical_payload_sha256": sha256(
                reference_text.encode("utf-8")
            ).hexdigest(),
            "byte_length": len(reference_text.encode("utf-8")),
            "reference_race_ids_sha256": _sequence_digest(reference_race_ids),
            "regenerated_race_ids_sha256": _sequence_digest(regenerated_race_ids),
            "reference_snapshot_ids_sha256": _sequence_digest(reference_snapshot_ids),
            "regenerated_snapshot_ids_sha256": _sequence_digest(
                regenerated_snapshot_ids
            ),
            "race_id_mismatch": _sequence_mismatch_details(
                reference_race_ids,
                regenerated_race_ids,
            ),
            "snapshot_id_mismatch": _sequence_mismatch_details(
                reference_snapshot_ids,
                regenerated_snapshot_ids,
            ),
        }

    return {
        "passed": all(result["passed"] for result in dataset_results.values()),
        "manifest_created_at": normalized_created_at.isoformat(),
        "rule_version": DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
        "entry_finalization_rule_version": DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
        "batch_race_selection_policy_version": BATCH_RACE_SELECTION_POLICY_VERSION,
        "datasets": dataset_results,
    }


def write_split_manifest(
    manifest: HoldoutSplitManifest,
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_split_manifest(manifest), encoding="utf-8")
    return path


def write_split_manifests(
    manifests: dict[str, HoldoutSplitManifest],
    *,
    output_dir: Path = DEFAULT_SPLIT_OUTPUT_DIR,
) -> dict[str, Path]:
    written_paths: dict[str, Path] = {}
    for dataset, manifest in manifests.items():
        filename = DEFAULT_SPLIT_OUTPUT_FILENAMES[dataset]
        written_paths[dataset] = write_split_manifest(manifest, output_dir / filename)
    return written_paths
