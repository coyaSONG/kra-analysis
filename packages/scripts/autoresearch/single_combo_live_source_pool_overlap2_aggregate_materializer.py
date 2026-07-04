"""Materialize or strictly block live source-pool overlap2 aggregate source."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_overlap2_aggregate_selector_diagnostic as overlap,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_source_meta_extension_prior_date_selector_diagnostic as source_meta,
)
from autoresearch import (  # noqa: E402
    single_combo_live_all_allowed_source_pool_ranker_prior_date_materializer as source_pool_live,
)
from autoresearch import (  # noqa: E402
    single_combo_source_pool_overlap2_aggregate_train_surface as train_surface,
)
from autoresearch.clean_release_row_feature_rank_pattern_probe import (  # noqa: E402
    _build_rank_and_hit_caches,
    _race_rows,
)

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_overlap2_aggregate_selector_"
    "after_source_meta_extension_prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_all_allowed_source_pool_ranker_source_meta_extension_after_variant_calibration_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_all_allowed_source_pool_overlap2_aggregate_after_source_meta_extension_predictions.json"
)
DEFAULT_TRAIN_SURFACE = (
    DEFAULT_CACHE_DIR
    / "single_combo_source_pool_overlap2_aggregate_after_source_meta_extension_prior_date_train_surface.json"
)

EXPECTED_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
LIVE_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
PARENT_ACTION = "port_locked_best_source_pool_overlap2_aggregate_source_to_live_runner"
CHILD_ACTION = (
    "port_locked_best_source_pool_source_meta_extension_source_to_live_runner"
)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coverage_rate(coverage: dict[str, Any]) -> float | None:
    try:
        return float(coverage.get("coverage_rate"))
    except (TypeError, ValueError):
        return None


def _best_selector(source_target: dict[str, Any]) -> dict[str, Any]:
    best = _dict(source_target.get("best"))
    return {
        "candidate": best.get("candidate"),
        "selector_spec": best.get("selector_spec"),
        "selection_contract": source_target.get("selection_contract"),
        "source_artifact": source_target.get("source_artifact"),
        "window_diagnostics": [
            _dict(window).get("diagnostics")
            for window in _list(best.get("windows"))
            if isinstance(_dict(window).get("diagnostics"), dict)
        ],
    }


def _window_prediction_count(payload: dict[str, Any]) -> int:
    total = 0
    for window_payload in _dict(payload.get("predictions_by_window")).values():
        total += len(_dict(window_payload))
    return total


def _source_context(path: Path) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    selection_contract = payload.get("selection_contract")
    source_selection_contract = (
        payload.get("source_selection_contract") or selection_contract
    )
    predicted_count = _int(coverage.get("predicted_race_count"))
    if predicted_count is None:
        predicted_count = _window_prediction_count(payload)
    status = "missing"
    if path.exists():
        if (
            payload.get("status") == "passed"
            and source_selection_contract == LIVE_SOURCE_SELECTION_CONTRACT
            and _coverage_rate(coverage) == 1.0
            and predicted_count > 0
        ):
            status = "passed"
        else:
            status = "failed"
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": payload.get("status"),
        "selection_contract": selection_contract,
        "source_selection_contract": source_selection_contract,
        "expected_source_selection_contract": LIVE_SOURCE_SELECTION_CONTRACT,
        "coverage": coverage,
        "predicted_race_count": predicted_count,
        "contract_match": source_selection_contract == LIVE_SOURCE_SELECTION_CONTRACT,
        "diagnostic_only": payload.get("diagnostic_only"),
        "counts_as_70_percent_evidence": payload.get("counts_as_70_percent_evidence"),
        "recommended_next_action": payload.get("recommended_next_action"),
        "blocked_reason": payload.get("blocked_reason"),
    }


def _candidate_context(path: Path) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    expected = _int(coverage.get("expected_race_count")) or 0
    candidate_count = _int(coverage.get("candidate_race_count")) or 0
    missing = _list(coverage.get("missing_race_ids"))
    current_candidates = _dict(payload.get("current_candidates_by_race"))
    live_records = _list(payload.get("live_records"))
    status = "missing"
    if path.exists():
        status = (
            "passed"
            if payload.get("status") == "passed"
            and expected > 0
            and candidate_count == expected
            and not missing
            and len(current_candidates) == expected
            and len(live_records) == expected
            else "failed"
        )
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": payload.get("status"),
        "coverage": coverage,
        "current_candidate_race_count": len(current_candidates),
        "live_record_count": len(live_records),
        "source_signal_window": payload.get("source_signal_window"),
        "target_dataset_path": payload.get("target_dataset_path"),
        "train_replay_contract": payload.get("train_replay_contract"),
    }


def _race_ids(candidate_context: dict[str, Any]) -> list[str]:
    coverage = _dict(candidate_context.get("coverage"))
    return [str(race_id) for race_id in _list(coverage.get("race_ids"))]


def _load_training_state(
    *,
    train_surface_path: Path,
    live_race_ids: list[str],
) -> dict[str, Any]:
    surface_payload = _dict(_read_json(train_surface_path))
    source_group_name = str(surface_payload.get("source_group_spec") or "")
    selector_spec_name = str(surface_payload.get("selector_spec") or "")
    if not source_group_name or not selector_spec_name:
        raise ValueError("train surface is missing source_group_spec or selector_spec")
    source_group, selector_spec = train_surface._resolve_specs(
        selector_spec_name=selector_spec_name,
        source_group_spec_name=source_group_name,
    )
    selected_window = source_pool_live._selected_train_window(
        surface_payload,
        live_min_date=source_pool_live._live_min_date(live_race_ids),
    )
    if selected_window is None:
        raise ValueError("no frozen train window ends before the live race date")

    row_cache_path = source_pool_live._resolve_path(surface_payload["row_cache"])
    source_payload = train_surface._read_json(
        source_pool_live._resolve_path(surface_payload["source_artifact"])
    )
    answers_by_window, _window_context, row_cache = (
        train_surface._train_answers_by_window(
            config_path=overlap.base.DEFAULT_CONFIG,
            row_cache_path=row_cache_path,
        )
    )
    source_train = train_surface._load_train_predictions(source_payload)
    answers = _dict(answers_by_window.get(selected_window))
    source_predictions = source_train.get(selected_window)
    if not answers or source_predictions is None:
        raise ValueError(f"missing frozen train inputs for window: {selected_window}")

    rows = row_cache["rows"]
    rows_by_race = _race_rows(rows)
    train_race_ids = tuple(
        sorted(race_id for race_id in answers if race_id in rows_by_race)
    )
    race_index_by_id = {
        race_id: index for index, race_id in enumerate(train_race_ids)
    }
    feature_names = tuple(
        str(name)
        for name in (
            surface_payload.get("feature_names")
            or overlap.base.vote._available_all_allowed_features(rows)
        )
    )
    patterns = tuple(itertools.combinations(range(1, 11), 3))
    ranked_cache, hit_cache = _build_rank_and_hit_caches(
        rows_by_race=rows_by_race,
        race_ids=train_race_ids,
        answers={
            str(race_id): list(answer[:3])
            for race_id, answer in answers.items()
        },
        features=feature_names,
        patterns=patterns,
    )
    completed_race_ids = sorted(
        race_id
        for race_id in answers
        if race_id in source_predictions and race_id in race_index_by_id
    )
    train_indices = [race_index_by_id[race_id] for race_id in completed_race_ids]
    sources = overlap.base.vote._selected_sources(
        hit_cache=hit_cache,
        train_indices=train_indices,
        patterns=patterns,
        source_count=source_group.source_count,
        metric=source_group.metric,
    )
    return {
        "feature_names": feature_names,
        "selected_train_window": selected_window,
        "selector_spec": selector_spec,
        "source_count": len(sources),
        "source_group": source_group,
        "sources": sources,
        "surface_payload": surface_payload,
        "train_race_count": len(completed_race_ids),
    }


def _predict_live_window(
    *,
    race_ids: list[str],
    current_best_predictions: dict[str, tuple[int, int, int]],
    live_rows_by_race: dict[str, list[dict[str, Any]]],
    train_state: dict[str, Any],
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    source_group = train_state["source_group"]
    selector_spec = train_state["selector_spec"]
    sources = train_state["sources"]
    live_ranked_cache = source_pool_live._live_ranked_cache(
        rows_by_race=live_rows_by_race,
        feature_names=train_state["feature_names"],
    )
    fallback_predictions = {
        race_id: current_best_predictions[race_id]
        for race_id in race_ids
        if race_id in current_best_predictions
    }
    eval_rows_by_race = {
        race_id: source_meta._source_meta_candidate_rows_for_race(
            race_id=race_id,
            race_rows=live_rows_by_race.get(race_id, []),
            sources=sources,
            ranked_cache=live_ranked_cache,
            spec=source_group,
            answer=None,
            fallback_combo=fallback_combo,
        )
        for race_id, fallback_combo in fallback_predictions.items()
    }
    selected, selection_diagnostics = overlap._select_overlap2_predictions(
        rows_by_race=eval_rows_by_race,
        fallback_predictions=fallback_predictions,
        source_group=source_group,
        spec=selector_spec,
    )
    candidate_counts = [
        float(len(eval_rows_by_race.get(race_id, []))) for race_id in race_ids
    ]
    predictions = {race_id: list(combo) for race_id, combo in sorted(selected.items())}
    diagnostics = {
        "avg_candidate_row_count": round(
            sum(candidate_counts) / max(len(candidate_counts), 1),
            3,
        ),
        "feature_contract": "source_pool_overlap2_aggregate_live_rows_no_answer",
        "history_update": "completed_frozen_train_dates_only_no_live_label_updates",
        "live_answer_sentinel_used_for_feature_shape_only": True,
        "missing_fallback_prediction_race_ids": sorted(
            set(race_ids) - set(fallback_predictions)
        ),
        "selected_score_mean": round(
            float(selection_diagnostics.get("selected_score_mean", 0.0)),
            6,
        ),
        "selected_train_window": train_state["selected_train_window"],
        "selection_uses_labels": False,
        "selection_uses_live_labels": False,
        "selector": f"{source_group.name}/{selector_spec.name}",
        "selector_spec": selector_spec.name,
        "source_count": train_state["source_count"],
        "source_group_spec": source_group.name,
        "switch_rate": round(float(selection_diagnostics.get("switch_rate", 0.0)), 6),
        "switched_exact_rate_available": False,
        "train_race_count": train_state["train_race_count"],
    }
    return predictions, diagnostics


def _recommended_next_action(
    *,
    live_source_context: dict[str, Any],
    candidate_status: str,
    status: str,
    train_surface_status: str,
) -> dict[str, Any]:
    if live_source_context.get("status") != "passed":
        child_recommended = _dict(live_source_context.get("recommended_next_action"))
        child_action = child_recommended.get("action")
        if isinstance(child_action, str) and child_action:
            return {
                "action": child_action,
                "blocking": bool(child_recommended.get("blocking", False)),
                "classification": child_recommended.get(
                    "classification", "background_modeling_candidate"
                ),
                "queue_priority_score": float(
                    child_recommended.get("queue_priority_score", 94.8)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The required source-meta extension source reported a downstream live-port dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.8,
            "reason": (
                "The source-pool overlap2 aggregate live source cannot emit "
                "predictions until the all-allowed source-pool ranker "
                "source-meta-extension after variant-calibration source is "
                "materialized with the exact contract."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_source_pool_overlap2_aggregate_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.78,
            "reason": (
                "The overlap2 aggregate selector needs complete live full-combo "
                "candidate features and live records before prediction logic can run."
            ),
        }
    if train_surface_status != "passed":
        return {
            "action": "repair_source_pool_overlap2_aggregate_train_surface_before_live_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.77,
            "reason": (
                "The live scorer needs the frozen source-pool overlap2 aggregate "
                "train surface to rebuild the prior-date source selection."
            ),
        }
    if status == "passed":
        return {
            "action": "materialize_locked_best_source_pool_ranker_overlap2_from_passed_overlap2_aggregate",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.75,
            "reason": (
                "The source-pool overlap2 aggregate emitted complete pre-race "
                "live predictions; proceed to the source-pool ranker parent."
            ),
        }
    return {
        "action": "implement_locked_best_source_pool_overlap2_aggregate_prediction_logic",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.76,
        "reason": (
            "The source-meta-extension fallback source is present; implement "
            "pre-race overlap2 aggregate scoring without active labels."
        ),
    }


def build_artifact(
    *,
    source_target_path: Path = DEFAULT_SOURCE_TARGET,
    live_source_path: Path = DEFAULT_LIVE_SOURCE,
    candidate_features_path: Path = DEFAULT_CANDIDATE_FEATURES,
    train_surface_path: Path = DEFAULT_TRAIN_SURFACE,
) -> dict[str, Any]:
    source_target = _dict(_read_json(source_target_path))
    selector = _best_selector(source_target)
    source_context = _source_context(live_source_path)
    candidate_context = _candidate_context(candidate_features_path)
    candidate_coverage = _dict(candidate_context.get("coverage"))
    expected_race_count = _int(candidate_coverage.get("expected_race_count")) or 0
    race_ids = _race_ids(candidate_context)
    train_surface_exists = train_surface_path.exists()
    train_surface_status = "passed" if train_surface_exists else "missing"
    if (
        source_context["status"] != "passed"
        and source_context.get("exists")
        and _dict(source_context.get("recommended_next_action")).get("action")
    ):
        status = "blocked_live_source_child_dependency"
    elif source_context["status"] != "passed":
        status = "blocked_missing_live_source_artifact"
    elif candidate_context["status"] != "passed":
        status = "blocked_incomplete_live_candidate_features"
    elif train_surface_status != "passed":
        status = "blocked_missing_source_pool_overlap2_aggregate_train_surface"
    else:
        status = "blocked_pending_source_pool_overlap2_aggregate_prediction_logic"
    coverage = {
        "status": "blocked",
        "expected_race_count": expected_race_count,
        "predicted_race_count": 0,
        "coverage_rate": 0.0 if expected_race_count else None,
        "missing_race_ids": race_ids,
        "race_ids": race_ids,
    }
    predictions_by_window: dict[str, dict[str, list[int]]] = {}
    live_prediction_diagnostics: dict[str, Any] = {}
    if status == "blocked_pending_source_pool_overlap2_aggregate_prediction_logic":
        live_source_payload = _dict(_read_json(live_source_path))
        output_window, fallback_predictions = source_pool_live._flatten_simple_predictions(
            live_source_payload
        )
        candidate_payload = _dict(_read_json(candidate_features_path))
        live_rows_by_race = source_pool_live._live_rows_by_race_from_candidate_payload(
            candidate_payload,
            expected_race_ids=race_ids,
        )
        missing_live_rows = sorted(set(race_ids) - set(live_rows_by_race))
        if missing_live_rows:
            status = "blocked_incomplete_live_candidate_features"
            live_prediction_diagnostics = {
                "missing_live_row_cache_race_ids": missing_live_rows,
            }
        else:
            train_state = _load_training_state(
                train_surface_path=train_surface_path,
                live_race_ids=race_ids,
            )
            predicted, live_prediction_diagnostics = _predict_live_window(
                race_ids=race_ids,
                current_best_predictions=fallback_predictions,
                live_rows_by_race=live_rows_by_race,
                train_state=train_state,
            )
            missing_race_ids = sorted(set(race_ids) - set(predicted))
            predictions_by_window = {output_window: predicted}
            coverage = {
                "status": "passed" if not missing_race_ids else "blocked",
                "expected_race_count": expected_race_count,
                "predicted_race_count": len(predicted),
                "coverage_rate": (
                    round(len(predicted) / expected_race_count, 6)
                    if expected_race_count
                    else None
                ),
                "missing_race_ids": missing_race_ids,
                "race_ids": race_ids,
            }
            status = (
                "passed" if not missing_race_ids else "blocked_incomplete_live_predictions"
            )
            live_prediction_diagnostics = {
                **live_prediction_diagnostics,
                "train_surface_path": str(train_surface_path),
                "train_surface_contract": _dict(
                    train_state.get("surface_payload")
                ).get("train_prediction_contract"),
            }
    recommended = _recommended_next_action(
        candidate_status=str(candidate_context.get("status")),
        live_source_context=source_context,
        status=status,
        train_surface_status=train_surface_status,
    )
    return {
        "format_version": "single-combo-live-source-pool-overlap2-aggregate-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": status != "passed",
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": "one_unordered_top3_combo_per_race",
        "source_selection_contract": selector.get("selection_contract"),
        "expected_source_selection_contract": EXPECTED_SOURCE_SELECTION_CONTRACT,
        "selector_spec": selector.get("selector_spec"),
        "source_target_artifact": str(source_target_path),
        "source_target_source_artifact": selector.get("source_artifact"),
        "live_source_context": source_context,
        "candidate_feature_context": candidate_context,
        "train_surface_context": {
            "path": str(train_surface_path),
            "exists": train_surface_exists,
            "status": train_surface_status,
        },
        "coverage": coverage,
        "predictions_by_window": predictions_by_window,
        "selector_diagnostics": {
            "selector": "overlap2_aggregate",
            "fallback_only": False,
            "source_must_be_materialized_before_scoring": True,
            "prediction_logic_pending_after_source_materialization": (
                status
                == "blocked_pending_source_pool_overlap2_aggregate_prediction_logic"
            ),
            "selection_uses_live_labels": False,
            "live_prediction_diagnostics": live_prediction_diagnostics,
            "window_diagnostics": selector.get("window_diagnostics"),
        },
        "recommended_next_action": recommended,
        "policy": {
            "overlap2_aggregate_must_not_be_treated_as_pass_through": True,
            "do_not_substitute_champion_clean_top3_for_locked_source": True,
            "diagnostic_shadow_substitution_must_not_unblock_locked_parent": True,
            "required_source_must_be_materialized_before_prediction": True,
            "active_live_labels_must_not_be_used": True,
            "prior_date_history_must_not_include_current_or_future_labels": True,
            "same_day_result_history_updates_without_contract_forbidden": True,
            "counts_as_70_percent_evidence": False,
        },
        "blocked_reason": None if status == "passed" else recommended["reason"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-target", type=Path, default=DEFAULT_SOURCE_TARGET)
    parser.add_argument("--live-source", type=Path, default=DEFAULT_LIVE_SOURCE)
    parser.add_argument(
        "--candidate-features",
        type=Path,
        default=DEFAULT_CANDIDATE_FEATURES,
    )
    parser.add_argument("--train-surface", type=Path, default=DEFAULT_TRAIN_SURFACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_artifact(
        candidate_features_path=args.candidate_features,
        live_source_path=args.live_source,
        source_target_path=args.source_target,
        train_surface_path=args.train_surface,
    )
    payload["output_path"] = str(args.output)
    _write_json(args.output, payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "recommended_next_action": payload["recommended_next_action"]["action"],
                "status": payload["status"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
