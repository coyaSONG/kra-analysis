"""10-seed recent-holdout execution matrix contract and execution journal schema."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from hashlib import sha256
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

EXPECTED_EVALUATION_SEED_COUNT = 10
EXECUTION_MATRIX_VERSION = "holdout-execution-matrix-v1"
EXECUTION_JOURNAL_VERSION = "holdout-execution-journal-v1"
SEED_RESULT_RECORD_VERSION = "holdout-seed-result-record-v1"
SEED_RESULT_REPOSITORY_VERSION = "holdout-seed-result-repository-v1"
DEFAULT_EVALUATION_SEEDS = (11, 17, 23, 31, 37, 41, 47, 53, 59, 61)
DEFAULT_SELECTION_METHOD = "time_ordered_complete_date_accumulation"
DEFAULT_BOUNDARY_UNIT = "race_date"
DEFAULT_TARGET_LABEL = "unordered_top3"
DEFAULT_ACTIVE_RUNNER_RULE = "candidate_filter_minimum_info_fallback_v1"
DEFAULT_LEAKAGE_POLICY_VERSION = "leakage-checks-v1"
DEFAULT_EXECUTION_GROUP_ID = "recent-holdout-10seed"
DEFAULT_EXECUTION_JOURNAL_FILENAME = "holdout_execution_journal.json"
DEFAULT_SEED_RESULT_REPOSITORY_FILENAME = "holdout_seed_result_repository.json"
TERMINAL_EXECUTION_STATUSES = frozenset({"completed", "failed"})
MODEL_CONFIG_ID_PREFIX = "model-config-v1:"
SEED_RESULT_RECORD_REQUIRED_FIELDS = frozenset(
    {
        "format_version",
        "run_id",
        "seed",
        "run_at",
        "model_config_id",
        "overall_holdout_hit_rate",
        "overall_holdout_hit_rate_source",
    }
)
SEED_RESULT_RUN_ID_PATTERN = re.compile(r"^seed_(?P<seed_index>\d{2})_rs(?P<seed>\d+)$")


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def build_model_config_id(config: dict[str, Any] | bytes | str) -> str:
    """모델 설정 식별자를 canonical SHA 기반 문자열로 만든다."""

    if isinstance(config, dict):
        payload = json.dumps(
            config,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    elif isinstance(config, bytes):
        payload = config
    else:
        payload = str(config).encode("utf-8")
    return MODEL_CONFIG_ID_PREFIX + sha256(payload).hexdigest()[:16]


def validate_evaluation_seeds(
    value: tuple[int, ...],
    *,
    allow_empty: bool = False,
) -> tuple[int, ...]:
    normalized = tuple(int(seed) for seed in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError("evaluation_seeds 에 중복 시드를 넣을 수 없다.")
    if allow_empty and not normalized:
        return normalized
    if len(normalized) != EXPECTED_EVALUATION_SEED_COUNT:
        raise ValueError(
            f"evaluation_seeds 는 정확히 {EXPECTED_EVALUATION_SEED_COUNT}개의 서로 다른 시드여야 한다."
        )
    return normalized


class CommonHoldoutEvaluationParameters(_FrozenModel):
    """10-seed 반복 평가가 공통으로 공유하는 최근 기간 홀드아웃 계약."""

    selection_method: Literal["time_ordered_complete_date_accumulation"] = (
        DEFAULT_SELECTION_METHOD
    )
    boundary_unit: Literal["race_date"] = DEFAULT_BOUNDARY_UNIT
    require_complete_race_dates: Literal[True] = True
    allow_intra_day_cut: Literal[False] = False
    active_runner_rule: Literal["candidate_filter_minimum_info_fallback_v1"] = (
        DEFAULT_ACTIVE_RUNNER_RULE
    )
    target_label: Literal["unordered_top3"] = DEFAULT_TARGET_LABEL
    selection_seed_invariant: Literal[True] = True
    leakage_policy_version: str = Field(
        default=DEFAULT_LEAKAGE_POLICY_VERSION,
        min_length=1,
    )


class ExecutionMatrixRun(_FrozenModel):
    """단일 랜덤 시드 반복 실행 항목."""

    run_id: str = Field(min_length=1)
    seed_index: int = Field(ge=1)
    model_random_state: int
    holdout: CommonHoldoutEvaluationParameters


class ExecutionMatrix(_FrozenModel):
    """최근 기간 holdout 고정 조건을 10개 시드 반복으로 펼친 실행 매트릭스."""

    format_version: Literal["holdout-execution-matrix-v1"] = EXECUTION_MATRIX_VERSION
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS
    holdout: CommonHoldoutEvaluationParameters = Field(
        default_factory=CommonHoldoutEvaluationParameters
    )

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_evaluation_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return validate_evaluation_seeds(value)

    def build_runs(self) -> tuple[ExecutionMatrixRun, ...]:
        return tuple(
            ExecutionMatrixRun(
                run_id=f"seed_{index:02d}_rs{seed}",
                seed_index=index,
                model_random_state=seed,
                holdout=self.holdout,
            )
            for index, seed in enumerate(self.evaluation_seeds, start=1)
        )


def expected_run_ids_for_seeds(
    evaluation_seeds: tuple[int, ...],
) -> tuple[str, ...]:
    validated = validate_evaluation_seeds(evaluation_seeds)
    return tuple(
        f"seed_{index:02d}_rs{seed}" for index, seed in enumerate(validated, start=1)
    )


class SeedExecutionArtifacts(_FrozenModel):
    output_path: str | None = None
    manifest_path: str | None = None


class SeedExecutionFailure(_FrozenModel):
    error_type: str = Field(min_length=1)
    error_message: str = Field(min_length=1)
    reason_code: str | None = None
    reason: str | None = None
    missing_count: int | None = Field(default=None, ge=0)
    missing_items: tuple[str, ...] = ()
    incomplete_top3_count: int | None = Field(default=None, ge=0)
    incomplete_top3_race_ids: tuple[str, ...] = ()
    expected_race_count: int | None = Field(default=None, ge=0)
    predicted_race_count: int | None = Field(default=None, ge=0)
    evaluation_window: dict[str, Any] | None = None
    traceback_excerpt: str | None = None


class SeedExecutionMetrics(_FrozenModel):
    robust_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    overfit_safe_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    blended_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    rolling_min_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    rolling_mean_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    dev_test_gap: float | None = Field(default=None, ge=0.0, le=1.0)
    dev_exact_3of3_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    dev_avg_set_match: float | None = Field(default=None, ge=0.0, le=1.0)
    dev_races: int | None = Field(default=None, ge=0)
    test_exact_3of3_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    test_avg_set_match: float | None = Field(default=None, ge=0.0, le=1.0)
    test_races: int | None = Field(default=None, ge=0)


class CommonSeedResultRecord(_FrozenModel):
    """시드 실행 결과를 저장하는 공통 레코드 스키마."""

    format_version: Literal["holdout-seed-result-record-v1"] = (
        SEED_RESULT_RECORD_VERSION
    )
    run_id: str = Field(min_length=1)
    seed: int
    run_at: datetime
    model_config_id: str = Field(min_length=1)
    overall_holdout_hit_rate: float = Field(ge=0.0, le=1.0)
    overall_holdout_hit_rate_source: Literal[
        "summary.overfit_safe_exact_rate",
        "summary.robust_exact_rate",
        "test.exact_3of3_rate",
    ]

    @field_validator("run_id")
    @classmethod
    def _validate_run_id_format(cls, value: str) -> str:
        if not SEED_RESULT_RUN_ID_PATTERN.fullmatch(value):
            raise ValueError("run_id 는 seed_XX_rsYY 형식이어야 한다.")
        return value

    @field_validator("model_config_id")
    @classmethod
    def _validate_model_config_id(cls, value: str) -> str:
        if not value.startswith(MODEL_CONFIG_ID_PREFIX):
            raise ValueError(
                f"model_config_id 는 {MODEL_CONFIG_ID_PREFIX}<hex> 형식이어야 한다."
            )
        suffix = value.removeprefix(MODEL_CONFIG_ID_PREFIX)
        if len(suffix) < 16 or any(
            ch not in "0123456789abcdef" for ch in suffix.lower()
        ):
            raise ValueError(
                "model_config_id suffix 는 최소 16자리 hexadecimal 이어야 한다."
            )
        return value.lower()

    @model_validator(mode="after")
    def _validate_run_id_seed_consistency(self) -> CommonSeedResultRecord:
        match = SEED_RESULT_RUN_ID_PATTERN.fullmatch(self.run_id)
        if match is None:
            raise ValueError("run_id 는 seed_XX_rsYY 형식이어야 한다.")
        run_id_seed = int(match.group("seed"))
        if run_id_seed != self.seed:
            raise ValueError("run_id 의 rs 시드 값과 seed 필드는 일치해야 한다.")
        return self


class SeedExecutionRecord(_FrozenModel):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    seed_index: int = Field(ge=1)
    model_random_state: int | None = None
    status: Literal["pending", "running", "completed", "failed"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifacts: SeedExecutionArtifacts | None = None
    metrics: SeedExecutionMetrics | None = None
    common_result: CommonSeedResultRecord | None = None
    failure: SeedExecutionFailure | None = None

    @model_validator(mode="after")
    def _validate_terminal_state(self) -> SeedExecutionRecord:
        if self.status in TERMINAL_EXECUTION_STATUSES and self.finished_at is None:
            raise ValueError("terminal execution record must include finished_at.")
        if self.status == "completed":
            if self.metrics is None:
                raise ValueError("completed execution record must include metrics.")
            if self.common_result is None:
                raise ValueError(
                    "completed execution record must include common_result."
                )
            if self.common_result.run_id != self.run_id:
                raise ValueError("common_result.run_id must match record.run_id.")
            if (
                self.model_random_state is not None
                and self.common_result.seed != self.model_random_state
            ):
                raise ValueError("common_result.seed must match model_random_state.")
        if self.status == "failed" and self.failure is None:
            raise ValueError("failed execution record must include failure details.")
        return self


class ExecutionJournalSummary(_FrozenModel):
    expected_run_count: int = Field(ge=1)
    recorded_run_count: int = Field(ge=0)
    pending_run_count: int = Field(ge=0)
    running_run_count: int = Field(ge=0)
    completed_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    terminal_run_count: int = Field(ge=0)
    missing_run_ids: tuple[str, ...] = ()
    missing_completed_run_ids: tuple[str, ...] = ()
    failed_run_ids: tuple[str, ...] = ()
    all_expected_runs_recorded: bool
    all_runs_terminal: bool
    all_expected_runs_completed: bool
    all_runs_completed_successfully: bool
    lowest_overfit_safe_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    lowest_robust_exact_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    lowest_test_exact_3of3_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class ExecutionJournal(_FrozenModel):
    format_version: Literal["holdout-execution-journal-v1"] = EXECUTION_JOURNAL_VERSION
    group_id: str = Field(default=DEFAULT_EXECUTION_GROUP_ID, min_length=1)
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS
    expected_run_ids: tuple[str, ...] = Field(
        default_factory=lambda: expected_run_ids_for_seeds(DEFAULT_EVALUATION_SEEDS)
    )
    records: tuple[SeedExecutionRecord, ...] = ()
    summary: ExecutionJournalSummary

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_journal_evaluation_seeds(
        cls, value: tuple[int, ...]
    ) -> tuple[int, ...]:
        return validate_evaluation_seeds(value)

    @field_validator("records")
    @classmethod
    def _validate_records(
        cls, value: tuple[SeedExecutionRecord, ...]
    ) -> tuple[SeedExecutionRecord, ...]:
        run_ids = [record.run_id for record in value]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("records.run_id 는 중복될 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_expected_run_ids_and_summary(self) -> ExecutionJournal:
        expected_ids = expected_run_ids_for_seeds(self.evaluation_seeds)
        if self.expected_run_ids != expected_ids:
            raise ValueError(
                "expected_run_ids 는 evaluation_seeds 로부터 계산된 값과 일치해야 한다."
            )
        expected_summary = summarize_execution_journal(
            records=self.records,
            expected_run_ids=self.expected_run_ids,
        )
        if self.summary != expected_summary:
            raise ValueError("summary must match records and expected_run_ids.")
        return self


class SeedResultRepositorySummary(_FrozenModel):
    expected_run_count: int = Field(ge=1)
    recorded_run_count: int = Field(ge=0)
    missing_run_ids: tuple[str, ...] = ()
    all_expected_runs_recorded: bool
    lowest_overall_holdout_hit_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    highest_overall_holdout_hit_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    model_config_ids: tuple[str, ...] = ()


class SeedResultRepository(_FrozenModel):
    format_version: Literal["holdout-seed-result-repository-v1"] = (
        SEED_RESULT_REPOSITORY_VERSION
    )
    group_id: str = Field(default=DEFAULT_EXECUTION_GROUP_ID, min_length=1)
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS
    expected_run_ids: tuple[str, ...] = Field(
        default_factory=lambda: expected_run_ids_for_seeds(DEFAULT_EVALUATION_SEEDS)
    )
    records: tuple[CommonSeedResultRecord, ...] = ()
    summary: SeedResultRepositorySummary

    @field_validator("evaluation_seeds")
    @classmethod
    def _validate_repository_evaluation_seeds(
        cls, value: tuple[int, ...]
    ) -> tuple[int, ...]:
        return validate_evaluation_seeds(value)

    @field_validator("records")
    @classmethod
    def _validate_repository_records(
        cls, value: tuple[CommonSeedResultRecord, ...]
    ) -> tuple[CommonSeedResultRecord, ...]:
        run_ids = [record.run_id for record in value]
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("records.run_id 는 중복될 수 없다.")
        return value

    @model_validator(mode="after")
    def _validate_expected_run_ids_and_summary(self) -> SeedResultRepository:
        expected_ids = expected_run_ids_for_seeds(self.evaluation_seeds)
        if self.expected_run_ids != expected_ids:
            raise ValueError(
                "expected_run_ids 는 evaluation_seeds 로부터 계산된 값과 일치해야 한다."
            )
        expected_summary = summarize_seed_result_repository(
            records=self.records,
            expected_run_ids=self.expected_run_ids,
        )
        if self.summary != expected_summary:
            raise ValueError("summary must match records and expected_run_ids.")
        return self


def build_execution_matrix(
    *,
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS,
    leakage_policy_version: str = DEFAULT_LEAKAGE_POLICY_VERSION,
) -> ExecutionMatrix:
    return ExecutionMatrix.model_validate(
        {
            "evaluation_seeds": evaluation_seeds,
            "holdout": {
                "leakage_policy_version": leakage_policy_version,
            },
        }
    )


def summarize_execution_journal(
    *,
    records: tuple[SeedExecutionRecord, ...],
    expected_run_ids: tuple[str, ...],
) -> ExecutionJournalSummary:
    counts = Counter(record.status for record in records)
    expected_set = set(expected_run_ids)
    recorded_run_ids = {record.run_id for record in records}
    completed_run_ids = tuple(
        record.run_id for record in records if record.status == "completed"
    )
    completed_run_id_set = set(completed_run_ids)
    missing_run_ids = tuple(
        run_id for run_id in expected_run_ids if run_id not in recorded_run_ids
    )
    missing_completed_run_ids = tuple(
        run_id for run_id in expected_run_ids if run_id not in completed_run_id_set
    )
    failed_run_ids = tuple(
        record.run_id for record in records if record.status == "failed"
    )
    completed_metrics = [
        record.metrics
        for record in records
        if record.status == "completed" and record.metrics
    ]
    overfit_rates = [
        metrics.overfit_safe_exact_rate
        for metrics in completed_metrics
        if metrics.overfit_safe_exact_rate is not None
    ]
    robust_rates = [
        metrics.robust_exact_rate
        for metrics in completed_metrics
        if metrics.robust_exact_rate is not None
    ]
    test_exact_rates = [
        metrics.test_exact_3of3_rate
        for metrics in completed_metrics
        if metrics.test_exact_3of3_rate is not None
    ]
    terminal_run_count = counts["completed"] + counts["failed"]
    all_expected_runs_recorded = (
        not missing_run_ids and recorded_run_ids == expected_set
    )
    all_expected_runs_completed = (
        not missing_completed_run_ids
        and counts["completed"] == len(expected_run_ids)
        and completed_run_id_set == expected_set
    )
    return ExecutionJournalSummary(
        expected_run_count=len(expected_run_ids),
        recorded_run_count=len(records),
        pending_run_count=counts["pending"],
        running_run_count=counts["running"],
        completed_run_count=counts["completed"],
        failed_run_count=counts["failed"],
        terminal_run_count=terminal_run_count,
        missing_run_ids=missing_run_ids,
        missing_completed_run_ids=missing_completed_run_ids,
        failed_run_ids=failed_run_ids,
        all_expected_runs_recorded=all_expected_runs_recorded,
        all_runs_terminal=all_expected_runs_recorded
        and terminal_run_count == len(expected_run_ids),
        all_expected_runs_completed=all_expected_runs_completed,
        all_runs_completed_successfully=all_expected_runs_completed,
        lowest_overfit_safe_exact_rate=min(overfit_rates) if overfit_rates else None,
        lowest_robust_exact_rate=min(robust_rates) if robust_rates else None,
        lowest_test_exact_3of3_rate=min(test_exact_rates) if test_exact_rates else None,
    )


def build_execution_journal(
    *,
    group_id: str = DEFAULT_EXECUTION_GROUP_ID,
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS,
    records: tuple[SeedExecutionRecord, ...] = (),
) -> ExecutionJournal:
    expected_run_ids = expected_run_ids_for_seeds(evaluation_seeds)
    summary = summarize_execution_journal(
        records=records,
        expected_run_ids=expected_run_ids,
    )
    return ExecutionJournal.model_validate(
        {
            "group_id": group_id,
            "evaluation_seeds": evaluation_seeds,
            "expected_run_ids": expected_run_ids,
            "records": records,
            "summary": summary.model_dump(mode="json"),
        }
    )


def summarize_seed_result_repository(
    *,
    records: tuple[CommonSeedResultRecord, ...],
    expected_run_ids: tuple[str, ...],
) -> SeedResultRepositorySummary:
    expected_set = set(expected_run_ids)
    recorded_run_ids = {record.run_id for record in records}
    missing_run_ids = tuple(
        run_id for run_id in expected_run_ids if run_id not in recorded_run_ids
    )
    hit_rates = [record.overall_holdout_hit_rate for record in records]
    model_config_ids = tuple(sorted({record.model_config_id for record in records}))
    return SeedResultRepositorySummary(
        expected_run_count=len(expected_run_ids),
        recorded_run_count=len(records),
        missing_run_ids=missing_run_ids,
        all_expected_runs_recorded=(
            not missing_run_ids and recorded_run_ids == expected_set
        ),
        lowest_overall_holdout_hit_rate=min(hit_rates) if hit_rates else None,
        highest_overall_holdout_hit_rate=max(hit_rates) if hit_rates else None,
        model_config_ids=model_config_ids,
    )


def build_seed_result_repository(
    *,
    group_id: str = DEFAULT_EXECUTION_GROUP_ID,
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS,
    records: tuple[CommonSeedResultRecord, ...] = (),
) -> SeedResultRepository:
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
    summary = summarize_seed_result_repository(
        records=ordered_records,
        expected_run_ids=expected_run_ids,
    )
    return SeedResultRepository.model_validate(
        {
            "group_id": group_id,
            "evaluation_seeds": evaluation_seeds,
            "expected_run_ids": expected_run_ids,
            "records": ordered_records,
            "summary": summary.model_dump(mode="json"),
        }
    )


def seed_result_repository_from_journal(
    journal: ExecutionJournal,
) -> SeedResultRepository:
    records = tuple(
        record.common_result
        for record in journal.records
        if record.common_result is not None
    )
    return build_seed_result_repository(
        group_id=journal.group_id,
        evaluation_seeds=journal.evaluation_seeds,
        records=records,
    )


def upsert_execution_record(
    journal: ExecutionJournal | None,
    record: SeedExecutionRecord,
    *,
    group_id: str = DEFAULT_EXECUTION_GROUP_ID,
    evaluation_seeds: tuple[int, ...] = DEFAULT_EVALUATION_SEEDS,
) -> ExecutionJournal:
    base_records = list(journal.records) if journal else []
    replaced = False
    for index, existing in enumerate(base_records):
        if existing.run_id == record.run_id:
            base_records[index] = record
            replaced = True
            break
    if not replaced:
        base_records.append(record)
    base_records.sort(key=lambda item: (item.seed_index, item.run_id))
    return build_execution_journal(
        group_id=journal.group_id if journal else group_id,
        evaluation_seeds=journal.evaluation_seeds if journal else evaluation_seeds,
        records=tuple(base_records),
    )


def build_holdout_manifest_parameters(
    *,
    dataset: Literal["holdout", "mini_val"],
    minimum_race_count: int,
    execution_matrix: ExecutionMatrix,
) -> dict[str, object]:
    holdout = execution_matrix.holdout
    return {
        "dataset": dataset,
        "selection_method": holdout.selection_method,
        "boundary_unit": holdout.boundary_unit,
        "minimum_race_count": minimum_race_count,
        "require_complete_race_dates": holdout.require_complete_race_dates,
        "allow_intra_day_cut": holdout.allow_intra_day_cut,
        "active_runner_rule": holdout.active_runner_rule,
        "target_label": holdout.target_label,
        "leakage_policy_version": holdout.leakage_policy_version,
    }


def validate_execution_matrix_payload(
    payload: dict[str, object],
) -> tuple[bool, list[str]]:
    try:
        ExecutionMatrix.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return False, errors
    return True, []


def validate_execution_journal_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    try:
        ExecutionJournal.model_validate(payload)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return False, errors
    return True, []


def validate_seed_result_repository_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    records = payload.get("records")
    if records is not None:
        if not isinstance(records, list):
            errors.append("records: Input should be a valid list")
        else:
            for index, record_payload in enumerate(records):
                ok, record_errors = validate_seed_result_record_payload(record_payload)
                if not ok:
                    errors.extend(f"records.{index}.{error}" for error in record_errors)
    try:
        SeedResultRepository.model_validate(payload)
    except ValidationError as exc:
        errors.extend(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return False, errors
    if errors:
        return False, errors
    return True, []


def validate_seed_result_record_payload(
    payload: Any,
) -> tuple[bool, list[str]]:
    if not isinstance(payload, dict):
        return False, ["payload: Input should be a valid dictionary"]

    errors: list[str] = []
    missing_required_fields = sorted(
        SEED_RESULT_RECORD_REQUIRED_FIELDS - set(payload.keys())
    )
    if missing_required_fields:
        errors.append(f"missing_required_fields: {missing_required_fields}")

    try:
        CommonSeedResultRecord.model_validate(payload)
    except ValidationError as exc:
        errors.extend(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return False, errors
    return (False, errors) if errors else (True, [])
