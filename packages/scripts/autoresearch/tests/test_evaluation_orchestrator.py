from __future__ import annotations

import csv
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.execution_matrix import (  # noqa: E402
    DEFAULT_EVALUATION_SEEDS,
    CommonSeedResultRecord,
    SeedExecutionMetrics,
    SeedExecutionRecord,
    build_execution_journal,
    build_model_config_id,
    upsert_execution_record,
    validate_execution_journal_payload,
    validate_seed_result_repository_payload,
)
from shared.seed_result_recording import (  # noqa: E402
    DetailedSeedResultArtifacts,
    DetailedSeedResultRecord,
    EvaluationOutcomeSnapshot,
    SearchParametersSnapshot,
    SeedContextSnapshot,
    SplitSettingsSnapshot,
    build_detailed_seed_result_repository,
    validate_detailed_seed_result_repository_payload,
)

from autoresearch.evaluation_orchestrator import (  # noqa: E402
    BatchExecutionOptions,
    OrchestratorRequest,
    SchedulingMode,
    SingleSeedEvaluationTask,
    _load_request_payload,
    execute_single_seed_task,
    orchestrate_request,
    resolve_execution_mode,
)
from autoresearch.holdout_dataset import build_dataset_manifest  # noqa: E402
from autoresearch.research_clean import PredictionCoverageError  # noqa: E402
from autoresearch.seed_summary_report import build_seed_summary_report  # noqa: E402


def _build_task(tmp_path: Path) -> SingleSeedEvaluationTask:
    return SingleSeedEvaluationTask(
        task_id="seed-task-01",
        run_id="seed_01_rs11",
        config_path=str(tmp_path / "config.json"),
        output_path=str(tmp_path / "research_clean.json"),
        runtime_params_path=str(tmp_path / "runtime_params.json"),
        model_random_state=11,
    )


