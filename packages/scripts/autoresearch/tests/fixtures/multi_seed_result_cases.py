from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.execution_matrix import (
    DEFAULT_EVALUATION_SEEDS,
    CommonSeedResultRecord,
    SeedExecutionRecord,
    build_execution_journal,
)
from shared.seed_result_recording import DetailedSeedResultRecord


@dataclass(frozen=True, slots=True)
class MultiSeedRunSpec:
    run_no: int
    seed: int
    seed_payloads: tuple[tuple[tuple[str, ...], Any], ...]
    expected_seed_source: str
    summary_overfit: Any
    summary_robust: Any
    summary_blended: Any
    summary_rolling_min: Any
    summary_rolling_mean: Any
    dev_test_gap: Any
    dev_exact: Any
    dev_avg_set_match: Any
    test_exact: Any
    test_avg_set_match: Any
    expected_overall_hit_rate: float
    expected_overall_source: str
    expected_overfit_safe_exact_rate: float | None
    expected_robust_exact_rate: float | None
    expected_dev_test_gap: float | None
    mutation: tuple[str, ...]

    @property
    def run_id(self) -> str:
        return f"run-{self.run_no:04d}"

    @property
    def task_id(self) -> str:
        return f"candidate-{self.run_no:04d}"

    @property
    def candidate_name(self) -> str:
        return self.task_id


