"""Capture safe train predictions for source-pool overlap-2 aggregate artifacts."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_overlap2_aggregate_selector_diagnostic as overlap,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_prior_date_selector_diagnostic as base,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_source_meta_extension_prior_date_selector_diagnostic as source_meta,
)
from autoresearch.clean_release_row_feature_rank_pattern_probe import (  # noqa: E402
    _build_rank_and_hit_caches,
    _race_rows,
)
from autoresearch.clean_top50_history_overlay_probe import (  # noqa: E402
    _summarize_predictions,
)
from autoresearch.single_combo_broad_component_train_surface_inventory import (  # noqa: E402
    TRAIN_PREDICTION_CONTRACT,
)
from autoresearch.single_combo_source_pool_ranker_prior_date_train_surface import (  # noqa: E402
    _date_groups,
    _json_predictions,
    _train_answers_by_window,
)

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_DIAGNOSTIC_ARTIFACT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_overlap2_aggregate_selector_"
    "after_source_meta_extension_prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_SOURCE_ARTIFACT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_ranker_source_meta_extension_"
    "after_variant_calibration_prior_date_selector_rerun_repro_diagnostic_"
    "with_safe_train_predictions.json"
)
DEFAULT_SURFACE_OUTPUT = DEFAULT_CACHE_DIR / (
    "single_combo_source_pool_overlap2_aggregate_after_source_meta_extension_"
    "prior_date_train_surface.json"
)
DEFAULT_PATCHED_OUTPUT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_overlap2_aggregate_selector_"
    "after_source_meta_extension_prior_date_selector_rerun_repro_diagnostic_"
    "with_safe_train_predictions.json"
)
FORMAT_VERSION = "single-combo-source-pool-overlap2-aggregate-train-surface-v1"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _combo_key(combo: Any) -> tuple[int, int, int]:
    if not isinstance(combo, list | tuple) or len(combo) < 3:
        raise ValueError(f"Expected a 3-horse combo, got: {combo!r}")
    return tuple(sorted(int(chul_no) for chul_no in combo[:3]))


def _load_train_predictions(
    payload: dict[str, Any],
) -> dict[str, dict[str, tuple[int, int, int]]]:
    raw = payload.get("train_predictions_by_window")
    if not isinstance(raw, dict):
        return {}
    return {
        str(window_name): {
            str(race_id): _combo_key(combo)
            for race_id, combo in predictions.items()
        }
        for window_name, predictions in raw.items()
        if isinstance(predictions, dict)
    }


def _resolve_specs(
    *,
    source_group_spec_name: str,
    selector_spec_name: str,
) -> tuple[base.SourceGroupSpec, overlap.AggregateSpec]:
    source_group = next(
        (
            spec
            for spec in overlap._source_group_specs()
            if spec.name == source_group_spec_name
        ),
        None,
    )
    if source_group is None:
        raise ValueError(f"Unable to resolve source_group_spec: {source_group_spec_name}")
    selector = next(
        (spec for spec in overlap._aggregate_specs() if spec.name == selector_spec_name),
        None,
    )
    if selector is None:
        raise ValueError(f"Unable to resolve selector_spec: {selector_spec_name}")
    return source_group, selector


def _predict_train_window(
    *,
    answers: dict[str, list[int]],
    source_predictions: dict[str, tuple[int, int, int]],
    rows_by_race: dict[str, list[dict[str, Any]]],
    race_index_by_id: dict[str, int],
    ranked_cache: dict[tuple[str, int], dict[str, list[int]]],
    hit_cache: dict[tuple[str, int], np.ndarray],
    patterns: tuple[tuple[int, int, int], ...],
    source_group: base.SourceGroupSpec,
    selector_spec: overlap.AggregateSpec,
) -> tuple[dict[str, tuple[int, int, int]], dict[str, Any]]:
    predictions: dict[str, tuple[int, int, int]] = {}
    switch_values: list[float] = []
    source_count_values: list[float] = []
    pool_values: list[float] = []
    race_ids = sorted(
        race_id
        for race_id in answers
        if race_id in source_predictions and race_id in race_index_by_id
    )
    prior_ids: list[str] = []
    for _date, date_ids in _date_groups(race_ids):
        date_source = {
            race_id: source_predictions[race_id]
            for race_id in date_ids
            if race_id in source_predictions
        }
        if not prior_ids:
            predictions.update(date_source)
            switch_values.append(0.0)
            source_count_values.append(0.0)
            pool_values.append(
                float(
                    np.mean(
                        [
                            float(_combo_key(combo) == _combo_key(answers[race_id]))
                            for race_id, combo in date_source.items()
                        ]
                    )
                )
                if date_source
                else 0.0
            )
            prior_ids.extend(date_ids)
            continue

        train_indices = [race_index_by_id[race_id] for race_id in prior_ids]
        sources = base.vote._selected_sources(
            hit_cache=hit_cache,
            train_indices=train_indices,
            patterns=patterns,
            source_count=source_group.source_count,
            metric=source_group.metric,
        )
        eval_rows_by_race = {
            race_id: source_meta._source_meta_candidate_rows_for_race(
                race_id=race_id,
                race_rows=rows_by_race.get(race_id, []),
                sources=sources,
                ranked_cache=ranked_cache,
                spec=source_group,
                answer=answers.get(race_id),
                fallback_combo=fallback_combo,
            )
            for race_id, fallback_combo in date_source.items()
        }
        selected, diagnostics = overlap._select_overlap2_predictions(
            rows_by_race=eval_rows_by_race,
            fallback_predictions=date_source,
            source_group=source_group,
            spec=selector_spec,
        )
        predictions.update(selected)
        switch_values.append(float(diagnostics["switch_rate"]))
        source_count_values.append(float(len(sources)))
        pool_values.append(
            base._pool_oracle_rate(
                eval_rows_by_race=eval_rows_by_race,
                fallback_predictions=date_source,
                eval_answers={race_id: answers[race_id] for race_id in date_source},
            )
        )
        prior_ids.extend(date_ids)

    return predictions, {
        "selector": f"{source_group.name}/{selector_spec.name}",
        "source_group_spec": source_group.name,
        "selector_spec": selector_spec.name,
        "switch_rate": round(float(np.mean(switch_values)) if switch_values else 0.0, 6),
        "avg_source_count": round(
            float(np.mean(source_count_values)) if source_count_values else 0.0,
            6,
        ),
        "avg_pool_oracle_exact_rate": round(
            float(np.mean(pool_values)) if pool_values else 0.0,
            6,
        ),
        "history_update": "completed_prior_target_train_dates_only",
        "selection_uses_labels": False,
    }


def build_surface(
    *,
    config_path: Path = base.DEFAULT_CONFIG,
    diagnostic_artifact: Path = DEFAULT_DIAGNOSTIC_ARTIFACT,
    source_artifact: Path = DEFAULT_SOURCE_ARTIFACT,
    row_cache_path: Path = base.DEFAULT_ROW_CACHE,
) -> dict[str, Any]:
    started = time.time()
    diagnostic_payload = _read_json(diagnostic_artifact)
    source_payload = _read_json(source_artifact)
    if source_payload.get("train_prediction_contract") != TRAIN_PREDICTION_CONTRACT:
        raise ValueError("source artifact is missing the safe train contract")
    best = diagnostic_payload.get("best")
    if not isinstance(best, dict):
        raise ValueError("diagnostic artifact is missing best")
    source_group_name = best.get("source_group_spec")
    selector_name = best.get("selector_spec")
    if not isinstance(source_group_name, str) or not isinstance(selector_name, str):
        raise ValueError("diagnostic artifact is missing source/selector spec")
    source_group, selector_spec = _resolve_specs(
        source_group_spec_name=source_group_name,
        selector_spec_name=selector_name,
    )

    answers_by_window, window_context, row_cache = _train_answers_by_window(
        config_path=config_path,
        row_cache_path=row_cache_path,
    )
    source_train = _load_train_predictions(source_payload)
    rows = row_cache["rows"]
    answers = {
        str(race_id): list(answer[:3])
        for race_id, answer in row_cache["answers"].items()
    }
    rows_by_race = _race_rows(rows)
    race_ids = tuple(sorted(race_id for race_id in answers if race_id in rows_by_race))
    race_index_by_id = {race_id: index for index, race_id in enumerate(race_ids)}
    features = base.vote._available_all_allowed_features(rows)
    patterns = tuple(itertools.combinations(range(1, 11), 3))
    ranked_cache, hit_cache = _build_rank_and_hit_caches(
        rows_by_race=rows_by_race,
        race_ids=race_ids,
        answers=answers,
        features=features,
        patterns=patterns,
    )

    predictions_by_window: dict[str, dict[str, tuple[int, int, int]]] = {}
    window_rows: list[dict[str, Any]] = []
    for window_name, window_answers in answers_by_window.items():
        source_predictions = source_train.get(window_name)
        if source_predictions is None:
            raise ValueError(f"source is missing train window: {window_name}")
        predicted, diagnostics = _predict_train_window(
            answers=window_answers,
            source_predictions=source_predictions,
            rows_by_race=rows_by_race,
            race_index_by_id=race_index_by_id,
            ranked_cache=ranked_cache,
            hit_cache=hit_cache,
            patterns=patterns,
            source_group=source_group,
            selector_spec=selector_spec,
        )
        predictions_by_window[window_name] = predicted
        window_rows.append(
            {
                "name": window_name,
                **window_context[window_name],
                "summary": _summarize_predictions(predicted, window_answers),
                "diagnostics": diagnostics,
            }
        )

    return {
        "format_version": FORMAT_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "source_artifact_target": str(diagnostic_artifact),
        "source_artifact": str(source_artifact),
        "row_cache": str(row_cache_path),
        "source_group_spec": source_group.name,
        "selector_spec": selector_spec.name,
        "feature_names": list(features),
        "train_prediction_contract": TRAIN_PREDICTION_CONTRACT,
        "train_prediction_capture": {
            "status": "captured_source_pool_overlap2_aggregate_train_surface",
            "contract": TRAIN_PREDICTION_CONTRACT,
            "target_windows": sorted(predictions_by_window),
            "history_update": "completed_prior_target_train_dates_only",
            "source_group_spec": source_group.name,
            "selector_spec": selector_spec.name,
            "source_train_artifact": str(source_artifact),
            "counts_as_70_percent_evidence": False,
        },
        "windows": window_rows,
        "train_predictions_by_window": _json_predictions(predictions_by_window),
        "elapsed_seconds": round(time.time() - started, 2),
    }


def patch_diagnostic_artifact(
    *,
    diagnostic_artifact: Path,
    source_artifact: Path,
    surface_payload: dict[str, Any],
    surface_output: Path,
    patched_output: Path,
) -> dict[str, Any]:
    diagnostic_payload = _read_json(diagnostic_artifact)
    patched = copy.deepcopy(diagnostic_payload)
    patched["original_source_artifact"] = patched.get("source_artifact")
    patched["source_artifact"] = str(source_artifact)
    patched["train_prediction_contract"] = TRAIN_PREDICTION_CONTRACT
    patched["train_predictions_by_window"] = copy.deepcopy(
        surface_payload["train_predictions_by_window"]
    )
    patched["train_prediction_capture"] = {
        "status": "patched_from_source_pool_overlap2_aggregate_train_surface",
        "contract": TRAIN_PREDICTION_CONTRACT,
        "source_artifact": str(diagnostic_artifact),
        "source_surface": str(surface_output),
        "surface_format_version": surface_payload.get("format_version"),
        "surface_source_artifact_target": surface_payload.get("source_artifact_target"),
        "surface_train_prediction_capture": surface_payload.get(
            "train_prediction_capture"
        ),
        "window_count": len(surface_payload["train_predictions_by_window"]),
        "race_count_by_window": {
            window_name: len(predictions)
            for window_name, predictions in surface_payload[
                "train_predictions_by_window"
            ].items()
        },
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "counts_as_70_percent_evidence": False,
    }
    patched["counts_as_70_percent_evidence"] = False
    patched["diagnostic_only"] = True
    patched["patched_source_artifact_output_path"] = str(patched_output)
    return patched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=base.DEFAULT_CONFIG)
    parser.add_argument(
        "--diagnostic-artifact",
        type=Path,
        default=DEFAULT_DIAGNOSTIC_ARTIFACT,
    )
    parser.add_argument("--source-artifact", type=Path, default=DEFAULT_SOURCE_ARTIFACT)
    parser.add_argument("--row-cache", type=Path, default=base.DEFAULT_ROW_CACHE)
    parser.add_argument("--surface-output", type=Path, default=DEFAULT_SURFACE_OUTPUT)
    parser.add_argument("--patched-output", type=Path, default=DEFAULT_PATCHED_OUTPUT)
    args = parser.parse_args()
    surface_payload = build_surface(
        config_path=args.config,
        diagnostic_artifact=args.diagnostic_artifact,
        source_artifact=args.source_artifact,
        row_cache_path=args.row_cache,
    )
    surface_payload["output_path"] = str(args.surface_output)
    _write_json(args.surface_output, surface_payload)
    patched_payload = patch_diagnostic_artifact(
        diagnostic_artifact=args.diagnostic_artifact,
        source_artifact=args.source_artifact,
        surface_payload=surface_payload,
        surface_output=args.surface_output,
        patched_output=args.patched_output,
    )
    _write_json(args.patched_output, patched_payload)
    print(
        json.dumps(
            {
                "surface_output": str(args.surface_output),
                "patched_output": str(args.patched_output),
                "source_group_spec": surface_payload["source_group_spec"],
                "selector_spec": surface_payload["selector_spec"],
                "train_prediction_contract": TRAIN_PREDICTION_CONTRACT,
                "race_count_by_window": patched_payload["train_prediction_capture"][
                    "race_count_by_window"
                ],
                "counts_as_70_percent_evidence": False,
                "elapsed_seconds": surface_payload["elapsed_seconds"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
