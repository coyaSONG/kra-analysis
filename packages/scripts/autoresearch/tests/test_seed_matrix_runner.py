from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.execution_matrix import DEFAULT_EVALUATION_SEEDS  # noqa: E402

from autoresearch.parameter_context import (
    load_evaluation_parameter_context,  # noqa: E402
)
from autoresearch.seed_matrix_runner import (  # noqa: E402
    build_seed_matrix_plan,
    execute_seed_matrix,
    load_verification_gate_result,
    main,
)


def test_build_seed_matrix_plan_writes_execution_metadata_files(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
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

    plan = build_seed_matrix_plan(
        config_path=config_path,
        output_dir=tmp_path / "outputs",
    )

    execution_matrix_payload = json.loads(
        plan.execution_matrix_path.read_text(encoding="utf-8")
    )
    execution_metadata_payload = json.loads(
        plan.execution_metadata_path.read_text(encoding="utf-8")
    )

    assert len(plan.requests) == 10
    assert execution_matrix_payload["evaluation_seeds"] == list(
        DEFAULT_EVALUATION_SEEDS
    )
    assert (
        execution_metadata_payload["format_version"] == "holdout-execution-metadata-v1"
    )
    assert execution_metadata_payload["phase"] == "planned"
    assert execution_metadata_payload["plan"]["expected_run_count"] == 10
    assert execution_metadata_payload["plan"]["config_path"] == str(
        config_path.resolve()
    )
    assert (
        execution_metadata_payload["plan"]["evaluation_seed_source"]
        == "execution_matrix.default_evaluation_seeds"
    )
    assert len(execution_metadata_payload["expected_runs"]) == 10
    assert plan.requests[0].task.run_id == "seed_01_rs11"
    assert plan.requests[-1].task.run_id == "seed_10_rs61"
    assert plan.requests[0].task.output_path.endswith(
        "seed_01_rs11/research_clean.json"
    )
    assert plan.requests[0].task.runtime_params_path is None
    assert plan.requests[0].task.model_random_state is None


def test_build_seed_matrix_plan_uses_config_experiment_seeds_when_cli_override_missing(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "experiment": {
                    "evaluation_seeds": [71, 73, 79, 83, 89, 97, 101, 103, 107, 109]
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    plan = build_seed_matrix_plan(
        config_path=config_path,
        output_dir=tmp_path / "outputs",
    )

    assert plan.execution_matrix.evaluation_seeds == (
        71,
        73,
        79,
        83,
        89,
        97,
        101,
        103,
        107,
        109,
    )
    assert plan.requests[0].task.run_id == "seed_01_rs71"
    assert plan.requests[-1].task.run_id == "seed_10_rs109"


def test_execute_seed_matrix_persists_standard_validation_outputs(
    tmp_path: Path,
) -> None:
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def fake_task_runner(task) -> dict[str, object]:
        exact_rate = 0.74
        if task.seed_index == 10:
            exact_rate = 0.71
        parameter_context = load_evaluation_parameter_context(
            config_path=config_path,
            seed_index=task.seed_index,
            run_id=task.run_id,
            model_random_state=None,
        ).model_dump(mode="json")
        output_path = Path(task.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"run_id": task.run_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest_path = output_path.with_name(f"{output_path.stem}_manifest.json")
        manifest_path.write_text(
            json.dumps({"run_id": task.run_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "summary": {
                "robust_exact_rate": exact_rate,
                "overfit_safe_exact_rate": exact_rate,
                "blended_exact_rate": exact_rate,
                "rolling_min_exact_rate": exact_rate,
                "rolling_mean_exact_rate": exact_rate,
                "dev_test_gap": 0.01,
            },
            "dev": {"exact_3of3_rate": exact_rate, "avg_set_match": 0.8, "races": 120},
            "test": {
                "exact_3of3_rate": exact_rate,
                "avg_set_match": 0.81,
                "races": 130,
            },
            "seeds": {"model_random_state": int(task.run_id.split("rs", 1)[1])},
            "runtime_params": {
                "model_random_state": int(task.run_id.split("rs", 1)[1])
            },
            "config": config_payload,
            "parameter_context": parameter_context,
        }

    result = execute_seed_matrix(
        config_path=config_path,
        output_dir=tmp_path / "outputs",
        task_runner=fake_task_runner,
    )

    report_payload = json.loads(
        Path(result["summary_report_json_path"]).read_text(encoding="utf-8")
    )
    csv_rows = list(
        csv.DictReader(
            Path(result["summary_report_csv_path"])
            .read_text(encoding="utf-8")
            .splitlines()
        )
    )

    assert result["failed_task_count"] == 0
    assert len(result["runs"]) == 10
    assert result["runs"][0]["run_id"] == "seed_01_rs11"
    assert result["runs"][-1]["run_id"] == "seed_10_rs61"
    assert Path(result["execution_matrix_path"]).exists() is True
    assert Path(result["execution_metadata_path"]).exists() is True
    assert Path(result["execution_journal_path"]).exists() is True
    assert Path(result["seed_result_repository_path"]).exists() is True
    assert result["execution_metadata"]["consistency_check"]["status"] == "PASS"
    assert result["execution_metadata"]["consistency_check"]["mismatched_run_ids"] == []
    assert report_payload["gate"]["metric"] == "lowest_overall_holdout_hit_rate"
    assert (
        report_payload["gate"]["metric_source"]
        == "seed_result_repository.summary.lowest_overall_holdout_hit_rate"
    )
    assert report_payload["gate"]["actual"] == 0.71
    assert report_payload["gate"]["passed"] is True
    assert report_payload["verification_verdict"]["status"] == "PASS"
    assert report_payload["verification_verdict"]["lowest_hit_rate"] == 0.71
    assert report_payload["verification_verdict"]["margin_vs_threshold"] == 0.01
    assert result["verification_verdict"]["status"] == "PASS"
    assert report_payload["completion_check"]["done_run_count"] == 10
    assert len(csv_rows) == 10
    assert csv_rows[-1]["run_id"] == "seed_10_rs61"
    assert csv_rows[-1]["overall_holdout_hit_rate"] == "0.71"
    assert result["runs"][-1]["parameter_context_present"] is True
    assert (
        result["execution_metadata"]["observed_runs"][0]["setting_snapshot"][
            "input_contract_signature"
        ]
        is None
    )


def test_execute_seed_matrix_reuses_completed_runs_on_rerun(
    tmp_path: Path,
) -> None:
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def initial_task_runner(task) -> dict[str, object]:
        parameter_context = load_evaluation_parameter_context(
            config_path=config_path,
            seed_index=task.seed_index,
            run_id=task.run_id,
            model_random_state=None,
        ).model_dump(mode="json")
        output_path = Path(task.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"run_id": task.run_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest_path = output_path.with_name(f"{output_path.stem}_manifest.json")
        manifest_path.write_text(
            json.dumps({"run_id": task.run_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        seed = int(task.run_id.split("rs", 1)[1])
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "summary": {"robust_exact_rate": 0.72, "overfit_safe_exact_rate": 0.72},
            "dev": {"exact_3of3_rate": 0.72, "avg_set_match": 0.8, "races": 120},
            "test": {"exact_3of3_rate": 0.72, "avg_set_match": 0.81, "races": 130},
            "seeds": {"model_random_state": seed},
            "runtime_params": {"model_random_state": seed},
            "config": config_payload,
            "parameter_context": parameter_context,
        }

    execute_seed_matrix(
        config_path=config_path,
        output_dir=tmp_path / "outputs",
        task_runner=initial_task_runner,
    )

    rerun_calls: list[str] = []

    def rerun_task_runner(task) -> dict[str, object]:
        rerun_calls.append(task.run_id)
        raise AssertionError("completed runs should be reused on rerun")

    rerun_result = execute_seed_matrix(
        config_path=config_path,
        output_dir=tmp_path / "outputs",
        task_runner=rerun_task_runner,
    )

    assert rerun_calls == []
    assert rerun_result["executed_task_count"] == 0
    assert rerun_result["reused_completed_task_count"] == 10
    assert rerun_result["failed_task_count"] == 0
    assert all(
        run["execution_action"] == "reused_completed" for run in rerun_result["runs"]
    )
    assert rerun_result["verification_verdict"]["status"] == "PASS"


def test_execute_seed_matrix_reports_config_consistency_failure(
    tmp_path: Path,
) -> None:
    config_payload = {
        "dataset": "holdout",
        "model": {"kind": "hgb", "params": {"max_depth": 6}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def fake_task_runner(task) -> dict[str, object]:
        parameter_context = load_evaluation_parameter_context(
            config_path=config_path,
            seed_index=task.seed_index,
            run_id=task.run_id,
            model_random_state=None,
        ).model_dump(mode="json")
        if task.seed_index == 10:
            parameter_context["config_sha256"] = "0" * 64
        return {
            "task_id": task.task_id,
            "run_id": task.run_id,
            "output_path": str(Path(task.output_path)),
            "manifest_path": str(
                Path(task.output_path).with_name("research_clean_manifest.json")
            ),
            "summary": {
                "robust_exact_rate": 0.74,
                "overfit_safe_exact_rate": 0.74,
                "blended_exact_rate": 0.74,
                "rolling_min_exact_rate": 0.74,
                "rolling_mean_exact_rate": 0.74,
                "dev_test_gap": 0.01,
            },
            "dev": {"exact_3of3_rate": 0.74, "avg_set_match": 0.8, "races": 120},
            "test": {"exact_3of3_rate": 0.74, "avg_set_match": 0.81, "races": 130},
            "seeds": {"model_random_state": int(task.run_id.split("rs", 1)[1])},
            "runtime_params": {
                "model_random_state": int(task.run_id.split("rs", 1)[1])
            },
            "config": config_payload,
            "parameter_context": parameter_context,
        }

    result = execute_seed_matrix(
        config_path=config_path,
        output_dir=tmp_path / "outputs",
        task_runner=fake_task_runner,
    )

    metadata_payload = json.loads(
        Path(result["execution_metadata_path"]).read_text(encoding="utf-8")
    )

    assert result["execution_metadata"]["consistency_check"]["status"] == "FAIL"
    assert result["execution_metadata"]["consistency_check"]["mismatched_run_ids"] == [
        "seed_10_rs61"
    ]
    assert (
        result["execution_metadata"]["consistency_check"]["field_mismatch_counts"][
            "config_sha256"
        ]
        == 1
    )
    assert metadata_payload["observed_runs"][-1]["matched_expected_settings"] is False
    assert metadata_payload["observed_runs"][-1]["mismatch_fields"] == ["config_sha256"]


def test_load_verification_gate_result_reads_final_status_from_summary_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "holdout_seed_summary_report.json"
    report_path.write_text(
        json.dumps(
            {
                "gate": {"passed": False},
                "verification_verdict": {
                    "status": "FAIL",
                    "passed": False,
                    "blockers": ["below_threshold"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    gate = load_verification_gate_result(report_path)

    assert gate["status"] == "FAIL"
    assert gate["passed"] is False
    assert gate["verification_verdict"]["blockers"] == ["below_threshold"]


def test_load_verification_gate_result_rejects_invalid_summary_report(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "holdout_seed_summary_report.json"
    report_path.write_text(
        json.dumps(
            {
                "gate": {"passed": True},
                "verification_verdict": {"status": "FAIL"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="gate.passed does not match verification_verdict.status",
    ):
        load_verification_gate_result(report_path)


def test_seed_matrix_main_returns_nonzero_when_final_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    report_path = tmp_path / "holdout_seed_summary_report.json"
    report_path.write_text(
        json.dumps(
            {
                "gate": {"passed": False},
                "verification_verdict": {"status": "FAIL", "passed": False},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "autoresearch.seed_matrix_runner.execute_seed_matrix",
        lambda **_: {
            "summary_report_json_path": str(report_path),
            "failed_task_count": 0,
            "execution_metadata": {
                "consistency_check": {"status": "PASS", "passed": True}
            },
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seed_matrix_runner.py",
            "--config",
            str(config_path),
            "--output-dir",
            str(tmp_path / "outputs"),
        ],
    )

    with pytest.raises(SystemExit, match="1"):
        main()


def test_seed_matrix_main_returns_zero_when_final_verification_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    report_path = tmp_path / "holdout_seed_summary_report.json"
    report_path.write_text(
        json.dumps(
            {
                "gate": {"passed": True},
                "verification_verdict": {"status": "PASS", "passed": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "autoresearch.seed_matrix_runner.execute_seed_matrix",
        lambda **_: {
            "summary_report_json_path": str(report_path),
            "failed_task_count": 0,
            "execution_metadata": {
                "consistency_check": {"status": "PASS", "passed": True}
            },
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seed_matrix_runner.py",
            "--config",
            str(config_path),
            "--output-dir",
            str(tmp_path / "outputs"),
        ],
    )

    main()
