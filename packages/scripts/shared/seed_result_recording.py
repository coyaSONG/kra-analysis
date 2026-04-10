"""상세 시드별 평가 결과 기록 스키마와 저장소 helpers."""

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

from shared.execution_matrix import (
    MODEL_CONFIG_ID_PREFIX,
    SeedExecutionMetrics,
    expected_run_ids_for_seeds,
    validate_evaluation_seeds,
)

DETAILED_SEED_RESULT_RECORD_VERSION = "holdout-detailed-seed-result-record-v1"
DETAILED_SEED_RESULT_REPOSITORY_VERSION = "holdout-detailed-seed-result-repository-v1"
DEFAULT_DETAILED_SEED_RESULT_REPOSITORY_FILENAME = "holdout_seed_result_records.json"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DatasetSelectionSnapshot(_FrozenModel):
    source_artifact_path: str | None = None
    source_artifact_sha256: str | None = Field(
        default=None, min_length=64, max_length=64
    )
    expected_race_count: int = Field(ge=1)
    final_race_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_artifact_sha256")
    @classmethod
    def _validate_source_artifact_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if len(lowered) != 64 or any(ch not in "0123456789abcdef" for ch in lowered):
            raise ValueError(
                "source_artifact_sha256 는 64자리 hexadecimal 이어야 한다."
            )
        return lowered

    @field_validator("final_race_ids")
    @classmethod
    def _validate_final_race_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("final_race_ids 에 중복 race_id 를 넣을 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_expected_race_count(self) -> DatasetSelectionSnapshot:
        if self.expected_race_count != len(self.final_race_ids):
            raise ValueError("expected_race_count must match final_race_ids length.")
        return self


class SplitSettingsSnapshot(_FrozenModel):
    dataset: str = Field(min_length=1)
    split: dict[str, Any] = Field(default_factory=dict)
    rolling_windows: tuple[dict[str, Any], ...] = ()
    evaluation_contract: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] = Field(default_factory=dict)
    input_contract_signature: str | None = None
    selected_run_id: str | None = None
    dataset_selection: DatasetSelectionSnapshot | None = None


class SearchParametersSnapshot(_FrozenModel):
    experiment_profile_version: str | None = None
    repeat_count: int | None = Field(default=None, ge=1)
    evaluation_seeds: tuple[int, ...] = ()
    model_search_strategy: str | None = None
    candidate_names: tuple[str, ...] = ()
    candidate_count: int = Field(ge=0)
    model_candidates: tuple[dict[str, Any], ...] = ()
    common_hyperparameters: dict[str, Any] = Field(default_factory=dict)
    resolved_model_parameters: dict[str, Any] = Field(default_factory=dict)
    parameter_source: str = Field(min_length=1)
    model_parameter_source: str = Field(min_length=1)

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value, allow_empty=True)

    @model_validator(mode="after")
    def _validate_candidate_count(self) -> SearchParametersSnapshot:
        if self.candidate_count != len(self.model_candidates):
            raise ValueError("candidate_count must match model_candidates length.")
        if self.candidate_names and len(self.candidate_names) != self.candidate_count:
            raise ValueError("candidate_names length must match candidate_count.")
        return self


class SeedContextSnapshot(_FrozenModel):
    run_id: str = Field(min_length=1)
    seed_index: int = Field(ge=1)
    model_random_state: int
    evaluation_seeds: tuple[int, ...] = ()
    parameter_source: str = Field(min_length=1)
    selection_seed_invariant: bool | None = None

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value, allow_empty=True)


class EvaluationOutcomeSnapshot(_FrozenModel):
    summary: dict[str, Any] = Field(default_factory=dict)
    dev: dict[str, Any] | None = None
    test: dict[str, Any] | None = None
    core_metrics: SeedExecutionMetrics
    overall_holdout_hit_rate: float = Field(ge=0.0, le=1.0)
    overall_holdout_hit_rate_source: str = Field(min_length=1)
    metric_normalization: dict[str, Any] = Field(default_factory=dict)


