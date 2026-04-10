from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.execution_matrix import build_model_config_id  # noqa: E402

from autoresearch.random_split_result_collector import (  # noqa: E402
    collect_detailed_records_from_ralph_runs,
)

from .fixtures.multi_seed_result_cases import (  # noqa: E402
    EXPECTED_COLLECTION_ROWS,
    write_multi_seed_random_split_case,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _result_payload(*, seed: int | None, max_depth: int, candidate_name: str) -> dict:
    payload = {
        "config_path": "packages/scripts/autoresearch/clean_model_config.json",
        "config": {
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
                "evaluation_seeds": [11, 17, 23, 31, 37, 41, 47, 53, 59, 61],
                "common_hyperparameters": {
                    "prediction_top_k": 3,
                    "random_state_source": "evaluation_seed",
                },
            },
            "features": ["rating", "draw_rr"],
            "notes": {"last_mutation": candidate_name},
        },
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
            "params": {"max_depth": max_depth, "learning_rate": 0.05},
        },
        "summary": {
            "robust_exact_rate": 0.61 + (max_depth / 1000.0),
            "overfit_safe_exact_rate": 0.55 + (max_depth / 1000.0),
            "rolling_min_exact_rate": 0.52 + (max_depth / 1000.0),
            "rolling_mean_exact_rate": 0.58 + (max_depth / 1000.0),
            "dev_test_gap": 0.03,
        },
        "dev": {
            "races": 100,
            "exact_3of3_rate": 0.61,
            "avg_set_match": 0.73,
        },
        "test": {
            "races": 40,
            "exact_3of3_rate": 0.62,
            "avg_set_match": 0.75,
        },
        "integrity": {"all_missing_features": [], "normalized_first3_match_rate": 0.0},
    }
    if seed is not None:
        payload["seeds"] = {"model_random_state": seed}
    return payload


def _write_run_fixture(
    base_dir: Path,
    *,
    run_no: int,
    seed: int | None,
    max_depth: int,
    candidate_name: str,
) -> Path:
    run_id = f"run-{run_no:04d}"
    candidate_id = f"candidate-{run_no:04d}"
    artifact_path = (
        base_dir / "runs" / run_id / "artifacts" / candidate_id / "clean_research.json"
    )
    _write_json(
        artifact_path,
        _result_payload(seed=seed, max_depth=max_depth, candidate_name=candidate_name),
    )
    _write_json(
        base_dir / "decisions" / f"decision-{run_id}.json",
        {
            "decisionId": f"decision-{run_id}",
            "outcome": "accepted" if run_no % 2 else "rejected",
            "reason": "epsilon-improve",
        },
    )
    _write_json(
        base_dir / "runs" / run_id / "logs" / f"{candidate_id}.propose.stdout.log",
        {
            "config": "packages/scripts/autoresearch/clean_model_config.json",
            "mutation": [candidate_name],
        },
    )
    run_json_path = base_dir / "runs" / f"{run_id}.json"
    _write_json(
        run_json_path,
        {
            "runId": run_id,
            "candidateId": candidate_id,
            "status": "accepted" if run_no % 2 else "rejected",
            "phase": "completed",
            "startedAt": f"2026-04-11T00:0{run_no}:00+09:00",
            "endedAt": f"2026-04-11T00:0{run_no}:30+09:00",
            "manifestHash": f"{run_no:064x}",
            "workspaceRef": "main",
            "proposal": {
                "proposerType": "command",
                "summary": f"proposal-{run_no}",
            },
            "artifacts": [{"id": "clean_research", "path": str(artifact_path)}],
            "metrics": {
                "dev_exact_rate": {
                    "metricId": "dev_exact_rate",
                    "value": 0.55 + (max_depth / 1000.0),
                    "direction": "maximize",
                }
            },
            "decisionId": f"decision-{run_id}",
            "logs": {
                "proposeStdoutPath": str(
                    base_dir
                    / "runs"
                    / run_id
                    / "logs"
                    / f"{candidate_id}.propose.stdout.log"
                ),
                "runStdoutPath": str(
                    base_dir
                    / "runs"
                    / run_id
                    / "logs"
                    / f"{candidate_id}.experiment.stdout.log"
                ),
            },
        },
    )
    return run_json_path