MULTI_SEED_RUN_SPECS: tuple[MultiSeedRunSpec, ...] = (
    MultiSeedRunSpec(
        run_no=1,
        seed=11,
        seed_payloads=((("seeds", "model_random_state"), 11),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.72,
        summary_robust=0.73,
        summary_blended=0.74,
        summary_rolling_min=0.71,
        summary_rolling_mean=0.735,
        dev_test_gap=0.02,
        dev_exact=0.74,
        dev_avg_set_match=0.81,
        test_exact=0.74,
        test_avg_set_match=0.82,
        expected_overall_hit_rate=0.72,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.72,
        expected_robust_exact_rate=0.73,
        expected_dev_test_gap=0.02,
        mutation=("baseline-depth6",),
    ),
    MultiSeedRunSpec(
        run_no=2,
        seed=17,
        seed_payloads=(
            (("parameter_context", "runtime_params", "model_random_state"), 17),
            (("parameter_context", "evaluation_seeds"), list(DEFAULT_EVALUATION_SEEDS)),
        ),
        expected_seed_source="parameter_context.runtime_params.model_random_state",
        summary_overfit="71%",
        summary_robust=74,
        summary_blended=73,
        summary_rolling_min=70,
        summary_rolling_mean=72,
        dev_test_gap="3%",
        dev_exact="74%",
        dev_avg_set_match=0.82,
        test_exact="75%",
        test_avg_set_match=0.83,
        expected_overall_hit_rate=0.71,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.71,
        expected_robust_exact_rate=0.74,
        expected_dev_test_gap=0.03,
        mutation=("percent-normalization",),
    ),
    MultiSeedRunSpec(
        run_no=3,
        seed=23,
        seed_payloads=((("model", "random_state"), 23),),
        expected_seed_source="model.random_state",
        summary_overfit=None,
        summary_robust="69%",
        summary_blended="70%",
        summary_rolling_min="68%",
        summary_rolling_mean=69,
        dev_test_gap=0.01,
        dev_exact=0.71,
        dev_avg_set_match=0.79,
        test_exact=0.68,
        test_avg_set_match=0.8,
        expected_overall_hit_rate=0.69,
        expected_overall_source="summary.robust_exact_rate",
        expected_overfit_safe_exact_rate=None,
        expected_robust_exact_rate=0.69,
        expected_dev_test_gap=0.01,
        mutation=("robust-fallback",),
    ),
    MultiSeedRunSpec(
        run_no=4,
        seed=31,
        seed_payloads=((("runtime_params", "model_random_state"), 31),),
        expected_seed_source="runtime_params.model_random_state",
        summary_overfit=None,
        summary_robust=None,
        summary_blended=0.68,
        summary_rolling_min=0.66,
        summary_rolling_mean=0.67,
        dev_test_gap=0.04,
        dev_exact=0.69,
        dev_avg_set_match=0.78,
        test_exact="67%",
        test_avg_set_match=0.79,
        expected_overall_hit_rate=0.67,
        expected_overall_source="test.exact_3of3_rate",
        expected_overfit_safe_exact_rate=None,
        expected_robust_exact_rate=None,
        expected_dev_test_gap=0.04,
        mutation=("test-fallback",),
    ),
    MultiSeedRunSpec(
        run_no=5,
        seed=37,
        seed_payloads=((("seeds", "model_random_state"), 37),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.7,
        summary_robust=0.71,
        summary_blended=0.715,
        summary_rolling_min=0.69,
        summary_rolling_mean=0.705,
        dev_test_gap=0.02,
        dev_exact=0.72,
        dev_avg_set_match=0.8,
        test_exact=0.71,
        test_avg_set_match=0.81,
        expected_overall_hit_rate=0.7,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.7,
        expected_robust_exact_rate=0.71,
        expected_dev_test_gap=0.02,
        mutation=("mid-band",),
    ),
    MultiSeedRunSpec(
        run_no=6,
        seed=41,
        seed_payloads=((("seeds", "model_random_state"), 41),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.76,
        summary_robust=0.77,
        summary_blended=0.775,
        summary_rolling_min=0.75,
        summary_rolling_mean=0.765,
        dev_test_gap=0.015,
        dev_exact=0.78,
        dev_avg_set_match=0.84,
        test_exact=0.77,
        test_avg_set_match=0.85,
        expected_overall_hit_rate=0.76,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.76,
        expected_robust_exact_rate=0.77,
        expected_dev_test_gap=0.015,
        mutation=("strong-run",),
    ),
    MultiSeedRunSpec(
        run_no=7,
        seed=47,
        seed_payloads=((("seeds", "model_random_state"), 47),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.79,
        summary_robust=0.8,
        summary_blended=0.805,
        summary_rolling_min=0.78,
        summary_rolling_mean=0.795,
        dev_test_gap=0.02,
        dev_exact=0.8,
        dev_avg_set_match=0.85,
        test_exact=0.81,
        test_avg_set_match=0.86,
        expected_overall_hit_rate=0.79,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.79,
        expected_robust_exact_rate=0.8,
        expected_dev_test_gap=0.02,
        mutation=("best-run",),
    ),
    MultiSeedRunSpec(
        run_no=8,
        seed=53,
        seed_payloads=((("seeds", "model_random_state"), 53),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.75,
        summary_robust=0.76,
        summary_blended=0.765,
        summary_rolling_min=0.74,
        summary_rolling_mean=0.755,
        dev_test_gap=0.01,
        dev_exact=0.77,
        dev_avg_set_match=0.83,
        test_exact=0.76,
        test_avg_set_match=0.84,
        expected_overall_hit_rate=0.75,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.75,
        expected_robust_exact_rate=0.76,
        expected_dev_test_gap=0.01,
        mutation=("recovery-run",),
    ),
    MultiSeedRunSpec(
        run_no=9,
        seed=59,
        seed_payloads=((("seeds", "model_random_state"), 59),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.73,
        summary_robust=0.74,
        summary_blended=0.745,
        summary_rolling_min=0.72,
        summary_rolling_mean=0.735,
        dev_test_gap=0.025,
        dev_exact=0.75,
        dev_avg_set_match=0.82,
        test_exact=0.74,
        test_avg_set_match=0.83,
        expected_overall_hit_rate=0.73,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.73,
        expected_robust_exact_rate=0.74,
        expected_dev_test_gap=0.025,
        mutation=("slight-drift",),
    ),
    MultiSeedRunSpec(
        run_no=10,
        seed=61,
        seed_payloads=((("seeds", "model_random_state"), 61),),
        expected_seed_source="seeds.model_random_state",
        summary_overfit=0.74,
        summary_robust=0.75,
        summary_blended=0.755,
        summary_rolling_min=0.73,
        summary_rolling_mean=0.745,
        dev_test_gap=0.03,
        dev_exact=0.76,
        dev_avg_set_match=0.82,
        test_exact=0.75,
        test_avg_set_match=0.83,
        expected_overall_hit_rate=0.74,
        expected_overall_source="summary.overfit_safe_exact_rate",
        expected_overfit_safe_exact_rate=0.74,
        expected_robust_exact_rate=0.75,
        expected_dev_test_gap=0.03,
        mutation=("final-band",),
    ),
)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _set_nested(payload: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = payload
    for key in path[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current[path[-1]] = value


def _base_config_payload() -> dict[str, Any]:
    return {
        "dataset": "full_year_2025",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "rolling_windows": [
            {
                "name": "fold_a",
                "train_end": "20250731",
                "eval_start": "20250801",
                "eval_end": "20250930",
            }
        ],
        "evaluation_contract": {
            "selection_seed_invariant": True,
            "target_label": "unordered_top3",
        },
        "experiment": {
            "profile_version": "autoresearch-experiment-profile-v1",
            "repeat_count": 10,
            "evaluation_seeds": list(DEFAULT_EVALUATION_SEEDS),
            "common_hyperparameters": {
                "prediction_top_k": 3,
                "random_state_source": "evaluation_seed",
            },
        },
        "features": ["rating", "draw_rr"],
        "notes": {"fixture": "multi_seed_random_split"},
    }


def _result_payload(spec: MultiSeedRunSpec) -> dict[str, Any]:
    payload = {
        "config_path": "packages/scripts/autoresearch/clean_model_config.json",
        "config": _base_config_payload(),
        "feature_count": 2,
        "market_feature_count": 0,
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "model": {
            "kind": "hgb",
            "positive_class_weight": 1.0,
            "params": {
                "max_depth": 5 + spec.run_no,
                "learning_rate": 0.05,
            },
        },
        "summary": {
            "robust_exact_rate": spec.summary_robust,
            "overfit_safe_exact_rate": spec.summary_overfit,
            "blended_exact_rate": spec.summary_blended,
            "rolling_min_exact_rate": spec.summary_rolling_min,
            "rolling_mean_exact_rate": spec.summary_rolling_mean,
            "dev_test_gap": spec.dev_test_gap,
        },
        "dev": {
            "races": 100 + spec.run_no,
            "exact_3of3_rate": spec.dev_exact,
            "avg_set_match": spec.dev_avg_set_match,
        },
        "test": {
            "races": 40 + spec.run_no,
            "exact_3of3_rate": spec.test_exact,
            "avg_set_match": spec.test_avg_set_match,
        },
        "integrity": {"all_missing_features": [], "normalized_first3_match_rate": 0.0},
    }
    for path, value in spec.seed_payloads:
        _set_nested(payload, path, value)
    return payload


def write_multi_seed_random_split_case(base_dir: Path) -> tuple[Path, ...]:
    run_paths: list[Path] = []
    for spec in MULTI_SEED_RUN_SPECS:
        artifact_path = (
            base_dir
            / "runs"
            / spec.run_id
            / "artifacts"
            / spec.task_id
            / "clean_research.json"
        )
        _write_json(artifact_path, _result_payload(spec))
        _write_json(
            base_dir / "decisions" / f"decision-{spec.run_id}.json",
            {
                "decisionId": f"decision-{spec.run_id}",
                "outcome": "accepted" if spec.run_no % 2 else "rejected",
                "reason": "fixture-check",
            },
        )
        _write_json(
            base_dir
            / "runs"
            / spec.run_id
            / "logs"
            / f"{spec.task_id}.propose.stdout.log",
            {
                "config": "packages/scripts/autoresearch/clean_model_config.json",
                "mutation": list(spec.mutation),
            },
        )
        run_json_path = base_dir / "runs" / f"{spec.run_id}.json"
        _write_json(
            run_json_path,
            {
                "runId": spec.run_id,
                "candidateId": spec.task_id,
                "status": "accepted" if spec.run_no % 2 else "rejected",
                "phase": "completed",
                "startedAt": f"2026-04-11T00:{spec.run_no:02d}:00+09:00",
                "endedAt": f"2026-04-11T00:{spec.run_no:02d}:30+09:00",
                "manifestHash": f"{spec.run_no:064x}",
                "workspaceRef": "main",
                "proposal": {
                    "proposerType": "command",
                    "summary": f"proposal-{spec.run_no}",
                },
                "artifacts": [{"id": "clean_research", "path": str(artifact_path)}],
                "metrics": {
                    "dev_exact_rate": {
                        "metricId": "dev_exact_rate",
                        "value": spec.dev_exact,
                        "direction": "maximize",
                    }
                },
                "decisionId": f"decision-{spec.run_id}",
                "logs": {
                    "proposeStdoutPath": str(
                        base_dir
                        / "runs"
                        / spec.run_id
                        / "logs"
                        / f"{spec.task_id}.propose.stdout.log"
                    ),
                    "runStdoutPath": str(
                        base_dir
                        / "runs"
                        / spec.run_id
                        / "logs"
                        / f"{spec.task_id}.experiment.stdout.log"
                    ),
                },
            },
        )
        run_paths.append(run_json_path)
    return tuple(run_paths)


EXPECTED_COLLECTION_ROWS: tuple[dict[str, Any], ...] = tuple(
    {
        "run_id": spec.run_id,
        "seed": spec.seed,
        "seed_index": index,
        "seed_source": spec.expected_seed_source,
        "overall_holdout_hit_rate": spec.expected_overall_hit_rate,
        "overall_holdout_hit_rate_source": spec.expected_overall_source,
        "overfit_safe_exact_rate": spec.expected_overfit_safe_exact_rate,
        "robust_exact_rate": spec.expected_robust_exact_rate,
        "dev_test_gap": spec.expected_dev_test_gap,
        "candidate_name": spec.candidate_name,
        "mutation": list(spec.mutation),
    }
    for index, spec in enumerate(MULTI_SEED_RUN_SPECS, start=1)
)

EXPECTED_REPORT_SUMMARY: dict[str, Any] = {
    "gate_actual": 0.67,
    "gate_passed": False,
    "verification_status": "FAIL",
    "verification_blockers": ["below_threshold"],
    "worst_completed_run_id": "seed_04_rs31",
    "overall_distribution": {
        "count": 10,
        "min": 0.67,
        "max": 0.79,
        "mean": 0.726,
        "median": 0.725,
        "stddev": 0.033823,
        "quantiles": {
            "p10": 0.688,
            "p25": 0.7025,
            "p50": 0.725,
            "p75": 0.7475,
            "p90": 0.763,
        },
        "outlier_count": 0,
    },
    "normalized_overall_summary": {
        "row_count": 10,
        "ok_count": 10,
        "normalized_mean": 0.726,
        "normalized_median": 0.725,
        "normalized_stddev": 0.033823,
        "comparable_mean": 0.726,
        "comparable_median": 0.725,
        "comparable_stddev": 0.033823,
        "outlier_count": 0,
    },
    "normalized_dev_gap_summary": {
        "row_count": 10,
        "ok_count": 10,
        "comparable_mean": 0.978,
    },
    "fallback_sources_by_run_id": {
        "seed_03_rs23": "summary.robust_exact_rate",
        "seed_04_rs31": "test.exact_3of3_rate",
    },
}


def build_execution_journal_from_detailed_records(
    records: tuple[DetailedSeedResultRecord, ...],
):
    execution_records = []
    for record in records:
        seed_run_id = f"seed_{record.seed_index:02d}_rs{record.seed}"
        execution_records.append(
            SeedExecutionRecord(
                run_id=seed_run_id,
                task_id=record.task_id,
                seed_index=record.seed_index,
                model_random_state=record.seed,
                status="completed",
                started_at=record.run_at,
                finished_at=record.run_at,
                artifacts={
                    "output_path": record.artifacts.output_path,
                    "manifest_path": record.artifacts.manifest_path,
                },
                metrics=record.evaluation_result.core_metrics,
                common_result=CommonSeedResultRecord(
                    run_id=seed_run_id,
                    seed=record.seed,
                    run_at=record.run_at,
                    model_config_id=record.model_config_id,
                    overall_holdout_hit_rate=record.evaluation_result.overall_holdout_hit_rate,
                    overall_holdout_hit_rate_source=record.evaluation_result.overall_holdout_hit_rate_source,
                ),
            )
        )

    return build_execution_journal(
        evaluation_seeds=DEFAULT_EVALUATION_SEEDS,
        records=tuple(execution_records),
    )