class DetailedSeedResultArtifacts(_FrozenModel):
    output_path: str | None = None
    manifest_path: str | None = None
    config_path: str | None = None
    runtime_params_path: str | None = None


class DetailedSeedResultRecord(_FrozenModel):
    format_version: Literal["holdout-detailed-seed-result-record-v1"] = (
        DETAILED_SEED_RESULT_RECORD_VERSION
    )
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    seed: int
    seed_index: int = Field(ge=1)
    run_at: datetime
    model_config_id: str = Field(min_length=1)
    split_settings: SplitSettingsSnapshot
    search_parameters: SearchParametersSnapshot
    seed_context: SeedContextSnapshot
    evaluation_result: EvaluationOutcomeSnapshot
    artifacts: DetailedSeedResultArtifacts = Field(
        default_factory=DetailedSeedResultArtifacts
    )

    @field_validator("model_config_id")
    @classmethod
    def _validate_model_config_id(cls, value: str) -> str:
        lowered = value.lower()
        if not lowered.startswith(MODEL_CONFIG_ID_PREFIX):
            raise ValueError(
                f"model_config_id 는 {MODEL_CONFIG_ID_PREFIX}<hex> 형식이어야 한다."
            )
        suffix = lowered.removeprefix(MODEL_CONFIG_ID_PREFIX)
        if len(suffix) < 16 or any(ch not in "0123456789abcdef" for ch in suffix):
            raise ValueError(
                "model_config_id suffix 는 최소 16자리 hexadecimal 이어야 한다."
            )
        return lowered

    @model_validator(mode="after")
    def _validate_consistency(self) -> DetailedSeedResultRecord:
        if self.seed_context.run_id != self.run_id:
            raise ValueError("seed_context.run_id must match run_id.")
        if self.seed_context.seed_index != self.seed_index:
            raise ValueError("seed_context.seed_index must match seed_index.")
        if self.seed_context.model_random_state != self.seed:
            raise ValueError("seed_context.model_random_state must match seed.")
        if (
            self.evaluation_result.core_metrics.overfit_safe_exact_rate is not None
            and self.evaluation_result.overall_holdout_hit_rate_source
            == "summary.overfit_safe_exact_rate"
            and self.evaluation_result.overall_holdout_hit_rate
            != self.evaluation_result.core_metrics.overfit_safe_exact_rate
        ):
            raise ValueError(
                "overall_holdout_hit_rate must match core_metrics.overfit_safe_exact_rate when sourced from summary.overfit_safe_exact_rate."
            )
        return self


class DetailedSeedResultRepositorySummary(_FrozenModel):
    expected_run_count: int = Field(ge=1)
    recorded_run_count: int = Field(ge=0)
    missing_run_ids: tuple[str, ...] = ()
    all_expected_runs_recorded: bool
    lowest_overall_holdout_hit_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    highest_overall_holdout_hit_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    model_config_ids: tuple[str, ...] = ()


class DetailedSeedResultRepository(_FrozenModel):
    format_version: Literal["holdout-detailed-seed-result-repository-v1"] = (
        DETAILED_SEED_RESULT_REPOSITORY_VERSION
    )
    group_id: str = Field(min_length=1)
    evaluation_seeds: tuple[int, ...]
    expected_run_ids: tuple[str, ...]
    records: tuple[DetailedSeedResultRecord, ...] = ()
    summary: DetailedSeedResultRepositorySummary

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value)

    @field_validator("records")
    @classmethod
    def _validate_records(
        cls, value: tuple[DetailedSeedResultRecord, ...]
    ) -> tuple[DetailedSeedResultRecord, ...]:
        run_ids = [record.run_id for record in value]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("records.run_id 는 중복될 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_expected_run_ids_and_summary(
        self,
    ) -> DetailedSeedResultRepository:
        expected_ids = expected_run_ids_for_seeds(self.evaluation_seeds)
        if self.expected_run_ids != expected_ids:
            raise ValueError(
                "expected_run_ids 는 evaluation_seeds 로부터 계산된 값과 일치해야 한다."
            )
        expected_summary = summarize_detailed_seed_result_repository(
            records=self.records,
            expected_run_ids=self.expected_run_ids,
        )
        if self.summary != expected_summary:
            raise ValueError("summary must match records and expected_run_ids.")
        return self


