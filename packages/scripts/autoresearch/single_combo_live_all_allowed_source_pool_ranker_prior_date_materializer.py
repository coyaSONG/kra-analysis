"""Strict live materializer for the base all-allowed source-pool ranker."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

# ruff: noqa: E402

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared.prediction_input_schema import (  # noqa: E402
    build_alternative_ranking_rows_for_race,
)

from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_prior_date_selector_diagnostic as selector_base,
)
from autoresearch import (  # noqa: E402
    single_combo_source_pool_ranker_prior_date_train_surface as train_surface,
)
from autoresearch.clean_release_row_feature_rank_pattern_probe import (  # noqa: E402
    _build_rank_and_hit_caches,
    _race_rows,
    _ranked_chuls,
)

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_ranker_prior_date_"
    "selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_row_cache_rank_pattern_prior_date_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_all_allowed_source_pool_ranker_prior_date_predictions.json"
)
DEFAULT_TRAIN_SURFACE = (
    DEFAULT_CACHE_DIR / "single_combo_source_pool_ranker_prior_date_train_surface.json"
)

LIVE_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
PARENT_ACTION = (
    "port_locked_best_all_allowed_source_pool_ranker_prior_date_source_to_live_runner"
)
CHILD_ACTION = (
    "port_locked_best_row_cache_rank_pattern_prior_date_source_to_live_runner"
)
CandidateRowsBuilder = Callable[..., list[dict[str, Any]]]


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


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


def _window_prediction_count(payload: dict[str, Any]) -> int:
    total = 0
    for window_payload in _dict(payload.get("predictions_by_window")).values():
        total += len(_dict(window_payload))
    return total


def _best_selector(source_target: dict[str, Any]) -> dict[str, Any]:
    best = _dict(source_target.get("best"))
    windows: list[dict[str, Any]] = []
    for window in _list(best.get("windows")):
        window_dict = _dict(window)
        diagnostics = _dict(window_dict.get("diagnostics"))
        if diagnostics:
            windows.append(
                {
                    "name": window_dict.get("name"),
                    "diagnostics": diagnostics,
                }
            )
    return {
        "candidate": best.get("candidate"),
        "selector_spec": best.get("selector_spec"),
        "selector_type": best.get("selector_type") or "hgb_source_pool_ranker",
        "source_group_spec": best.get("source_group_spec"),
        "model_spec": best.get("model_spec") or "hgb",
        "summary": _dict(best.get("summary")),
        "selection_contract": source_target.get("selection_contract"),
        "source_artifact": source_target.get("source_artifact"),
        "window_diagnostics": windows,
    }


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


def _candidate_race_ids(candidate_context: dict[str, Any]) -> list[str]:
    coverage = _dict(candidate_context.get("coverage"))
    return [str(race_id) for race_id in _list(coverage.get("race_ids"))]


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


def _race_payload_rows(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict) and isinstance(raw.get("races"), list):
        rows = raw["races"]
    else:
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def _race_id(row: dict[str, Any]) -> str:
    explicit = row.get("race_id")
    if explicit:
        return str(explicit)
    race_date = row.get("race_date") or row.get("rcDate")
    meet = row.get("meet")
    race_no = row.get("race_no") or row.get("rcNo")
    if race_date and meet and race_no:
        return f"{race_date}_{meet}_{race_no}"
    return ""


def _live_rows_by_race_from_candidate_payload(
    candidate_payload: dict[str, Any],
    *,
    expected_race_ids: list[str],
) -> dict[str, list[dict[str, Any]]]:
    target_dataset_path = candidate_payload.get("target_dataset_path")
    if not isinstance(target_dataset_path, str) or not target_dataset_path:
        return {}
    dataset = _read_json(_resolve_path(target_dataset_path))
    expected = set(expected_race_ids)
    rows: list[dict[str, Any]] = []
    for race in _race_payload_rows(dataset):
        race_id = _race_id(race)
        if race_id not in expected:
            continue
        for row in build_alternative_ranking_rows_for_race(
            race,
            actual_top3=None,
            validate_rows=True,
        ):
            live_row = dict(row)
            live_row["target"] = 0
            rows.append(live_row)
    return _race_rows(rows)


def _live_ranked_cache(
    *,
    rows_by_race: dict[str, list[dict[str, Any]]],
    feature_names: tuple[str, ...],
) -> dict[tuple[str, int], dict[str, list[int]]]:
    ranked_cache: dict[tuple[str, int], dict[str, list[int]]] = {}
    for feature_name in feature_names:
        for direction in (1, -1):
            ranked_cache[(feature_name, direction)] = {
                race_id: _ranked_chuls(
                    race_rows=race_rows,
                    feature_name=feature_name,
                    direction=direction,
                )
                for race_id, race_rows in rows_by_race.items()
                if len(race_rows) >= 3
            }
    return ranked_cache


def _load_training_state(
    *,
    train_surface_path: Path,
    live_race_ids: list[str],
    candidate_rows_builder: CandidateRowsBuilder = selector_base._candidate_rows_for_race,
) -> dict[str, Any]:
    surface_payload = _dict(_read_json(train_surface_path))
    source_group_name = str(surface_payload.get("source_group_spec") or "")
    model_spec_name = str(surface_payload.get("model_spec") or "")
    selector_spec_name = str(surface_payload.get("selector_spec") or "")
    if not all((source_group_name, model_spec_name, selector_spec_name)):
        raise ValueError(
            "train surface is missing source_group_spec, model_spec, or selector_spec"
        )
    source_group, model_spec, selector_spec = train_surface._resolve_best_specs(
        source_group_spec_name=source_group_name,
        model_spec_name=model_spec_name,
        selector_spec_name=selector_spec_name,
    )
    selected_window = _selected_train_window(
        surface_payload,
        live_min_date=_live_min_date(live_race_ids),
    )
    if selected_window is None:
        raise ValueError("no frozen train window ends before the live race date")

    row_cache_path = _resolve_path(surface_payload["row_cache"])
    source_payload = train_surface._read_json(
        _resolve_path(surface_payload["source_artifact"])
    )
    answers_by_window, _window_context, row_cache = (
        train_surface._train_answers_by_window(
            config_path=selector_base.DEFAULT_CONFIG,
            row_cache_path=row_cache_path,
        )
    )
    source_train = train_surface._load_simple_train_predictions(source_payload)
    answers = _dict(answers_by_window.get(selected_window))
    source_predictions = source_train.get(selected_window)
    if not answers or source_predictions is None:
        raise ValueError(f"missing frozen train inputs for window: {selected_window}")

    rows = row_cache["rows"]
    rows_by_race = _race_rows(rows)
    race_ids = tuple(sorted(race_id for race_id in answers if race_id in rows_by_race))
    race_index_by_id = {race_id: index for index, race_id in enumerate(race_ids)}
    feature_names = tuple(
        str(name)
        for name in (
            surface_payload.get("feature_names")
            or selector_base.vote._available_all_allowed_features(rows)
        )
    )
    patterns = tuple(itertools.combinations(range(1, 11), 3))
    ranked_cache, hit_cache = _build_rank_and_hit_caches(
        rows_by_race=rows_by_race,
        race_ids=race_ids,
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
    sources = selector_base.vote._selected_sources(
        hit_cache=hit_cache,
        train_indices=train_indices,
        patterns=patterns,
        source_count=source_group.source_count,
        metric=source_group.metric,
    )
    train_rows: list[dict[str, Any]] = []
    for race_id in completed_race_ids:
        train_rows.extend(
            candidate_rows_builder(
                race_id=race_id,
                race_rows=rows_by_race.get(race_id, []),
                sources=sources,
                ranked_cache=ranked_cache,
                spec=source_group,
                answer=answers.get(race_id),
                fallback_combo=None,
            )
        )
    model, fit_diagnostics = selector_base._fit_model(
        rows=train_rows,
        spec=model_spec,
    )
    labels = [int(row["exact_label"]) for row in train_rows]
    return {
        "feature_names": feature_names,
        "fit_diagnostics": fit_diagnostics,
        "model": model,
        "model_spec": model_spec,
        "selected_train_window": selected_window,
        "selector_spec": selector_spec,
        "source_count": len(sources),
        "source_group": source_group,
        "sources": sources,
        "surface_payload": surface_payload,
        "train_candidate_rows": len(train_rows),
        "train_label_unique_count": len(set(labels)),
    }


def _predict_live_window(
    *,
    race_ids: list[str],
    current_best_predictions: dict[str, tuple[int, int, int]],
    live_rows_by_race: dict[str, list[dict[str, Any]]],
    train_state: dict[str, Any],
    candidate_rows_builder: CandidateRowsBuilder = selector_base._candidate_rows_for_race,
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    source_group = train_state["source_group"]
    selector_spec = train_state["selector_spec"]
    model_spec = train_state["model_spec"]
    sources = train_state["sources"]
    live_ranked_cache = _live_ranked_cache(
        rows_by_race=live_rows_by_race,
        feature_names=train_state["feature_names"],
    )
    fallback_predictions = {
        race_id: current_best_predictions[race_id]
        for race_id in race_ids
        if race_id in current_best_predictions
    }
    eval_rows_by_race: dict[str, list[dict[str, Any]]] = {}
    eval_rows: list[dict[str, Any]] = []
    for race_id, fallback_combo in fallback_predictions.items():
        rows_for_race = candidate_rows_builder(
            race_id=race_id,
            race_rows=live_rows_by_race.get(race_id, []),
            sources=sources,
            ranked_cache=live_ranked_cache,
            spec=source_group,
            answer=None,
            fallback_combo=fallback_combo,
        )
        eval_rows_by_race[race_id] = rows_for_race
        eval_rows.extend(rows_for_race)
    score_map = selector_base._model_scores(
        model=train_state["model"],
        rows=eval_rows,
    )
    selected, selection_diagnostics = selector_base._select_predictions(
        eval_rows_by_race=eval_rows_by_race,
        fallback_predictions=fallback_predictions,
        model_scores=score_map,
        selector=selector_spec,
    )
    candidate_counts = [
        float(len(eval_rows_by_race.get(race_id, []))) for race_id in race_ids
    ]
    missing_fallback_race_ids = sorted(set(race_ids) - set(fallback_predictions))
    predictions = {race_id: list(combo) for race_id, combo in sorted(selected.items())}
    fit_diagnostics = _dict(train_state.get("fit_diagnostics"))
    diagnostics = {
        "avg_candidate_row_count": round(_safe_mean(candidate_counts), 3),
        "feature_contract": "all_allowed_source_pool_ranker_prior_date_live_rows_no_answer",
        "fit_diagnostics": fit_diagnostics,
        "history_update": "completed_frozen_train_dates_only_no_live_label_updates",
        "live_answer_sentinel_used_for_feature_shape_only": True,
        "missing_fallback_prediction_race_ids": missing_fallback_race_ids,
        "model_fitted": train_state["model"] is not None,
        "model_spec": model_spec.name,
        "selected_model_score_mean": round(
            float(selection_diagnostics.get("selected_model_score_mean", 0.0)),
            6,
        ),
        "selected_train_window": train_state["selected_train_window"],
        "selection_uses_labels": False,
        "selection_uses_live_labels": False,
        "selector": f"{source_group.name}/{model_spec.name}/{selector_spec.name}",
        "selector_spec": selector_spec.name,
        "source_count": train_state["source_count"],
        "source_group_spec": source_group.name,
        "switch_rate": round(float(selection_diagnostics.get("switch_rate", 0.0)), 6),
        "train_candidate_rows": train_state["train_candidate_rows"],
        "train_label_unique_count": train_state["train_label_unique_count"],
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
                    child_recommended.get("queue_priority_score", 94.86)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The row-cache prior-date source reported a downstream live-port dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.86,
            "reason": (
                "The all-allowed source-pool ranker live source cannot emit "
                "predictions until the row-cache rank-pattern prior-date source "
                "is materialized with the exact contract."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_all_allowed_source_pool_ranker_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.84,
            "reason": (
                "The all-allowed source-pool ranker needs complete live full-combo "
                "candidate features and live records before scoring can be trusted."
            ),
        }
    if train_surface_status != "passed":
        return {
            "action": "repair_all_allowed_source_pool_ranker_train_surface_before_live_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.83,
            "reason": (
                "The live scorer needs the frozen all-allowed source-pool ranker "
                "train surface to rebuild the prior-date HGB history."
            ),
        }
    if (
        status
        == "blocked_pending_all_allowed_source_pool_ranker_prior_date_prediction_logic"
    ):
        return {
            "action": "implement_locked_best_all_allowed_source_pool_ranker_prior_date_prediction_logic",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.82,
            "reason": (
                "The source and candidate live inputs are available, but the locked "
                "HGB source-pool ranker prediction logic has not been ported yet."
            ),
        }
    return {
        "action": "inspect_all_allowed_source_pool_ranker_prior_date_live_materializer_gap",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.8,
        "reason": (
            "The all-allowed source-pool ranker materializer reached an unexpected "
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
    train_surface_path: Path = DEFAULT_TRAIN_SURFACE,
    candidate_rows_builder: CandidateRowsBuilder = selector_base._candidate_rows_for_race,
) -> dict[str, Any]:
    source_target = _dict(_read_json(source_target_path))
    selector = _best_selector(source_target)
    live_source_context = _source_context(live_source_path)
    candidate_context = _candidate_context(candidate_features_path)
    candidate_coverage = _dict(candidate_context.get("coverage"))
    expected_race_count = _int(candidate_coverage.get("expected_race_count")) or 0
    race_ids = _candidate_race_ids(candidate_context)
    train_surface_exists = train_surface_path.exists()
    train_surface_status = "passed" if train_surface_exists else "missing"
    pre_status = _status_for_source(live_source_context)

    if pre_status is not None:
        status = pre_status
    elif candidate_context["status"] != "passed":
        status = "blocked_incomplete_live_candidate_features"
    elif train_surface_status != "passed":
        status = "blocked_missing_all_allowed_source_pool_ranker_train_surface"
    else:
        status = (
            "blocked_pending_all_allowed_source_pool_ranker_prior_date_prediction_logic"
        )

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
        == "blocked_pending_all_allowed_source_pool_ranker_prior_date_prediction_logic"
    ):
        live_source_payload = _dict(_read_json(live_source_path))
        output_window, current_best_predictions = _flatten_simple_predictions(
            live_source_payload
        )
        candidate_payload = _dict(_read_json(candidate_features_path))
        live_rows_by_race = _live_rows_by_race_from_candidate_payload(
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
                candidate_rows_builder=candidate_rows_builder,
                train_surface_path=train_surface_path,
                live_race_ids=race_ids,
            )
            predicted, live_prediction_diagnostics = _predict_live_window(
                candidate_rows_builder=candidate_rows_builder,
                race_ids=race_ids,
                current_best_predictions=current_best_predictions,
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
        live_source_context=live_source_context,
        status=status,
        train_surface_status=train_surface_status,
    )
    if status == "passed":
        recommended = {
            "action": "materialize_locked_best_next_parent_after_all_allowed_source_pool_ranker_prior_date",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.81,
            "reason": (
                "The locked all-allowed source-pool ranker emitted complete "
                "pre-race live predictions; proceed to the next live-port parent "
                "in the chain."
            ),
        }
    return {
        "format_version": "single-combo-live-all-allowed-source-pool-ranker-prior-date-materializer-v1",
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
        "source_group_spec": selector.get("source_group_spec"),
        "model_spec": selector.get("model_spec"),
        "source_target_artifact": str(source_target_path),
        "offline_source_artifact": selector.get("source_artifact"),
        "live_source_context": live_source_context,
        "candidate_feature_context": candidate_context,
        "train_surface_context": {
            "path": str(train_surface_path),
            "exists": train_surface_exists,
            "status": train_surface_status,
        },
        "coverage": coverage,
        "predictions_by_window": predictions_by_window,
        "selector_diagnostics": {
            "selector": "source_pool_ranker_prior_date",
            "candidate": selector.get("candidate"),
            "selector_spec": selector.get("selector_spec"),
            "source_group_spec": selector.get("source_group_spec"),
            "model_spec": selector.get("model_spec"),
            "summary": selector.get("summary"),
            "window_diagnostics": selector.get("window_diagnostics"),
            "selection_uses_target_labels": False,
            "selection_uses_live_labels": False,
            "history_uses_completed_prior_outcomes": False,
            "prediction_logic_pending_after_source_materialization": (
                status
                == "blocked_pending_all_allowed_source_pool_ranker_prior_date_prediction_logic"
            ),
            "live_prediction_diagnostics": live_prediction_diagnostics,
        },
        "recommended_next_action": recommended,
        "policy": {
            "ranker_must_not_be_treated_as_pass_through": True,
            "hgb_model_prediction_logic_must_be_ported_before_emit": status
            != "passed",
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
