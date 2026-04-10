"""10개 랜덤 시드 recent-holdout 반복 평가 러너."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from shared.execution_matrix import (
    DEFAULT_EVALUATION_SEEDS,
    DEFAULT_EXECUTION_JOURNAL_FILENAME,
    DEFAULT_SEED_RESULT_REPOSITORY_FILENAME,
    ExecutionMatrix,
    build_execution_matrix,
    build_model_config_id,
    validate_evaluation_seeds,
)
from shared.seed_result_recording import (
    DEFAULT_DETAILED_SEED_RESULT_REPOSITORY_FILENAME,
)

from autoresearch.evaluation_orchestrator import (
    BatchExecutionOptions,
    OrchestratorRequest,
    SchedulingMode,
    SingleSeedEvaluationTask,
    execute_single_seed_task,
    orchestrate_request,
)
from autoresearch.parameter_context import (
    load_evaluation_parameter_context,
    load_seed_matrix_parameter_context,
)
from autoresearch.seed_summary_report import (
    SUMMARY_REPORT_CSV_FILENAME,
    SUMMARY_REPORT_JSON_FILENAME,
    SUMMARY_REPORT_MARKDOWN_FILENAME,
)

DEFAULT_EXECUTION_MATRIX_FILENAME = "holdout_execution_matrix.json"
DEFAULT_EXECUTION_METADATA_FILENAME = "holdout_execution_metadata.json"
DEFAULT_OUTPUT_FILENAME = "research_clean.json"
TERMINAL_VERIFICATION_STATUSES = {"PASS", "FAIL"}
EXECUTION_METADATA_VERSION = "holdout-execution-metadata-v1"
CONSISTENCY_FIELD_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("config_path", ("config_path",)),
    ("config_sha256", ("config_sha256",)),
    ("input_contract_signature", ("input_contract_signature",)),
    ("model_config_id", ("model_config_id",)),
    ("evaluation_seeds", ("evaluation_seeds",)),
    ("parameter_source", ("parameter_source",)),
    ("model_parameter_source", ("model_parameter_source",)),
    ("runtime_params.model_random_state", ("runtime_params", "model_random_state")),
    ("model_parameters.candidate_name", ("model_parameters", "candidate_name")),
    ("model_parameters.kind", ("model_parameters", "kind")),
    ("model_parameters.params", ("model_parameters", "params")),
    (
        "model_parameters.positive_class_weight",
        ("model_parameters", "positive_class_weight"),
    ),
    ("model_parameters.imputer_strategy", ("model_parameters", "imputer_strategy")),
    ("model_parameters.prediction_top_k", ("model_parameters", "prediction_top_k")),
    ("model_parameters.random_state", ("model_parameters", "random_state")),
    (
        "model_parameters.random_state_source",
        ("model_parameters", "random_state_source"),
    ),
)


@dataclass(frozen=True, slots=True)
class SeedMatrixPlan:
    execution_matrix: ExecutionMatrix
    execution_matrix_path: Path
    execution_metadata_path: Path
    journal_path: Path
    output_dir: Path
    requests: tuple[OrchestratorRequest, ...]


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _parse_evaluation_seeds(raw: str | None) -> tuple[int, ...]:
    if raw is None or not raw.strip():
        return DEFAULT_EVALUATION_SEEDS
    return validate_evaluation_seeds(
        tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    )


def _stable_sha256(payload: Any) -> str:
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _extract_setting_snapshot(
    parameter_context: dict[str, Any],
    *,
    model_config_id: str | None = None,
) -> dict[str, Any]:
    config = parameter_context.get("config")
    resolved_model_config_id = model_config_id
    if resolved_model_config_id is None and isinstance(config, dict):
        resolved_model_config_id = build_model_config_id(config)

    runtime_params = parameter_context.get("runtime_params")
    model_parameters = parameter_context.get("model_parameters")

    return {
        "config_path": parameter_context.get("config_path"),
        "config_sha256": parameter_context.get("config_sha256"),
        "input_contract_signature": parameter_context.get("input_contract_signature"),
        "model_config_id": resolved_model_config_id,
        "evaluation_seeds": parameter_context.get("evaluation_seeds"),
        "parameter_source": parameter_context.get("parameter_source"),
        "model_parameter_source": parameter_context.get("model_parameter_source"),
        "runtime_params": (
            {"model_random_state": runtime_params.get("model_random_state")}
            if isinstance(runtime_params, dict)
            else None
        ),
        "model_parameters": (
            {
                "candidate_name": model_parameters.get("candidate_name"),
                "kind": model_parameters.get("kind"),
                "params": model_parameters.get("params"),
                "positive_class_weight": model_parameters.get("positive_class_weight"),
                "imputer_strategy": model_parameters.get("imputer_strategy"),
                "prediction_top_k": model_parameters.get("prediction_top_k"),
                "random_state": model_parameters.get("random_state"),
                "random_state_source": model_parameters.get("random_state_source"),
            }
            if isinstance(model_parameters, dict)
            else None
        ),
    }


def _build_expected_run_metadata(task: SingleSeedEvaluationTask) -> dict[str, Any]:
    runtime_params_path = (
        Path(task.runtime_params_path) if task.runtime_params_path else None
    )
    config_path = Path(task.config_path)
    try:
        parameter_context = load_evaluation_parameter_context(
            config_path=config_path,
            seed_index=task.seed_index,
            run_id=task.run_id,
            runtime_params_path=runtime_params_path,
            model_random_state=task.model_random_state,
        ).model_dump(mode="json")
        setting_snapshot = _extract_setting_snapshot(parameter_context)
    except ValueError:
        config_payload = (
            json.loads(config_path.read_text(encoding="utf-8"))
            if config_path.exists()
            else {}
        )
        raw_evaluation_seeds = None
        experiment = config_payload.get("experiment")
        if isinstance(experiment, dict):
            raw_seeds = experiment.get("evaluation_seeds")
            if isinstance(raw_seeds, list):
                raw_evaluation_seeds = [int(seed) for seed in raw_seeds]
        config_bytes = config_path.read_bytes() if config_path.exists() else b"{}"
        setting_snapshot = {
            "config_path": str(config_path.resolve()),
            "config_sha256": sha256(config_bytes).hexdigest(),
            "model_config_id": build_model_config_id(config_bytes),
            "evaluation_seeds": raw_evaluation_seeds,
            "parameter_source": None,
            "model_parameter_source": None,
            "runtime_params": {
                "model_random_state": task.model_random_state,
            },
            "model_parameters": None,
        }
    return {
        "run_id": task.run_id,
        "seed_index": task.seed_index,
        "setting_snapshot": setting_snapshot,
        "setting_signature": _stable_sha256(setting_snapshot),
    }


def _build_planned_execution_metadata(
    *,
    plan: SeedMatrixPlan,
    parameter_context: Any,
    phase: str,
    observed_runs: list[dict[str, Any]] | None = None,
    consistency_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_params = parameter_context.runtime_params
    expected_runs = [
        _build_expected_run_metadata(request.task) for request in plan.requests
    ]
    payload: dict[str, Any] = {
        "format_version": EXECUTION_METADATA_VERSION,
        "phase": phase,
        "plan": {
            "config_path": parameter_context.config_path,
            "config_sha256": parameter_context.config_sha256,
            "execution_matrix_path": str(plan.execution_matrix_path),
            "execution_journal_path": str(plan.journal_path),
            "execution_metadata_path": str(plan.execution_metadata_path),
            "evaluation_seeds": list(runtime_params.evaluation_seeds),
            "evaluation_seed_source": parameter_context.evaluation_seed_source,
            "group_id": runtime_params.group_id,
            "group_id_source": parameter_context.group_id_source,
            "max_workers": runtime_params.max_workers,
            "max_workers_source": parameter_context.max_workers_source,
            "execution_journal_path_source": parameter_context.execution_journal_path_source,
            "expected_run_count": len(plan.requests),
        },
        "expected_runs": expected_runs,
    }
    if observed_runs is not None:
        payload["observed_runs"] = observed_runs
    if consistency_check is not None:
        payload["consistency_check"] = consistency_check
    return payload


def _nested_value(payload: dict[str, Any] | None, path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _compare_setting_snapshots(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> list[str]:
    mismatches: list[str] = []
    for field_name, field_path in CONSISTENCY_FIELD_PATHS:
        expected_value = _nested_value(expected, field_path)
        if expected_value is None:
            continue
        if expected_value != _nested_value(observed, field_path):
            mismatches.append(field_name)
    return mismatches


def _build_execution_consistency_metadata(
    *,
    plan: SeedMatrixPlan,
    run_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_by_run_id = {
        item["run_id"]: item
        for item in (
            _build_expected_run_metadata(request.task) for request in plan.requests
        )
    }

    observed_by_run_id: dict[str, dict[str, Any]] = {}
    for run_result in run_results:
        results = run_result.get("results") or []
        for task_result in results:
            if not isinstance(task_result, dict):
                continue
            run_id = task_result.get("run_id")
            if isinstance(run_id, str):
                observed_by_run_id[run_id] = task_result

    observed_runs: list[dict[str, Any]] = []
    mismatched_run_ids: list[str] = []
    missing_parameter_context_run_ids: list[str] = []
    missing_run_ids: list[str] = []
    unexpected_run_ids = sorted(
        run_id for run_id in observed_by_run_id if run_id not in expected_by_run_id
    )
    field_mismatch_counts: dict[str, int] = {}

    for request in plan.requests:
        run_id = request.task.run_id
        if run_id is None:
            continue
        expected = expected_by_run_id[run_id]
        task_result = observed_by_run_id.get(run_id)
        if task_result is None:
            missing_run_ids.append(run_id)
            observed_runs.append(
                {
                    "run_id": run_id,
                    "seed_index": request.task.seed_index,
                    "status": "missing",
                    "parameter_context_present": False,
                    "matched_expected_settings": False,
                    "mismatch_fields": ["run_result_missing"],
                    "expected_setting_signature": expected["setting_signature"],
                    "observed_setting_signature": None,
                    "setting_snapshot": None,
                }
            )
            continue

        parameter_context = task_result.get("parameter_context")
        metadata_present = isinstance(parameter_context, dict)
        status = str(task_result.get("status") or "unknown")
        observed_snapshot = (
            _extract_setting_snapshot(
                parameter_context,
                model_config_id=(
                    str(task_result["model_config_id"])
                    if task_result.get("model_config_id") is not None
                    else None
                ),
            )
            if metadata_present
            else None
        )
        mismatch_fields = (
            _compare_setting_snapshots(expected["setting_snapshot"], observed_snapshot)
            if observed_snapshot is not None
            else ["parameter_context_missing"]
        )
        if not metadata_present:
            missing_parameter_context_run_ids.append(run_id)
        if mismatch_fields:
            mismatched_run_ids.append(run_id)
            for field_name in mismatch_fields:
                field_mismatch_counts[field_name] = (
                    field_mismatch_counts.get(field_name, 0) + 1
                )
        observed_runs.append(
            {
                "run_id": run_id,
                "seed_index": request.task.seed_index,
                "status": status,
                "parameter_context_present": metadata_present,
                "matched_expected_settings": not mismatch_fields,
                "mismatch_fields": mismatch_fields,
                "expected_setting_signature": expected["setting_signature"],
                "observed_setting_signature": (
                    _stable_sha256(observed_snapshot)
                    if observed_snapshot is not None
                    else None
                ),
                "setting_snapshot": observed_snapshot,
            }
        )

    passed = not (
        mismatched_run_ids
        or missing_parameter_context_run_ids
        or missing_run_ids
        or unexpected_run_ids
    )
    consistency_check = {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "checked_run_count": len(observed_runs),
        "expected_run_count": len(plan.requests),
        "mismatched_run_ids": mismatched_run_ids,
        "missing_parameter_context_run_ids": missing_parameter_context_run_ids,
        "missing_run_ids": missing_run_ids,
        "unexpected_run_ids": unexpected_run_ids,
        "field_mismatch_counts": field_mismatch_counts,
    }
    return observed_runs, consistency_check


def load_verification_gate_result(report_json_path: Path) -> dict[str, Any]:
    """최종 요약 리포트의 PASS/FAIL verdict를 읽고 게이트 판단용으로 정규화한다."""

    if not report_json_path.exists():
        raise ValueError(f"verification report not found: {report_json_path}")

    payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    verification_verdict = payload.get("verification_verdict")
    if not isinstance(verification_verdict, dict):
        raise ValueError("verification_verdict is missing from summary report")

    status = verification_verdict.get("status")
    if status not in TERMINAL_VERIFICATION_STATUSES:
        raise ValueError("verification_verdict.status must be one of PASS/FAIL")

    gate = payload.get("gate")
    if isinstance(gate, dict) and "passed" in gate:
        gate_passed = bool(gate["passed"])
        if gate_passed != (status == "PASS"):
            raise ValueError(
                "summary report gate.passed does not match verification_verdict.status"
            )

    return {
        "status": status,
        "passed": status == "PASS",
        "verification_verdict": verification_verdict,
    }


def build_seed_matrix_plan(
    *,
    config_path: Path,
    output_dir: Path,
    evaluation_seeds: tuple[int, ...] | None = None,
    group_id: str | None = None,
    journal_path: Path | None = None,
    max_workers: int | None = None,
) -> SeedMatrixPlan:
    parameter_context = load_seed_matrix_parameter_context(
        config_path=config_path,
        evaluation_seeds=evaluation_seeds,
        group_id=group_id,
        max_workers=max_workers,
        execution_journal_path=journal_path,
    )
    resolved_runtime_params = parameter_context.runtime_params
    execution_matrix = build_execution_matrix(
        evaluation_seeds=resolved_runtime_params.evaluation_seeds
    )
    if parameter_context.execution_matrix is not None:
        execution_matrix = parameter_context.execution_matrix
    normalized_output_dir = output_dir.resolve()
    normalized_output_dir.mkdir(parents=True, exist_ok=True)
    normalized_journal_path = (
        Path(resolved_runtime_params.execution_journal_path)
        if resolved_runtime_params.execution_journal_path is not None
        else normalized_output_dir / DEFAULT_EXECUTION_JOURNAL_FILENAME
    )
    execution_matrix_path = normalized_output_dir / DEFAULT_EXECUTION_MATRIX_FILENAME
    execution_metadata_path = (
        normalized_output_dir / DEFAULT_EXECUTION_METADATA_FILENAME
    )
    _atomic_write_json(
        execution_matrix_path,
        execution_matrix.model_dump(mode="json"),
    )

    requests: list[OrchestratorRequest] = []
    expected_task_count = len(execution_matrix.evaluation_seeds)
    for run in execution_matrix.build_runs():
        run_dir = normalized_output_dir / run.run_id
        task = SingleSeedEvaluationTask(
            task_id=f"holdout-seed-eval-{run.seed_index:02d}",
            run_id=run.run_id,
            seed_index=run.seed_index,
            config_path=str(config_path.resolve()),
            output_path=str(run_dir / DEFAULT_OUTPUT_FILENAME),
            runtime_params_path=None,
            model_random_state=None,
        )
        requests.append(
            OrchestratorRequest(
                task=task,
                mode=SchedulingMode.SEQUENTIAL,
                batch=BatchExecutionOptions(
                    enabled=False,
                    group_id=resolved_runtime_params.group_id,
                    expected_task_count=expected_task_count,
                    max_workers=resolved_runtime_params.max_workers,
                    execution_journal_path=str(normalized_journal_path),
                    evaluation_seeds=execution_matrix.evaluation_seeds,
                ),
            )
        )

    plan = SeedMatrixPlan(
        execution_matrix=execution_matrix,
        execution_matrix_path=execution_matrix_path,
        execution_metadata_path=execution_metadata_path,
        journal_path=normalized_journal_path,
        output_dir=normalized_output_dir,
        requests=tuple(requests),
    )
    _atomic_write_json(
        execution_metadata_path,
        _build_planned_execution_metadata(
            plan=plan,
            parameter_context=parameter_context,
            phase="planned",
        ),
    )
    return plan


def _execute_request(
    request: OrchestratorRequest,
    *,
    task_runner: Callable[[SingleSeedEvaluationTask], dict[str, Any]],
    orchestrate_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    return orchestrate_fn(request, task_runner=task_runner)


def _build_batch_request(plan: SeedMatrixPlan) -> OrchestratorRequest:
    if not plan.requests:
        raise ValueError("seed matrix plan must include at least one request.")

    first_batch = plan.requests[0].batch or BatchExecutionOptions(enabled=True)
    return OrchestratorRequest(
        tasks=tuple(request.task for request in plan.requests),
        mode=SchedulingMode.BATCH,
        batch=BatchExecutionOptions(
            enabled=True,
            group_id=first_batch.group_id,
            expected_task_count=len(plan.requests),
            max_workers=first_batch.max_workers,
            execution_journal_path=first_batch.execution_journal_path,
            evaluation_seeds=first_batch.evaluation_seeds,
        ),
    )


def _iter_task_results(run_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for run_result in run_results:
        results = run_result.get("results") or []
        for task_result in results:
            if isinstance(task_result, dict):
                flattened.append(task_result)
    flattened.sort(
        key=lambda item: (
            item.get("seed_index") or 0,
            item.get("run_id") or "",
        )
    )
    return flattened


def execute_seed_matrix(
    *,
    config_path: Path,
    output_dir: Path,
    evaluation_seeds: tuple[int, ...] | None = None,
    group_id: str | None = None,
    journal_path: Path | None = None,
    max_workers: int | None = None,
    task_runner: Callable[
        [SingleSeedEvaluationTask], dict[str, Any]
    ] = execute_single_seed_task,
    orchestrate_fn: Callable[..., dict[str, Any]] = orchestrate_request,
) -> dict[str, Any]:
    plan = build_seed_matrix_plan(
        config_path=config_path,
        output_dir=output_dir,
        evaluation_seeds=evaluation_seeds,
        group_id=group_id,
        journal_path=journal_path,
        max_workers=max_workers,
    )
    parameter_context = load_seed_matrix_parameter_context(
        config_path=config_path,
        evaluation_seeds=evaluation_seeds,
        group_id=group_id,
        max_workers=max_workers,
        execution_journal_path=journal_path,
    )
    run_results = [
        _execute_request(
            _build_batch_request(plan),
            task_runner=task_runner,
            orchestrate_fn=orchestrate_fn,
        )
    ]
    task_results = _iter_task_results(run_results)

    report_json_path = plan.journal_path.with_name(SUMMARY_REPORT_JSON_FILENAME)
    report_markdown_path = plan.journal_path.with_name(SUMMARY_REPORT_MARKDOWN_FILENAME)
    report_csv_path = plan.journal_path.with_name(SUMMARY_REPORT_CSV_FILENAME)
    repository_path = plan.journal_path.with_name(
        DEFAULT_SEED_RESULT_REPOSITORY_FILENAME
    )
    detailed_repository_path = plan.journal_path.with_name(
        DEFAULT_DETAILED_SEED_RESULT_REPOSITORY_FILENAME
    )
    report_payload = (
        json.loads(report_json_path.read_text(encoding="utf-8"))
        if report_json_path.exists()
        else None
    )
    observed_runs, consistency_check = _build_execution_consistency_metadata(
        plan=plan,
        run_results=run_results,
    )
    execution_metadata_payload = _build_planned_execution_metadata(
        plan=plan,
        parameter_context=parameter_context,
        phase="completed",
        observed_runs=observed_runs,
        consistency_check=consistency_check,
    )
    _atomic_write_json(plan.execution_metadata_path, execution_metadata_payload)

    flattened_runs: list[dict[str, Any]] = []
    for task_result in task_results:
        common_result = task_result.get("common_result") or {}
        flattened_runs.append(
            {
                "run_id": task_result.get("run_id"),
                "seed_index": task_result.get("seed_index"),
                "model_random_state": (
                    task_result.get("runtime_params", {}).get("model_random_state")
                    or task_result.get("seeds", {}).get("model_random_state")
                    or task_result.get("model_random_state")
                ),
                "status": task_result.get("status"),
                "execution_action": task_result.get("execution_action"),
                "resume_reason": task_result.get("resume_reason"),
                "resumed_from_existing": bool(task_result.get("resumed_from_existing")),
                "overall_holdout_hit_rate": common_result.get(
                    "overall_holdout_hit_rate"
                ),
                "overall_holdout_hit_rate_source": common_result.get(
                    "overall_holdout_hit_rate_source"
                ),
                "detailed_result_record_present": isinstance(
                    task_result.get("detailed_result"),
                    dict,
                ),
                "output_path": task_result.get("output_path"),
                "manifest_path": task_result.get("manifest_path"),
                "parameter_context_present": isinstance(
                    task_result.get("parameter_context"),
                    dict,
                ),
            }
        )

    return {
        "config_path": str(config_path.resolve()),
        "output_dir": str(plan.output_dir),
        "execution_matrix_path": str(plan.execution_matrix_path),
        "execution_metadata_path": str(plan.execution_metadata_path),
        "execution_journal_path": str(plan.journal_path),
        "seed_result_repository_path": str(repository_path),
        "detailed_seed_result_repository_path": str(detailed_repository_path),
        "summary_report_json_path": str(report_json_path),
        "summary_report_markdown_path": str(report_markdown_path),
        "summary_report_csv_path": str(report_csv_path),
        "evaluation_seeds": list(plan.execution_matrix.evaluation_seeds),
        "execution_metadata": execution_metadata_payload,
        "task_count": len(flattened_runs),
        "executed_task_count": sum(
            1 for run in flattened_runs if run.get("execution_action") == "executed"
        ),
        "reused_completed_task_count": sum(
            1
            for run in flattened_runs
            if run.get("execution_action") == "reused_completed"
        ),
        "failed_task_count": sum(
            1 for run in flattened_runs if run.get("status") == "failed"
        ),
        "gate": report_payload.get("gate") if report_payload else None,
        "verification_verdict": (
            report_payload.get("verification_verdict") if report_payload else None
        ),
        "runs": flattened_runs,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="recent-holdout 10개 랜덤 시드 반복 평가를 실행하고 표준 검증 결과 파일을 저장한다."
    )
    parser.add_argument("--config", required=True, help="research_clean 설정 JSON 경로")
    parser.add_argument("--output-dir", required=True, help="시드별 출력 디렉터리")
    parser.add_argument(
        "--journal-path",
        help="실행 저널 경로. 생략 시 output-dir 아래 holdout_execution_journal.json 사용",
    )
    parser.add_argument(
        "--group-id",
        help="시드 실행 그룹 식별자. 생략 시 파라미터 컨텍스트 기본값 사용",
    )
    parser.add_argument(
        "--evaluation-seeds",
        help="쉼표 구분 10개 시드 목록. 기본값은 표준 10개 시드",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="동시 실행 worker 수. 생략 시 파라미터 컨텍스트 기본값 사용",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.max_workers is not None and args.max_workers < 1:
        parser.error("--max-workers 는 1 이상이어야 합니다.")

    result = execute_seed_matrix(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir),
        evaluation_seeds=(
            _parse_evaluation_seeds(args.evaluation_seeds)
            if args.evaluation_seeds
            else None
        ),
        group_id=args.group_id,
        journal_path=Path(args.journal_path) if args.journal_path else None,
        max_workers=args.max_workers,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    verification_gate = load_verification_gate_result(
        Path(result["summary_report_json_path"])
    )
    consistency_check = (result.get("execution_metadata") or {}).get(
        "consistency_check"
    ) or {}
    if (
        result["failed_task_count"] > 0
        or not verification_gate["passed"]
        or not bool(consistency_check.get("passed"))
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
