from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.execution_matrix import (  # noqa: E402
    DEFAULT_EVALUATION_SEEDS,
    EXECUTION_MATRIX_VERSION,
    MODEL_CONFIG_ID_PREFIX,
    CommonSeedResultRecord,
    ExecutionMatrix,
    SeedExecutionMetrics,
    SeedExecutionRecord,
    build_execution_journal,
    build_execution_matrix,
    build_holdout_manifest_parameters,
    build_model_config_id,
    seed_result_repository_from_journal,
    upsert_execution_record,
    validate_execution_journal_payload,
    validate_execution_matrix_payload,
    validate_seed_result_record_payload,
    validate_seed_result_repository_payload,
)


def test_default_execution_matrix_declares_10_unique_seed_runs() -> None:
    matrix = build_execution_matrix()

    runs = matrix.build_runs()

    assert matrix.format_version == EXECUTION_MATRIX_VERSION
    assert matrix.evaluation_seeds == DEFAULT_EVALUATION_SEEDS
    assert len(runs) == 10
    assert len({run.model_random_state for run in runs}) == 10
    assert runs[0].run_id == "seed_01_rs11"
    assert all(run.holdout.selection_seed_invariant is True for run in runs)


def test_execution_matrix_rejects_duplicate_or_short_seed_lists() -> None:
    ok, errors = validate_execution_matrix_payload(
        {
            "evaluation_seeds": [11, 11, 23, 31, 37, 41, 47, 53, 59, 61],
            "holdout": {},
        }
    )
    short_ok, short_errors = validate_execution_matrix_payload(
        {
            "evaluation_seeds": [11, 17, 23],
            "holdout": {},
        }
    )

    assert ok is False
    assert any("evaluation_seeds" in error for error in errors)
    assert short_ok is False
    assert any("정확히 10개" in error for error in short_errors)


def test_build_holdout_manifest_parameters_reuses_common_contract() -> None:
    matrix = ExecutionMatrix.model_validate(
        {
            "evaluation_seeds": DEFAULT_EVALUATION_SEEDS,
            "holdout": {
                "leakage_policy_version": "leakage-checks-v2",
            },
        }
    )

    parameters = build_holdout_manifest_parameters(
        dataset="holdout",
        minimum_race_count=500,
        execution_matrix=matrix,
    )

    assert parameters == {
        "dataset": "holdout",
        "selection_method": "time_ordered_complete_date_accumulation",
        "boundary_unit": "race_date",
        "minimum_race_count": 500,
        "require_complete_race_dates": True,
        "allow_intra_day_cut": False,
        "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
        "target_label": "unordered_top3",
        "leakage_policy_version": "leakage-checks-v2",
    }


def test_execution_journal_tracks_completion_and_lowest_metric() -> None:
    journal = build_execution_journal()
    model_config_id = build_model_config_id(
        {"model": {"kind": "hgb", "params": {"max_depth": 6}}}
    )

    journal = upsert_execution_record(
        journal,
        SeedExecutionRecord(
            run_id="seed_01_rs11",
            task_id="task-01",
            seed_index=1,
            model_random_state=11,
            status="completed",
            started_at="2026-04-10T12:00:00+09:00",
            finished_at="2026-04-10T12:01:00+09:00",
            metrics=SeedExecutionMetrics(
                overfit_safe_exact_rate=0.72,
                robust_exact_rate=0.75,
                test_exact_3of3_rate=0.78,
            ),
            common_result=CommonSeedResultRecord(
                run_id="seed_01_rs11",
                seed=11,
                run_at="2026-04-10T12:01:00+09:00",
                model_config_id=model_config_id,
                overall_holdout_hit_rate=0.72,
                overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
            ),
        ),
    )
    journal = upsert_execution_record(
        journal,
        SeedExecutionRecord(
            run_id="seed_02_rs17",
            task_id="task-02",
            seed_index=2,
            model_random_state=17,
            status="failed",
            started_at="2026-04-10T12:02:00+09:00",
            finished_at="2026-04-10T12:03:00+09:00",
            failure={
                "error_type": "RuntimeError",
                "error_message": "boom",
            },
        ),
    )

    summary = journal.summary

    assert summary.expected_run_count == 10
    assert summary.recorded_run_count == 2
    assert summary.completed_run_count == 1
    assert summary.failed_run_count == 1
    assert summary.all_expected_runs_recorded is False
    assert summary.all_expected_runs_completed is False
    assert summary.all_runs_completed_successfully is False
    assert summary.lowest_overfit_safe_exact_rate == 0.72
    assert summary.lowest_robust_exact_rate == 0.75
    assert summary.lowest_test_exact_3of3_rate == 0.78
    assert summary.missing_completed_run_ids[0] == "seed_02_rs17"
    assert summary.missing_run_ids[0] == "seed_03_rs23"


