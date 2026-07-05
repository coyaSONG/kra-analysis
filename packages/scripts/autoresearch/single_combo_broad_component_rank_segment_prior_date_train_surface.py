"""Capture safe train predictions for broad-component rank-segment artifacts."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_prior_date_selector_diagnostic as source_pool_base,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_rank_segment_prior_date_selector_diagnostic as rank_segment,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_full_field_one_swap_static_repair_diagnostic as static_repair,
)
from autoresearch.clean_top50_history_overlay_probe import (  # noqa: E402
    _summarize_predictions,
)
from autoresearch.single_combo_broad_component_train_surface_inventory import (  # noqa: E402
    TRAIN_PREDICTION_CONTRACT,
)
from autoresearch.single_combo_source_pool_ranker_prior_date_train_surface import (  # noqa: E402
    _json_predictions,
    _train_answers_by_window,
)

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_DIAGNOSTIC_ARTIFACT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_rank_segment_aggressive_after_"
    "row_cache_rank_pattern_reanchor_prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_SOURCE_ARTIFACT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_row_cache_rank_pattern_after_source_pool_reanchor_"
    "prior_date_selector_rerun_repro_diagnostic_with_safe_train_predictions.json"
)
DEFAULT_SURFACE_OUTPUT = DEFAULT_CACHE_DIR / (
    "single_combo_broad_component_rank_segment_aggressive_after_row_cache_"
    "prior_date_train_surface.json"
)
DEFAULT_PATCHED_OUTPUT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_rank_segment_aggressive_after_"
    "row_cache_rank_pattern_reanchor_prior_date_selector_rerun_repro_diagnostic_"
    "with_safe_train_predictions.json"
)
FORMAT_VERSION = "single-combo-broad-component-rank-segment-train-surface-v1"


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


def _load_component_train_predictions(
    payload: dict[str, Any],
) -> dict[str, dict[str, dict[str, tuple[int, int, int]]]]:
    raw = payload.get("train_predictions_by_window")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {}
    for window_name, component_predictions in raw.items():
        if not isinstance(component_predictions, dict):
            continue
        window_out: dict[str, dict[str, tuple[int, int, int]]] = {}
        for component_name, race_predictions in component_predictions.items():
            if not isinstance(race_predictions, dict):
                continue
            window_out[str(component_name)] = {
                str(race_id): _combo_key(combo)
                for race_id, combo in race_predictions.items()
            }
        out[str(window_name)] = window_out
    return out


def _resolve_best_specs(
    *,
    selector_spec_name: str,
    grid_name: str,
) -> tuple[Any, rank_segment.ChoiceSpec]:
    choice_specs = rank_segment._choice_specs(grid_name=grid_name)
    for surface in rank_segment._surface_specs():
        prefix = surface.name + "/"
        if not selector_spec_name.startswith(prefix):
            continue
        choice_name = selector_spec_name[len(prefix) :]
        choice = next((spec for spec in choice_specs if spec.name == choice_name), None)
        if choice is None:
            raise ValueError(f"Unable to resolve choice spec: {choice_name}")
        return surface, choice
    raise ValueError(f"Unable to resolve selector_spec: {selector_spec_name}")


def build_surface(
    *,
    config_path: Path = static_repair.DEFAULT_CONFIG,
    diagnostic_artifact: Path = DEFAULT_DIAGNOSTIC_ARTIFACT,
    source_artifact: Path = DEFAULT_SOURCE_ARTIFACT,
    component_cache: Path | None = None,
    cache_dir: Path = rank_segment.DEFAULT_CACHE_DIR,
) -> dict[str, Any]:
    started = time.time()
    diagnostic_payload = _read_json(diagnostic_artifact)
    source_payload = _read_json(source_artifact)
    if source_payload.get("train_prediction_contract") != TRAIN_PREDICTION_CONTRACT:
        raise ValueError("source artifact is missing the safe train contract")
    component_cache = component_cache or Path(str(diagnostic_payload["component_cache"]))
    component_payload = _read_json(component_cache)
    if component_payload.get("train_prediction_contract") != TRAIN_PREDICTION_CONTRACT:
        raise ValueError("component cache is missing the safe train contract")

    best = diagnostic_payload.get("best")
    if not isinstance(best, dict):
        raise ValueError("diagnostic artifact is missing best")
    selector_name = best.get("selector_spec")
    grid_name = str(diagnostic_payload.get("grid_name") or "focused")
    if not isinstance(selector_name, str):
        raise ValueError("diagnostic artifact is missing selector spec")
    surface_spec, choice_spec = _resolve_best_specs(
        selector_spec_name=selector_name,
        grid_name=grid_name,
    )

    answers_by_window, window_context, _row_cache = _train_answers_by_window(
        config_path=config_path,
        row_cache_path=source_pool_base.DEFAULT_ROW_CACHE,
    )
    source_train = _load_train_predictions(source_payload)
    component_train = _load_component_train_predictions(component_payload)
    component_names = tuple(str(name) for name in component_payload["components"])

    predictions_by_window: dict[str, dict[str, tuple[int, int, int]]] = {}
    window_rows: list[dict[str, Any]] = []
    for window_name, window_answers in answers_by_window.items():
        current_predictions = source_train.get(window_name)
        window_component_predictions = component_train.get(window_name)
        if current_predictions is None:
            raise ValueError(f"source is missing train window: {window_name}")
        if window_component_predictions is None:
            raise ValueError(f"component cache is missing train window: {window_name}")
        predicted, diagnostics = rank_segment._predict_surface_window(
            answers=window_answers,
            current_best_predictions=current_predictions,
            component_predictions=window_component_predictions,
            component_names=component_names,
            surface=surface_spec,
            choice_specs=(choice_spec,),
        )[choice_spec.name]
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
        "component_cache": str(component_cache),
        "cache_dir": str(cache_dir),
        "grid_name": grid_name,
        "max_rank": diagnostic_payload.get("max_rank"),
        "component_count": len(component_names),
        "surface_spec": surface_spec.name,
        "choice_spec": choice_spec.name,
        "selector_spec": selector_name,
        "train_prediction_contract": TRAIN_PREDICTION_CONTRACT,
        "train_prediction_capture": {
            "status": "captured_broad_component_rank_segment_train_surface",
            "contract": TRAIN_PREDICTION_CONTRACT,
            "target_windows": sorted(predictions_by_window),
            "history_update": "completed_prior_target_train_dates_only",
            "surface_spec": surface_spec.name,
            "choice_spec": choice_spec.name,
            "selector_spec": selector_name,
            "source_train_artifact": str(source_artifact),
            "component_cache": str(component_cache),
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
        "status": "patched_from_broad_component_rank_segment_train_surface",
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
    parser.add_argument("--config", type=Path, default=static_repair.DEFAULT_CONFIG)
    parser.add_argument(
        "--diagnostic-artifact",
        type=Path,
        default=DEFAULT_DIAGNOSTIC_ARTIFACT,
    )
    parser.add_argument("--source-artifact", type=Path, default=DEFAULT_SOURCE_ARTIFACT)
    parser.add_argument("--component-cache", type=Path, default=None)
    parser.add_argument("--cache-dir", type=Path, default=rank_segment.DEFAULT_CACHE_DIR)
    parser.add_argument("--surface-output", type=Path, default=DEFAULT_SURFACE_OUTPUT)
    parser.add_argument("--patched-output", type=Path, default=DEFAULT_PATCHED_OUTPUT)
    args = parser.parse_args()
    surface_payload = build_surface(
        config_path=args.config,
        diagnostic_artifact=args.diagnostic_artifact,
        source_artifact=args.source_artifact,
        component_cache=args.component_cache,
        cache_dir=args.cache_dir,
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