def summarize_detailed_seed_result_repository(
    *,
    records: tuple[DetailedSeedResultRecord, ...],
    expected_run_ids: tuple[str, ...],
) -> DetailedSeedResultRepositorySummary:
    recorded_run_ids = {record.run_id for record in records}
    missing_run_ids = tuple(
        run_id for run_id in expected_run_ids if run_id not in recorded_run_ids
    )
    hit_rates = [
        record.evaluation_result.overall_holdout_hit_rate for record in records
    ]
    model_config_ids = tuple(sorted({record.model_config_id for record in records}))
    return DetailedSeedResultRepositorySummary(
        expected_run_count=len(expected_run_ids),
        recorded_run_count=len(records),
        missing_run_ids=missing_run_ids,
        all_expected_runs_recorded=not missing_run_ids,
        lowest_overall_holdout_hit_rate=min(hit_rates) if hit_rates else None,
        highest_overall_holdout_hit_rate=max(hit_rates) if hit_rates else None,
        model_config_ids=model_config_ids,
    )


def build_detailed_seed_result_repository(
    *,
    group_id: str,
    evaluation_seeds: tuple[int, ...],
    records: tuple[DetailedSeedResultRecord, ...] = (),
) -> DetailedSeedResultRepository:
    expected_run_ids = expected_run_ids_for_seeds(evaluation_seeds)
    rank = {run_id: index for index, run_id in enumerate(expected_run_ids)}
    ordered_records = tuple(
        sorted(
            records,
            key=lambda item: (
                rank.get(item.run_id, len(expected_run_ids)),
                item.run_id,
            ),
        )
    )
    summary = summarize_detailed_seed_result_repository(
        records=ordered_records,
        expected_run_ids=expected_run_ids,
    )
    return DetailedSeedResultRepository.model_validate(
        {
            "group_id": group_id,
            "evaluation_seeds": evaluation_seeds,
            "expected_run_ids": expected_run_ids,
            "records": ordered_records,
            "summary": summary.model_dump(mode="json"),
        }
    )


def upsert_detailed_seed_result_record(
    repository: DetailedSeedResultRepository | None,
    record: DetailedSeedResultRecord,
    *,
    group_id: str,
    evaluation_seeds: tuple[int, ...],
) -> DetailedSeedResultRepository:
    base_records = list(repository.records) if repository else []
    replaced = False
    for index, existing in enumerate(base_records):
        if existing.run_id == record.run_id:
            base_records[index] = record
            replaced = True
            break
    if not replaced:
        base_records.append(record)

    return build_detailed_seed_result_repository(
        group_id=repository.group_id if repository else group_id,
        evaluation_seeds=repository.evaluation_seeds
        if repository
        else evaluation_seeds,
        records=tuple(base_records),
    )


def validate_detailed_seed_result_record_payload(
    payload: Any,
) -> tuple[bool, list[str]]:
    if not isinstance(payload, dict):
        return False, ["payload: Input should be a valid dictionary"]
    try:
        DetailedSeedResultRecord.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return False, errors
    return True, []


def validate_detailed_seed_result_repository_payload(
    payload: Any,
) -> tuple[bool, list[str]]:
    if not isinstance(payload, dict):
        return False, ["payload: Input should be a valid dictionary"]

    errors: list[str] = []
    records = payload.get("records")
    if records is not None:
        if not isinstance(records, list):
            errors.append("records: Input should be a valid list")
        else:
            for index, record_payload in enumerate(records):
                ok, record_errors = validate_detailed_seed_result_record_payload(
                    record_payload
                )
                if not ok:
                    errors.extend(f"records.{index}.{error}" for error in record_errors)

    try:
        DetailedSeedResultRepository.model_validate(payload)
    except ValidationError as exc:
        errors.extend(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return False, errors
    return (False, errors) if errors else (True, [])