def _write_artifacts(output_path: Path) -> tuple[Path, Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"run_id": output_path.parent.name}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest_path = output_path.with_name(f"{output_path.stem}_manifest.json")
    manifest_path.write_text(
        json.dumps({"manifest": output_path.parent.name}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path, manifest_path


def _snapshot_meta(*, race_id: str, race_date: str = "20250101") -> dict:
    entry_finalized_at = "2025-01-01T10:35:00+09:00"
    return {
        "race_id": race_id,
        "format_version": "holdout-snapshot-v1",
        "rule_version": "holdout-entry-finalization-rule-v1",
        "source_filter_basis": "entry_finalized_at",
        "scheduled_start_at": "2025-01-01T11:00:00+09:00",
        "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
        "snapshot_ready_at": entry_finalized_at,
        "entry_finalized_at": entry_finalized_at,
        "selected_timestamp_field": "basic_data.collected_at",
        "selected_timestamp_value": entry_finalized_at,
        "timestamp_source": "snapshot_collected_at",
        "timestamp_confidence": "medium",
        "revision_id": None,
        "late_reissue_after_cutoff": False,
        "cutoff_unbounded": False,
        "replay_status": "strict",
        "include_in_strict_dataset": True,
        "hard_required_sources_present": True,
        "hard_required_source_status": {
            "API214_1": "present",
            "API72_2": "present",
            "API189_1": "present",
            "API9_1": "present",
        },
        "source_lookup": {
            "race_id": race_id,
            "race_date": race_date,
            "entry_snapshot_at": entry_finalized_at,
        },
    }


def _write_valid_dataset_artifacts(tmp_path: Path, *, dataset: str = "holdout") -> None:
    race_id = "race-1"
    race = {
        "race_id": race_id,
        "race_date": "20250101",
        "meet": "서울",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "rcDist": 1200,
            "track": "건조",
            "weather": "맑음",
            "meet": "서울",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마1",
                "computed_features": {"horse_win_rate": 0.1},
            },
            {
                "chulNo": 2,
                "hrName": "테스트마2",
                "computed_features": {"horse_win_rate": 0.2},
            },
            {
                "chulNo": 3,
                "hrName": "테스트마3",
                "computed_features": {"horse_win_rate": 0.3},
            },
        ],
        "snapshot_meta": _snapshot_meta(race_id=race_id),
    }
    (tmp_path / f"{dataset}.json").write_text(
        json.dumps([race], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / f"{dataset}_answer_key.json").write_text(
        json.dumps({race_id: [1, 2, 3]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / f"{dataset}_manifest.json").write_text(
        json.dumps(
            build_dataset_manifest(
                mode=dataset,
                created_at="2026-04-10T12:00:00+09:00",
                races=[race["snapshot_meta"]],
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_detailed_record(
    *,
    task: SingleSeedEvaluationTask,
    seed: int,
    model_config_id: str,
    output_path: Path,
    manifest_path: Path,
    hit_rate: float = 0.71,
) -> DetailedSeedResultRecord:
    return DetailedSeedResultRecord(
        run_id=task.run_id or task.task_id,
        task_id=task.task_id,
        seed=seed,
        seed_index=task.seed_index or 1,
        run_at="2026-04-10T12:01:00+09:00",
        model_config_id=model_config_id,
        split_settings=SplitSettingsSnapshot(dataset="holdout"),
        search_parameters=SearchParametersSnapshot(
            candidate_count=0,
            parameter_source="test",
            model_parameter_source="test",
        ),
        seed_context=SeedContextSnapshot(
            run_id=task.run_id or task.task_id,
            seed_index=task.seed_index or 1,
            model_random_state=seed,
            parameter_source="test",
        ),
        evaluation_result=EvaluationOutcomeSnapshot(
            summary={"overfit_safe_exact_rate": hit_rate},
            core_metrics=SeedExecutionMetrics(
                robust_exact_rate=hit_rate,
                overfit_safe_exact_rate=hit_rate,
                test_exact_3of3_rate=hit_rate,
            ),
            overall_holdout_hit_rate=hit_rate,
            overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
        ),
        artifacts=DetailedSeedResultArtifacts(
            output_path=str(output_path),
            manifest_path=str(manifest_path),
            config_path=task.config_path,
            runtime_params_path=task.runtime_params_path,
        ),
    )


def test_resolve_execution_mode_defaults_to_sequential(tmp_path: Path) -> None:
    request = OrchestratorRequest(task=_build_task(tmp_path))

    assert resolve_execution_mode(request) is SchedulingMode.SEQUENTIAL


def test_resolve_execution_mode_promotes_batch_when_group_context_exists(
    tmp_path: Path,
) -> None:
    request = OrchestratorRequest(
        task=_build_task(tmp_path),
        batch=BatchExecutionOptions(
            enabled=True,
            group_id="holdout-10seed",
            expected_task_count=10,
            max_workers=4,
        ),
    )

    assert resolve_execution_mode(request) is SchedulingMode.BATCH


def test_execute_single_seed_task_runs_evaluation_and_writes_bundle(
    tmp_path: Path,
) -> None:
    task = _build_task(tmp_path)
    task = task.model_copy(update={"runtime_params_path": None})
    _write_valid_dataset_artifacts(tmp_path, dataset="holdout")
    config_path = Path(task.config_path)
    config_path.write_text(
        json.dumps(
            {
                "dataset": "holdout",
                "model": {"kind": "hgb", "params": {"max_depth": 6}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_evaluate(
        config_path_arg: Path,
        *,
        evaluation_context: object,
    ) -> dict[str, object]:
        captured["config_path"] = config_path_arg
        captured["evaluation_context"] = evaluation_context
        config = {
            "dataset": "holdout",
            "model": {"kind": "hgb", "params": {"max_depth": 6}},
        }
        return {
            "summary": {"robust_exact_rate": 0.71},
            "dev": {"exact_3of3_rate": 0.69, "avg_set_match": 0.8, "races": 120},
            "test": {"exact_3of3_rate": 0.71},
            "seeds": {"model_random_state": 11},
            "runtime_params": {"model_random_state": 11},
            "config": config,
        }

    def fake_bundle_writer(**kwargs: object) -> tuple[Path, Path]:
        captured["bundle_kwargs"] = kwargs
        output_path = kwargs["output_path"]
        assert isinstance(output_path, Path)
        dataset_artifacts = kwargs["dataset_artifacts"]
        assert dataset_artifacts.dataset == "holdout"
        assert dataset_artifacts.dataset_path == tmp_path / "holdout.json"
        assert dataset_artifacts.answer_key_path == tmp_path / "holdout_answer_key.json"
        assert dataset_artifacts.manifest_path == tmp_path / "holdout_manifest.json"
        return output_path, output_path.with_name(f"{output_path.stem}_manifest.json")

    result = execute_single_seed_task(
        task,
        dataset_artifact_root=tmp_path,
        evaluate_fn=fake_evaluate,
        bundle_writer=fake_bundle_writer,
        created_at_factory=lambda: datetime(2026, 4, 10, 12, 0, 0),
    )

    assert captured["config_path"] == config_path
    assert captured["evaluation_context"] is not None
    assert result["task_id"] == "seed-task-01"
    assert result["summary"]["robust_exact_rate"] == 0.71
    assert result["dev"]["exact_3of3_rate"] == 0.69
    assert result["manifest_path"].endswith("_manifest.json")
    assert result["config"]["dataset"] == "holdout"
    assert result["model_config_id"] == build_model_config_id(result["config"])


def test_execute_single_seed_task_fails_when_dataset_temporal_audit_breaks(
    tmp_path: Path,
) -> None:
    task = _build_task(tmp_path).model_copy(update={"runtime_params_path": None})
    _write_valid_dataset_artifacts(tmp_path, dataset="holdout")
    manifest_path = tmp_path / "holdout_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["races"][0]["entry_finalized_at"] = "2025-01-01T10:55:00+09:00"
    manifest["races"][0]["snapshot_ready_at"] = "2025-01-01T10:55:00+09:00"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    config_path = Path(task.config_path)
    config_path.write_text(
        json.dumps(
            {
                "dataset": "holdout",
                "model": {"kind": "hgb", "params": {"max_depth": 6}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    def fake_evaluate(
        config_path_arg: Path,
        *,
        evaluation_context: object,
    ) -> dict[str, object]:
        _ = config_path_arg, evaluation_context
        return {
            "summary": {"robust_exact_rate": 0.71},
            "dev": {"exact_3of3_rate": 0.69},
            "test": {"exact_3of3_rate": 0.71},
            "seeds": {"model_random_state": 11},
            "runtime_params": {"model_random_state": 11},
            "config": {
                "dataset": "holdout",
                "model": {"kind": "hgb", "params": {"max_depth": 6}},
            },
        }

    with pytest.raises(ValueError, match="timing audit failed"):
        execute_single_seed_task(
            task,
            dataset_artifact_root=tmp_path,
            evaluate_fn=fake_evaluate,
        )


def test_orchestrate_request_routes_to_batch_runner(tmp_path: Path) -> None:
    request = OrchestratorRequest(
        task=_build_task(tmp_path),
        batch=BatchExecutionOptions(
            enabled=True, expected_task_count=10, max_workers=4
        ),
    )
    calls: list[str] = []

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        return {"task_id": task.task_id}

    def fake_sequential_runner(
        *args: object, **kwargs: object
    ) -> list[dict[str, object]]:
        calls.append("sequential")
        return []

    def fake_batch_runner(*args: object, **kwargs: object) -> list[dict[str, object]]:
        calls.append("batch")
        return [{"task_id": "seed-task-01"}]

    result = orchestrate_request(
        request,
        task_runner=fake_task_runner,
        sequential_runner=fake_sequential_runner,
        batch_runner=fake_batch_runner,
    )

    assert calls == ["batch"]
    assert result["resolved_mode"] == "batch"
    assert result["task_count"] == 1


def test_cli_payload_shape_can_be_bare_task(tmp_path: Path) -> None:
    task = _build_task(tmp_path)
    payload = json.loads(task.model_dump_json())
    request = _load_request_payload(payload)

    assert request.task.task_id == "seed-task-01"


def test_cli_payload_shape_can_be_task_list(tmp_path: Path) -> None:
    base_task = _build_task(tmp_path)
    second_task = base_task.model_copy(
        update={
            "task_id": "seed-task-02",
            "run_id": "seed_02_rs17",
            "seed_index": 2,
            "output_path": str(tmp_path / "seed_02_rs17" / "research_clean.json"),
        }
    )
    request = _load_request_payload(
        [
            json.loads(base_task.model_dump_json()),
            json.loads(second_task.model_dump_json()),
        ]
    )

    assert request.tasks is not None
    assert len(request.tasks) == 2
    assert request.tasks[1].run_id == "seed_02_rs17"


def test_orchestrate_request_runs_multiple_tasks_sequentially_in_batch_order(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    task_one = _build_task(tmp_path).model_copy(
        update={
            "config_path": str(config_path),
            "output_path": str(tmp_path / "seed_01_rs11" / "research_clean.json"),
        }
    )
    task_two = task_one.model_copy(
        update={
            "task_id": "seed-task-02",
            "run_id": "seed_02_rs17",
            "seed_index": 2,
            "output_path": str(tmp_path / "seed_02_rs17" / "research_clean.json"),
        }
    )
    task_three = task_one.model_copy(
        update={
            "task_id": "seed-task-03",
            "run_id": "seed_03_rs23",
            "seed_index": 3,
            "output_path": str(tmp_path / "seed_03_rs23" / "research_clean.json"),
        }
    )
    request = OrchestratorRequest(
        tasks=(task_one, task_two, task_three),
        batch=BatchExecutionOptions(enabled=True, expected_task_count=3, max_workers=1),
    )
    call_order: list[str] = []

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        call_order.append(task.run_id or task.task_id)
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "summary": {"robust_exact_rate": 0.72},
            "dev": {"exact_3of3_rate": 0.71},
            "test": {"exact_3of3_rate": 0.72},
            "seeds": {
                "model_random_state": int((task.run_id or "rs0").split("rs", 1)[1])
            },
            "runtime_params": {
                "model_random_state": int((task.run_id or "rs0").split("rs", 1)[1])
            },
            "config": {"dataset": "holdout"},
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    assert result["resolved_mode"] == "batch"
    assert result["task_count"] == 3
    assert call_order == ["seed_01_rs11", "seed_02_rs17", "seed_03_rs23"]
    assert [item["run_id"] for item in result["results"]] == call_order


def test_orchestrate_request_runs_multiple_tasks_in_parallel_when_enabled(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    tasks = tuple(
        _build_task(tmp_path).model_copy(
            update={
                "task_id": f"seed-task-{index:02d}",
                "run_id": f"seed_{index:02d}_rs{seed}",
                "seed_index": index,
                "config_path": str(config_path),
                "output_path": str(
                    tmp_path / f"seed_{index:02d}_rs{seed}" / "research_clean.json"
                ),
            }
        )
        for index, seed in enumerate((11, 17, 23), start=1)
    )
    request = OrchestratorRequest(
        tasks=tasks,
        batch=BatchExecutionOptions(enabled=True, expected_task_count=3, max_workers=3),
    )
    active_count = 0
    peak_active_count = 0
    lock = threading.Lock()

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        nonlocal active_count, peak_active_count
        with lock:
            active_count += 1
            peak_active_count = max(peak_active_count, active_count)
        time.sleep(0.05)
        with lock:
            active_count -= 1
        seed = int((task.run_id or "rs0").split("rs", 1)[1])
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "summary": {"robust_exact_rate": 0.72},
            "dev": {"exact_3of3_rate": 0.71},
            "test": {"exact_3of3_rate": 0.72},
            "seeds": {"model_random_state": seed},
            "runtime_params": {"model_random_state": seed},
            "config": {"dataset": "holdout"},
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    assert result["failed_task_count"] == 0
    assert result["task_count"] == 3
    assert peak_active_count >= 2
    assert [item["run_id"] for item in result["results"]] == [
        "seed_01_rs11",
        "seed_02_rs17",
        "seed_03_rs23",
    ]


def test_orchestrate_request_stops_submitting_batch_tasks_after_coverage_failure(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    tasks = tuple(
        _build_task(tmp_path).model_copy(
            update={
                "task_id": f"seed-task-{index:02d}",
                "run_id": f"seed_{index:02d}_rs{seed}",
                "seed_index": index,
                "config_path": str(config_path),
                "output_path": str(
                    tmp_path / f"seed_{index:02d}_rs{seed}" / "research_clean.json"
                ),
            }
        )
        for index, seed in enumerate((11, 17, 23, 29, 31), start=1)
    )
    request = OrchestratorRequest(
        tasks=tasks,
        batch=BatchExecutionOptions(enabled=True, expected_task_count=5, max_workers=2),
    )
    started_run_ids: list[str] = []

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        started_run_ids.append(task.run_id or task.task_id)
        if task.seed_index == 1:
            time.sleep(0.05)
        if task.seed_index == 2:
            raise PredictionCoverageError(
                "prediction coverage validation failed",
                missing_race_ids=["race-002", "race-005"],
                incomplete_top3_race_ids=["race-005"],
                expected_race_count=5,
                predicted_race_count=3,
                train_end="20250331",
                eval_start="20250401",
                eval_end="20250402",
            )
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "summary": {"robust_exact_rate": 0.72},
            "dev": {"exact_3of3_rate": 0.71},
            "test": {"exact_3of3_rate": 0.72},
            "seeds": {
                "model_random_state": int((task.run_id or "rs0").split("rs", 1)[1])
            },
            "runtime_params": {
                "model_random_state": int((task.run_id or "rs0").split("rs", 1)[1])
            },
            "config": {"dataset": "holdout"},
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)
    journal_payload = json.loads(
        Path(str(result["execution_journal_path"])).read_text(encoding="utf-8")
    )
    report_payload = json.loads(
        (tmp_path / "holdout_seed_summary_report.json").read_text(encoding="utf-8")
    )
    report_markdown = (tmp_path / "holdout_seed_summary_report.md").read_text(
        encoding="utf-8"
    )
    failure_row = next(
        row
        for row in report_payload["completion_check"]["rows"]
        if row["run_id"] == "seed_02_rs17"
    )
    failed_run = report_payload["failed_runs"][0]
    journal_failure = next(
        record["failure"]
        for record in journal_payload["records"]
        if record["run_id"] == "seed_02_rs17"
    )

    assert sorted(started_run_ids) == ["seed_01_rs11", "seed_02_rs17"]
    assert result["failed_task_count"] == 1
    assert [item["run_id"] for item in result["results"]] == [
        "seed_01_rs11",
        "seed_02_rs17",
    ]
    assert result["results"][1]["halt_batch"] is True
    assert (
        result["results"][1]["failure_reason_code"]
        == "prediction_coverage_validation_failed"
    )
    assert result["results"][1]["failure_reason"] is not None
    assert result["results"][1]["failure_missing_count"] == 2
    assert result["results"][1]["failure_missing_items"] == ["race-002", "race-005"]
    assert (
        result["results"][1]["error"]["reason_code"]
        == "prediction_coverage_validation_failed"
    )
    assert result["results"][1]["error"]["missing_count"] == 2
    assert result["results"][1]["error"]["missing_items"] == ["race-002", "race-005"]
    assert result["results"][1]["error"]["incomplete_top3_race_ids"] == ["race-005"]
    assert result["postprocess_report"]["verification_verdict"]["status"] == "FAIL"
    assert result["postprocess_report"]["completion_check"][
        "failure_reason_counts"
    ] == {"prediction_coverage_validation_failed": 1}
    assert (
        result["postprocess_report"]["completion_check"]["failure_missing_total"] == 2
    )
    assert (
        failure_row["failure"]["reason_code"] == "prediction_coverage_validation_failed"
    )
    assert failure_row["failure"]["missing_count"] == 2
    assert failure_row["failure"]["missing_items"] == ["race-002", "race-005"]
    assert failure_row["failure"]["incomplete_top3_race_ids"] == ["race-005"]
    assert journal_failure["reason_code"] == "prediction_coverage_validation_failed"
    assert journal_failure["missing_count"] == 2
    assert journal_failure["missing_items"] == ["race-002", "race-005"]
    assert journal_failure["incomplete_top3_race_ids"] == ["race-005"]
    assert journal_failure["traceback_excerpt"] is not None
    assert "PredictionCoverageError" in journal_failure["traceback_excerpt"]
    assert (
        "prediction coverage validation failed" in journal_failure["traceback_excerpt"]
    )
    assert failed_run["reason_code"] == "prediction_coverage_validation_failed"
    assert failed_run["missing_count"] == 2
    assert failed_run["missing_items"] == ["race-002", "race-005"]
    assert failed_run["incomplete_top3_race_ids"] == ["race-005"]
    assert failed_run["evaluation_window"] == {
        "train_end": "20250331",
        "eval_start": "20250401",
        "eval_end": "20250402",
    }
    assert "## Failed Runs" in report_markdown
    assert "prediction_coverage_validation_failed" in report_markdown
    assert "race-002, race-005" in report_markdown
    assert '"eval_end": "20250402"' in report_markdown


def test_orchestrate_request_writes_seed_execution_journal(tmp_path: Path) -> None:
    journal_path = tmp_path / "seed_runs.json"
    repository_path = tmp_path / "holdout_seed_result_repository.json"
    detailed_repository_path = tmp_path / "holdout_seed_result_records.json"
    report_json_path = tmp_path / "holdout_seed_summary_report.json"
    report_md_path = tmp_path / "holdout_seed_summary_report.md"
    report_csv_path = tmp_path / "holdout_seed_hit_rate_rows.csv"
    config_path = tmp_path / "config.json"
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    request = OrchestratorRequest(
        task=_build_task(tmp_path).model_copy(update={"config_path": str(config_path)}),
        batch=BatchExecutionOptions(
            execution_journal_path=str(journal_path),
            group_id="holdout-10seed",
        ),
    )

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(tmp_path / "research_clean.json"),
            "manifest_path": str(tmp_path / "research_clean_manifest.json"),
            "dataset_selection": {
                "source_artifact_path": str(tmp_path / "holdout_manifest.json"),
                "source_artifact_sha256": "a" * 64,
                "expected_race_count": 2,
                "final_race_ids": ["race-2", "race-1"],
            },
            "summary": {
                "robust_exact_rate": 0.74,
                "overfit_safe_exact_rate": 0.71,
                "blended_exact_rate": 0.76,
                "rolling_min_exact_rate": 0.71,
                "rolling_mean_exact_rate": 0.75,
                "dev_test_gap": 0.03,
            },
            "dev": {"exact_3of3_rate": 0.74, "avg_set_match": 0.81, "races": 120},
            "test": {"exact_3of3_rate": 0.76, "avg_set_match": 0.83, "races": 130},
            "seeds": {"model_random_state": 11},
            "runtime_params": {"model_random_state": 11},
            "config": config_payload,
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    payload = json.loads(journal_path.read_text(encoding="utf-8"))
    repository_payload = json.loads(repository_path.read_text(encoding="utf-8"))
    detailed_repository_payload = json.loads(
        detailed_repository_path.read_text(encoding="utf-8")
    )
    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    report_csv_rows = list(
        csv.DictReader(report_csv_path.read_text(encoding="utf-8").splitlines())
    )
    ok, errors = validate_execution_journal_payload(payload)
    repository_ok, repository_errors = validate_seed_result_repository_payload(
        repository_payload
    )
    detailed_repository_ok, detailed_repository_errors = (
        validate_detailed_seed_result_repository_payload(detailed_repository_payload)
    )

    assert ok is True, errors
    assert repository_ok is True, repository_errors
    assert detailed_repository_ok is True, detailed_repository_errors
    assert result["failed_task_count"] == 0
    assert result["execution_summary"]["completed_run_count"] == 1
    assert result["execution_summary"]["all_expected_runs_completed"] is False
    assert result["execution_summary"]["all_runs_completed_successfully"] is False
    assert result["seed_result_repository_path"] == str(repository_path)
    assert result["detailed_seed_result_repository_path"] == str(
        detailed_repository_path
    )
    assert result["results"][0]["seed_result_repository_path"] == str(repository_path)
    assert result["results"][0]["detailed_seed_result_repository_path"] == str(
        detailed_repository_path
    )
    assert (
        result["results"][0]["seed_result_repository_summary"]["recorded_run_count"]
        == 1
    )
    assert (
        result["results"][0]["detailed_seed_result_repository_summary"][
            "recorded_run_count"
        ]
        == 1
    )
    assert result["postprocess_report"]["json_path"] == str(report_json_path)
    assert result["postprocess_report"]["markdown_path"] == str(report_md_path)
    assert result["postprocess_report"]["csv_path"] == str(report_csv_path)
    assert result["postprocess_report"]["verification_verdict"]["status"] == "FAIL"
    assert result["postprocess_report"]["completion_check"]["done_run_count"] == 1
    assert payload["records"][0]["status"] == "completed"
    assert payload["records"][0]["metrics"]["overfit_safe_exact_rate"] == 0.71
    assert payload["records"][0]["common_result"] == {
        "format_version": "holdout-seed-result-record-v1",
        "run_id": "seed_01_rs11",
        "seed": 11,
        "run_at": payload["records"][0]["finished_at"],
        "model_config_id": build_model_config_id(config_payload),
        "overall_holdout_hit_rate": 0.71,
        "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
    }
    assert payload["records"][0]["artifacts"]["manifest_path"].endswith(
        "research_clean_manifest.json"
    )
    assert repository_payload["records"] == [payload["records"][0]["common_result"]]
    assert detailed_repository_payload["records"][0]["run_id"] == "seed_01_rs11"
    assert (
        detailed_repository_payload["records"][0]["split_settings"]["dataset"]
        == "holdout"
    )
    assert (
        detailed_repository_payload["records"][0]["split_settings"][
            "dataset_selection"
        ]["expected_race_count"]
        == 2
    )
    assert detailed_repository_payload["records"][0]["split_settings"][
        "dataset_selection"
    ]["final_race_ids"] == ["race-2", "race-1"]
    assert (
        detailed_repository_payload["records"][0]["search_parameters"][
            "resolved_model_parameters"
        ]
        == {}
    )
    assert (
        detailed_repository_payload["records"][0]["seed_context"]["model_random_state"]
        == 11
    )
    assert (
        detailed_repository_payload["records"][0]["evaluation_result"][
            "overall_holdout_hit_rate"
        ]
        == 0.71
    )
    assert repository_payload["summary"]["missing_run_ids"][0] == "seed_02_rs17"
    assert (
        detailed_repository_payload["summary"]["missing_run_ids"][0] == "seed_02_rs17"
    )
    assert report_payload["format_version"] == "holdout-seed-summary-report-v2"
    assert report_payload["gate"]["metric"] == "lowest_overall_holdout_hit_rate"
    assert (
        report_payload["gate"]["metric_source"]
        == "seed_result_repository.summary.lowest_overall_holdout_hit_rate"
    )
    assert report_payload["completion_check"]["done_run_count"] == 1
    assert report_payload["verification_verdict"]["status"] == "FAIL"
    assert report_payload["verification_verdict"]["blockers"] == [
        "expected_runs_incomplete",
        "non_terminal_runs_present",
    ]
    assert report_payload["seed_result_repository_summary"]["recorded_run_count"] == 1
    assert len(report_payload["completion_check"]["rows"]) == 10
    assert report_payload["completion_check"]["rows"][0]["run_id"] == "seed_01_rs11"
    assert report_payload["completion_check"]["rows"][0]["completion_state"] == "done"
    assert report_payload["completion_check"]["rows"][0]["format_check_passed"] is True
    assert report_payload["completion_check"]["rows"][1]["run_id"] == "seed_02_rs17"
    assert (
        "execution_record"
        in report_payload["completion_check"]["rows"][1]["missing_items"]
    )
    assert len(report_payload["seed_hit_rate_rows"]) == 10
    assert report_payload["seed_hit_rate_rows"][0]["overall_holdout_hit_rate"] == 0.71
    assert report_payload["seed_hit_rate_rows"][1]["overall_holdout_hit_rate"] is None
    assert report_payload["aggregates"]["overall_holdout_hit_rate"]["count"] == 1
    assert report_payload["aggregates"]["overall_holdout_hit_rate"]["min"] == 0.71
    assert (
        report_payload["normalized_metrics"]["schema_version"]
        == "seed-performance-aggregation-v1"
    )
    assert (
        report_payload["normalized_metrics"]["metrics"]["overall_holdout_hit_rate"][
            "summary"
        ]["ok_count"]
        == 1
    )
    assert (
        report_payload["normalized_metrics"]["metrics"]["overall_holdout_hit_rate"][
            "summary"
        ]["normalized_value_aggregate"]["sample_count"]
        == 1
    )
    assert (
        report_payload["normalized_metrics"]["metrics"]["overall_holdout_hit_rate"][
            "summary"
        ]["normalized_value_aggregate"]["stddev"]
        == 0.0
    )
    assert len(report_csv_rows) == 10
    assert report_csv_rows[0]["run_id"] == "seed_01_rs11"
    assert report_csv_rows[0]["overall_holdout_hit_rate"] == "0.71"
    assert report_csv_rows[1]["run_id"] == "seed_02_rs17"
    assert report_csv_rows[1]["status"] == "missing"
    assert report_csv_rows[1]["overall_holdout_hit_rate"] == ""
    assert report_md_path.exists() is True


def test_orchestrate_request_records_failed_seed_execution(tmp_path: Path) -> None:
    journal_path = tmp_path / "seed_runs.json"
    repository_path = tmp_path / "holdout_seed_result_repository.json"
    detailed_repository_path = tmp_path / "holdout_seed_result_records.json"
    report_json_path = tmp_path / "holdout_seed_summary_report.json"
    request = OrchestratorRequest(
        task=_build_task(tmp_path),
        batch=BatchExecutionOptions(execution_journal_path=str(journal_path)),
    )

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        raise RuntimeError("evaluation crashed")

    result = orchestrate_request(request, task_runner=fake_task_runner)

    payload = json.loads(journal_path.read_text(encoding="utf-8"))
    repository_payload = json.loads(repository_path.read_text(encoding="utf-8"))
    detailed_repository_payload = json.loads(
        detailed_repository_path.read_text(encoding="utf-8")
    )
    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    ok, errors = validate_execution_journal_payload(payload)
    repository_ok, repository_errors = validate_seed_result_repository_payload(
        repository_payload
    )
    detailed_repository_ok, detailed_repository_errors = (
        validate_detailed_seed_result_repository_payload(detailed_repository_payload)
    )

    assert ok is True, errors
    assert repository_ok is True, repository_errors
    assert detailed_repository_ok is True, detailed_repository_errors
    assert result["failed_task_count"] == 1
    assert result["results"][0]["status"] == "failed"
    assert payload["records"][0]["status"] == "failed"
    assert payload["records"][0]["failure"]["error_type"] == "RuntimeError"
    assert payload["summary"]["failed_run_count"] == 1
    assert repository_payload["records"] == []
    assert repository_payload["summary"]["recorded_run_count"] == 0
    assert result["detailed_seed_result_repository_path"] == str(
        detailed_repository_path
    )
    assert detailed_repository_payload["records"] == []
    assert detailed_repository_payload["summary"]["recorded_run_count"] == 0
    assert result["postprocess_report"]["json_path"] == str(report_json_path)
    assert report_payload["completion_check"]["rows"][0]["status"] == "failed"
    assert "metrics" in report_payload["completion_check"]["rows"][0]["missing_items"]
    assert (
        "common_result"
        in report_payload["completion_check"]["rows"][0]["missing_items"]
    )


def test_orchestrate_request_writes_summary_report_after_tenth_seed_finishes(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "seed_runs.json"
    repository_path = tmp_path / "holdout_seed_result_repository.json"
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    model_config_id = build_model_config_id(config_payload)
    journal = build_execution_journal()
    for seed_index, seed in enumerate(DEFAULT_EVALUATION_SEEDS[:-1], start=1):
        journal = upsert_execution_record(
            journal,
            SeedExecutionRecord(
                run_id=f"seed_{seed_index:02d}_rs{seed}",
                task_id=f"task-{seed_index:02d}",
                seed_index=seed_index,
                model_random_state=seed,
                status="completed",
                started_at="2026-04-10T12:00:00+09:00",
                finished_at="2026-04-10T12:01:00+09:00",
                metrics=SeedExecutionMetrics(
                    overfit_safe_exact_rate=0.78,
                    robust_exact_rate=0.79,
                    test_exact_3of3_rate=0.8,
                ),
                common_result=CommonSeedResultRecord(
                    run_id=f"seed_{seed_index:02d}_rs{seed}",
                    seed=seed,
                    run_at="2026-04-10T12:01:00+09:00",
                    model_config_id=model_config_id,
                    overall_holdout_hit_rate=0.78,
                    overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
                ),
                artifacts={
                    "output_path": str(tmp_path / f"seed_{seed_index:02d}.json"),
                    "manifest_path": str(
                        tmp_path / f"seed_{seed_index:02d}_manifest.json"
                    ),
                },
            ),
        )
    journal_path.write_text(
        json.dumps(journal.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    task = SingleSeedEvaluationTask(
        task_id="seed-task-10",
        run_id="seed_10_rs61",
        seed_index=10,
        config_path=str(tmp_path / "config.json"),
        output_path=str(tmp_path / "research_clean.json"),
        runtime_params_path=str(tmp_path / "runtime_params.json"),
        model_random_state=61,
    )
    Path(task.config_path).write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    request = OrchestratorRequest(
        task=task,
        batch=BatchExecutionOptions(
            execution_journal_path=str(journal_path),
            group_id="holdout-10seed",
        ),
    )

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(tmp_path / "research_clean.json"),
            "manifest_path": str(tmp_path / "research_clean_manifest.json"),
            "summary": {
                "robust_exact_rate": 0.72,
                "overfit_safe_exact_rate": 0.71,
                "blended_exact_rate": 0.73,
                "rolling_min_exact_rate": 0.71,
                "rolling_mean_exact_rate": 0.74,
                "dev_test_gap": 0.02,
            },
            "dev": {"exact_3of3_rate": 0.72, "avg_set_match": 0.81, "races": 120},
            "test": {"exact_3of3_rate": 0.75, "avg_set_match": 0.82, "races": 130},
            "seeds": {"model_random_state": 61},
            "runtime_params": {"model_random_state": 61},
            "config": config_payload,
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    report_json_path = tmp_path / "holdout_seed_summary_report.json"
    report_md_path = tmp_path / "holdout_seed_summary_report.md"
    report_csv_path = tmp_path / "holdout_seed_hit_rate_rows.csv"
    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    repository_payload = json.loads(repository_path.read_text(encoding="utf-8"))
    report_csv_rows = list(
        csv.DictReader(report_csv_path.read_text(encoding="utf-8").splitlines())
    )
    markdown = report_md_path.read_text(encoding="utf-8")

    assert result["failed_task_count"] == 0
    assert result["execution_summary"]["completed_run_count"] == 10
    assert result["execution_summary"]["all_runs_terminal"] is True
    assert result["execution_summary"]["all_expected_runs_completed"] is True
    assert result["seed_result_repository_path"] == str(repository_path)
    assert result["postprocess_report"]["json_path"] == str(report_json_path)
    assert result["postprocess_report"]["markdown_path"] == str(report_md_path)
    assert result["postprocess_report"]["csv_path"] == str(report_csv_path)
    assert result["postprocess_report"]["verification_verdict"]["status"] == "PASS"
    assert report_payload["gate"]["passed"] is True
    assert report_payload["gate"]["metric"] == "lowest_overall_holdout_hit_rate"
    assert (
        report_payload["gate"]["metric_source"]
        == "seed_result_repository.summary.lowest_overall_holdout_hit_rate"
    )
    assert report_payload["gate"]["actual"] == 0.71
    assert report_payload["gate"]["completed_run_count"] == 10
    assert report_payload["gate"]["expected_run_count"] == 10
    assert report_payload["gate"]["all_expected_runs_completed"] is True
    assert report_payload["verification_verdict"]["status"] == "PASS"
    assert report_payload["verification_verdict"]["lowest_hit_rate"] == 0.71
    assert report_payload["verification_verdict"]["margin_vs_threshold"] == 0.01
    assert report_payload["verification_verdict"]["blockers"] == []
    assert report_payload["aggregates"]["overall_holdout_hit_rate"]["min"] == 0.71
    assert report_payload["aggregates"]["overall_holdout_hit_rate"]["count"] == 10
    assert report_payload["aggregates"]["overfit_safe_exact_rate"]["min"] == 0.71
    assert report_payload["aggregates"]["overfit_safe_exact_rate"]["count"] == 10
    assert report_payload["worst_completed_run"]["run_id"] == "seed_10_rs61"
    assert report_payload["worst_completed_run"]["overall_holdout_hit_rate"] == 0.71
    assert report_payload["execution_summary"]["missing_run_ids"] == []
    assert report_payload["execution_summary"]["missing_completed_run_ids"] == []
    assert report_payload["completion_check"]["done_run_count"] == 10
    assert report_payload["completion_check"]["format_check_passed_run_count"] == 10
    assert len(report_payload["seed_hit_rate_rows"]) == 10
    assert report_payload["seed_hit_rate_rows"][-1]["run_id"] == "seed_10_rs61"
    assert report_payload["seed_hit_rate_rows"][-1]["overall_holdout_hit_rate"] == 0.71
    assert len(report_csv_rows) == 10
    assert report_csv_rows[-1]["run_id"] == "seed_10_rs61"
    assert report_csv_rows[-1]["status"] == "completed"
    assert report_csv_rows[-1]["overall_holdout_hit_rate"] == "0.71"
    assert len(repository_payload["records"]) == 10
    assert repository_payload["summary"]["all_expected_runs_recorded"] is True
    assert repository_payload["summary"]["lowest_overall_holdout_hit_rate"] == 0.71
    assert "## Final Verification Verdict" in markdown
    assert "final_status: `PASS`" in markdown
    assert "lowest_hit_rate: `0.71` / threshold `0.70` / margin `0.01`" in markdown
    assert "seed_10_rs61" in markdown
    assert "PASS" in markdown
    assert "## Seed Completion Check" in markdown


def test_orchestrate_request_builds_common_result_from_robust_fallback(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "seed_runs.json"
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    request = OrchestratorRequest(
        task=_build_task(tmp_path).model_copy(update={"config_path": str(config_path)}),
        batch=BatchExecutionOptions(execution_journal_path=str(journal_path)),
    )

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(tmp_path / "research_clean.json"),
            "manifest_path": str(tmp_path / "research_clean_manifest.json"),
            "model_config_id": build_model_config_id(config_payload),
            "summary": {
                "robust_exact_rate": 0.73,
                "blended_exact_rate": 0.74,
                "rolling_min_exact_rate": 0.73,
                "rolling_mean_exact_rate": 0.74,
                "dev_test_gap": 0.01,
            },
            "dev": {"exact_3of3_rate": 0.74, "avg_set_match": 0.82, "races": 120},
            "test": {"exact_3of3_rate": 0.76, "avg_set_match": 0.83, "races": 130},
            "seeds": {"model_random_state": 11},
            "runtime_params": {"model_random_state": 11},
            "config": config_payload,
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    payload = json.loads(journal_path.read_text(encoding="utf-8"))

    assert result["results"][0]["common_result"]["seed"] == 11
    assert result["results"][0]["common_result"][
        "model_config_id"
    ] == build_model_config_id(config_payload)
    assert (
        result["results"][0]["common_result"]["overall_holdout_hit_rate_source"]
        == "summary.robust_exact_rate"
    )
    assert result["results"][0]["common_result"]["overall_holdout_hit_rate"] == 0.73
    assert (
        payload["records"][0]["common_result"]["overall_holdout_hit_rate_source"]
        == "summary.robust_exact_rate"
    )


def test_orchestrate_request_normalizes_percent_metrics_before_persisting(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "seed_runs.json"
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    request = OrchestratorRequest(
        task=_build_task(tmp_path).model_copy(update={"config_path": str(config_path)}),
        batch=BatchExecutionOptions(execution_journal_path=str(journal_path)),
    )

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(tmp_path / "research_clean.json"),
            "manifest_path": str(tmp_path / "research_clean_manifest.json"),
            "model_config_id": build_model_config_id(config_payload),
            "summary": {
                "overfit_safe_exact_rate": "71%",
                "robust_exact_rate": 74,
                "blended_exact_rate": "75%",
                "rolling_min_exact_rate": 70,
                "rolling_mean_exact_rate": "73%",
                "dev_test_gap": "2%",
            },
            "dev": {"exact_3of3_rate": "72%", "avg_set_match": 81, "races": 120},
            "test": {"exact_3of3_rate": "75%", "avg_set_match": "82%", "races": 130},
            "seeds": {"model_random_state": 11},
            "runtime_params": {"model_random_state": 11},
            "config": config_payload,
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    payload = json.loads(journal_path.read_text(encoding="utf-8"))
    detailed_payload = json.loads(
        (tmp_path / "holdout_seed_result_records.json").read_text(encoding="utf-8")
    )

    assert result["results"][0]["summary"]["overfit_safe_exact_rate"] == "71%"
    assert result["results"][0]["common_result"]["overall_holdout_hit_rate"] == 0.71
    assert payload["records"][0]["metrics"]["robust_exact_rate"] == 0.74
    assert payload["records"][0]["metrics"]["dev_test_gap"] == 0.02
    assert (
        detailed_payload["records"][0]["evaluation_result"]["metric_normalization"][
            "metrics"
        ]["test_avg_set_match"]["normalized_value"]
        == 0.82
    )


def test_build_seed_summary_report_uses_lowest_seed_hit_rate_for_gate(
    tmp_path: Path,
) -> None:
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    model_config_id = build_model_config_id(config_payload)
    journal = build_execution_journal()

    for seed_index, seed in enumerate(DEFAULT_EVALUATION_SEEDS, start=1):
        overall_hit_rate = 0.74
        overfit_safe_exact_rate = 0.78
        if seed_index == 10:
            overall_hit_rate = 0.69
            overfit_safe_exact_rate = 0.71
        journal = upsert_execution_record(
            journal,
            SeedExecutionRecord(
                run_id=f"seed_{seed_index:02d}_rs{seed}",
                task_id=f"task-{seed_index:02d}",
                seed_index=seed_index,
                model_random_state=seed,
                status="completed",
                started_at="2026-04-10T12:00:00+09:00",
                finished_at="2026-04-10T12:01:00+09:00",
                metrics=SeedExecutionMetrics(
                    overfit_safe_exact_rate=overfit_safe_exact_rate,
                    robust_exact_rate=0.79,
                    test_exact_3of3_rate=0.8,
                ),
                common_result=CommonSeedResultRecord(
                    run_id=f"seed_{seed_index:02d}_rs{seed}",
                    seed=seed,
                    run_at="2026-04-10T12:01:00+09:00",
                    model_config_id=model_config_id,
                    overall_holdout_hit_rate=overall_hit_rate,
                    overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
                ),
                artifacts={
                    "output_path": str(tmp_path / f"seed_{seed_index:02d}.json"),
                    "manifest_path": str(
                        tmp_path / f"seed_{seed_index:02d}_manifest.json"
                    ),
                },
            ),
        )

    report = build_seed_summary_report(
        journal,
        journal_path=tmp_path / "seed_runs.json",
    )

    assert report["gate"]["metric"] == "lowest_overall_holdout_hit_rate"
    assert (
        report["gate"]["metric_source"]
        == "seed_result_repository.summary.lowest_overall_holdout_hit_rate"
    )
    assert report["gate"]["actual"] == 0.69
    assert report["gate"]["passed"] is False
    assert report["verification_verdict"]["status"] == "FAIL"
    assert report["verification_verdict"]["lowest_hit_rate"] == 0.69
    assert report["verification_verdict"]["margin_vs_threshold"] == -0.01
    assert report["verification_verdict"]["blockers"] == ["below_threshold"]
    assert report["aggregates"]["overall_holdout_hit_rate"]["min"] == 0.69
    assert report["aggregates"]["overfit_safe_exact_rate"]["min"] == 0.71
    assert report["worst_completed_run"]["run_id"] == "seed_10_rs61"
    assert report["worst_completed_run"]["overall_holdout_hit_rate"] == 0.69


def test_orchestrate_request_reuses_completed_runs_and_reruns_failed_runs(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "seed_runs.json"
    detailed_repository_path = tmp_path / "holdout_seed_result_records.json"
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "runtime_params.json").write_text(
        json.dumps({"model_random_state": 11}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    task_one = _build_task(tmp_path).model_copy(
        update={
            "config_path": str(config_path),
            "output_path": str(tmp_path / "seed_01_rs11" / "research_clean.json"),
        }
    )
    task_two = task_one.model_copy(
        update={
            "task_id": "seed-task-02",
            "run_id": "seed_02_rs17",
            "seed_index": 2,
            "output_path": str(tmp_path / "seed_02_rs17" / "research_clean.json"),
        }
    )
    output_path, manifest_path = _write_artifacts(Path(task_one.output_path))
    model_config_id = build_model_config_id(config_payload)
    journal = build_execution_journal(
        records=(
            SeedExecutionRecord(
                run_id="seed_01_rs11",
                task_id=task_one.task_id,
                seed_index=1,
                model_random_state=11,
                status="completed",
                started_at="2026-04-10T12:00:00+09:00",
                finished_at="2026-04-10T12:01:00+09:00",
                artifacts={
                    "output_path": str(output_path),
                    "manifest_path": str(manifest_path),
                },
                metrics=SeedExecutionMetrics(
                    robust_exact_rate=0.71,
                    overfit_safe_exact_rate=0.71,
                    test_exact_3of3_rate=0.71,
                ),
                common_result=CommonSeedResultRecord(
                    run_id="seed_01_rs11",
                    seed=11,
                    run_at="2026-04-10T12:01:00+09:00",
                    model_config_id=model_config_id,
                    overall_holdout_hit_rate=0.71,
                    overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
                ),
            ),
            SeedExecutionRecord(
                run_id="seed_02_rs17",
                task_id=task_two.task_id,
                seed_index=2,
                model_random_state=17,
                status="failed",
                started_at="2026-04-10T12:02:00+09:00",
                finished_at="2026-04-10T12:03:00+09:00",
                failure={
                    "error_type": "RuntimeError",
                    "error_message": "old failure",
                },
            ),
        )
    )
    journal_path.write_text(
        json.dumps(journal.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    detailed_repository = build_detailed_seed_result_repository(
        group_id="holdout-10seed",
        evaluation_seeds=DEFAULT_EVALUATION_SEEDS,
        records=(
            _build_detailed_record(
                task=task_one,
                seed=11,
                model_config_id=model_config_id,
                output_path=output_path,
                manifest_path=manifest_path,
            ),
        ),
    )
    detailed_repository_path.write_text(
        json.dumps(
            detailed_repository.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    request = OrchestratorRequest(
        tasks=(task_one, task_two),
        batch=BatchExecutionOptions(
            enabled=True,
            execution_journal_path=str(journal_path),
            group_id="holdout-10seed",
            max_workers=2,
        ),
    )
    call_order: list[str] = []

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        call_order.append(task.run_id or task.task_id)
        rerun_output_path, rerun_manifest_path = _write_artifacts(
            Path(task.output_path)
        )
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(rerun_output_path),
            "manifest_path": str(rerun_manifest_path),
            "summary": {"robust_exact_rate": 0.73, "overfit_safe_exact_rate": 0.73},
            "dev": {"exact_3of3_rate": 0.73, "avg_set_match": 0.8, "races": 100},
            "test": {"exact_3of3_rate": 0.73, "avg_set_match": 0.81, "races": 110},
            "seeds": {"model_random_state": 17},
            "runtime_params": {"model_random_state": 17},
            "config": config_payload,
        }

    result = orchestrate_request(request, task_runner=fake_task_runner)

    assert call_order == ["seed_02_rs17"]
    assert result["executed_task_count"] == 1
    assert result["reused_completed_task_count"] == 1
    assert result["failed_task_count"] == 0
    assert result["recovery_summary"]["reason_counts"] == {
        "already_completed_with_storage": 1,
        "previous_failed": 1,
    }
    assert [item["run_id"] for item in result["results"]] == [
        "seed_01_rs11",
        "seed_02_rs17",
    ]
    assert result["results"][0]["execution_action"] == "reused_completed"
    assert result["results"][0]["resumed_from_existing"] is True
    assert result["results"][1]["execution_action"] == "executed"
    assert result["results"][1]["resumed_from_existing"] is False
    assert result["execution_summary"]["completed_run_count"] == 2
    assert result["execution_summary"]["failed_run_count"] == 0


def test_orchestrate_request_recovers_aggregate_outputs_without_reexecution(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "seed_runs.json"
    repository_path = tmp_path / "holdout_seed_result_repository.json"
    detailed_repository_path = tmp_path / "holdout_seed_result_records.json"
    report_path = tmp_path / "holdout_seed_summary_report.json"
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "runtime_params.json").write_text(
        json.dumps({"model_random_state": 11}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    task = _build_task(tmp_path).model_copy(update={"config_path": str(config_path)})
    output_path, manifest_path = _write_artifacts(Path(task.output_path))
    model_config_id = build_model_config_id(config_payload)
    journal = build_execution_journal(
        records=(
            SeedExecutionRecord(
                run_id="seed_01_rs11",
                task_id=task.task_id,
                seed_index=1,
                model_random_state=11,
                status="completed",
                started_at="2026-04-10T12:00:00+09:00",
                finished_at="2026-04-10T12:01:00+09:00",
                artifacts={
                    "output_path": str(output_path),
                    "manifest_path": str(manifest_path),
                },
                metrics=SeedExecutionMetrics(
                    robust_exact_rate=0.71,
                    overfit_safe_exact_rate=0.71,
                    test_exact_3of3_rate=0.71,
                ),
                common_result=CommonSeedResultRecord(
                    run_id="seed_01_rs11",
                    seed=11,
                    run_at="2026-04-10T12:01:00+09:00",
                    model_config_id=model_config_id,
                    overall_holdout_hit_rate=0.71,
                    overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
                ),
            ),
        )
    )
    journal_path.write_text(
        json.dumps(journal.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    detailed_repository = build_detailed_seed_result_repository(
        group_id="holdout-10seed",
        evaluation_seeds=DEFAULT_EVALUATION_SEEDS,
        records=(
            _build_detailed_record(
                task=task,
                seed=11,
                model_config_id=model_config_id,
                output_path=output_path,
                manifest_path=manifest_path,
            ),
        ),
    )
    detailed_repository_path.write_text(
        json.dumps(
            detailed_repository.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    request = OrchestratorRequest(
        task=task,
        batch=BatchExecutionOptions(
            enabled=True,
            execution_journal_path=str(journal_path),
            group_id="holdout-10seed",
        ),
    )
    calls: list[str] = []

    def fake_task_runner(task: SingleSeedEvaluationTask) -> dict[str, object]:
        calls.append(task.run_id or task.task_id)
        raise AssertionError("completed run should have been reused")

    result = orchestrate_request(request, task_runner=fake_task_runner)

    repository_payload = json.loads(repository_path.read_text(encoding="utf-8"))
    assert calls == []
    assert result["executed_task_count"] == 0
    assert result["reused_completed_task_count"] == 1
    assert result["failed_task_count"] == 0
    assert result["results"][0]["execution_action"] == "reused_completed"
    assert repository_payload["records"][0]["run_id"] == "seed_01_rs11"
    assert report_path.exists() is True
    assert result["postprocess_report"]["completion_check"]["done_run_count"] == 1
