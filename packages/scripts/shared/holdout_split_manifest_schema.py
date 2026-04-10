"""최근 기간 홀드아웃 경주 선정 manifest 저장 계약."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from shared.execution_matrix import (
    DEFAULT_ACTIVE_RUNNER_RULE,
    DEFAULT_BOUNDARY_UNIT,
    DEFAULT_SELECTION_METHOD,
    DEFAULT_TARGET_LABEL,
    validate_evaluation_seeds,
)

HOLDOUT_SPLIT_MANIFEST_VERSION = "holdout-split-manifest-v1"
DEFAULT_RECENT_HOLDOUT_RULE_VERSION = "recent-holdout-split-rule-v1"
DEFAULT_ENTRY_FINALIZATION_RULE_VERSION = "holdout-entry-finalization-rule-v1"
DEFAULT_PERIOD_DIRECTION = "backward_from_latest_complete_date"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HoldoutSplitParameters(_FrozenModel):
    """홀드아웃 경주 집합을 결정할 때 고정하는 입력 파라미터."""

    dataset: Literal["holdout", "mini_val"]
    selection_method: Literal["time_ordered_complete_date_accumulation"] = (
        DEFAULT_SELECTION_METHOD
    )
    boundary_unit: Literal["race_date"] = DEFAULT_BOUNDARY_UNIT
    minimum_race_count: int = Field(ge=1)
    require_complete_race_dates: bool = True
    allow_intra_day_cut: bool = False
    active_runner_rule: Literal["candidate_filter_minimum_info_fallback_v1"] = (
        DEFAULT_ACTIVE_RUNNER_RULE
    )
    target_label: Literal["unordered_top3"] = DEFAULT_TARGET_LABEL
    leakage_policy_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_boundary_policy(self) -> HoldoutSplitParameters:
        if self.allow_intra_day_cut:
            raise ValueError("최근 기간 홀드아웃은 평가일 내부 절단을 허용하지 않는다.")
        return self


class HoldoutPeriodMetadata(_FrozenModel):
    """고정된 기간 경계와 실제 포함 규모."""

    start_date: date
    end_date: date
    latest_complete_race_date: date
    race_count: int = Field(ge=0)
    race_date_count: int = Field(ge=0)
    accumulation_direction: Literal["backward_from_latest_complete_date"] = (
        DEFAULT_PERIOD_DIRECTION
    )

    @model_validator(mode="after")
    def _validate_date_order(self) -> HoldoutPeriodMetadata:
        if self.start_date > self.end_date:
            raise ValueError("period.start_date 는 end_date 이후일 수 없다.")
        if not (self.start_date <= self.latest_complete_race_date <= self.end_date):
            raise ValueError(
                "period.latest_complete_race_date 는 start_date 와 end_date 사이에 있어야 한다."
            )
        return self


class HoldoutSeedMetadata(_FrozenModel):
    """시드 고정 정책과 반복 평가 시드 목록."""

    selection_seed: int | None = None
    selection_seed_invariant: bool = True
    evaluation_seeds: tuple[int, ...] = ()

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value)

    @model_validator(mode="after")
    def _validate_selection_seed(self) -> HoldoutSeedMetadata:
        if self.selection_seed_invariant and self.selection_seed is not None:
            raise ValueError(
                "selection_seed_invariant=true 이면 selection_seed 는 null 이어야 한다."
            )
        if not self.selection_seed_invariant and self.selection_seed is None:
            raise ValueError(
                "selection_seed_invariant=false 이면 selection_seed 를 명시해야 한다."
            )
        return self


class HoldoutDataSnapshotMetadata(_FrozenModel):
    """데이터 기준 시점과 스냅샷 컷오프."""

    data_as_of: datetime
    results_as_of: datetime
    entry_snapshot_as_of: datetime

    @model_validator(mode="after")
    def _validate_snapshot_order(self) -> HoldoutDataSnapshotMetadata:
        if self.entry_snapshot_as_of > self.data_as_of:
            raise ValueError(
                "metadata.data_snapshot.entry_snapshot_as_of 는 data_as_of 이후일 수 없다."
            )
        if self.data_as_of > self.results_as_of:
            raise ValueError(
                "metadata.data_snapshot.data_as_of 는 results_as_of 이후일 수 없다."
            )
        return self


class HoldoutRuleMetadata(_FrozenModel):
    """문서화된 규칙 버전 고정 정보."""

    rule_version: str = Field(min_length=1)
    rule_path: str = Field(min_length=1)
    entry_finalization_rule_version: str = Field(min_length=1)
    batch_race_selection_policy_version: str = Field(min_length=1)


class HoldoutSelectionMetadata(_FrozenModel):
    """홀드아웃 선택 결과를 재생하기 위한 핵심 메타데이터."""

    manifest_created_at: datetime
    period: HoldoutPeriodMetadata
    seed: HoldoutSeedMetadata
    data_snapshot: HoldoutDataSnapshotMetadata
    rule: HoldoutRuleMetadata


class HoldoutRaceInputSnapshotBasis(_FrozenModel):
    """개별 경주 입력 스냅샷을 어떤 기준으로 선택했는지 기록한다."""

    source_filter_basis: Literal["entry_finalized_at"]
    timestamp_source: str = Field(min_length=1)
    selected_timestamp_field: str = Field(min_length=1)
    selected_timestamp_value: datetime | None = None
    snapshot_ready_at: datetime | None = None
    entry_finalized_at: datetime | None = None


class HoldoutRaceInputSnapshotReference(_FrozenModel):
    """개별 경주 입력 스냅샷 식별자와 생성 기준."""

    snapshot_id: str = Field(min_length=1)
    snapshot_generation_basis: HoldoutRaceInputSnapshotBasis


class HoldoutSplitManifest(_FrozenModel):
    """최근 기간 홀드아웃/mini_val 경주 선택 결과 manifest."""

    format_version: Literal["holdout-split-manifest-v1"] = (
        HOLDOUT_SPLIT_MANIFEST_VERSION
    )
    parameters: HoldoutSplitParameters
    metadata: HoldoutSelectionMetadata
    included_race_ids: tuple[str, ...]
    race_input_snapshot_map: dict[str, HoldoutRaceInputSnapshotReference]
    excluded_race_dates: tuple[date, ...] = ()
    exclusion_reason_counts: dict[str, int] = Field(default_factory=dict)
    manifest_sha256: str | None = None

    @field_validator("included_race_ids")
    @classmethod
    def _validate_included_race_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("included_race_ids 는 최소 1개 이상이어야 한다.")
        if len(value) != len(set(value)):
            raise ValueError("included_race_ids 에 중복 race_id 를 넣을 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_race_input_snapshot_map(self) -> HoldoutSplitManifest:
        included_ids = set(self.included_race_ids)
        mapped_ids = set(self.race_input_snapshot_map)
        if included_ids != mapped_ids:
            missing_ids = sorted(included_ids - mapped_ids)
            extra_ids = sorted(mapped_ids - included_ids)
            details: list[str] = []
            if missing_ids:
                details.append(f"missing={missing_ids[:5]}")
            if extra_ids:
                details.append(f"extra={extra_ids[:5]}")
            joined = ", ".join(details) or "unknown mismatch"
            raise ValueError(
                "race_input_snapshot_map 은 included_race_ids 와 정확히 같은 race_id 집합을 가져야 한다: "
                f"{joined}"
            )
        return self


def holdout_split_manifest_json_schema() -> dict[str, Any]:
    """외부 저장/검증에 사용할 JSON schema dict를 반환한다."""

    return HoldoutSplitManifest.model_json_schema()


def validate_holdout_split_manifest(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """manifest payload를 검증하고 오류 메시지를 정규화해서 반환한다."""

    try:
        HoldoutSplitManifest.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return False, errors
    return True, []