def test_execution_journal_distinguishes_terminal_runs_from_all_completed_runs() -> (
    None
):
    model_config_id = build_model_config_id(
        {"model": {"kind": "hgb", "params": {"max_depth": 6}}}
    )
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
                    overfit_safe_exact_rate=0.72,
                    robust_exact_rate=0.75,
                    test_exact_3of3_rate=0.78,
                ),
                common_result=CommonSeedResultRecord(
                    run_id=f"seed_{seed_index:02d}_rs{seed}",
                    seed=seed,
                    run_at="2026-04-10T12:01:00+09:00",
                    model_config_id=model_config_id,
                    overall_holdout_hit_rate=0.72,
                    overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
                ),
            ),
        )

    journal = upsert_execution_record(
        journal,
        SeedExecutionRecord(
            run_id="seed_10_rs61",
            task_id="task-10",
            seed_index=10,
            model_random_state=61,
            status="failed",
            started_at="2026-04-10T12:00:00+09:00",
            finished_at="2026-04-10T12:01:00+09:00",
            failure={
                "error_type": "RuntimeError",
                "error_message": "boom",
            },
        ),
    )

    summary = journal.summary

    assert summary.recorded_run_count == 10
    assert summary.completed_run_count == 9
    assert summary.failed_run_count == 1
    assert summary.all_expected_runs_recorded is True
    assert summary.all_runs_terminal is True
    assert summary.all_expected_runs_completed is False
    assert summary.all_runs_completed_successfully is False
    assert summary.missing_run_ids == ()
    assert summary.missing_completed_run_ids == ("seed_10_rs61",)


def test_common_seed_result_record_uses_stable_storage_fields() -> None:
    model_config_id = build_model_config_id(
        {"dataset": "holdout", "model": {"kind": "hgb", "params": {"max_depth": 6}}}
    )
    record = CommonSeedResultRecord(
        run_id="seed_01_rs11",
        seed=11,
        run_at="2026-04-10T12:01:00+09:00",
        model_config_id=model_config_id,
        overall_holdout_hit_rate=0.71,
        overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
    )

    payload = record.model_dump(mode="json")

    assert payload["format_version"] == "holdout-seed-result-record-v1"
    assert payload["seed"] == 11
    assert payload["run_at"] == "2026-04-10T12:01:00+09:00"
    assert payload["model_config_id"].startswith(MODEL_CONFIG_ID_PREFIX)
    assert payload["overall_holdout_hit_rate"] == 0.71


def test_validate_seed_result_record_payload_rejects_missing_required_fields() -> None:
    ok, errors = validate_seed_result_record_payload(
        {
            "format_version": "holdout-seed-result-record-v1",
            "run_id": "seed_01_rs11",
            "seed": 11,
        }
    )

    assert ok is False
    assert any("missing_required_fields" in error for error in errors)
    assert any("run_at" in error for error in errors)