def test_collect_random_split_runs_builds_detailed_seed_records(tmp_path: Path) -> None:
    run_2 = _write_run_fixture(
        tmp_path,
        run_no=2,
        seed=17,
        max_depth=8,
        candidate_name="candidate-depth8",
    )
    run_1 = _write_run_fixture(
        tmp_path,
        run_no=1,
        seed=11,
        max_depth=6,
        candidate_name="candidate-depth6",
    )

    records = collect_detailed_records_from_ralph_runs((run_2, run_1))

    assert [record.run_id for record in records] == ["run-0001", "run-0002"]
    assert [record.seed for record in records] == [11, 17]
    assert [record.seed_index for record in records] == [1, 2]
    assert records[0].seed_context.parameter_source == "seeds.model_random_state"
    assert records[0].evaluation_result.overall_holdout_hit_rate == pytest.approx(0.556)
    assert records[
        1
    ].evaluation_result.core_metrics.rolling_min_exact_rate == pytest.approx(0.528)
    assert (
        records[0].split_settings.evaluation_contract["source_metadata"]["run_status"]
        == "accepted"
    )
    assert records[1].search_parameters.model_candidates[0]["mutation"] == [
        "candidate-depth8"
    ]
    assert records[0].model_config_id == build_model_config_id(
        _result_payload(seed=11, max_depth=6, candidate_name="candidate-depth6")[
            "config"
        ]
    )


def test_collect_random_split_runs_rejects_missing_seed_without_override(
    tmp_path: Path,
) -> None:
    run_path = _write_run_fixture(
        tmp_path,
        run_no=1,
        seed=None,
        max_depth=6,
        candidate_name="legacy-candidate",
    )

    with pytest.raises(ValueError, match="Unable to resolve seed"):
        collect_detailed_records_from_ralph_runs((run_path,))


def test_collect_random_split_runs_accepts_seed_override_for_legacy_payload(
    tmp_path: Path,
) -> None:
    run_path = _write_run_fixture(
        tmp_path,
        run_no=3,
        seed=None,
        max_depth=7,
        candidate_name="legacy-candidate",
    )

    records = collect_detailed_records_from_ralph_runs(
        (run_path,),
        seed_overrides={"run-0003": 23},
    )

    assert len(records) == 1
    assert records[0].seed == 23
    assert records[0].seed_index == 1
    assert records[0].seed_context.parameter_source == "seed_overrides[run-0003]"


def test_collect_random_split_runs_normalizes_percent_and_numeric_scales(
    tmp_path: Path,
) -> None:
    run_path = _write_run_fixture(
        tmp_path,
        run_no=4,
        seed=31,
        max_depth=9,
        candidate_name="candidate-depth9",
    )
    payload = json.loads(
        (
            tmp_path
            / "runs"
            / "run-0004"
            / "artifacts"
            / "candidate-0004"
            / "clean_research.json"
        ).read_text(encoding="utf-8")
    )
    payload["summary"]["overfit_safe_exact_rate"] = "71%"
    payload["summary"]["robust_exact_rate"] = 74
    payload["summary"]["dev_test_gap"] = "3%"
    payload["test"]["exact_3of3_rate"] = "75%"
    (
        tmp_path
        / "runs"
        / "run-0004"
        / "artifacts"
        / "candidate-0004"
        / "clean_research.json"
    ).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    records = collect_detailed_records_from_ralph_runs((run_path,))

    assert records[0].evaluation_result.overall_holdout_hit_rate == pytest.approx(0.71)
    assert records[0].evaluation_result.core_metrics.robust_exact_rate == pytest.approx(
        0.74
    )
    assert records[0].evaluation_result.core_metrics.dev_test_gap == pytest.approx(0.03)
    assert records[0].evaluation_result.metric_normalization["metrics"]["dev_test_gap"][
        "comparable_value"
    ] == pytest.approx(0.97)


def test_collect_random_split_runs_matches_representative_multi_seed_fixture(
    tmp_path: Path,
) -> None:
    run_paths = write_multi_seed_random_split_case(tmp_path)

    records = collect_detailed_records_from_ralph_runs(tuple(reversed(run_paths)))

    projected = [
        {
            "run_id": record.run_id,
            "seed": record.seed,
            "seed_index": record.seed_index,
            "seed_source": record.seed_context.parameter_source,
            "overall_holdout_hit_rate": record.evaluation_result.overall_holdout_hit_rate,
            "overall_holdout_hit_rate_source": record.evaluation_result.overall_holdout_hit_rate_source,
            "overfit_safe_exact_rate": record.evaluation_result.core_metrics.overfit_safe_exact_rate,
            "robust_exact_rate": record.evaluation_result.core_metrics.robust_exact_rate,
            "dev_test_gap": record.evaluation_result.core_metrics.dev_test_gap,
            "candidate_name": record.search_parameters.candidate_names[0],
            "mutation": list(record.search_parameters.model_candidates[0]["mutation"]),
        }
        for record in records
    ]

    assert projected == list(EXPECTED_COLLECTION_ROWS)
    assert (
        records[1].evaluation_result.metric_normalization["metrics"][
            "overfit_safe_exact_rate"
        ]["scale_applied"]
        == "percent_string"
    )
    assert (
        records[1].evaluation_result.metric_normalization["metrics"][
            "robust_exact_rate"
        ]["scale_applied"]
        == "percent_numeric"
    )
    assert records[1].evaluation_result.metric_normalization["metrics"]["dev_test_gap"][
        "comparable_value"
    ] == pytest.approx(0.97)
