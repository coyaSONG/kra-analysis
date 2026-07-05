"""Materialize or strictly block live broad-component rank-segment after row-cache source."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_gain_loss_prior_date_selector_diagnostic as gain_loss,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_prior_date_selector_diagnostic as broad_selector,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_rank_segment_prior_date_selector_diagnostic as rank_segment,
)
from autoresearch import (  # noqa: E402
    single_combo_broad_component_rank_segment_prior_date_train_surface as train_surface,
)
from autoresearch import (  # noqa: E402
    single_combo_live_all_allowed_source_pool_ranker_prior_date_materializer as source_pool_live,
)

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_rank_segment_aggressive_after_"
    "row_cache_rank_pattern_reanchor_prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_row_cache_rank_pattern_after_source_pool_predictions.json"
)
DEFAULT_LIVE_BROAD_COMPONENTS = (
    DEFAULT_CACHE_DIR / "single_combo_live_broad_component_predictions.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_broad_component_rank_segment_after_row_cache_rank_pattern_predictions.json"
)
DEFAULT_TRAIN_SURFACE = (
    DEFAULT_CACHE_DIR
    / "single_combo_broad_component_rank_segment_aggressive_after_row_cache_prior_date_train_surface.json"
)

EXPECTED_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
LIVE_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"


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


def _broad_context(path: Path) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    missing = _list(payload.get("missing_components"))
    status = "missing"
    if path.exists():
        status = (
            "passed"
            if payload.get("status") == "passed"
            and coverage.get("status") == "passed"
            and not missing
            else "failed"
        )
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": payload.get("status"),
        "coverage": coverage,
        "materialized_component_count": len(
            _list(payload.get("materialized_components"))
        ),
        "missing_component_count": len(missing),
        "prediction_windows": sorted(_dict(payload.get("predictions_by_window"))),
    }


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


def _broad_race_ids(broad_context: dict[str, Any]) -> list[str]:
    coverage = _dict(broad_context.get("coverage"))
    return [
        str(race_id)
        for race_id in _list(
            coverage.get("expected_race_ids") or coverage.get("race_ids")
        )
    ]


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


def _build_segment_history(
    *,
    answers: dict[str, list[int]],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    surface: gain_loss.SurfaceSpec,
    choice: rank_segment.ChoiceSpec,
) -> tuple[
    dict[str, broad_selector.SourceStats],
    dict[str, rank_segment.SegmentStats],
]:
    source_stats: dict[str, broad_selector.SourceStats] = {}
    stats_by_key: dict[str, rank_segment.SegmentStats] = defaultdict(
        rank_segment.SegmentStats
    )
    score_spec = rank_segment._score_spec_by_name()[surface.score_spec_name]
    race_ids = sorted(
        race_id for race_id in answers if race_id in current_best_predictions
    )
    for _date_value, date_race_ids in broad_selector._date_groups(race_ids):
        date_rows: list[dict[str, Any]] = []
        pending_updates: list[tuple[str, tuple[int, int, int], tuple[int, int, int]]] = []
        for race_id in date_race_ids:
            answer = broad_selector._answer_combo(answers, race_id)
            current_best_combo = broad_selector._combo_key(
                current_best_predictions[race_id]
            )
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
            ranked_rows = gain_loss._rank_surface_rows(
                rows=raw_rows,
                surface=surface,
                score_spec=score_spec,
                component_count=len(component_names),
            )
            rows = gain_loss._augment_rows(ranked_rows)
            date_rows.extend(rows)
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

        for row in date_rows:
            if float(row["is_current_best"]) >= 1.0:
                continue
            if float(row["surface_rank"]) > choice.max_surface_rank:
                continue
            key = rank_segment._segment_key(row, choice.segment_profile)
            rank_segment._add_segment_row(stats_by_key[key], row)
        for source_name, combo, answer in pending_updates:
            broad_selector._update_stats(
                stats=source_stats.setdefault(source_name, broad_selector.SourceStats()),
                combo=combo,
                answer=answer,
            )
    return source_stats, stats_by_key


def _load_training_state(
    *,
    train_surface_path: Path,
    live_race_ids: list[str],
) -> dict[str, Any]:
    surface_payload = _dict(_read_json(train_surface_path))
    selector_spec = str(surface_payload.get("selector_spec") or "")
    grid_name = str(surface_payload.get("grid_name") or "focused")
    if not selector_spec:
        raise ValueError("train surface is missing selector_spec")
    surface, choice = train_surface._resolve_best_specs(
        grid_name=grid_name,
        selector_spec_name=selector_spec,
    )
    selected_window = source_pool_live._selected_train_window(
        surface_payload,
        live_min_date=source_pool_live._live_min_date(live_race_ids),
    )
    if selected_window is None:
        raise ValueError("no frozen train window ends before the live race date")

    source_payload = train_surface._read_json(
        source_pool_live._resolve_path(surface_payload["source_artifact"])
    )
    component_payload = train_surface._read_json(
        source_pool_live._resolve_path(surface_payload["component_cache"])
    )
    answers_by_window, _window_context, _row_cache = (
        train_surface._train_answers_by_window(
            config_path=train_surface.static_repair.DEFAULT_CONFIG,
            row_cache_path=train_surface.source_pool_base.DEFAULT_ROW_CACHE,
        )
    )
    source_train = train_surface._load_train_predictions(source_payload)
    component_train = train_surface._load_component_train_predictions(component_payload)
    answers = _dict(answers_by_window.get(selected_window))
    current_best_predictions = source_train.get(selected_window)
    component_predictions = component_train.get(selected_window)
    if (
        not answers
        or current_best_predictions is None
        or component_predictions is None
    ):
        raise ValueError(f"missing frozen train inputs for window: {selected_window}")
    component_names = tuple(str(name) for name in component_payload["components"])
    source_stats, stats_by_key = _build_segment_history(
        answers=answers,
        component_names=component_names,
        component_predictions=component_predictions,
        current_best_predictions=current_best_predictions,
        choice=choice,
        surface=surface,
    )
    return {
        "choice": choice,
        "component_names": component_names,
        "selected_train_window": selected_window,
        "source_stats": source_stats,
        "stats_by_key": stats_by_key,
        "surface": surface,
        "surface_payload": surface_payload,
        "train_race_count": len(current_best_predictions),
    }


def _predict_live_window(
    *,
    race_ids: list[str],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    train_state: dict[str, Any],
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    surface = train_state["surface"]
    choice = train_state["choice"]
    component_names = train_state["component_names"]
    source_stats = train_state["source_stats"]
    stats_by_key = train_state["stats_by_key"]
    score_spec = rank_segment._score_spec_by_name()[surface.score_spec_name]
    predictions: dict[str, list[int]] = {}
    switch_values: list[float] = []
    selected_current_values: list[float] = []
    selected_rank_values: list[float] = []
    selected_score_values: list[float] = []
    candidate_count_values: list[float] = []
    selected_segment_count_values: list[float] = []
    selected_segment_delta_values: list[float] = []
    missing_candidate_rows: list[str] = []
    fallback_predictions = {
        race_id: current_best_predictions[race_id]
        for race_id in race_ids
        if race_id in current_best_predictions
    }
    for race_id in sorted(race_ids):
        current_best_combo = fallback_predictions.get(race_id)
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
        ranked_rows = gain_loss._rank_surface_rows(
            rows=raw_rows,
            surface=surface,
            score_spec=score_spec,
            component_count=len(component_names),
        )
        rows = gain_loss._augment_rows(ranked_rows)
        selected_row, selected_score, details = rank_segment._select_row(
            rows=rows,
            stats_by_key=stats_by_key,
            spec=choice,
        )
        selected_combo = broad_selector._combo_key(selected_row["combo"])
        predictions[race_id] = list(selected_combo)
        switch_values.append(float(selected_combo != current_best_combo))
        selected_current_values.append(float(selected_combo == current_best_combo))
        selected_rank_values.append(float(selected_row["surface_rank"]))
        selected_score_values.append(float(selected_score))
        candidate_count_values.append(float(len(rows)))
        selected_segment_count_values.append(details["segment_count"])
        selected_segment_delta_values.append(details["segment_delta"])
    diagnostics = {
        "avg_selected_score": round(rank_segment._safe_mean(selected_score_values), 6),
        "avg_selected_segment_count": round(
            rank_segment._safe_mean(selected_segment_count_values),
            3,
        ),
        "avg_selected_segment_delta": round(
            rank_segment._safe_mean(selected_segment_delta_values),
            6,
        ),
        "avg_selected_surface_rank": round(
            rank_segment._safe_mean(selected_rank_values),
            3,
        ),
        "avg_surface_candidate_count": round(
            rank_segment._safe_mean(candidate_count_values),
            3,
        ),
        "choice_model": choice.name,
        "feature_contract": "current_best_broad_component_rank_segment_live_no_answer",
        "history_update": "completed_frozen_train_dates_only_no_live_label_updates",
        "live_answer_sentinel_used_for_feature_shape_only": True,
        "missing_candidate_row_race_ids": missing_candidate_rows,
        "missing_fallback_prediction_race_ids": sorted(
            set(race_ids) - set(fallback_predictions)
        ),
        "selected_current_best_rate": round(
            rank_segment._safe_mean(selected_current_values),
            6,
        ),
        "selected_train_window": train_state["selected_train_window"],
        "selection_uses_labels": False,
        "selection_uses_live_labels": False,
        "segment_profile": choice.segment_profile,
        "surface_spec": surface.name,
        "switch_rate": round(rank_segment._safe_mean(switch_values), 6),
        "train_race_count": train_state["train_race_count"],
    }
    return predictions, diagnostics


def _recommended_next_action(
    *,
    live_source_context: dict[str, Any],
    live_source_status: str,
    broad_status: str,
    status: str,
    train_surface_status: str,
) -> dict[str, Any]:
    if live_source_status != "passed":
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
                    child_recommended.get("queue_priority_score", 94.74)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The required row-cache after-source-pool source reported a downstream live-port dependency."
                ),
                "upstream_action": (
                    "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner"
                ),
            }
        return {
            "action": "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.74,
            "reason": (
                "The broad-component rank-segment after row-cache live source "
                "cannot emit predictions until its row-cache rank-pattern "
                "after source-pool fallback source is materialized with the "
                "exact contract."
            ),
        }
    if broad_status != "passed":
        return {
            "action": "repair_live_broad_component_predictions_before_rank_segment_after_row_cache_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.72,
            "reason": (
                "The rank-segment selector needs complete live broad component "
                "predictions before prediction logic can run."
            ),
        }
    if train_surface_status != "passed":
        return {
            "action": "repair_broad_component_rank_segment_after_row_cache_train_surface_before_live_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.71,
            "reason": (
                "The rank-segment selector needs the frozen broad-component "
                "rank-segment train surface before prediction logic can run."
            ),
        }
    if status == "passed":
        return {
            "action": "materialize_locked_best_row_cache_rank_pattern_after_broad_rank_segment_from_passed_broad_rank_segment",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.69,
            "reason": (
                "The broad-component rank-segment selector emitted complete "
                "pre-race live predictions; proceed to the next row-cache parent."
            ),
        }
    return {
        "action": "implement_locked_best_broad_component_rank_segment_after_row_cache_prediction_logic",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.7,
        "reason": (
            "The row-cache fallback source and broad components are present; "
            "implement prior-date rank-segment scoring without active labels."
        ),
    }


def build_artifact(
    *,
    source_target_path: Path = DEFAULT_SOURCE_TARGET,
    live_source_path: Path = DEFAULT_LIVE_SOURCE,
    live_broad_components_path: Path = DEFAULT_LIVE_BROAD_COMPONENTS,
    train_surface_path: Path = DEFAULT_TRAIN_SURFACE,
) -> dict[str, Any]:
    source_target = _dict(_read_json(source_target_path))
    selector = _best_selector(source_target)
    source_context = _source_context(live_source_path)
    broad_context = _broad_context(live_broad_components_path)
    broad_coverage = _dict(broad_context.get("coverage"))
    expected_race_count = _int(broad_coverage.get("expected_race_count")) or 0
    race_ids = _broad_race_ids(broad_context)
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
    elif broad_context["status"] != "passed":
        status = "blocked_incomplete_live_broad_components"
    elif train_surface_status != "passed":
        status = "blocked_missing_broad_component_rank_segment_after_row_cache_train_surface"
    else:
        status = "blocked_pending_broad_component_rank_segment_after_row_cache_prediction_logic"
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
    if (
        status
        == "blocked_pending_broad_component_rank_segment_after_row_cache_prediction_logic"
    ):
        live_source_payload = _dict(_read_json(live_source_path))
        output_window, current_best_predictions = (
            source_pool_live._flatten_simple_predictions(live_source_payload)
        )
        train_state = _load_training_state(
            train_surface_path=train_surface_path,
            live_race_ids=race_ids,
        )
        component_predictions = _load_live_component_predictions(
            live_broad_components_path,
            component_names=train_state["component_names"],
            race_ids=race_ids,
        )
        predicted, live_prediction_diagnostics = _predict_live_window(
            component_predictions=component_predictions,
            current_best_predictions=current_best_predictions,
            race_ids=race_ids,
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
        status = "passed" if not missing_race_ids else "blocked_incomplete_live_predictions"
        live_prediction_diagnostics = {
            **live_prediction_diagnostics,
            "component_count": len(train_state["component_names"]),
            "train_surface_contract": _dict(train_state.get("surface_payload")).get(
                "train_prediction_contract"
            ),
            "train_surface_path": str(train_surface_path),
        }
    recommended = _recommended_next_action(
        broad_status=str(broad_context.get("status")),
        live_source_context=source_context,
        live_source_status=str(source_context.get("status")),
        status=status,
        train_surface_status=train_surface_status,
    )
    return {
        "format_version": "single-combo-live-broad-component-rank-segment-after-row-cache-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": status != "passed",
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": (
            "live_current_best_plus_broad_component_rank_segment_prior_date_selector_predictions_by_window"
        ),
        "source_selection_contract": selector.get("selection_contract"),
        "expected_source_selection_contract": EXPECTED_SOURCE_SELECTION_CONTRACT,
        "selector_spec": selector.get("selector_spec"),
        "source_target_artifact": str(source_target_path),
        "source_target_source_artifact": selector.get("source_artifact"),
        "live_source_context": source_context,
        "broad_component_context": broad_context,
        "train_surface_context": {
            "path": str(train_surface_path),
            "exists": train_surface_exists,
            "status": train_surface_status,
        },
        "coverage": coverage,
        "predictions_by_window": predictions_by_window,
        "selector_diagnostics": {
            "selector": "broad_component_rank_segment_after_row_cache",
            "prediction_logic_pending_after_source_materialization": (
                status
                == "blocked_pending_broad_component_rank_segment_after_row_cache_prediction_logic"
            ),
            "selection_uses_live_labels": False,
            "live_prediction_diagnostics": live_prediction_diagnostics,
        },
        "recommended_next_action": recommended,
        "policy": {
            "do_not_substitute_champion_clean_top3_for_locked_source": True,
            "diagnostic_shadow_substitution_must_not_unblock_locked_parent": True,
            "required_source_must_be_materialized_before_prediction": True,
            "active_live_labels_must_not_be_used": True,
            "prior_date_history_must_use_completed_prior_dates_only": True,
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
        "--live-broad-components",
        type=Path,
        default=DEFAULT_LIVE_BROAD_COMPONENTS,
    )
    parser.add_argument("--train-surface", type=Path, default=DEFAULT_TRAIN_SURFACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_artifact(
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
