"""Collect random-split exploration outputs into detailed seed result records."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.execution_matrix import SeedExecutionMetrics, build_model_config_id
from shared.seed_metric_normalization import (
    DEFAULT_SEED_METRIC_NAMES,
    build_metric_normalization_snapshot,
    normalize_metric_mapping,
    normalize_metric_value,
)
from shared.seed_result_recording import (
    DetailedSeedResultArtifacts,
    DetailedSeedResultRecord,
    EvaluationOutcomeSnapshot,
    SearchParametersSnapshot,
    SeedContextSnapshot,
    SplitSettingsSnapshot,
)

RESULT_ARTIFACT_ID = "clean_research"
SOURCE_KIND = "ralph-random-split-run-v1"
SEED_LOOKUP_PATHS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("parameter_context", "runtime_params", "model_random_state"),
        "parameter_context.runtime_params.model_random_state",
    ),
    (
        ("parameter_context", "model_parameters", "random_state"),
        "parameter_context.model_parameters.random_state",
    ),
    (("runtime_params", "model_random_state"), "runtime_params.model_random_state"),
    (("seeds", "model_random_state"), "seeds.model_random_state"),
    (("seed",), "seed"),
    (("model", "random_state"), "model.random_state"),
)


@dataclass(frozen=True, slots=True)
class _RecordDraft:
    run_id: str
    task_id: str
    seed: int
    seed_source: str
    run_at: datetime
    model_config_id: str
    split_settings: SplitSettingsSnapshot
    search_parameters: SearchParametersSnapshot
    evaluation_result: EvaluationOutcomeSnapshot
    artifacts: DetailedSeedResultArtifacts
    evaluation_seeds: tuple[int, ...]
    selection_seed_invariant: bool | None


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def _read_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return _read_json(path)


def _nested_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _int_or_none(value: Any) -> int | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _datetime_or_none(value: Any) -> datetime | None:
    if value in ("", None):
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _extract_core_metrics(result_payload: dict[str, Any]) -> SeedExecutionMetrics:
    summary = (
        result_payload.get("summary")
        if isinstance(result_payload.get("summary"), dict)
        else {}
    )
    dev = (
        result_payload.get("dev") if isinstance(result_payload.get("dev"), dict) else {}
    )
    test = (
        result_payload.get("test")
        if isinstance(result_payload.get("test"), dict)
        else {}
    )
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


def _extract_overall_holdout_hit_rate(
    result_payload: dict[str, Any],
    metrics: SeedExecutionMetrics,
) -> tuple[float, str]:
    summary = (
        result_payload.get("summary")
        if isinstance(result_payload.get("summary"), dict)
        else {}
    )
    test = (
        result_payload.get("test")
        if isinstance(result_payload.get("test"), dict)
        else {}
    )
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
        return metrics.test_exact_3of3_rate, "test.exact_3of3_rate"
    raise ValueError("Unable to resolve overall holdout hit rate from result payload.")


def _build_metric_normalization_payload(
    result_payload: dict[str, Any],
    *,
    overall_holdout_hit_rate: float,
    overall_holdout_hit_rate_source: str,
) -> dict[str, Any]:
    summary = (
        result_payload.get("summary")
        if isinstance(result_payload.get("summary"), dict)
        else {}
    )
    dev = (
        result_payload.get("dev") if isinstance(result_payload.get("dev"), dict) else {}
    )
    test = (
        result_payload.get("test")
        if isinstance(result_payload.get("test"), dict)
        else {}
    )
    snapshot = build_metric_normalization_snapshot(
        {
            "overall_holdout_hit_rate": overall_holdout_hit_rate,
            "overfit_safe_exact_rate": summary.get("overfit_safe_exact_rate"),
            "robust_exact_rate": summary.get("robust_exact_rate"),
            "blended_exact_rate": summary.get("blended_exact_rate"),
            "rolling_min_exact_rate": summary.get("rolling_min_exact_rate"),
            "rolling_mean_exact_rate": summary.get("rolling_mean_exact_rate"),
            "dev_test_gap": summary.get("dev_test_gap"),
            "dev_exact_3of3_rate": dev.get("exact_3of3_rate"),
            "dev_avg_set_match": dev.get("avg_set_match"),
            "test_exact_3of3_rate": test.get("exact_3of3_rate"),
            "test_avg_set_match": test.get("avg_set_match"),
        },
        metric_names=DEFAULT_SEED_METRIC_NAMES,
    )
    snapshot["overall_holdout_hit_rate_source"] = overall_holdout_hit_rate_source
    return snapshot


def _extract_evaluation_seeds(result_payload: dict[str, Any]) -> tuple[int, ...]:
    raw = (
        _nested_get(result_payload, ("parameter_context", "evaluation_seeds"))
        or _nested_get(result_payload, ("config", "experiment", "evaluation_seeds"))
        or ()
    )
    if not isinstance(raw, (list, tuple)):
        return ()
    resolved: list[int] = []
    for item in raw:
        seed = _int_or_none(item)
        if seed is None:
            return ()
        resolved.append(seed)
    return tuple(resolved)


def _extract_seed(
    *,
    run_id: str,
    task_id: str,
    run_path: Path,
    result_payload: dict[str, Any],
    seed_overrides: Mapping[str, int] | None,
) -> tuple[int, str]:
    if seed_overrides:
        for key in (run_id, task_id, run_path.stem, str(run_path)):
            if key in seed_overrides:
                return int(seed_overrides[key]), f"seed_overrides[{key}]"

    for path, source in SEED_LOOKUP_PATHS:
        resolved = _int_or_none(_nested_get(result_payload, path))
        if resolved is not None:
            return resolved, source

    raise ValueError(
        "Unable to resolve seed for random split result. "
        f"run_id={run_id} path={run_path}"
    )


def _source_metadata(
    *,
    run_path: Path,
    run_payload: dict[str, Any],
    decision_path: Path | None,
    decision_payload: dict[str, Any] | None,
    propose_log_path: Path | None,
    propose_log_payload: dict[str, Any] | None,
    run_log_path: Path | None,
    artifact_path: Path,
) -> dict[str, Any]:
    mutation = (
        propose_log_payload.get("mutation")
        if isinstance(propose_log_payload, dict)
        else []
    )
    if not isinstance(mutation, list):
        mutation = []
    return {
        "source_kind": SOURCE_KIND,
        "run_path": str(run_path),
        "decision_path": str(decision_path) if decision_path is not None else None,
        "propose_log_path": str(propose_log_path)
        if propose_log_path is not None
        else None,
        "run_log_path": str(run_log_path) if run_log_path is not None else None,
        "artifact_path": str(artifact_path),
        "run_status": run_payload.get("status"),
        "run_phase": run_payload.get("phase"),
        "decision_outcome": decision_payload.get("outcome")
        if isinstance(decision_payload, dict)
        else None,
        "decision_reason": decision_payload.get("reason")
        if isinstance(decision_payload, dict)
        else None,
        "metric_id": _nested_get(
            run_payload, ("metrics", "dev_exact_rate", "metricId")
        ),
        "metric_direction": _nested_get(
            run_payload, ("metrics", "dev_exact_rate", "direction")
        ),
        "metric_value": _nested_get(
            run_payload, ("metrics", "dev_exact_rate", "value")
        ),
        "manifest_hash": run_payload.get("manifestHash"),
        "workspace_ref": run_payload.get("workspaceRef"),
        "proposal_summary": _nested_get(run_payload, ("proposal", "summary")),
        "mutation": [str(item) for item in mutation],
    }


def _build_draft(
    run_path: Path,
    *,
    seed_overrides: Mapping[str, int] | None,
) -> _RecordDraft:
    run_payload = _read_json(run_path)
    run_id = str(run_payload.get("runId") or run_path.stem)
    task_id = str(run_payload.get("candidateId") or run_id)

    artifacts = run_payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError(f"artifacts list missing in {run_path}")
    artifact_payload = next(
        (
            item
            for item in artifacts
            if isinstance(item, dict)
            and item.get("id") == RESULT_ARTIFACT_ID
            and item.get("path")
        ),
        None,
    )
    if artifact_payload is None:
        raise ValueError(f"{RESULT_ARTIFACT_ID} artifact missing in {run_path}")

    artifact_path = Path(str(artifact_payload["path"]))
    result_payload = _read_json(artifact_path)
    decision_id = run_payload.get("decisionId")
    decision_path = (
        run_path.parents[1] / "decisions" / f"{decision_id}.json"
        if isinstance(decision_id, str) and decision_id
        else None
    )
    decision_payload = _read_optional_json(decision_path)

    logs_payload = (
        run_payload.get("logs") if isinstance(run_payload.get("logs"), dict) else {}
    )
    propose_log_path = (
        Path(str(logs_payload["proposeStdoutPath"]))
        if logs_payload.get("proposeStdoutPath")
        else None
    )
    run_log_path = (
        Path(str(logs_payload["runStdoutPath"]))
        if logs_payload.get("runStdoutPath")
        else None
    )
    propose_log_payload = _read_optional_json(propose_log_path)

    metrics = _extract_core_metrics(result_payload)
    overall_holdout_hit_rate, hit_rate_source = _extract_overall_holdout_hit_rate(
        result_payload,
        metrics,
    )
    seed, seed_source = _extract_seed(
        run_id=run_id,
        task_id=task_id,
        run_path=run_path,
        result_payload=result_payload,
        seed_overrides=seed_overrides,
    )
    evaluation_seeds = _extract_evaluation_seeds(result_payload)
    config_payload = (
        result_payload.get("config")
        if isinstance(result_payload.get("config"), dict)
        else {}
    )
    experiment_payload = (
        config_payload.get("experiment")
        if isinstance(config_payload.get("experiment"), dict)
        else {}
    )
    model_search_payload = (
        experiment_payload.get("model_search")
        if isinstance(experiment_payload.get("model_search"), dict)
        else {}
    )
    common_hyperparameters = (
        experiment_payload.get("common_hyperparameters")
        if isinstance(experiment_payload.get("common_hyperparameters"), dict)
        else {}
    )
    result_model = (
        result_payload.get("model")
        if isinstance(result_payload.get("model"), dict)
        else {}
    )
    config_notes = (
        config_payload.get("notes")
        if isinstance(config_payload.get("notes"), dict)
        else {}
    )
    resolved_model_parameters = dict(result_model)
    resolved_model_parameters["features"] = list(config_payload.get("features") or ())
    resolved_model_parameters["feature_count"] = _int_or_none(
        result_payload.get("feature_count")
    )
    resolved_model_parameters["market_feature_count"] = _int_or_none(
        result_payload.get("market_feature_count")
    )
    if config_notes:
        resolved_model_parameters["notes"] = dict(config_notes)

    source_metadata = _source_metadata(
        run_path=run_path,
        run_payload=run_payload,
        decision_path=decision_path,
        decision_payload=decision_payload,
        propose_log_path=propose_log_path,
        propose_log_payload=propose_log_payload,
        run_log_path=run_log_path,
        artifact_path=artifact_path,
    )
    evaluation_contract = (
        dict(config_payload.get("evaluation_contract"))
        if isinstance(config_payload.get("evaluation_contract"), dict)
        else {}
    )
    evaluation_contract["source_metadata"] = source_metadata

    candidate_name = str(config_notes.get("last_mutation") or task_id)
    proposal_summary = _nested_get(run_payload, ("proposal", "summary"))
    candidate_descriptor = {
        "candidate_id": task_id,
        "candidate_name": candidate_name,
        "proposal_summary": proposal_summary,
        "mutation": source_metadata["mutation"],
        "status": run_payload.get("status"),
    }

    split_settings = SplitSettingsSnapshot(
        dataset=str(
            config_payload.get("dataset") or result_payload.get("dataset") or "unknown"
        ),
        split=dict(result_payload.get("split") or config_payload.get("split") or {}),
        rolling_windows=tuple(
            dict(item)
            for item in (config_payload.get("rolling_windows") or ())
            if isinstance(item, dict)
        ),
        evaluation_contract=evaluation_contract,
        input_data=dict(experiment_payload.get("input_data") or {}),
        selected_run_id=run_id,
    )
    search_parameters = SearchParametersSnapshot(
        experiment_profile_version=experiment_payload.get("profile_version"),
        repeat_count=_int_or_none(experiment_payload.get("repeat_count")),
        evaluation_seeds=evaluation_seeds,
        model_search_strategy=str(
            model_search_payload.get("strategy")
            or _nested_get(run_payload, ("proposal", "proposerType"))
            or SOURCE_KIND
        ),
        candidate_names=(candidate_name,),
        candidate_count=1,
        model_candidates=(candidate_descriptor,),
        common_hyperparameters={
            **dict(common_hyperparameters),
            "seed_source": seed_source,
        },
        resolved_model_parameters=resolved_model_parameters,
        parameter_source="ralph.run_meta",
        model_parameter_source="artifact.config.model",
    )

    run_at = (
        _datetime_or_none(run_payload.get("endedAt"))
        or _datetime_or_none(run_payload.get("startedAt"))
        or datetime.fromtimestamp(artifact_path.stat().st_mtime).astimezone()
    )
    model_config_id = build_model_config_id(
        config_payload or result_model or str(artifact_path)
    )
    return _RecordDraft(
        run_id=run_id,
        task_id=task_id,
        seed=seed,
        seed_source=seed_source,
        run_at=run_at,
        model_config_id=model_config_id,
        split_settings=split_settings,
        search_parameters=search_parameters,
        evaluation_result=EvaluationOutcomeSnapshot(
            summary=dict(result_payload.get("summary") or {}),
            dev=dict(result_payload.get("dev") or {})
            if result_payload.get("dev") is not None
            else None,
            test=dict(result_payload.get("test") or {})
            if result_payload.get("test") is not None
            else None,
            core_metrics=metrics,
            overall_holdout_hit_rate=overall_holdout_hit_rate,
            overall_holdout_hit_rate_source=hit_rate_source,
            metric_normalization=_build_metric_normalization_payload(
                result_payload,
                overall_holdout_hit_rate=overall_holdout_hit_rate,
                overall_holdout_hit_rate_source=hit_rate_source,
            ),
        ),
        artifacts=DetailedSeedResultArtifacts(
            output_path=str(artifact_path),
            manifest_path=str(run_path),
            config_path=str(result_payload.get("config_path"))
            if result_payload.get("config_path")
            else None,
        ),
        evaluation_seeds=evaluation_seeds,
        selection_seed_invariant=_nested_get(
            config_payload, ("evaluation_contract", "selection_seed_invariant")
        ),
    )


def _resolve_seed_order(drafts: tuple[_RecordDraft, ...]) -> tuple[int, ...]:
    seeds = [draft.seed for draft in drafts]
    if len(seeds) != len(set(seeds)):
        raise ValueError(
            "Duplicate seeds detected while collecting random split results."
        )

    candidate_orders = [
        draft.evaluation_seeds for draft in drafts if draft.evaluation_seeds
    ]
    if candidate_orders:
        first = candidate_orders[0]
        for order in candidate_orders[1:]:
            if order != first:
                raise ValueError(
                    "Inconsistent evaluation_seeds detected across result files."
                )
        ordered = tuple(seed for seed in first if seed in set(seeds))
        extras = tuple(sorted(seed for seed in seeds if seed not in set(ordered)))
        return ordered + extras

    return tuple(sorted(seeds))


def collect_detailed_records_from_ralph_runs(
    run_paths: Iterable[Path | str],
    *,
    seed_overrides: Mapping[str, int] | None = None,
) -> tuple[DetailedSeedResultRecord, ...]:
    drafts = tuple(
        _build_draft(Path(run_path), seed_overrides=seed_overrides)
        for run_path in sorted(Path(path) for path in run_paths)
    )
    seed_order = _resolve_seed_order(drafts)
    index_by_seed = {seed: index for index, seed in enumerate(seed_order, start=1)}
    records = [
        DetailedSeedResultRecord(
            run_id=draft.run_id,
            task_id=draft.task_id,
            seed=draft.seed,
            seed_index=index_by_seed[draft.seed],
            run_at=draft.run_at,
            model_config_id=draft.model_config_id,
            split_settings=draft.split_settings,
            search_parameters=draft.search_parameters,
            seed_context=SeedContextSnapshot(
                run_id=draft.run_id,
                seed_index=index_by_seed[draft.seed],
                model_random_state=draft.seed,
                evaluation_seeds=draft.evaluation_seeds,
                parameter_source=draft.seed_source,
                selection_seed_invariant=draft.selection_seed_invariant,
            ),
            evaluation_result=draft.evaluation_result,
            artifacts=draft.artifacts,
        )
        for draft in drafts
    ]
    return tuple(
        sorted(records, key=lambda item: (item.seed_index, item.seed, item.run_id))
    )


def discover_ralph_run_paths(runs_dir: Path | str) -> tuple[Path, ...]:
    return tuple(sorted(Path(runs_dir).glob("run-*.json")))


def _load_seed_overrides(path: Path | None) -> dict[str, int]:
    if path is None:
        return {}
    payload = _read_json(path)
    resolved: dict[str, int] = {}
    for key, value in payload.items():
        seed = _int_or_none(value)
        if seed is None:
            raise ValueError(f"seed override must be an integer: {key}={value!r}")
        resolved[str(key)] = seed
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs-dir", required=True, help="Directory containing ralph run-*.json files."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Where to write collected DetailedSeedResultRecord payloads.",
    )
    parser.add_argument(
        "--seed-overrides",
        help="Optional JSON file mapping run ids or candidate ids to numeric seeds for legacy outputs.",
    )
    args = parser.parse_args()

    run_paths = discover_ralph_run_paths(args.runs_dir)
    if not run_paths:
        raise SystemExit(f"No run-*.json files found in {args.runs_dir}")

    records = collect_detailed_records_from_ralph_runs(
        run_paths,
        seed_overrides=_load_seed_overrides(Path(args.seed_overrides))
        if args.seed_overrides
        else None,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            [record.model_dump(mode="json") for record in records],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
