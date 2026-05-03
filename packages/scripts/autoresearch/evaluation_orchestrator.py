"""단일 시드 평가 작업 오케스트레이션 엔트리포인트."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import traceback
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from shared.execution_matrix import (
    DEFAULT_EXECUTION_JOURNAL_FILENAME,
    DEFAULT_SEED_RESULT_REPOSITORY_FILENAME,
    CommonSeedResultRecord,
    ExecutionJournal,
    SeedExecutionArtifacts,
    SeedExecutionFailure,
    SeedExecutionMetrics,
    SeedExecutionRecord,
    SeedResultRepository,
    build_model_config_id,
    seed_result_repository_from_journal,
    upsert_execution_record,
)
from shared.seed_metric_normalization import (
    DEFAULT_SEED_METRIC_NAMES,
    build_metric_normalization_snapshot,
    normalize_metric_mapping,
    normalize_metric_value,
)
from shared.seed_result_recording import (
    DEFAULT_DETAILED_SEED_RESULT_REPOSITORY_FILENAME,
    DetailedSeedResultArtifacts,
    DetailedSeedResultRecord,
    DetailedSeedResultRepository,
    EvaluationOutcomeSnapshot,
    SearchParametersSnapshot,
    SeedContextSnapshot,
    SplitSettingsSnapshot,
    build_detailed_seed_result_repository,
    upsert_detailed_seed_result_record,
)

from autoresearch.dataset_artifacts import (
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.parameter_context import (
    load_evaluation_parameter_context,
    load_seed_matrix_parameter_context,
)
from autoresearch.reproducibility import write_research_evaluation_bundle
from autoresearch.research_clean import (
    SNAPSHOT_DIR,
    PredictionCoverageError,
    evaluate,
)
from autoresearch.seed_summary_report import sync_seed_summary_report


class SchedulingMode(StrEnum):
    AUTO = "auto"
    SEQUENTIAL = "sequential"
    BATCH = "batch"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BatchExecutionOptions(_FrozenModel):
    enabled: bool = False
    group_id: str | None = None
    expected_task_count: int | None = Field(default=None, ge=1)
    max_workers: int | None = Field(default=None, ge=1)
    execution_journal_path: str | None = None
    evaluation_seeds: tuple[int, ...] | None = None


class SingleSeedEvaluationTask(_FrozenModel):
    task_id: str = Field(min_length=1)
    run_id: str | None = None
    seed_index: int | None = Field(default=None, ge=1)
    config_path: str = Field(min_length=1)
    output_path: str = Field(min_length=1)
    runtime_params_path: str | None = None
    model_random_state: int | None = None


class OrchestratorRequest(_FrozenModel):
    task: SingleSeedEvaluationTask | None = None
    tasks: tuple[SingleSeedEvaluationTask, ...] | None = Field(
        default=None,
        min_length=1,
    )
    mode: SchedulingMode = SchedulingMode.AUTO
    batch: BatchExecutionOptions | None = None

    @model_validator(mode="after")
    def _validate_task_shape(self) -> OrchestratorRequest:
        if self.task is None and self.tasks is None:
            raise ValueError("task 또는 tasks 중 하나는 필요합니다.")
        if self.task is not None and self.tasks is not None:
            raise ValueError("task 와 tasks 를 동시에 지정할 수 없습니다.")
        return self


@dataclass(frozen=True, slots=True)
class ExecutionJournalContext:
    path: Path
    seed_result_repository_path: Path
    detailed_seed_result_repository_path: Path
    group_id: str
    evaluation_seeds: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class TaskExecutionDecision:
    task: SingleSeedEvaluationTask
    action: str
    reason: str
    existing_record: SeedExecutionRecord | None = None


def _seed_index_for_task(task: SingleSeedEvaluationTask) -> int:
    if task.seed_index is not None:
        return task.seed_index
    if task.run_id:
        parts = task.run_id.split("_")
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    return 1


def _model_random_state_from_run_id(run_id: str | None) -> int | None:
    if not run_id:
        return None
    parts = run_id.split("_")
    if len(parts) >= 3 and parts[2].startswith("rs") and parts[2][2:].isdigit():
        return int(parts[2][2:])
    return None


def _tasks_for_request(
    request: OrchestratorRequest,
) -> tuple[SingleSeedEvaluationTask, ...]:
    if request.tasks is not None:
        return request.tasks
    if request.task is None:
        raise ValueError("task 또는 tasks 중 하나는 필요합니다.")
    return (request.task,)


def _default_storage_dir_for_request(request: OrchestratorRequest) -> Path:
    task_output_dirs = [
        str(Path(task.output_path).resolve().parent)
        for task in _tasks_for_request(request)
    ]
    return Path(os.path.commonpath(task_output_dirs))


def _journal_context_for_request(
    request: OrchestratorRequest,
) -> ExecutionJournalContext:
    batch = request.batch
    parameter_context = load_seed_matrix_parameter_context(
        config_path=Path(_tasks_for_request(request)[0].config_path),
        evaluation_seeds=batch.evaluation_seeds if batch else None,
        group_id=batch.group_id if batch else None,
        max_workers=batch.max_workers if batch else None,
        execution_journal_path=(
            Path(batch.execution_journal_path)
            if batch and batch.execution_journal_path
            else None
        ),
    )
    runner_params = parameter_context.runtime_params
    default_storage_dir = _default_storage_dir_for_request(request)
    journal_path = (
        Path(runner_params.execution_journal_path)
        if runner_params.execution_journal_path
        else default_storage_dir / DEFAULT_EXECUTION_JOURNAL_FILENAME
    )
    seed_result_repository_path = (
        journal_path.parent / DEFAULT_SEED_RESULT_REPOSITORY_FILENAME
        if runner_params.execution_journal_path
        else default_storage_dir / DEFAULT_SEED_RESULT_REPOSITORY_FILENAME
    )
    detailed_seed_result_repository_path = (
        journal_path.parent / DEFAULT_DETAILED_SEED_RESULT_REPOSITORY_FILENAME
        if runner_params.execution_journal_path
        else default_storage_dir / DEFAULT_DETAILED_SEED_RESULT_REPOSITORY_FILENAME
    )
    return ExecutionJournalContext(
        path=journal_path,
        seed_result_repository_path=seed_result_repository_path,
        detailed_seed_result_repository_path=detailed_seed_result_repository_path,
        group_id=runner_params.group_id,
        evaluation_seeds=runner_params.evaluation_seeds,
    )


def _load_existing_journal(path: Path) -> ExecutionJournal | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExecutionJournal.model_validate(payload)


def _load_existing_detailed_repository(
    path: Path,
) -> DetailedSeedResultRepository | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DetailedSeedResultRepository.model_validate(payload)


def _write_json_atomic(path: Path, payload: BaseModel | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    dumped = (
        payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    )
    tmp_path.write_text(
        json.dumps(dumped, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _synchronize_aggregate_storage(
    context: ExecutionJournalContext,
) -> tuple[
    ExecutionJournal | None,
    SeedResultRepository | None,
    DetailedSeedResultRepository | None,
]:
    if not context.path.exists():
        return None, None, None

    lock_path = context.path.with_suffix(f"{context.path.suffix}.lock")
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        journal = _load_existing_journal(context.path)
        if journal is None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            return None, None, None
        repository = seed_result_repository_from_journal(journal)
        _write_json_atomic(context.seed_result_repository_path, repository)
        detailed_repository = _load_existing_detailed_repository(
            context.detailed_seed_result_repository_path
        )
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return journal, repository, detailed_repository


def _build_existing_result_snapshot(
    task: SingleSeedEvaluationTask,
    *,
    record: SeedExecutionRecord,
    journal_context: ExecutionJournalContext,
    execution_summary: dict[str, Any] | None,
    seed_result_repository_summary: dict[str, Any] | None,
    detailed_seed_result_repository_summary: dict[str, Any] | None,
    detailed_result: DetailedSeedResultRecord | None,
) -> dict[str, Any]:
    run_id = task.run_id or task.task_id
    runtime_params_path = (
        Path(task.runtime_params_path) if task.runtime_params_path else None
    )
    if runtime_params_path is not None and not runtime_params_path.exists():
        runtime_params_path = None
    parameter_context = load_evaluation_parameter_context(
        config_path=Path(task.config_path),
        seed_index=task.seed_index,
        run_id=task.run_id,
        runtime_params_path=runtime_params_path,
        model_random_state=task.model_random_state,
    ).model_dump(mode="json")
    metrics = record.metrics
    artifacts = record.artifacts
    common_result = record.common_result
    resolved_model_random_state = (
        record.model_random_state
        or task.model_random_state
        or _model_random_state_from_run_id(run_id)
    )
    return {
        "task_id": task.task_id,
        "run_id": task.run_id,
        "seed_index": _seed_index_for_task(task),
        "status": record.status,
        "execution_action": "reused_completed",
        "resume_reason": "already_completed_with_storage",
        "resumed_from_existing": True,
        "parameter_context": parameter_context,
        "summary": {
            "robust_exact_rate": metrics.robust_exact_rate if metrics else None,
            "overfit_safe_exact_rate": (
                metrics.overfit_safe_exact_rate if metrics else None
            ),
            "blended_exact_rate": metrics.blended_exact_rate if metrics else None,
            "rolling_min_exact_rate": (
                metrics.rolling_min_exact_rate if metrics else None
            ),
            "rolling_mean_exact_rate": (
                metrics.rolling_mean_exact_rate if metrics else None
            ),
            "dev_test_gap": metrics.dev_test_gap if metrics else None,
        },
        "dev": {
            "exact_3of3_rate": metrics.dev_exact_3of3_rate if metrics else None,
            "avg_set_match": metrics.dev_avg_set_match if metrics else None,
            "races": metrics.dev_races if metrics else None,
        },
        "test": {
            "exact_3of3_rate": metrics.test_exact_3of3_rate if metrics else None,
            "avg_set_match": metrics.test_avg_set_match if metrics else None,
            "races": metrics.test_races if metrics else None,
        },
        "seeds": {"model_random_state": resolved_model_random_state},
        "runtime_params": {"model_random_state": resolved_model_random_state},
        "output_path": artifacts.output_path if artifacts is not None else None,
        "manifest_path": artifacts.manifest_path if artifacts is not None else None,
        "model_config_id": (
            common_result.model_config_id if common_result is not None else None
        ),
        "core_metrics": metrics.model_dump(mode="json")
        if metrics is not None
        else None,
        "common_result": (
            common_result.model_dump(mode="json") if common_result is not None else None
        ),
        "detailed_result": (
            detailed_result.model_dump(mode="json")
            if detailed_result is not None
            else None
        ),
        "execution_journal_path": str(journal_context.path),
        "seed_result_repository_path": str(journal_context.seed_result_repository_path),
        "detailed_seed_result_repository_path": str(
            journal_context.detailed_seed_result_repository_path
        ),
        "execution_summary": execution_summary,
        "seed_result_repository_summary": seed_result_repository_summary,
        "detailed_seed_result_repository_summary": (
            detailed_seed_result_repository_summary
        ),
    }


def _plan_task_execution(
    tasks: tuple[SingleSeedEvaluationTask, ...],
    *,
    journal_context: ExecutionJournalContext,
) -> tuple[list[TaskExecutionDecision], dict[str, Any]]:
    journal = _load_existing_journal(journal_context.path)
    detailed_repository = _load_existing_detailed_repository(
        journal_context.detailed_seed_result_repository_path
    )
    records_by_run_id = (
        {record.run_id: record for record in journal.records}
        if journal is not None
        else {}
    )
    detailed_run_ids = (
        {record.run_id for record in detailed_repository.records}
        if detailed_repository is not None
        else set()
    )
    reason_counts: dict[str, int] = {}
    decisions: list[TaskExecutionDecision] = []

    for task in tasks:
        run_id = task.run_id or task.task_id
        record = records_by_run_id.get(run_id)
        if record is None:
            action = "execute"
            reason = "missing_execution_record"
        elif record.status == "completed":
            artifacts = record.artifacts
            output_exists = (
                artifacts is not None
                and bool(artifacts.output_path)
                and Path(str(artifacts.output_path)).exists()
            )
            manifest_exists = (
                artifacts is not None
                and bool(artifacts.manifest_path)
                and Path(str(artifacts.manifest_path)).exists()
            )
            detailed_exists = run_id in detailed_run_ids
            if (
                record.metrics is not None
                and record.common_result is not None
                and output_exists
                and manifest_exists
                and detailed_exists
            ):
                action = "reuse_completed"
                reason = "already_completed_with_storage"
            else:
                action = "execute"
                reason = "storage_incomplete"
        elif record.status == "failed":
            action = "execute"
            reason = "previous_failed"
        else:
            action = "execute"
            reason = "non_terminal_existing_record"
        decisions.append(
            TaskExecutionDecision(
                task=task,
                action=action,
                reason=reason,
                existing_record=record,
            )
        )
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return decisions, {
        "total_task_count": len(tasks),
        "planned_execution_count": sum(
            1 for decision in decisions if decision.action == "execute"
        ),
        "reused_completed_count": sum(
            1 for decision in decisions if decision.action == "reuse_completed"
        ),
        "reason_counts": dict(sorted(reason_counts.items())),
    }


def _write_execution_storage(
    context: ExecutionJournalContext,
    record: SeedExecutionRecord,
    *,
    detailed_result: DetailedSeedResultRecord | None = None,
) -> tuple[
    ExecutionJournal,
    SeedResultRepository,
    DetailedSeedResultRepository,
]:
    context.path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = context.path.with_suffix(f"{context.path.suffix}.lock")
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        current = _load_existing_journal(context.path)
        updated = upsert_execution_record(
            current,
            record,
            group_id=context.group_id,
            evaluation_seeds=context.evaluation_seeds,
        )
        tmp_path = context.path.with_suffix(f"{context.path.suffix}.tmp")
        tmp_path.write_text(
            json.dumps(updated.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(context.path)
        repository = seed_result_repository_from_journal(updated)
        repository_tmp_path = context.seed_result_repository_path.with_suffix(
            f"{context.seed_result_repository_path.suffix}.tmp"
        )
        repository_tmp_path.write_text(
            json.dumps(
                repository.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        repository_tmp_path.replace(context.seed_result_repository_path)
        detailed_repository = build_detailed_seed_result_repository(
            group_id=context.group_id,
            evaluation_seeds=context.evaluation_seeds,
        )
        if context.detailed_seed_result_repository_path.exists():
            detailed_payload = json.loads(
                context.detailed_seed_result_repository_path.read_text(encoding="utf-8")
            )
            detailed_repository = DetailedSeedResultRepository.model_validate(
                detailed_payload
            )
        if detailed_result is not None:
            detailed_repository = upsert_detailed_seed_result_record(
                detailed_repository,
                detailed_result,
                group_id=context.group_id,
                evaluation_seeds=context.evaluation_seeds,
            )
        detailed_repository_tmp_path = (
            context.detailed_seed_result_repository_path.with_suffix(
                f"{context.detailed_seed_result_repository_path.suffix}.tmp"
            )
        )
        detailed_repository_tmp_path.write_text(
            json.dumps(
                detailed_repository.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        detailed_repository_tmp_path.replace(
            context.detailed_seed_result_repository_path
        )
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return updated, repository, detailed_repository


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _extract_core_metrics(result: dict[str, Any]) -> SeedExecutionMetrics:
    summary = result.get("summary") or {}
    dev = result.get("dev") or {}
    test = result.get("test") or {}
    normalized = normalize_metric_mapping(
        {
            "robust_exact_rate": summary.get("robust_exact_rate"),
            "overfit_safe_exact_rate": summary.get("overfit_safe_exact_rate"),
            "blended_exact_rate": summary.get("blended_exact_rate"),
            "rolling_min_exact_rate": summary.get("rolling_min_exact_rate"),
            "rolling_mean_exact_rate": summary.get("rolling_mean_exact_rate"),
            "dev_test_gap": summary.get("dev_test_gap"),
            "dev_exact_3of3_rate": dev.get("exact_3of3_rate"),
            "dev_avg_set_match": dev.get("avg_set_match"),
            "test_exact_3of3_rate": test.get("exact_3of3_rate"),
            "test_avg_set_match": test.get("avg_set_match"),
        }
    )
    return SeedExecutionMetrics(
        robust_exact_rate=normalized["robust_exact_rate"].normalized_value,
        overfit_safe_exact_rate=normalized["overfit_safe_exact_rate"].normalized_value,
        blended_exact_rate=normalized["blended_exact_rate"].normalized_value,
        rolling_min_exact_rate=normalized["rolling_min_exact_rate"].normalized_value,
        rolling_mean_exact_rate=normalized["rolling_mean_exact_rate"].normalized_value,
        dev_test_gap=normalized["dev_test_gap"].normalized_value,
        dev_exact_3of3_rate=normalized["dev_exact_3of3_rate"].normalized_value,
        dev_avg_set_match=normalized["dev_avg_set_match"].normalized_value,
        dev_races=_int_or_none(dev.get("races")),
        test_exact_3of3_rate=normalized["test_exact_3of3_rate"].normalized_value,
        test_avg_set_match=normalized["test_avg_set_match"].normalized_value,
        test_races=_int_or_none(test.get("races")),
    )


def _resolve_model_config_id(
    task: SingleSeedEvaluationTask,
    task_result: dict[str, Any],
) -> str:
    explicit = task_result.get("model_config_id")
    if explicit is not None:
        return str(explicit)

    config = task_result.get("config")
    if isinstance(config, dict):
        return build_model_config_id(config)

    config_path = Path(task.config_path)
    if config_path.exists():
        return build_model_config_id(config_path.read_bytes())
    return build_model_config_id(str(config_path))


def _extract_overall_holdout_hit_rate(
    task_result: dict[str, Any],
    metrics: SeedExecutionMetrics,
) -> tuple[float, str]:
    summary = task_result.get("summary") or {}
    test = task_result.get("test") or {}
    candidates: tuple[tuple[str, str, Any], ...] = (
        (
            "summary.overfit_safe_exact_rate",
            "overfit_safe_exact_rate",
            summary.get("overfit_safe_exact_rate"),
        ),
        (
            "summary.robust_exact_rate",
            "robust_exact_rate",
            summary.get("robust_exact_rate"),
        ),
        (
            "test.exact_3of3_rate",
            "test_exact_3of3_rate",
            test.get("exact_3of3_rate"),
        ),
    )
    for source, metric_name, value in candidates:
        normalized = normalize_metric_value(metric_name, value)
        if normalized.status == "ok" and normalized.normalized_value is not None:
            return normalized.normalized_value, source

    if metrics.test_exact_3of3_rate is not None:
        return float(metrics.test_exact_3of3_rate), "test.exact_3of3_rate"

    raise ValueError("completed seed task must provide an overall holdout hit rate.")


def _normalize_parameter_context(
    task_result: dict[str, Any],
) -> dict[str, Any]:
    parameter_context = task_result.get("parameter_context")
    if not isinstance(parameter_context, dict):
        return {}
    return parameter_context


def _build_task_metric_normalization_snapshot(
    task_result: dict[str, Any],
    *,
    overall_holdout_hit_rate: float,
    overall_holdout_hit_rate_source: str,
) -> dict[str, Any]:
    summary = task_result.get("summary")
    dev = task_result.get("dev")
    test = task_result.get("test")
    summary_payload = summary if isinstance(summary, dict) else {}
    dev_payload = dev if isinstance(dev, dict) else {}
    test_payload = test if isinstance(test, dict) else {}

    raw_metric_values = {
        "overall_holdout_hit_rate": overall_holdout_hit_rate,
        "overfit_safe_exact_rate": summary_payload.get("overfit_safe_exact_rate"),
        "robust_exact_rate": summary_payload.get("robust_exact_rate"),
        "blended_exact_rate": summary_payload.get("blended_exact_rate"),
        "rolling_min_exact_rate": summary_payload.get("rolling_min_exact_rate"),
        "rolling_mean_exact_rate": summary_payload.get("rolling_mean_exact_rate"),
        "dev_test_gap": summary_payload.get("dev_test_gap"),
        "dev_exact_3of3_rate": dev_payload.get("exact_3of3_rate"),
        "dev_avg_set_match": dev_payload.get("avg_set_match"),
        "test_exact_3of3_rate": test_payload.get("exact_3of3_rate"),
        "test_avg_set_match": test_payload.get("avg_set_match"),
    }
    snapshot = build_metric_normalization_snapshot(
        raw_metric_values,
        metric_names=DEFAULT_SEED_METRIC_NAMES,
    )
    snapshot["overall_holdout_hit_rate_source"] = overall_holdout_hit_rate_source
    return snapshot


def _build_detailed_result_record(
    *,
    task: SingleSeedEvaluationTask,
    run_id: str,
    seed_index: int,
    resolved_model_random_state: int,
    finished_at: datetime,
    metrics: SeedExecutionMetrics,
    overall_holdout_hit_rate: float,
    holdout_hit_rate_source: str,
    task_result: dict[str, Any],
    model_config_id: str,
) -> DetailedSeedResultRecord:
    parameter_context = _normalize_parameter_context(task_result)
    config = task_result.get("config")
    config_payload = config if isinstance(config, dict) else {}
    experiment = config_payload.get("experiment")
    experiment_payload = experiment if isinstance(experiment, dict) else {}
    model_search = experiment_payload.get("model_search")
    model_search_payload = model_search if isinstance(model_search, dict) else {}
    common_hyperparameters = experiment_payload.get("common_hyperparameters")
    common_hyperparameters_payload = (
        common_hyperparameters if isinstance(common_hyperparameters, dict) else {}
    )
    input_contract = parameter_context.get("input_contract")
    input_contract_payload = input_contract if isinstance(input_contract, dict) else {}
    execution_matrix = input_contract_payload.get("execution_matrix")
    execution_matrix_payload = (
        execution_matrix if isinstance(execution_matrix, dict) else {}
    )
    holdout_payload = execution_matrix_payload.get("holdout")
    holdout_settings = holdout_payload if isinstance(holdout_payload, dict) else {}
    model_parameters = parameter_context.get("model_parameters")
    model_parameters_payload = (
        model_parameters if isinstance(model_parameters, dict) else {}
    )
    evaluation_seeds = tuple(
        int(seed)
        for seed in (
            parameter_context.get("evaluation_seeds")
            or experiment_payload.get("evaluation_seeds")
            or ()
        )
    )
    selected_run = input_contract_payload.get("selected_run")
    selected_run_payload = selected_run if isinstance(selected_run, dict) else {}
    dataset_selection = task_result.get("dataset_selection")
    dataset_selection_payload = (
        dataset_selection if isinstance(dataset_selection, dict) else None
    )

    return DetailedSeedResultRecord(
        run_id=run_id,
        task_id=task.task_id,
        seed=resolved_model_random_state,
        seed_index=seed_index,
        run_at=finished_at,
        model_config_id=model_config_id,
        split_settings=SplitSettingsSnapshot(
            dataset=str(
                input_contract_payload.get("dataset")
                or config_payload.get("dataset")
                or "unknown"
            ),
            split=dict(
                input_contract_payload.get("split") or config_payload.get("split") or {}
            ),
            rolling_windows=tuple(
                dict(item)
                for item in (
                    input_contract_payload.get("rolling_windows")
                    or config_payload.get("rolling_windows")
                    or ()
                )
                if isinstance(item, dict)
            ),
            evaluation_contract=dict(
                input_contract_payload.get("evaluation_contract")
                or config_payload.get("evaluation_contract")
                or {}
            ),
            input_data=dict(
                input_contract_payload.get("input_data")
                or experiment_payload.get("input_data")
                or {}
            ),
            input_contract_signature=parameter_context.get("input_contract_signature"),
            selected_run_id=selected_run_payload.get("run_id"),
            dataset_selection=dataset_selection_payload,
        ),
        search_parameters=SearchParametersSnapshot(
            experiment_profile_version=experiment_payload.get("profile_version"),
            repeat_count=experiment_payload.get("repeat_count"),
            evaluation_seeds=evaluation_seeds,
            model_search_strategy=model_search_payload.get("strategy"),
            candidate_names=tuple(
                str(candidate.get("name"))
                for candidate in model_search_payload.get("candidates", ())
                if isinstance(candidate, dict) and candidate.get("name") is not None
            ),
            candidate_count=len(
                [
                    candidate
                    for candidate in model_search_payload.get("candidates", ())
                    if isinstance(candidate, dict)
                ]
            ),
            model_candidates=tuple(
                dict(candidate)
                for candidate in model_search_payload.get("candidates", ())
                if isinstance(candidate, dict)
            ),
            common_hyperparameters=dict(common_hyperparameters_payload),
            resolved_model_parameters=dict(model_parameters_payload),
            parameter_source=str(
                parameter_context.get("parameter_source")
                or "task_result.runtime_params"
            ),
            model_parameter_source=str(
                parameter_context.get("model_parameter_source") or "task_result.config"
            ),
        ),
        seed_context=SeedContextSnapshot(
            run_id=run_id,
            seed_index=seed_index,
            model_random_state=resolved_model_random_state,
            evaluation_seeds=evaluation_seeds,
            parameter_source=str(
                parameter_context.get("parameter_source")
                or "task_result.runtime_params"
            ),
            selection_seed_invariant=(
                holdout_settings.get("selection_seed_invariant")
                if holdout_settings
                else config_payload.get("evaluation_contract", {}).get(
                    "selection_seed_invariant"
                )
            ),
        ),
        evaluation_result=EvaluationOutcomeSnapshot(
            summary=dict(task_result.get("summary") or {}),
            dev=(
                dict(task_result.get("dev") or {})
                if task_result.get("dev") is not None
                else None
            ),
            test=(
                dict(task_result.get("test") or {})
                if task_result.get("test") is not None
                else None
            ),
            core_metrics=metrics,
            overall_holdout_hit_rate=overall_holdout_hit_rate,
            overall_holdout_hit_rate_source=holdout_hit_rate_source,
            metric_normalization=_build_task_metric_normalization_snapshot(
                task_result,
                overall_holdout_hit_rate=overall_holdout_hit_rate,
                overall_holdout_hit_rate_source=holdout_hit_rate_source,
            ),
        ),
        artifacts=DetailedSeedResultArtifacts(
            output_path=task_result.get("output_path"),
            manifest_path=task_result.get("manifest_path"),
            config_path=task.config_path,
            runtime_params_path=task.runtime_params_path,
        ),
    )


def _invoke_task(
    task: SingleSeedEvaluationTask,
    *,
    task_runner: Callable[[SingleSeedEvaluationTask], dict[str, Any]],
    journal_context: ExecutionJournalContext | None = None,
    now_factory: Callable[[], datetime] = lambda: datetime.now().astimezone(),
) -> dict[str, Any]:
    run_id = task.run_id or task.task_id
    started_at = now_factory()
    seed_index = _seed_index_for_task(task)

    if journal_context is not None:
        _write_execution_storage(
            journal_context,
            SeedExecutionRecord(
                run_id=run_id,
                task_id=task.task_id,
                seed_index=seed_index,
                model_random_state=task.model_random_state,
                status="running",
                started_at=started_at,
            ),
        )

    try:
        task_result = task_runner(task)
    except Exception as exc:
        finished_at = now_factory()
        halt_batch = isinstance(exc, PredictionCoverageError)
        coverage_failure_details = exc.to_failure_details() if halt_batch else {}
        failure = SeedExecutionFailure(
            error_type=type(exc).__name__,
            error_message=str(exc) or type(exc).__name__,
            reason_code=coverage_failure_details.get("reason_code"),
            reason=coverage_failure_details.get("reason"),
            missing_count=coverage_failure_details.get("missing_count"),
            missing_items=tuple(
                str(item) for item in coverage_failure_details.get("missing_items", ())
            ),
            incomplete_top3_count=coverage_failure_details.get("incomplete_top3_count"),
            incomplete_top3_race_ids=tuple(
                str(item)
                for item in coverage_failure_details.get("incomplete_top3_race_ids", ())
            ),
            expected_race_count=coverage_failure_details.get("expected_race_count"),
            predicted_race_count=coverage_failure_details.get("predicted_race_count"),
            evaluation_window=coverage_failure_details.get("evaluation_window"),
            traceback_excerpt=traceback.format_exc(limit=20),
        )
        journal = None
        seed_result_repository = None
        detailed_seed_result_repository = None
        if journal_context is not None:
            (
                journal,
                seed_result_repository,
                detailed_seed_result_repository,
            ) = _write_execution_storage(
                journal_context,
                SeedExecutionRecord(
                    run_id=run_id,
                    task_id=task.task_id,
                    seed_index=seed_index,
                    model_random_state=task.model_random_state,
                    status="failed",
                    started_at=started_at,
                    finished_at=finished_at,
                    failure=failure,
                ),
            )
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "seed_index": seed_index,
            "status": "failed",
            "execution_action": "executed",
            "resume_reason": "task_execution_failed",
            "resumed_from_existing": False,
            "halt_batch": halt_batch,
            "failure_reason_code": (
                "prediction_coverage_validation_failed" if halt_batch else None
            ),
            "failure_reason": coverage_failure_details.get("reason"),
            "failure_missing_count": coverage_failure_details.get("missing_count"),
            "failure_missing_items": coverage_failure_details.get("missing_items", []),
            "error": failure.model_dump(mode="json"),
            "execution_journal_path": (
                str(journal_context.path) if journal_context is not None else None
            ),
            "seed_result_repository_path": (
                str(journal_context.seed_result_repository_path)
                if journal_context is not None
                else None
            ),
            "detailed_seed_result_repository_path": (
                str(journal_context.detailed_seed_result_repository_path)
                if journal_context is not None
                else None
            ),
            "execution_summary": (
                journal.summary.model_dump(mode="json") if journal is not None else None
            ),
            "seed_result_repository_summary": (
                seed_result_repository.summary.model_dump(mode="json")
                if seed_result_repository is not None
                else None
            ),
            "detailed_seed_result_repository_summary": (
                detailed_seed_result_repository.summary.model_dump(mode="json")
                if detailed_seed_result_repository is not None
                else None
            ),
        }

    finished_at = now_factory()
    metrics = _extract_core_metrics(task_result)
    overall_holdout_hit_rate, holdout_hit_rate_source = (
        _extract_overall_holdout_hit_rate(
            task_result,
            metrics,
        )
    )
    resolved_model_random_state = (
        (task_result.get("runtime_params") or {}).get("model_random_state")
        or task.model_random_state
        or _model_random_state_from_run_id(run_id)
    )
    if resolved_model_random_state is None:
        raise ValueError("completed seed task must resolve model_random_state.")
    model_config_id = _resolve_model_config_id(task, task_result)
    common_result = CommonSeedResultRecord(
        run_id=run_id,
        seed=resolved_model_random_state,
        run_at=finished_at,
        model_config_id=model_config_id,
        overall_holdout_hit_rate=overall_holdout_hit_rate,
        overall_holdout_hit_rate_source=holdout_hit_rate_source,
    )
    detailed_result = _build_detailed_result_record(
        task=task,
        run_id=run_id,
        seed_index=seed_index,
        resolved_model_random_state=resolved_model_random_state,
        finished_at=finished_at,
        metrics=metrics,
        overall_holdout_hit_rate=overall_holdout_hit_rate,
        holdout_hit_rate_source=holdout_hit_rate_source,
        task_result=task_result,
        model_config_id=model_config_id,
    )
    journal = None
    seed_result_repository = None
    detailed_seed_result_repository = None
    if journal_context is not None:
        (
            journal,
            seed_result_repository,
            detailed_seed_result_repository,
        ) = _write_execution_storage(
            journal_context,
            SeedExecutionRecord(
                run_id=run_id,
                task_id=task.task_id,
                seed_index=seed_index,
                model_random_state=resolved_model_random_state,
                status="completed",
                started_at=started_at,
                finished_at=finished_at,
                artifacts=SeedExecutionArtifacts(
                    output_path=task_result.get("output_path"),
                    manifest_path=task_result.get("manifest_path"),
                ),
                metrics=metrics,
                common_result=common_result,
            ),
            detailed_result=detailed_result,
        )

    return {
        **task_result,
        "seed_index": seed_index,
        "status": "completed",
        "execution_action": "executed",
        "resume_reason": "executed_now",
        "resumed_from_existing": False,
        "core_metrics": metrics.model_dump(mode="json"),
        "common_result": common_result.model_dump(mode="json"),
        "detailed_result": detailed_result.model_dump(mode="json"),
        "execution_journal_path": (
            str(journal_context.path) if journal_context is not None else None
        ),
        "seed_result_repository_path": (
            str(journal_context.seed_result_repository_path)
            if journal_context is not None
            else None
        ),
        "detailed_seed_result_repository_path": (
            str(journal_context.detailed_seed_result_repository_path)
            if journal_context is not None
            else None
        ),
        "execution_summary": (
            journal.summary.model_dump(mode="json") if journal is not None else None
        ),
        "seed_result_repository_summary": (
            seed_result_repository.summary.model_dump(mode="json")
            if seed_result_repository is not None
            else None
        ),
        "detailed_seed_result_repository_summary": (
            detailed_seed_result_repository.summary.model_dump(mode="json")
            if detailed_seed_result_repository is not None
            else None
        ),
    }


def _load_request_payload(payload: Any) -> OrchestratorRequest:
    if isinstance(payload, list):
        return OrchestratorRequest.model_validate({"tasks": payload})
    if not isinstance(payload, dict):
        raise ValueError("request payload must be a JSON object or task array.")
    if "task" in payload or "tasks" in payload:
        return OrchestratorRequest.model_validate(payload)
    return OrchestratorRequest.model_validate({"task": payload})


def _should_halt_batch_after_result(result: dict[str, Any]) -> bool:
    return bool(result.get("halt_batch"))


def resolve_execution_mode(request: OrchestratorRequest) -> SchedulingMode:
    if request.mode is not SchedulingMode.AUTO:
        return request.mode

    batch = request.batch
    if not batch or not batch.enabled:
        return SchedulingMode.SEQUENTIAL

    if batch.group_id:
        return SchedulingMode.BATCH

    expected_task_count = batch.expected_task_count or 1
    max_workers = batch.max_workers or 1
    if expected_task_count > 1 or max_workers > 1:
        return SchedulingMode.BATCH

    return SchedulingMode.SEQUENTIAL


def execute_single_seed_task(
    task: SingleSeedEvaluationTask,
    *,
    dataset_artifact_root: Path = SNAPSHOT_DIR,
    evaluate_fn: Callable[..., dict[str, Any]] = evaluate,
    bundle_writer: Callable[..., tuple[Path, Path]] = write_research_evaluation_bundle,
    created_at_factory: Callable[[], datetime] = lambda: datetime.now().astimezone(),
) -> dict[str, Any]:
    config_path = Path(task.config_path)
    output_path = Path(task.output_path)
    runtime_params_path = (
        Path(task.runtime_params_path) if task.runtime_params_path else None
    )
    evaluation_context = load_evaluation_parameter_context(
        config_path=config_path,
        seed_index=task.seed_index,
        run_id=task.run_id,
        runtime_params_path=runtime_params_path,
        model_random_state=task.model_random_state,
    )

    result = evaluate_fn(
        config_path,
        evaluation_context=evaluation_context,
    )
    dataset_artifacts = resolve_offline_evaluation_dataset_artifacts(
        str(result["config"]["dataset"]),
        artifact_root=dataset_artifact_root,
    )
    written_output_path, manifest_path = bundle_writer(
        result=result,
        config_path=config_path,
        output_path=output_path,
        created_at=created_at_factory(),
        dataset_artifacts=dataset_artifacts,
        runtime_params_path=runtime_params_path,
        runtime_params=result["runtime_params"],
    )
    return {
        "task_id": task.task_id,
        "run_id": task.run_id,
        "output_path": str(written_output_path),
        "manifest_path": str(manifest_path),
        "config": result["config"],
        "model_config_id": build_model_config_id(result["config"]),
        "parameter_context": result.get("parameter_context"),
        "summary": result["summary"],
        "dev": result.get("dev"),
        "test": result.get("test"),
        "seeds": result["seeds"],
        "runtime_params": result["runtime_params"],
    }


def run_sequential(
    task: SingleSeedEvaluationTask,
    *,
    tasks: tuple[SingleSeedEvaluationTask, ...] | None = None,
    task_runner: Callable[
        [SingleSeedEvaluationTask], dict[str, Any]
    ] = execute_single_seed_task,
    journal_context: ExecutionJournalContext | None = None,
) -> list[dict[str, Any]]:
    scheduled_tasks = tasks or (task,)
    results: list[dict[str, Any]] = []
    for scheduled_task in scheduled_tasks:
        result = _invoke_task(
            scheduled_task,
            task_runner=task_runner,
            journal_context=journal_context,
        )
        results.append(result)
        if _should_halt_batch_after_result(result):
            break
    return results


def run_batch(
    task: SingleSeedEvaluationTask,
    *,
    batch: BatchExecutionOptions,
    tasks: tuple[SingleSeedEvaluationTask, ...] | None = None,
    task_runner: Callable[
        [SingleSeedEvaluationTask], dict[str, Any]
    ] = execute_single_seed_task,
    journal_context: ExecutionJournalContext | None = None,
) -> list[dict[str, Any]]:
    scheduled_tasks = tasks or (task,)
    max_workers = batch.max_workers or 1
    if len(scheduled_tasks) <= 1 or max_workers <= 1:
        return run_sequential(
            task,
            tasks=scheduled_tasks,
            task_runner=task_runner,
            journal_context=journal_context,
        )

    results_by_index: dict[int, dict[str, Any]] = {}
    next_index_to_submit = 0
    halt_submission = False

    def _submit_task(
        executor: ThreadPoolExecutor,
        index: int,
        scheduled_task: SingleSeedEvaluationTask,
    ):
        return executor.submit(
            _invoke_task,
            scheduled_task,
            task_runner=task_runner,
            journal_context=journal_context,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        in_flight: dict[Any, int] = {}
        while (
            next_index_to_submit < len(scheduled_tasks) and len(in_flight) < max_workers
        ):
            in_flight[
                _submit_task(
                    executor,
                    next_index_to_submit,
                    scheduled_tasks[next_index_to_submit],
                )
            ] = next_index_to_submit
            next_index_to_submit += 1

        while in_flight:
            done, _pending = wait(
                tuple(in_flight.keys()),
                return_when=FIRST_COMPLETED,
            )
            for future in done:
                index = in_flight.pop(future)
                result = future.result()
                results_by_index[index] = result
                if _should_halt_batch_after_result(result):
                    halt_submission = True

            if halt_submission:
                for future in list(in_flight.keys()):
                    if future.cancel():
                        in_flight.pop(future)
                continue

            while (
                next_index_to_submit < len(scheduled_tasks)
                and len(in_flight) < max_workers
            ):
                in_flight[
                    _submit_task(
                        executor,
                        next_index_to_submit,
                        scheduled_tasks[next_index_to_submit],
                    )
                ] = next_index_to_submit
                next_index_to_submit += 1

    return [results_by_index[index] for index in sorted(results_by_index)]


def orchestrate_request(
    request: OrchestratorRequest,
    *,
    task_runner: Callable[
        [SingleSeedEvaluationTask], dict[str, Any]
    ] = execute_single_seed_task,
    sequential_runner: Callable[..., list[dict[str, Any]]] = run_sequential,
    batch_runner: Callable[..., list[dict[str, Any]]] = run_batch,
) -> dict[str, Any]:
    resolved_mode = resolve_execution_mode(request)
    scheduled_tasks = _tasks_for_request(request)
    journal_context = _journal_context_for_request(request)
    decisions, recovery_summary = _plan_task_execution(
        scheduled_tasks,
        journal_context=journal_context,
    )
    tasks_to_execute = tuple(
        decision.task for decision in decisions if decision.action == "execute"
    )
    recovered_decisions = [
        decision for decision in decisions if decision.action == "reuse_completed"
    ]

    executed_results: list[dict[str, Any]] = []
    if tasks_to_execute:
        if resolved_mode is SchedulingMode.BATCH:
            executed_results = batch_runner(
                tasks_to_execute[0],
                batch=request.batch or BatchExecutionOptions(enabled=True),
                tasks=tasks_to_execute,
                task_runner=task_runner,
                journal_context=journal_context,
            )
        else:
            executed_results = sequential_runner(
                tasks_to_execute[0],
                tasks=tasks_to_execute,
                task_runner=task_runner,
                journal_context=journal_context,
            )

    (
        journal,
        seed_result_repository,
        detailed_seed_result_repository,
    ) = _synchronize_aggregate_storage(journal_context)
    detailed_records_by_run_id = (
        {record.run_id: record for record in detailed_seed_result_repository.records}
        if detailed_seed_result_repository is not None
        else {}
    )
    reused_results = [
        _build_existing_result_snapshot(
            decision.task,
            record=decision.existing_record,
            journal_context=journal_context,
            execution_summary=(
                journal.summary.model_dump(mode="json") if journal is not None else None
            ),
            seed_result_repository_summary=(
                seed_result_repository.summary.model_dump(mode="json")
                if seed_result_repository is not None
                else None
            ),
            detailed_seed_result_repository_summary=(
                detailed_seed_result_repository.summary.model_dump(mode="json")
                if detailed_seed_result_repository is not None
                else None
            ),
            detailed_result=detailed_records_by_run_id.get(
                decision.task.run_id or decision.task.task_id
            ),
        )
        for decision in recovered_decisions
        if decision.existing_record is not None
    ]
    executed_results_by_run_id = {
        (result.get("run_id") or result.get("task_id")): result
        for result in executed_results
    }
    reused_results_by_run_id = {
        (result.get("run_id") or result.get("task_id")): result
        for result in reused_results
    }
    results = [
        executed_results_by_run_id.get(task.run_id or task.task_id)
        or reused_results_by_run_id.get(task.run_id or task.task_id)
        for task in scheduled_tasks
    ]
    results = [result for result in results if result is not None]

    postprocess_report = (
        sync_seed_summary_report(journal, journal_path=journal_context.path)
        if journal is not None
        else None
    )
    failed_task_count = sum(1 for result in results if result.get("status") == "failed")

    return {
        "requested_mode": request.mode.value,
        "resolved_mode": resolved_mode.value,
        "task_count": len(scheduled_tasks),
        "executed_task_count": len(executed_results),
        "reused_completed_task_count": len(reused_results),
        "failed_task_count": failed_task_count,
        "execution_journal_path": str(journal_context.path),
        "seed_result_repository_path": str(journal_context.seed_result_repository_path),
        "detailed_seed_result_repository_path": str(
            journal_context.detailed_seed_result_repository_path
        ),
        "recovery_summary": recovery_summary,
        "execution_summary": (
            journal.summary.model_dump(mode="json") if journal is not None else None
        ),
        "postprocess_report": postprocess_report,
        "results": results,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="단일 시드 평가 작업을 자동 스케줄링해 실행한다."
    )
    parser.add_argument(
        "--request-file",
        help="오케스트레이터 요청 JSON 파일 경로. task 단독 JSON 또는 {task,mode,batch} 형식을 모두 허용한다.",
    )
    parser.add_argument(
        "--request-json",
        help="오케스트레이터 요청 JSON 문자열. task 단독 JSON 또는 {task,mode,batch} 형식을 모두 허용한다.",
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in SchedulingMode],
        help="CLI에서 모드를 강제 override 한다.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.request_file and not args.request_json:
        parser.error("--request-file 또는 --request-json 중 하나는 필요합니다.")

    if args.request_file:
        payload = json.loads(Path(args.request_file).read_text(encoding="utf-8"))
    else:
        payload = json.loads(args.request_json)

    request = _load_request_payload(payload)
    if args.mode:
        request = request.model_copy(update={"mode": SchedulingMode(args.mode)})

    result = orchestrate_request(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed_task_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
