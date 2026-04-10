"""Autoresearch 학습/검증 기간 및 홀드아웃 평가 계약 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from shared.batch_race_selection_policy import (
    BATCH_RACE_SELECTION_POLICY_VERSION,
    DEFAULT_BATCH_RACE_SELECTION_POLICY,
    BatchRaceSelectionPolicy,
    default_batch_race_selection_policy_payload,
)
from shared.execution_matrix import (
    DEFAULT_ACTIVE_RUNNER_RULE,
    DEFAULT_BOUNDARY_UNIT,
    DEFAULT_EVALUATION_SEEDS,
    DEFAULT_SELECTION_METHOD,
    DEFAULT_TARGET_LABEL,
    EXPECTED_EVALUATION_SEED_COUNT,
    validate_evaluation_seeds,
)
from shared.holdout_split_manifest_schema import (
    DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
    DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
)
from shared.prediction_input_schema import ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION

AUTORESEARCH_CONFIG_VERSION = "autoresearch-clean-config-v1"
AUTORESEARCH_EXPERIMENT_VERSION = "autoresearch-experiment-profile-v1"
DEFAULT_INPUT_DATA_POLICY_VERSION = "prerace-entry-finalized-only-v1"
DEFAULT_INPUT_FEATURE_SCHEMA_VERSION = ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
_DATE_PATTERN = "%Y%m%d"
_REQUIRED_REPLAY_EXCLUSION_STATUSES = (
    "late_snapshot_unusable",
    "missing_timestamp",
    "partial_snapshot",
)
_REQUIRED_RACE_EXCLUSION_REASONS = (
    "insufficient_active_runners",
    "invalid_top3_result",
    "late_snapshot_unusable",
    "leakage_violation",
    "missing_basic_data",
    "missing_result_data",
    "partial_snapshot",
    "payload_conversion_failed",
    "top3_not_in_active_runners",
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _parse_compact_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, _DATE_PATTERN)
    except ValueError as exc:
        raise ValueError("날짜는 YYYYMMDD 형식이어야 한다.") from exc


class PrimarySplitWindow(_FrozenModel):
    """기본 학습/dev/test 기간 경계."""

    train_end: str = Field(min_length=8, max_length=8)
    dev_end: str = Field(min_length=8, max_length=8)
    test_start: str = Field(min_length=8, max_length=8)

    @field_validator("train_end", "dev_end", "test_start")
    @classmethod
    def _validate_dates(cls, value: str) -> str:
        _parse_compact_date(value)
        return value

    @model_validator(mode="after")
    def _validate_order(self) -> PrimarySplitWindow:
        train_end = _parse_compact_date(self.train_end)
        dev_end = _parse_compact_date(self.dev_end)
        test_start = _parse_compact_date(self.test_start)
        if not (train_end < dev_end < test_start):
            raise ValueError(
                "split 기간은 train_end < dev_end < test_start 순서를 만족해야 한다."
            )
        return self


class RollingWindow(_FrozenModel):
    """walk-forward 검증용 추가 기간."""

    name: str = Field(min_length=1)
    train_end: str = Field(min_length=8, max_length=8)
    eval_start: str = Field(min_length=8, max_length=8)
    eval_end: str = Field(min_length=8, max_length=8)

    @field_validator("train_end", "eval_start", "eval_end")
    @classmethod
    def _validate_dates(cls, value: str) -> str:
        _parse_compact_date(value)
        return value

    @model_validator(mode="after")
    def _validate_order(self) -> RollingWindow:
        train_end = _parse_compact_date(self.train_end)
        eval_start = _parse_compact_date(self.eval_start)
        eval_end = _parse_compact_date(self.eval_end)
        if not (train_end < eval_start <= eval_end):
            raise ValueError(
                "rolling_windows 기간은 train_end < eval_start <= eval_end 순서를 만족해야 한다."
            )
        return self


class EvaluationContract(_FrozenModel):
    """같은 원천 데이터 입력에 대한 홀드아웃 경계/포함 계약."""

    same_source_data_required: Literal[True] = True
    selection_method: Literal["time_ordered_complete_date_accumulation"] = (
        DEFAULT_SELECTION_METHOD
    )
    boundary_unit: Literal["race_date"] = DEFAULT_BOUNDARY_UNIT
    minimum_holdout_race_count: int = Field(ge=1)
    minimum_mini_val_race_count: int = Field(ge=1)
    require_complete_race_dates: Literal[True] = True
    allow_intra_day_cut: Literal[False] = False
    selection_seed_invariant: Literal[True] = True
    active_runner_rule: Literal["candidate_filter_minimum_info_fallback_v1"] = (
        DEFAULT_ACTIVE_RUNNER_RULE
    )
    target_label: Literal["unordered_top3"] = DEFAULT_TARGET_LABEL
    holdout_rule_version: str = Field(min_length=1)
    entry_finalization_rule_version: str = Field(min_length=1)
    batch_target_selection: BatchRaceSelectionPolicy = Field(
        default_factory=BatchRaceSelectionPolicy
    )
    strict_dataset_selector: Literal["include_in_strict_dataset_true"] = (
        "include_in_strict_dataset_true"
    )
    excluded_replay_statuses: tuple[str, ...] = Field(min_length=1)
    excluded_race_reasons: tuple[str, ...] = Field(min_length=1)

    @field_validator("excluded_replay_statuses", "excluded_race_reasons")
    @classmethod
    def _validate_unique_tuples(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("중복 값을 넣을 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_contract_sets(self) -> EvaluationContract:
        if self.minimum_holdout_race_count < self.minimum_mini_val_race_count:
            raise ValueError(
                "minimum_holdout_race_count 는 minimum_mini_val_race_count 이상이어야 한다."
            )

        replay_statuses = tuple(sorted(self.excluded_replay_statuses))
        if replay_statuses != _REQUIRED_REPLAY_EXCLUSION_STATUSES:
            raise ValueError(
                "excluded_replay_statuses 는 "
                f"{list(_REQUIRED_REPLAY_EXCLUSION_STATUSES)} 와 정확히 일치해야 한다."
            )

        exclusion_reasons = tuple(sorted(self.excluded_race_reasons))
        if exclusion_reasons != _REQUIRED_RACE_EXCLUSION_REASONS:
            raise ValueError(
                "excluded_race_reasons 는 현재 홀드아웃 구현의 공식 제외 사유와 정확히 일치해야 한다."
            )

        if self.batch_target_selection != DEFAULT_BATCH_RACE_SELECTION_POLICY:
            raise ValueError(
                "batch_target_selection 은 실행 입력으로 덮어쓸 수 없는 고정 규칙이어야 한다."
            )

        if (
            self.batch_target_selection.policy_version
            != BATCH_RACE_SELECTION_POLICY_VERSION
        ):
            raise ValueError(
                "batch_target_selection.policy_version 이 저장소 기본 규칙 버전과 다릅니다."
            )

        return self


class ModelSpec(_FrozenModel):
    """모델 종류와 파라미터."""

    kind: Literal["hgb", "rf", "et", "logreg"]
    positive_class_weight: float | None = Field(default=None, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)


class InputDataVersion(_FrozenModel):
    """실험이 의존하는 입력 데이터 버전 계약."""

    dataset_name: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    source_policy_version: str = Field(min_length=1)
    feature_schema_version: str = Field(min_length=1)
    operational_snapshot_only: Literal[True] = True


class SearchModelCandidate(_FrozenModel):
    """탐색 후보로 허용된 모델/파라미터 프로파일."""

    name: str = Field(min_length=1)
    kind: Literal["hgb", "rf", "et", "logreg"]
    params: dict[str, Any] = Field(default_factory=dict)


class ModelSearchScope(_FrozenModel):
    """모델 탐색 범위를 고정하는 선언 블록."""

    strategy: Literal["curated_candidates_v1"] = "curated_candidates_v1"
    candidates: tuple[SearchModelCandidate, ...] = Field(min_length=1)

    @field_validator("candidates")
    @classmethod
    def _validate_unique_candidate_names(
        cls,
        value: tuple[SearchModelCandidate, ...],
    ) -> tuple[SearchModelCandidate, ...]:
        names = [candidate.name for candidate in value]
        if len(names) != len(set(names)):
            raise ValueError("model_search.candidates.name 은 중복될 수 없다.")
        return value


class CommonHyperparameterPolicy(_FrozenModel):
    """모든 탐색 후보에 공통으로 적용할 하이퍼파라미터."""

    positive_class_weight: float = Field(gt=0)
    imputer_strategy: Literal["median"] = "median"
    random_state_source: Literal["evaluation_seed"] = "evaluation_seed"
    target_label: Literal["unordered_top3"] = DEFAULT_TARGET_LABEL
    prediction_top_k: Literal[3] = 3


class ExperimentControl(_FrozenModel):
    """반복 평가/탐색/데이터 버전을 묶는 단일 실험 설정 블록."""

    profile_version: Literal["autoresearch-experiment-profile-v1"] = (
        AUTORESEARCH_EXPERIMENT_VERSION
    )
    repeat_count: int = Field(ge=1)
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS
    input_data: InputDataVersion
    model_search: ModelSearchScope
    common_hyperparameters: CommonHyperparameterPolicy

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value)

    @model_validator(mode="after")
    def _validate_repeat_count(self) -> ExperimentControl:
        if self.repeat_count != len(self.evaluation_seeds):
            raise ValueError(
                "experiment.repeat_count 는 evaluation_seeds 개수와 정확히 일치해야 한다."
            )
        if self.repeat_count != EXPECTED_EVALUATION_SEED_COUNT:
            raise ValueError(
                "experiment.repeat_count 는 현재 표준 반복 평가 계약상 정확히 10이어야 한다."
            )
        return self


class AutoresearchConfig(_FrozenModel):
    """Autoresearch clean 모델 설정 파일 계약."""

    format_version: Literal["autoresearch-clean-config-v1"]
    dataset: str = Field(min_length=1)
    split: PrimarySplitWindow
    rolling_windows: tuple[RollingWindow, ...] = ()
    evaluation_contract: EvaluationContract
    model: ModelSpec
    features: tuple[str, ...] = Field(min_length=1)
    experiment: ExperimentControl
    notes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("features")
    @classmethod
    def _validate_features(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("features 에 중복 값을 넣을 수 없다.")
        return value

    @field_validator("rolling_windows")
    @classmethod
    def _validate_rolling_window_names(
        cls, value: tuple[RollingWindow, ...]
    ) -> tuple[RollingWindow, ...]:
        names = [item.name for item in value]
        if len(names) != len(set(names)):
            raise ValueError("rolling_windows.name 은 중복될 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_experiment_alignment(self) -> AutoresearchConfig:
        if self.dataset != self.experiment.input_data.dataset_name:
            raise ValueError(
                "experiment.input_data.dataset_name 은 top-level dataset 과 일치해야 한다."
            )

        candidate_kinds = {
            candidate.kind for candidate in self.experiment.model_search.candidates
        }
        if self.model.kind not in candidate_kinds:
            raise ValueError(
                "model.kind 는 experiment.model_search.candidates 에 포함되어야 한다."
            )

        if (
            self.model.positive_class_weight is not None
            and self.model.positive_class_weight
            != self.experiment.common_hyperparameters.positive_class_weight
        ):
            raise ValueError(
                "model.positive_class_weight 는 experiment.common_hyperparameters.positive_class_weight 와 일치해야 한다."
            )

        if (
            self.evaluation_contract.target_label
            != self.experiment.common_hyperparameters.target_label
        ):
            raise ValueError(
                "evaluation_contract.target_label 과 experiment.common_hyperparameters.target_label 은 같아야 한다."
            )

        return self


def autoresearch_config_json_schema() -> dict[str, Any]:
    """외부 저장/검증용 JSON schema dict를 반환한다."""

    return AutoresearchConfig.model_json_schema()


def validate_autoresearch_config(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Autoresearch 설정 payload를 검증하고 오류 메시지를 정규화한다."""

    try:
        AutoresearchConfig.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return False, errors
    return True, []