def test_validate_seed_result_record_payload_rejects_run_id_seed_mismatch() -> None:
    model_config_id = build_model_config_id(
        {"dataset": "holdout", "model": {"kind": "hgb", "params": {"max_depth": 6}}}
    )

    ok, errors = validate_seed_result_record_payload(
        {
            "format_version": "holdout-seed-result-record-v1",
            "run_id": "seed_01_rs17",
            "seed": 11,
            "run_at": "2026-04-10T12:01:00+09:00",
            "model_config_id": model_config_id,
            "overall_holdout_hit_rate": 0.71,
            "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
        }
    )

    assert ok is False
    assert any("run_id 의 rs 시드 값과 seed 필드" in error for error in errors)


def test_seed_result_repository_projects_common_records_for_reuse() -> None:
    model_config_id = build_model_config_id(
        {"dataset": "holdout", "model": {"kind": "hgb", "params": {"max_depth": 6}}}
    )
    journal = upsert_execution_record(
        build_execution_journal(),
        SeedExecutionRecord(
            run_id="seed_01_rs11",
            task_id="task-01",
            seed_index=1,
            model_random_state=11,
            status="completed",
            started_at="2026-04-10T12:00:00+09:00",
            finished_at="2026-04-10T12:01:00+09:00",
            metrics=SeedExecutionMetrics(
                overfit_safe_exact_rate=0.72,
                robust_exact_rate=0.75,
                test_exact_3of3_rate=0.78,
            ),
            common_result=CommonSeedResultRecord(
                run_id="seed_01_rs11",
                seed=11,
                run_at="2026-04-10T12:01:00+09:00",
                model_config_id=model_config_id,
                overall_holdout_hit_rate=0.72,
                overall_holdout_hit_rate_source="summary.overfit_safe_exact_rate",
            ),
        ),
    )

    repository = seed_result_repository_from_journal(journal)
    payload = repository.model_dump(mode="json")
    ok, errors = validate_seed_result_repository_payload(payload)

    assert ok is True, errors
    assert payload["records"] == [
        {
            "format_version": "holdout-seed-result-record-v1",
            "run_id": "seed_01_rs11",
            "seed": 11,
            "run_at": "2026-04-10T12:01:00+09:00",
            "model_config_id": model_config_id,
            "overall_holdout_hit_rate": 0.72,
            "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
        }
    ]
    assert payload["summary"]["recorded_run_count"] == 1
    assert payload["summary"]["all_expected_runs_recorded"] is False
    assert payload["summary"]["missing_run_ids"][0] == "seed_02_rs17"
    assert payload["summary"]["lowest_overall_holdout_hit_rate"] == 0.72


def test_validate_seed_result_repository_payload_surfaces_record_format_errors() -> (
    None
):
    model_config_id = build_model_config_id(
        {"dataset": "holdout", "model": {"kind": "hgb", "params": {"max_depth": 6}}}
    )
    repository = seed_result_repository_from_journal(build_execution_journal())
    payload = repository.model_dump(mode="json")
    payload["records"] = [
        {
            "format_version": "holdout-seed-result-record-v1",
            "run_id": "seed_01_rs17",
            "seed": 11,
            "run_at": "2026-04-10T12:01:00+09:00",
            "model_config_id": model_config_id,
            "overall_holdout_hit_rate": 0.72,
            "overall_holdout_hit_rate_source": "summary.overfit_safe_exact_rate",
        }
    ]

    ok, errors = validate_seed_result_repository_payload(payload)

    assert ok is False
    assert any("records.0" in error for error in errors)
    assert any("run_id 의 rs 시드 값과 seed 필드" in error for error in errors)


def test_validate_execution_journal_payload_rejects_mismatched_summary() -> None:
    journal = build_execution_journal()
    payload = journal.model_dump(mode="json")
    payload["summary"]["expected_run_count"] = 9

    ok, errors = validate_execution_journal_payload(payload)

    assert ok is False
    assert any("summary" in error for error in errors)
