"""Strict prior-date source selector over top clean artifact outputs."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_horse_row_output_agreement_selector_probe as broad_agreement,
)
from autoresearch import (  # noqa: E402
    clean_release_current_horse_row_output_full_agreement_selector_probe as full_agreement,
)
from autoresearch import (  # noqa: E402
    clean_release_current_row_feature_output_agreement_selector_probe as agreement,
)
from autoresearch import (  # noqa: E402
    clean_release_current_row_feature_output_source_selector_probe as source_selector,
)
from autoresearch import (  # noqa: E402
    clean_release_current_row_feature_share2_output_agreement_selector_probe as share2_agreement,
)
from autoresearch import (  # noqa: E402
    clean_release_current_row_feature_share2_output_source_selector_probe as share2_source,
)
from autoresearch.clean_release_current_horse_top20_probability_ranker_probe import (  # noqa: E402,E501
    DEFAULT_POLICY_SOURCE,
)
from autoresearch.clean_release_current_row_feature_full_combo_top15_full_output_support_selector_probe import (  # noqa: E402,E501
    _load_json_predictions,
)
from autoresearch.clean_sparse_multichoice_policy_selector_probe import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)
from autoresearch.clean_top50_history_overlay_probe import (  # noqa: E402
    _summarize_predictions,
)
from autoresearch.clean_top50_pairwise_preference_probe import (  # noqa: E402
    _candidate_key,
)
from autoresearch.search_clean_model import _load_or_build_row_cache  # noqa: E402

DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR / "clean_release_top_clean_artifact_source_selector_probe.json"
)
DEFAULT_COMPONENT_CACHE = DEFAULT_CACHE_DIR / "clean_broad_component_predictions_max10.json"

ARTIFACT_SELECTOR_FALLBACKS = {
    "clean_release_current_row_feature_output_agreement_selector_probe.json": (
        "recovery/horse/top5/combo0.5/horse1/pair0/cur0.5/ov-0.5/offline"
    ),
    "clean_release_current_row_feature_output_source_selector_probe.json": (
        "all/blend/field/min3/prior5/cur-0.05/distinct0.01"
    ),
    "clean_release_current_row_feature_share2_output_agreement_selector_probe.json": (
        "all_plus_share2/combo/top5/combo1/horse0/pair0/cur-0.5/"
        "ov-0.5/offline"
    ),
    "clean_release_current_row_feature_share2_output_source_selector_probe.json": (
        "recovery_plus_share2/exact/all/min3/prior5/cur-0.05/distinct0.01"
    ),
    "clean_release_current_horse_row_output_agreement_selector_probe.json": (
        "expanded/combo/top5/combo1/horse0/pair0/cur-0.5/ov0.5/offline"
    ),
    "clean_release_current_horse_row_output_source_selector_probe.json": (
        "expanded/blend/all/min3/prior5/cur0.02/distinct0.01"
    ),
    "clean_release_current_horse_row_output_full_agreement_selector_probe.json": (
        "all_outputs/combo/top5/combo1/horse0/pair0/cur-0.5/ov0.5/offline"
    ),
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _best_selector_name(*, cache_dir: Path, file_name: str) -> str:
    payload = _read_json(cache_dir / file_name)
    best = payload.get("best")
    if isinstance(best, dict):
        selector_name = best.get("selector_spec")
        if isinstance(selector_name, str) and selector_name:
            return selector_name
    return ARTIFACT_SELECTOR_FALLBACKS[file_name]


def _find_spec(specs: tuple[Any, ...], *, name: str, source_name: str) -> Any:
    for spec in specs:
        if spec.name == name:
            return spec
    raise ValueError(f"Missing selector spec for {source_name}: {name}")


def _predict_agreement_output(
    *,
    predictions_by_window: dict[str, dict[str, dict[str, tuple[int, int, int]]]],
    current_payloads: dict[str, dict[str, Any]],
    windows: list[Any],
    component_sets: dict[str, tuple[str, ...]],
    spec: agreement.AgreementSpec,
) -> tuple[dict[str, dict[str, tuple[int, int, int]]], list[dict[str, Any]]]:
    predicted_by_window: dict[str, dict[str, tuple[int, int, int]]] = {}
    window_rows: list[dict[str, Any]] = []
    component_names = component_sets[spec.component_set]
    for window in windows:
        payload = current_payloads[window.name]
        if spec.component_score_weight > 0.0:
            predicted, diagnostics = agreement._predict_online_window(
                predictions_by_component=predictions_by_window[window.name],
                component_names=component_names,
                eval_answers=payload["eval_answers"],
                spec=spec,
            )
        else:
            predicted, diagnostics = agreement._predict_window(
                predictions_by_component=predictions_by_window[window.name],
                component_names=component_names,
                spec=spec,
            )
        predicted_by_window[window.name] = predicted
        window_rows.append(
            {
                "name": window.name,
                "summary": _summarize_predictions(predicted, payload["eval_answers"]),
                "diagnostics": diagnostics,
            }
        )
    return predicted_by_window, window_rows


def _predict_source_output(
    *,
    predictions_by_window: dict[str, dict[str, dict[str, tuple[int, int, int]]]],
    current_payloads: dict[str, dict[str, Any]],
    windows: list[Any],
    component_sets: dict[str, tuple[str, ...]],
    race_rows: dict[str, dict[str, Any]],
    spec: source_selector.OutputSourceSpec,
) -> tuple[dict[str, dict[str, tuple[int, int, int]]], list[dict[str, Any]]]:
    predicted_by_window: dict[str, dict[str, tuple[int, int, int]]] = {}
    window_rows: list[dict[str, Any]] = []
    component_names = component_sets[spec.component_set]
    for window in windows:
        payload = current_payloads[window.name]
        predicted, diagnostics = source_selector._predict_window(
            predictions_by_component=predictions_by_window[window.name],
            component_names=component_names,
            eval_answers=payload["eval_answers"],
            race_rows=race_rows,
            spec=spec,
        )
        predicted_by_window[window.name] = predicted
        window_rows.append(
            {
                "name": window.name,
                "summary": _summarize_predictions(predicted, payload["eval_answers"]),
                "diagnostics": diagnostics,
            }
        )
    return predicted_by_window, window_rows


def _load_broad_predictions(
    *,
    component_cache: Path,
    max_rank: int,
) -> tuple[dict[str, dict[str, dict[str, tuple[int, int, int]]]], dict[str, Any]]:
    payload = _read_json(component_cache)
    if (
        payload.get("selection_contract")
        != "captured_broad_clean_component_predictions"
        or payload.get("max_rank") != max_rank
    ):
        raise FileNotFoundError(
            "Missing captured broad clean component cache. Run a full-output "
            f"support probe first or provide --component-cache: {component_cache}"
        )
    return _load_json_predictions(payload), payload


def _selector_specs() -> tuple[source_selector.OutputSourceSpec, ...]:
    return tuple(
        source_selector.OutputSourceSpec(
            component_set=component_set,
            metric=metric,
            segmenter=segmenter,
            min_n=min_n,
            prior_weight=prior_weight,
            current_bias=current_bias,
            distinct_bonus=distinct_bonus,
        )
        for component_set in (
            "artifact_core",
            "artifact_plus_row_pattern",
            "artifact_plus_full_broad",
        )
        for metric in ("exact", "match", "blend")
        for segmenter in ("all", "field", "race_no_bucket", "meet_race_no_bucket")
        for min_n in (3, 10)
        for prior_weight in (5.0, 20.0, 80.0)
        for current_bias in (-0.05, 0.0, 0.02, 0.05)
        for distinct_bonus in (0.0, 0.01)
    )


def _window_names(windows: list[Any]) -> list[str]:
    return [str(window.name) for window in windows]


@dataclass(frozen=True, slots=True)
class ArtifactOutputBundle:
    windows: list[Any]
    current_payloads: dict[str, dict[str, Any]]
    race_rows: dict[str, dict[str, Any]]
    artifact_by_window: dict[str, dict[str, dict[str, tuple[int, int, int]]]]
    component_sets: dict[str, tuple[str, ...]]
    source_diagnostics: dict[str, Any]
    base_records: list[Any]
    aggregate_spec: str
    share2_aggregate_spec: str
    broad_payload: dict[str, Any]
    source_count: int


def build_artifact_output_bundle(
    *,
    config_path: Path,
    cache_dir: Path,
    policy_source: Path,
    max_rank: int,
    component_cache: Path,
) -> ArtifactOutputBundle:
    row_cache = _load_or_build_row_cache(
        config_path=config_path,
        cache_dir=cache_dir,
        refresh_cache=False,
    )
    race_rows = {str(row["race_id"]): row for row in row_cache["rows"]}
    windows, current_payloads, row_predictions, base_records, aggregate_spec = (
        agreement._build_component_predictions(
            config_path=config_path,
            cache_dir=cache_dir,
            policy_source=policy_source,
            max_rank=max_rank,
        )
    )
    window_names = _window_names(windows)
    broad_predictions, broad_payload = _load_broad_predictions(
        component_cache=component_cache,
        max_rank=max_rank,
    )
    if window_names != list(broad_predictions):
        raise ValueError("Row-feature and broad component windows do not align")

    share2_windows, share2_predictions, _share2_base, share2_aggregate = (
        share2_agreement._build_share2_predictions(
            config_path=config_path,
            cache_dir=cache_dir,
        )
    )
    if window_names != _window_names(share2_windows):
        raise ValueError("Row-feature and share2 windows do not align")
    hybrid_predictions = {
        window.name: dict(row_predictions[window.name]) for window in windows
    }
    for window in windows:
        hybrid_predictions[window.name].update(share2_predictions[window.name])

    artifact_predictions: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {
        "current": {
            window.name: row_predictions[window.name]["current"] for window in windows
        },
        "row_pattern_share2_formula_best": {
            window.name: share2_predictions[window.name]["share2_formula_horse_vote"]
            for window in windows
        },
    }
    source_diagnostics: dict[str, Any] = {
        "current": {"selector_spec": "current_component"},
        "row_pattern_share2_formula_best": {
            "selector_spec": "share2_formula_horse_vote"
        },
    }

    row_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_row_feature_output_agreement_selector_probe.json",
    )
    row_agreement_spec = _find_spec(
        agreement._selector_specs(),
        name=row_agreement_selector,
        source_name="row_feature_agreement_best",
    )
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=row_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=agreement._component_sets(),
        spec=row_agreement_spec,
    )
    artifact_predictions["row_feature_agreement_best"] = predicted
    source_diagnostics["row_feature_agreement_best"] = {
        "selector_spec": row_agreement_selector,
        "windows": diagnostics,
    }

    row_source_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_row_feature_output_source_selector_probe.json",
    )
    row_source_spec = _find_spec(
        source_selector._selector_specs(),
        name=row_source_selector,
        source_name="row_feature_source_best",
    )
    predicted, diagnostics = _predict_source_output(
        predictions_by_window=row_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=agreement._component_sets(),
        race_rows=race_rows,
        spec=row_source_spec,
    )
    artifact_predictions["row_feature_source_best"] = predicted
    source_diagnostics["row_feature_source_best"] = {
        "selector_spec": row_source_selector,
        "windows": diagnostics,
    }

    share2_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name=(
            "clean_release_current_row_feature_share2_output_agreement_selector_probe.json"
        ),
    )
    share2_agreement_spec = _find_spec(
        share2_agreement._selector_specs(),
        name=share2_agreement_selector,
        source_name="row_feature_share2_agreement_best",
    )
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=hybrid_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=share2_agreement._component_sets(),
        spec=share2_agreement_spec,
    )
    artifact_predictions["row_feature_share2_agreement_best"] = predicted
    source_diagnostics["row_feature_share2_agreement_best"] = {
        "selector_spec": share2_agreement_selector,
        "windows": diagnostics,
    }

    share2_source_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_row_feature_share2_output_source_selector_probe.json",
    )
    share2_source_spec = _find_spec(
        share2_source._selector_specs(),
        name=share2_source_selector,
        source_name="row_feature_share2_source_best",
    )
    predicted, diagnostics = _predict_source_output(
        predictions_by_window=hybrid_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=share2_agreement._component_sets(),
        race_rows=race_rows,
        spec=share2_source_spec,
    )
    artifact_predictions["row_feature_share2_source_best"] = predicted
    source_diagnostics["row_feature_share2_source_best"] = {
        "selector_spec": share2_source_selector,
        "windows": diagnostics,
    }

    broad_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_horse_row_output_agreement_selector_probe.json",
    )
    broad_agreement_spec = _find_spec(
        broad_agreement._selector_specs(),
        name=broad_agreement_selector,
        source_name="horse_row_agreement_best",
    )
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=broad_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=broad_agreement._component_sets(),
        spec=broad_agreement_spec,
    )
    artifact_predictions["horse_row_agreement_best"] = predicted
    source_diagnostics["horse_row_agreement_best"] = {
        "selector_spec": broad_agreement_selector,
        "windows": diagnostics,
    }

    broad_source_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_horse_row_output_source_selector_probe.json",
    )
    broad_source_specs = _broad_agreement_source_specs()
    broad_source_spec = _find_spec(
        broad_source_specs,
        name=broad_source_selector,
        source_name="horse_row_source_best",
    )
    predicted, diagnostics = _predict_source_output(
        predictions_by_window=broad_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=broad_agreement._component_sets(),
        race_rows=race_rows,
        spec=broad_source_spec,
    )
    artifact_predictions["horse_row_source_best"] = predicted
    source_diagnostics["horse_row_source_best"] = {
        "selector_spec": broad_source_selector,
        "selector_spec_count": len(broad_source_specs),
        "windows": diagnostics,
    }

    full_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_horse_row_output_full_agreement_selector_probe.json",
    )
    full_agreement_spec = _find_spec(
        full_agreement._selector_specs(),
        name=full_agreement_selector,
        source_name="horse_row_full_agreement_best",
    )
    full_component_names = tuple(broad_payload["components"])
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=broad_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets={"all_outputs": full_component_names},
        spec=full_agreement_spec.agreement_spec,
    )
    artifact_predictions["horse_row_full_agreement_best"] = predicted
    source_diagnostics["horse_row_full_agreement_best"] = {
        "selector_spec": full_agreement_selector,
        "windows": diagnostics,
    }

    artifact_by_window: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {}
    for source_name, by_window in artifact_predictions.items():
        for window_name, predictions in by_window.items():
            artifact_by_window.setdefault(window_name, {})[source_name] = predictions

    component_sets = {
        "artifact_core": (
            "current",
            "row_feature_agreement_best",
            "row_feature_source_best",
            "row_feature_share2_agreement_best",
            "row_feature_share2_source_best",
            "horse_row_agreement_best",
            "horse_row_source_best",
        ),
        "artifact_plus_row_pattern": (
            "current",
            "row_pattern_share2_formula_best",
            "row_feature_agreement_best",
            "row_feature_source_best",
            "row_feature_share2_agreement_best",
            "row_feature_share2_source_best",
            "horse_row_agreement_best",
            "horse_row_source_best",
        ),
        "artifact_plus_full_broad": (
            "current",
            "row_pattern_share2_formula_best",
            "row_feature_agreement_best",
            "row_feature_source_best",
            "row_feature_share2_agreement_best",
            "row_feature_share2_source_best",
            "horse_row_agreement_best",
            "horse_row_source_best",
            "horse_row_full_agreement_best",
        ),
    }
    return ArtifactOutputBundle(
        windows=windows,
        current_payloads=current_payloads,
        race_rows=race_rows,
        artifact_by_window=artifact_by_window,
        component_sets=component_sets,
        source_diagnostics=source_diagnostics,
        base_records=base_records,
        aggregate_spec=aggregate_spec,
        share2_aggregate_spec=share2_aggregate,
        broad_payload=broad_payload,
        source_count=len(artifact_predictions),
    )


def run_probe(
    *,
    config_path: Path,
    cache_dir: Path,
    output_path: Path,
    policy_source: Path,
    max_rank: int,
    component_cache: Path,
) -> dict[str, Any]:
    started = time.time()
    row_cache = _load_or_build_row_cache(
        config_path=config_path,
        cache_dir=cache_dir,
        refresh_cache=False,
    )
    race_rows = {str(row["race_id"]): row for row in row_cache["rows"]}
    windows, current_payloads, row_predictions, base_records, aggregate_spec = (
        agreement._build_component_predictions(
            config_path=config_path,
            cache_dir=cache_dir,
            policy_source=policy_source,
            max_rank=max_rank,
        )
    )
    window_names = _window_names(windows)
    broad_predictions, broad_payload = _load_broad_predictions(
        component_cache=component_cache,
        max_rank=max_rank,
    )
    if window_names != list(broad_predictions):
        raise ValueError("Row-feature and broad component windows do not align")

    share2_windows, share2_predictions, _share2_base, share2_aggregate = (
        share2_agreement._build_share2_predictions(
            config_path=config_path,
            cache_dir=cache_dir,
        )
    )
    if window_names != _window_names(share2_windows):
        raise ValueError("Row-feature and share2 windows do not align")
    hybrid_predictions = {
        window.name: dict(row_predictions[window.name]) for window in windows
    }
    for window in windows:
        hybrid_predictions[window.name].update(share2_predictions[window.name])

    artifact_predictions: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {
        "current": {
            window.name: row_predictions[window.name]["current"] for window in windows
        },
        "row_pattern_share2_formula_best": {
            window.name: share2_predictions[window.name]["share2_formula_horse_vote"]
            for window in windows
        },
    }
    source_diagnostics: dict[str, Any] = {
        "current": {"selector_spec": "current_component"},
        "row_pattern_share2_formula_best": {
            "selector_spec": "share2_formula_horse_vote"
        },
    }

    row_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_row_feature_output_agreement_selector_probe.json",
    )
    row_agreement_spec = _find_spec(
        agreement._selector_specs(),
        name=row_agreement_selector,
        source_name="row_feature_agreement_best",
    )
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=row_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=agreement._component_sets(),
        spec=row_agreement_spec,
    )
    artifact_predictions["row_feature_agreement_best"] = predicted
    source_diagnostics["row_feature_agreement_best"] = {
        "selector_spec": row_agreement_selector,
        "windows": diagnostics,
    }

    row_source_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_row_feature_output_source_selector_probe.json",
    )
    row_source_spec = _find_spec(
        source_selector._selector_specs(),
        name=row_source_selector,
        source_name="row_feature_source_best",
    )
    predicted, diagnostics = _predict_source_output(
        predictions_by_window=row_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=agreement._component_sets(),
        race_rows=race_rows,
        spec=row_source_spec,
    )
    artifact_predictions["row_feature_source_best"] = predicted
    source_diagnostics["row_feature_source_best"] = {
        "selector_spec": row_source_selector,
        "windows": diagnostics,
    }

    share2_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name=(
            "clean_release_current_row_feature_share2_output_agreement_selector_probe.json"
        ),
    )
    share2_agreement_spec = _find_spec(
        share2_agreement._selector_specs(),
        name=share2_agreement_selector,
        source_name="row_feature_share2_agreement_best",
    )
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=hybrid_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=share2_agreement._component_sets(),
        spec=share2_agreement_spec,
    )
    artifact_predictions["row_feature_share2_agreement_best"] = predicted
    source_diagnostics["row_feature_share2_agreement_best"] = {
        "selector_spec": share2_agreement_selector,
        "windows": diagnostics,
    }

    share2_source_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_row_feature_share2_output_source_selector_probe.json",
    )
    share2_source_spec = _find_spec(
        share2_source._selector_specs(),
        name=share2_source_selector,
        source_name="row_feature_share2_source_best",
    )
    predicted, diagnostics = _predict_source_output(
        predictions_by_window=hybrid_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=share2_agreement._component_sets(),
        race_rows=race_rows,
        spec=share2_source_spec,
    )
    artifact_predictions["row_feature_share2_source_best"] = predicted
    source_diagnostics["row_feature_share2_source_best"] = {
        "selector_spec": share2_source_selector,
        "windows": diagnostics,
    }

    broad_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_horse_row_output_agreement_selector_probe.json",
    )
    broad_agreement_spec = _find_spec(
        broad_agreement._selector_specs(),
        name=broad_agreement_selector,
        source_name="horse_row_agreement_best",
    )
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=broad_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=broad_agreement._component_sets(),
        spec=broad_agreement_spec,
    )
    artifact_predictions["horse_row_agreement_best"] = predicted
    source_diagnostics["horse_row_agreement_best"] = {
        "selector_spec": broad_agreement_selector,
        "windows": diagnostics,
    }

    broad_source_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_horse_row_output_source_selector_probe.json",
    )
    broad_source_specs = _broad_agreement_source_specs()
    broad_source_spec = _find_spec(
        broad_source_specs,
        name=broad_source_selector,
        source_name="horse_row_source_best",
    )
    predicted, diagnostics = _predict_source_output(
        predictions_by_window=broad_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets=broad_agreement._component_sets(),
        race_rows=race_rows,
        spec=broad_source_spec,
    )
    artifact_predictions["horse_row_source_best"] = predicted
    source_diagnostics["horse_row_source_best"] = {
        "selector_spec": broad_source_selector,
        "selector_spec_count": len(broad_source_specs),
        "windows": diagnostics,
    }

    full_agreement_selector = _best_selector_name(
        cache_dir=cache_dir,
        file_name="clean_release_current_horse_row_output_full_agreement_selector_probe.json",
    )
    full_agreement_spec = _find_spec(
        full_agreement._selector_specs(),
        name=full_agreement_selector,
        source_name="horse_row_full_agreement_best",
    )
    full_component_names = tuple(broad_payload["components"])
    predicted, diagnostics = _predict_agreement_output(
        predictions_by_window=broad_predictions,
        current_payloads=current_payloads,
        windows=windows,
        component_sets={"all_outputs": full_component_names},
        spec=full_agreement_spec.agreement_spec,
    )
    artifact_predictions["horse_row_full_agreement_best"] = predicted
    source_diagnostics["horse_row_full_agreement_best"] = {
        "selector_spec": full_agreement_selector,
        "windows": diagnostics,
    }

    artifact_by_window: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {}
    for source_name, by_window in artifact_predictions.items():
        for window_name, predictions in by_window.items():
            artifact_by_window.setdefault(window_name, {})[source_name] = predictions

    component_sets = {
        "artifact_core": (
            "current",
            "row_feature_agreement_best",
            "row_feature_source_best",
            "row_feature_share2_agreement_best",
            "row_feature_share2_source_best",
            "horse_row_agreement_best",
            "horse_row_source_best",
        ),
        "artifact_plus_row_pattern": (
            "current",
            "row_pattern_share2_formula_best",
            "row_feature_agreement_best",
            "row_feature_source_best",
            "row_feature_share2_agreement_best",
            "row_feature_share2_source_best",
            "horse_row_agreement_best",
            "horse_row_source_best",
        ),
        "artifact_plus_full_broad": (
            "current",
            "row_pattern_share2_formula_best",
            "row_feature_agreement_best",
            "row_feature_source_best",
            "row_feature_share2_agreement_best",
            "row_feature_share2_source_best",
            "horse_row_agreement_best",
            "horse_row_source_best",
            "horse_row_full_agreement_best",
        ),
    }

    results: list[dict[str, Any]] = []
    selectors = _selector_specs()
    for selector_index, selector in enumerate(selectors, start=1):
        window_rows: list[dict[str, Any]] = []
        component_names = component_sets[selector.component_set]
        for window in windows:
            predicted, diagnostics = source_selector._predict_window(
                predictions_by_component=artifact_by_window[window.name],
                component_names=component_names,
                eval_answers=current_payloads[window.name]["eval_answers"],
                race_rows=race_rows,
                spec=selector,
            )
            summary = _summarize_predictions(
                predicted,
                current_payloads[window.name]["eval_answers"],
            )
            window_rows.append(
                {
                    "name": window.name,
                    "summary": summary,
                    "diagnostics": diagnostics,
                }
            )
        results.append(
            {
                "candidate": (
                    "clean_top_clean_artifact_source/"
                    f"max{max_rank}/{selector.name}"
                ),
                "selector_spec": selector.name,
                "summary": source_selector._window_summary(window_rows),
                "windows": window_rows,
            }
        )
        if selector_index % 216 == 0:
            print(
                json.dumps(
                    {
                        "selector": selector_index,
                        "selector_count": len(selectors),
                        "best_so_far": max(
                            row["summary"]["overfit_safe_exact_rate"]
                            for row in results
                        ),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    results.sort(key=_candidate_key, reverse=True)
    payload = {
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Clean strict-prior-date source selector over reconstructed top "
            "clean artifact outputs. Each source emits one unordered top-3 "
            "combination per race from its own clean train-window-only "
            "procedure; the meta-selector chooses one source per race using "
            "only earlier evaluation dates for source history. Promotion still "
            "requires the exact 70% gate."
        ),
        "candidate_count": len(results),
        "max_rank": max_rank,
        "selector_count": len(selectors),
        "selection_contract": "strict_prior_date_top_clean_artifact_output_source",
        "component_cache": str(component_cache),
        "base_specs": base_records,
        "aggregate_spec": aggregate_spec,
        "share2_aggregate_spec": share2_aggregate,
        "source_count": len(artifact_predictions),
        "sources": list(artifact_predictions),
        "components_by_set": {
            name: list(components) for name, components in component_sets.items()
        },
        "source_diagnostics": source_diagnostics,
        "broad_component_count": broad_payload["component_count"],
        "broad_oracle_ceiling_summary": broad_payload["oracle_ceiling_summary"],
        "best": results[0],
        "max_test_exact_3of3_rate": max(
            row["summary"]["test_exact_3of3_rate"] for row in results
        ),
        "max_overfit_safe_exact_rate": max(
            row["summary"]["overfit_safe_exact_rate"] for row in results
        ),
        "ge_70_test_count": sum(
            1 for row in results if row["summary"]["test_exact_3of3_rate"] >= 0.7
        ),
        "ge_70_safe_count": sum(
            1 for row in results if row["summary"]["overfit_safe_exact_rate"] >= 0.7
        ),
        "results": results,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def _broad_agreement_source_specs() -> tuple[source_selector.OutputSourceSpec, ...]:
    return tuple(
        source_selector.OutputSourceSpec(
            component_set=component_set,
            metric=metric,
            segmenter=segmenter,
            min_n=min_n,
            prior_weight=prior_weight,
            current_bias=current_bias,
            distinct_bonus=distinct_bonus,
        )
        for component_set in broad_agreement._component_sets()
        for metric in ("exact", "match", "blend")
        for segmenter in ("all", "field", "race_no_bucket", "meet_race_no_bucket")
        for min_n in (3, 10)
        for prior_weight in (5.0, 20.0, 80.0)
        for current_bias in (-0.1, -0.05, 0.0, 0.02, 0.05)
        for distinct_bonus in (0.0, 0.01)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--policy-source", type=Path, default=DEFAULT_POLICY_SOURCE)
    parser.add_argument("--max-rank", type=int, default=10)
    parser.add_argument("--component-cache", type=Path, default=DEFAULT_COMPONENT_CACHE)
    args = parser.parse_args()
    payload = run_probe(
        config_path=args.config,
        cache_dir=args.cache_dir,
        output_path=args.output,
        policy_source=args.policy_source,
        max_rank=args.max_rank,
        component_cache=args.component_cache,
    )
    print(
        json.dumps(
            {
                "candidate_count": payload["candidate_count"],
                "source_count": payload["source_count"],
                "max_overfit_safe_exact_rate": payload[
                    "max_overfit_safe_exact_rate"
                ],
                "max_test_exact_3of3_rate": payload["max_test_exact_3of3_rate"],
                "ge_70_safe_count": payload["ge_70_safe_count"],
                "elapsed_seconds": payload["elapsed_seconds"],
                "best": payload["best"]["candidate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("best", payload["best"]["candidate"], payload["best"]["summary"])
    print("output", str(args.output))


if __name__ == "__main__":
    main()