def default_evaluation_contract_payload() -> dict[str, Any]:
    """현재 저장소 기준 기본 평가 계약 payload를 반환한다."""

    return {
        "same_source_data_required": True,
        "selection_method": DEFAULT_SELECTION_METHOD,
        "boundary_unit": DEFAULT_BOUNDARY_UNIT,
        "minimum_holdout_race_count": 500,
        "minimum_mini_val_race_count": 200,
        "require_complete_race_dates": True,
        "allow_intra_day_cut": False,
        "selection_seed_invariant": True,
        "active_runner_rule": DEFAULT_ACTIVE_RUNNER_RULE,
        "target_label": DEFAULT_TARGET_LABEL,
        "holdout_rule_version": DEFAULT_RECENT_HOLDOUT_RULE_VERSION,
        "entry_finalization_rule_version": DEFAULT_ENTRY_FINALIZATION_RULE_VERSION,
        "batch_target_selection": default_batch_race_selection_policy_payload(),
        "strict_dataset_selector": "include_in_strict_dataset_true",
        "excluded_replay_statuses": list(_REQUIRED_REPLAY_EXCLUSION_STATUSES),
        "excluded_race_reasons": list(_REQUIRED_RACE_EXCLUSION_REASONS),
    }


def default_experiment_payload(*, dataset: str = "full_year_2025") -> dict[str, Any]:
    """AC 4000101 기본 실험 제어 payload를 반환한다."""

    return {
        "profile_version": AUTORESEARCH_EXPERIMENT_VERSION,
        "repeat_count": EXPECTED_EVALUATION_SEED_COUNT,
        "evaluation_seeds": list(DEFAULT_EVALUATION_SEEDS),
        "input_data": {
            "dataset_name": dataset,
            "version_id": f"{dataset}-entry-finalized-prerace-v1",
            "source_policy_version": DEFAULT_INPUT_DATA_POLICY_VERSION,
            "feature_schema_version": DEFAULT_INPUT_FEATURE_SCHEMA_VERSION,
            "operational_snapshot_only": True,
        },
        "model_search": {
            "strategy": "curated_candidates_v1",
            "candidates": [
                {
                    "name": "baseline_hgb_depth6_lr005",
                    "kind": "hgb",
                    "params": {
                        "max_depth": 6,
                        "learning_rate": 0.05,
                        "max_iter": 600,
                        "min_samples_leaf": 30,
                        "l2_regularization": 0.4,
                    },
                },
                {
                    "name": "rf_depth8_600trees",
                    "kind": "rf",
                    "params": {
                        "n_estimators": 600,
                        "max_depth": 8,
                        "min_samples_leaf": 8,
                    },
                },
                {
                    "name": "et_depth8_800trees",
                    "kind": "et",
                    "params": {
                        "n_estimators": 800,
                        "max_depth": 8,
                        "min_samples_leaf": 6,
                    },
                },
                {
                    "name": "logreg_balanced_c075",
                    "kind": "logreg",
                    "params": {
                        "max_iter": 2000,
                        "C": 0.75,
                    },
                },
            ],
        },
        "common_hyperparameters": {
            "positive_class_weight": 1.0,
            "imputer_strategy": "median",
            "random_state_source": "evaluation_seed",
            "target_label": DEFAULT_TARGET_LABEL,
            "prediction_top_k": 3,
        },
    }
