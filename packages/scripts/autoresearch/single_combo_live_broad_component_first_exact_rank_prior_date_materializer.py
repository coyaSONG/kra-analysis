"""Strict live materializer for broad-component first-exact rank selector."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_first_exact_rank_prior_date_selector_diagnostic as selector_base,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_gain_loss_prior_date_selector_diagnostic as gain_loss,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_prior_date_selector_diagnostic as broad_selector,
)
from autoresearch import (  # noqa: E402
    single_combo_broad_component_first_exact_rank_prior_date_train_surface as train_surface,
)
from autoresearch.single_combo_live_row_cache_rank_pattern_prior_date_materializer import (  # noqa: E501
    DEFAULT_CACHE_DIR,
    LIVE_SOURCE_SELECTION_CONTRACT,
    _best_selector,
    _candidate_context,
    _candidate_race_ids,
    _dict,
    _int,
    _read_json,
    _source_context,
    _write_json,
)

DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_first_exact_rank_prior_date_"
    "selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_frontier_artifact_combo_prior_date_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_LIVE_BROAD_COMPONENTS = (
    DEFAULT_CACHE_DIR / "single_combo_live_broad_component_predictions.json"
)
DEFAULT_TRAIN_SURFACE = (
    DEFAULT_CACHE_DIR
    / "single_combo_broad_component_first_exact_rank_prior_date_train_surface.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_broad_component_first_exact_rank_prior_date_predictions.json"
)

PARENT_ACTION = (
    "port_locked_best_broad_component_first_exact_rank_prior_date_source_to_live_runner"
)
CHILD_ACTION = (
    "port_locked_best_frontier_artifact_combo_prior_date_source_to_live_runner"
)
LIVE_BROAD_COMPONENT_SELECTION_CONTRACT = "live_broad_component_predictions_partial_no_answer"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _combo_key(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, list | tuple) or len(value) < 3:
        return None
    try:
        combo = tuple(sorted(int(item) for item in value[:3]))
    except (TypeError, ValueError):
        return None
    if len(set(combo)) != 3:
        return None
    return combo


def _flatten_simple_predictions(
    payload: dict[str, Any],
) -> tuple[str, dict[str, tuple[int, int, int]]]:
    flattened: dict[str, tuple[int, int, int]] = {}
    window_names: list[str] = []
    for window_name, window_payload in _dict(
        payload.get("predictions_by_window")
    ).items():
        if not isinstance(window_name, str):
            continue
        rows = _dict(window_payload)
        if not rows:
            continue
        window_names.append(window_name)
        for race_id, raw_combo in rows.items():
            if not isinstance(race_id, str):
                continue
            combo = _combo_key(raw_combo)
            if combo is not None:
                flattened[race_id] = combo
    if len(window_names) == 1:
        return window_names[0], flattened
    return "collector_live", flattened


def _live_broad_context(
    path: Path,
    *,
    expected_race_ids: list[str],
) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    predictions_by_window = _dict(payload.get("predictions_by_window"))
    prediction_windows = sorted(str(window) for window in predictions_by_window)
    component_predictions: dict[str, dict[str, tuple[int, int, int]]] = {}
    for window_payload in predictions_by_window.values():
        for component, race_predictions in _dict(window_payload).items():
            if not isinstance(component, str):
                continue
            rows = component_predictions.setdefault(component, {})
            for race_id, raw_combo in _dict(race_predictions).items():
                if not isinstance(race_id, str):
                    continue
                combo = _combo_key(raw_combo)
                if combo is not None:
                    rows[race_id] = combo
    expected_set = set(expected_race_ids)
    available_race_ids = sorted(
        {
            race_id
            for predictions in component_predictions.values()
            for race_id in predictions
        }
    )
    missing_race_ids = sorted(expected_set - set(available_race_ids))
    missing_components = _list(payload.get("missing_components"))
    status = "missing"
    if path.exists():
        status = (
            "passed"
            if payload.get("status") == "passed"
            and coverage.get("status") == "passed"
            and payload.get("selection_contract")
            == LIVE_BROAD_COMPONENT_SELECTION_CONTRACT
            and not missing_components
            and not missing_race_ids
            else "failed"
        )
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": payload.get("status"),
        "selection_contract": payload.get("selection_contract"),
        "expected_selection_contract": LIVE_BROAD_COMPONENT_SELECTION_CONTRACT,
        "contract_match": (
            payload.get("selection_contract") == LIVE_BROAD_COMPONENT_SELECTION_CONTRACT
        ),
        "coverage": coverage,
        "materialized_component_count": len(
            _list(payload.get("materialized_components"))
        ),
        "required_component_count": len(_list(payload.get("required_components"))),
        "missing_component_count": len(missing_components),
        "missing_components": missing_components,
        "prediction_windows": prediction_windows,
        "expected_race_ids": expected_race_ids,
        "available_race_ids": available_race_ids,
        "missing_race_ids": missing_race_ids,
    }


def _load_live_component_predictions(
    path: Path,
    *,
    component_names: tuple[str, ...],
    race_ids: list[str],
) -> dict[str, dict[str, tuple[int, int, int]]]:
    payload = _dict(_read_json(path))
    output: dict[str, dict[str, tuple[int, int, int]]] = {
        component: {} for component in component_names
    }
    race_id_set = set(race_ids)
    for window_payload in _dict(payload.get("predictions_by_window")).values():
        for component, race_predictions in _dict(window_payload).items():
            if component not in output:
                continue
            for race_id, raw_combo in _dict(race_predictions).items():
                if race_id not in race_id_set:
                    continue
                combo = _combo_key(raw_combo)
                if combo is not None:
                    output[str(component)][str(race_id)] = combo
    return output


def _resolve_path(path_value: Any, *, base_path: Path = DEFAULT_CACHE_DIR) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    if path.exists():
        return path
    return base_path.parent.parent / path


def _live_min_date(race_ids: list[str]) -> str:
    dates = [race_id[:8] for race_id in race_ids if len(race_id) >= 8]
    return min(dates) if dates else "99999999"


def _selected_train_window(
    surface_payload: dict[str, Any],
    *,
    live_min_date: str,
) -> str | None:
    candidates: list[tuple[str, str]] = []
    for row in _list(surface_payload.get("windows")):
        row_dict = _dict(row)
        name = row_dict.get("name")
        train_end = row_dict.get("train_end")
        if not isinstance(name, str) or not isinstance(train_end, str):
            continue
        if train_end < live_min_date:
            candidates.append((train_end, name))
    if not candidates:
        return None
    return sorted(candidates)[-1][1]


def _ranked_augmented_rows(
    *,
    raw_rows: list[dict[str, Any]],
    surface: selector_base.SurfaceSpec,
    component_count: int,
) -> list[dict[str, Any]]:
    score_spec = selector_base._score_spec_by_name()[surface.score_spec_name]
    ranked_rows = gain_loss._rank_surface_rows(
        rows=raw_rows,
        surface=gain_loss.SurfaceSpec(surface.score_spec_name, surface.top_k),
        score_spec=score_spec,
        component_count=component_count,
    )
    return gain_loss._augment_rows(ranked_rows)


def _build_training_state(
    *,
    answers: dict[str, list[int]],
    source_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    surface: selector_base.SurfaceSpec,
) -> tuple[list[dict[str, Any]], dict[str, broad_selector.SourceStats]]:
    source_stats: dict[str, broad_selector.SourceStats] = {}
    history_records: list[dict[str, Any]] = []
    race_ids = sorted(race_id for race_id in answers if race_id in source_predictions)
    for _date_value, date_race_ids in broad_selector._date_groups(race_ids):
        date_records: list[dict[str, Any]] = []
        pending_updates: list[tuple[str, tuple[int, int, int], tuple[int, int, int]]] = []
        for race_id in date_race_ids:
            answer = broad_selector._answer_combo(answers, race_id)
            current_best_combo = broad_selector._combo_key(source_predictions[race_id])
            raw_rows = broad_selector._candidate_rows_for_race(
                race_id=race_id,
                answer=answer,
                current_best_combo=current_best_combo,
                component_predictions=component_predictions,
                component_names=component_names,
                source_stats=source_stats,
            )
            if not raw_rows:
                continue
            rows = _ranked_augmented_rows(
                raw_rows=raw_rows,
                surface=surface,
                component_count=len(component_names),
            )
            date_records.append(
                {
                    "race_id": race_id,
                    "rows": rows,
                    "label": selector_base._label_for_rows(
                        rows,
                        rank_limit=surface.rank_limit,
                    ),
                }
            )
            pending_updates.append(
                (broad_selector.CURRENT_SOURCE, current_best_combo, answer)
            )
            for source_name in component_names:
                combo_raw = component_predictions.get(source_name, {}).get(race_id)
                if combo_raw is None:
                    continue
                pending_updates.append(
                    (source_name, broad_selector._combo_key(combo_raw), answer)
                )
        history_records.extend(date_records)
        for source_name, combo, answer in pending_updates:
            broad_selector._update_stats(
                stats=source_stats.setdefault(source_name, broad_selector.SourceStats()),
                combo=combo,
                answer=answer,
            )
    return history_records, source_stats


def _load_training_inputs(
    *,
    train_surface_path: Path,
    live_race_ids: list[str],
) -> tuple[
    dict[str, Any],
    str,
    tuple[str, ...],
    list[dict[str, Any]],
    dict[str, broad_selector.SourceStats],
]:
    surface_payload = _dict(_read_json(train_surface_path))
    selector_spec = str(surface_payload.get("selector_spec") or "")
    if not selector_spec:
        raise ValueError("train surface is missing selector_spec")
    surface, _model, _choice = train_surface._resolve_best_specs(selector_spec)
    selected_window = _selected_train_window(
        surface_payload,
        live_min_date=_live_min_date(live_race_ids),
    )
    if selected_window is None:
        raise ValueError("no frozen train window ends before the live race date")
    source_payload = train_surface._read_json(
        _resolve_path(surface_payload["source_artifact"])
    )
    component_payload = train_surface._read_json(
        _resolve_path(surface_payload["component_cache"])
    )
    source_train = train_surface._load_simple_train_predictions(source_payload)
    component_train = train_surface._load_json_train_predictions(component_payload)
    component_names = tuple(str(name) for name in component_payload["components"])
    answers_by_window, _window_context = train_surface._train_answers_by_window(
        config_path=selector_base.DEFAULT_CONFIG,
        cache_dir=selector_base.DEFAULT_CACHE_DIR,
    )
    answers = _dict(answers_by_window.get(selected_window))
    source_predictions = source_train.get(selected_window)
    component_predictions = component_train.get(selected_window)
    if not answers or source_predictions is None or component_predictions is None:
        raise ValueError(f"missing frozen train inputs for window: {selected_window}")
    history_records, source_stats = _build_training_state(
        answers=answers,
        source_predictions=source_predictions,
        component_predictions=component_predictions,
        component_names=component_names,
        surface=surface,
    )
    return (
        surface_payload,
        selected_window,
        component_names,
        history_records,
        source_stats,
    )


def _predict_live_window(
    *,
    race_ids: list[str],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    source_stats: dict[str, broad_selector.SourceStats],
    surface: selector_base.SurfaceSpec,
    model: selector_base.ModelSpec,
    choice: selector_base.ChoiceSpec,
    history_records: list[dict[str, Any]],
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    fit = selector_base._fit_model(
        history_records,
        component_names=component_names,
        surface=surface,
        spec=model,
    )
    predictions: dict[str, list[int]] = {}
    switch_values: list[float] = []
    selected_ranks: list[float] = []
    selected_probabilities: list[float] = []
    selected_scores: list[float] = []
    default_probabilities: list[float] = []
    positive_probabilities: list[float] = []
    candidate_row_counts: list[float] = []
    missing_candidate_rows: list[str] = []
    for race_id in sorted(race_ids):
        current_best_combo = current_best_predictions.get(race_id)
        if current_best_combo is None:
            continue
        raw_rows = broad_selector._candidate_rows_for_race(
            race_id=race_id,
            answer=(0, 0, 0),
            current_best_combo=current_best_combo,
            component_predictions=component_predictions,
            component_names=component_names,
            source_stats=source_stats,
        )
        if not raw_rows:
            missing_candidate_rows.append(race_id)
            continue
        rows = _ranked_augmented_rows(
            raw_rows=raw_rows,
            surface=surface,
            component_count=len(component_names),
        )
        default_row = next(row for row in rows if float(row["is_current_best"]) >= 1.0)
        by_rank = selector_base._ranked_rows_by_rank(rows)
        record = {"race_id": race_id, "rows": rows, "label": 0}
        vector = selector_base._record_vector(
            record,
            component_names=component_names,
            rank_limit=surface.rank_limit,
        )
        probabilities = selector_base._probabilities(
            fit=fit,
            vector=vector,
            rank_limit=surface.rank_limit,
        )
        selected_rank, selected_score, selected_probability = selector_base._choose_rank(
            probabilities=probabilities,
            rows=rows,
            spec=choice,
            rank_limit=surface.rank_limit,
        )
        selected_row = by_rank.get(selected_rank, default_row)
        selected_combo = broad_selector._combo_key(selected_row["combo"])
        predictions[race_id] = list(selected_combo)
        switch_values.append(float(selected_combo != current_best_combo))
        selected_ranks.append(float(selected_rank))
        selected_probabilities.append(selected_probability)
        selected_scores.append(selected_score)
        default_probabilities.append(probabilities.get(0, 0.0))
        positive_probabilities.append(
            sum(probabilities.get(rank, 0.0) for rank in range(1, surface.rank_limit + 1))
        )
        candidate_row_counts.append(float(len(rows)))
    diagnostics = {
        "selector": f"{model.name}/{choice.name}",
        "surface_spec": surface.name,
        "model_spec": model.name,
        "choice_spec": choice.name,
        "feature_contract": "current_best_broad_component_first_exact_rank_prior_date",
        "history_update": "completed_frozen_train_dates_only_no_live_label_updates",
        "selection_uses_labels": False,
        "selection_uses_live_labels": False,
        "live_answer_sentinel_used_for_feature_shape_only": True,
        "train_rows": fit.train_rows,
        "positive_rows": fit.positive_rows,
        "class_count": fit.class_count,
        "model_fitted": fit.fitted,
        "switch_rate": round(_safe_mean(switch_values), 6),
        "avg_selected_rank": round(_safe_mean(selected_ranks), 3),
        "avg_selected_probability": round(_safe_mean(selected_probabilities), 6),
        "avg_selected_score": round(_safe_mean(selected_scores), 6),
        "avg_default_probability": round(_safe_mean(default_probabilities), 6),
        "avg_positive_probability": round(_safe_mean(positive_probabilities), 6),
        "avg_candidate_row_count": round(_safe_mean(candidate_row_counts), 3),
        "missing_candidate_row_race_ids": missing_candidate_rows,
    }
    return predictions, diagnostics


def _recommended_next_action(
    *,
    broad_component_status: str,
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
                    child_recommended.get("queue_priority_score", 94.96)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The frontier artifact combo source reported a downstream live-port dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.96,
            "reason": (
                "The broad-component first-exact rank live source cannot emit "
                "predictions until the frontier artifact combo prior-date source "
                "is materialized with the exact contract."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_broad_component_first_exact_rank_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.94,
            "reason": (
                "The broad-component first-exact rank selector needs complete live "
                "full-combo candidate features and live records before scoring can be trusted."
            ),
        }
    if broad_component_status != "passed":
        return {
            "action": "repair_live_broad_component_predictions_before_broad_component_first_exact_rank_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.93,
            "reason": (
                "The broad-component first-exact rank selector needs complete "
                "live broad component predictions before the locked HGB scorer "
                "can run."
            ),
        }
    if train_surface_status != "passed":
        return {
            "action": "repair_broad_component_first_exact_rank_train_surface_before_live_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.925,
            "reason": (
                "The live scorer needs the frozen broad-component first-exact "
                "rank train surface to rebuild the prior-date HGB history."
            ),
        }
    if (
        status
        == "blocked_pending_broad_component_first_exact_rank_prior_date_prediction_logic"
    ):
        return {
            "action": "implement_locked_best_broad_component_first_exact_rank_prior_date_prediction_logic",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.92,
            "reason": (
                "The source and candidate live inputs are available, but the locked "
                "HGB broad-component first-exact rank prediction logic has not been ported yet."
            ),
        }
    return {
        "action": "inspect_broad_component_first_exact_rank_prior_date_live_materializer_gap",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.9,
        "reason": (
            "The broad-component first-exact rank materializer reached an unexpected "
            "coverage state and needs inspection before unblocking its parent."
        ),
    }


def _status_for_source(live_source_context: dict[str, Any]) -> str | None:
    if live_source_context.get("status") == "passed":
        return None
    if live_source_context.get("exists") and _dict(
        live_source_context.get("recommended_next_action")
    ).get("action"):
        return "blocked_live_source_child_dependency"
    return "blocked_missing_live_source_artifact"


def build_artifact(
    *,
    source_target_path: Path = DEFAULT_SOURCE_TARGET,
    live_source_path: Path = DEFAULT_LIVE_SOURCE,
    candidate_features_path: Path = DEFAULT_CANDIDATE_FEATURES,
    live_broad_components_path: Path = DEFAULT_LIVE_BROAD_COMPONENTS,
    train_surface_path: Path = DEFAULT_TRAIN_SURFACE,
) -> dict[str, Any]:
    source_target = _dict(_read_json(source_target_path))
    selector = _best_selector(source_target)
    live_source_context = _source_context(live_source_path)
    candidate_context = _candidate_context(candidate_features_path)
    candidate_coverage = _dict(candidate_context.get("coverage"))
    expected_race_count = _int(candidate_coverage.get("expected_race_count")) or 0
    race_ids = _candidate_race_ids(candidate_context)
    live_broad_context = _live_broad_context(
        live_broad_components_path,
        expected_race_ids=race_ids,
    )
    train_surface_exists = train_surface_path.exists()
    train_surface_status = "passed" if train_surface_exists else "missing"
    pre_status = _status_for_source(live_source_context)

    if pre_status is not None:
        status = pre_status
    elif candidate_context["status"] != "passed":
        status = "blocked_incomplete_live_candidate_features"
    elif live_broad_context["status"] != "passed":
        status = "blocked_incomplete_live_broad_components"
    elif train_surface_status != "passed":
        status = "blocked_missing_broad_component_first_exact_rank_train_surface"
    else:
        status = "blocked_pending_broad_component_first_exact_rank_prior_date_prediction_logic"

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
    if status == "blocked_pending_broad_component_first_exact_rank_prior_date_prediction_logic":
        live_source_payload = _dict(_read_json(live_source_path))
        output_window, current_best_predictions = _flatten_simple_predictions(
            live_source_payload
        )
        (
            train_payload,
            selected_train_window,
            component_names,
            history_records,
            source_stats,
        ) = _load_training_inputs(
            train_surface_path=train_surface_path,
            live_race_ids=race_ids,
        )
        surface, model, choice = train_surface._resolve_best_specs(
            str(train_payload["selector_spec"])
        )
        component_predictions = _load_live_component_predictions(
            live_broad_components_path,
            component_names=component_names,
            race_ids=race_ids,
        )
        missing_component_race_rows = [
            {
                "component": component,
                "missing_race_ids": sorted(set(race_ids) - set(predictions)),
            }
            for component, predictions in sorted(component_predictions.items())
            if set(race_ids) - set(predictions)
        ]
        if missing_component_race_rows:
            status = "blocked_incomplete_live_broad_components"
            live_broad_context = {
                **live_broad_context,
                "status": "failed",
                "incomplete_components": missing_component_race_rows,
            }
        else:
            predicted, live_prediction_diagnostics = _predict_live_window(
                race_ids=race_ids,
                current_best_predictions=current_best_predictions,
                component_predictions=component_predictions,
                component_names=component_names,
                source_stats=source_stats,
                surface=surface,
                model=model,
                choice=choice,
                history_records=history_records,
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
            status = "passed" if not missing_race_ids else "blocked_incomplete_live_predictions"
            live_prediction_diagnostics = {
                **live_prediction_diagnostics,
                "selected_train_window": selected_train_window,
                "train_surface_path": str(train_surface_path),
                "train_surface_contract": train_payload.get("train_prediction_contract"),
                "component_count": len(component_names),
            }
    recommended = _recommended_next_action(
        broad_component_status=str(live_broad_context.get("status")),
        candidate_status=str(candidate_context.get("status")),
        live_source_context=live_source_context,
        status=status,
        train_surface_status=train_surface_status,
    )
    if status == "passed":
        recommended = {
            "action": "materialize_locked_best_next_parent_after_broad_component_first_exact_rank_prior_date",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.91,
            "reason": (
                "The locked broad-component first-exact rank selector emitted "
                "complete pre-race live predictions; proceed to the next live-port "
                "parent in the chain."
            ),
        }
    return {
        "format_version": "single-combo-live-broad-component-first-exact-rank-prior-date-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": status != "passed",
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": "one_unordered_top3_combo_per_race",
        "source_selection_contract": "one_unordered_top3_combo_per_race",
        "source_target_selection_contract": selector.get("selection_contract"),
        "expected_source_selection_contract": LIVE_SOURCE_SELECTION_CONTRACT,
        "selector_spec": selector.get("selector_spec"),
        "selector_type": selector.get("selector_type"),
        "model_spec": selector.get("model_spec"),
        "source_target_artifact": str(source_target_path),
        "offline_source_artifact": selector.get("source_artifact"),
        "live_source_context": live_source_context,
        "candidate_feature_context": candidate_context,
        "live_broad_component_context": live_broad_context,
        "train_surface_context": {
            "path": str(train_surface_path),
            "exists": train_surface_exists,
            "status": train_surface_status,
        },
        "coverage": coverage,
        "predictions_by_window": predictions_by_window,
        "selector_diagnostics": {
            "selector": "broad_component_first_exact_rank_prior_date",
            "candidate": selector.get("candidate"),
            "selector_spec": selector.get("selector_spec"),
            "model_spec": selector.get("model_spec"),
            "summary": selector.get("summary"),
            "window_diagnostics": selector.get("window_diagnostics"),
            "selection_uses_target_labels": False,
            "selection_uses_live_labels": False,
            "history_uses_completed_prior_outcomes": False,
            "prediction_logic_pending_after_source_materialization": (
                status
                == "blocked_pending_broad_component_first_exact_rank_prior_date_prediction_logic"
            ),
            "live_prediction_diagnostics": live_prediction_diagnostics,
        },
        "recommended_next_action": recommended,
        "policy": {
            "ranker_must_not_be_treated_as_pass_through": True,
            "hgb_model_prediction_logic_must_be_ported_before_emit": status != "passed",
            "active_live_labels_must_not_be_used": True,
            "do_not_substitute_champion_clean_top3_for_locked_source": True,
            "diagnostic_shadow_substitution_must_not_unblock_locked_parent": True,
            "required_sources_must_be_materialized_before_prediction": True,
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
    parser.add_argument(
        "--live-broad-components",
        type=Path,
        default=DEFAULT_LIVE_BROAD_COMPONENTS,
    )
    parser.add_argument("--train-surface", type=Path, default=DEFAULT_TRAIN_SURFACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_artifact(
        candidate_features_path=args.candidate_features,
        live_broad_components_path=args.live_broad_components,
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
