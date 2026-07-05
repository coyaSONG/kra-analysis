"""Complement diagnostic for current-best plus broad clean component outputs."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_full_field_one_swap_static_repair_diagnostic as static_repair,
)
from autoresearch import (  # noqa: E402
    clean_release_top_clean_artifact_source_selector_probe as artifact_source,
)
from autoresearch.clean_release_row_feature_full_policy_classifier_probe import (  # noqa: E501
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)

DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / (
    "adhoc_current_best_broad_component_output_complement_diagnostic.json"
)
FORMAT_VERSION = "adhoc-current-best-broad-component-complement-v1"


def _combo_key(combo: Any) -> tuple[int, int, int]:
    return tuple(sorted(int(chul_no) for chul_no in combo[:3]))


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _rate(values: list[bool]) -> float:
    return round(_safe_mean([float(value) for value in values]), 6)


def _window_answers_only(
    *,
    config_path: Path,
    cache_dir: Path,
) -> dict[str, dict[str, list[int]]]:
    config = static_repair._read_json(config_path)
    row_cache = static_repair._load_or_build_row_cache(
        config_path=config_path,
        cache_dir=cache_dir,
        refresh_cache=False,
    )
    rows = row_cache["rows"]
    answers = row_cache["answers"]
    dates = np.array([row["race_date"] for row in rows])
    windows = static_repair._window_specs(dates, config)
    return {
        window.name: static_repair._window_answers(
            answers,
            train_end=window.train_end,
            eval_start=window.eval_start,
            eval_end=window.eval_end,
        )
        for window in windows
    }


def _summarize_window(
    *,
    window_name: str,
    answers: dict[str, list[int]],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
) -> dict[str, Any]:
    component_names = tuple(sorted(component_predictions))
    fallback_exact_values: list[bool] = []
    pool_values: list[bool] = []
    current_miss_recovery_values: list[bool] = []
    distinct_counts: list[float] = []
    component_exact_counts: dict[str, Counter[str]] = {
        name: Counter() for name in component_names
    }

    for race_id in sorted(answers):
        fallback_combo = current_best_predictions.get(race_id)
        if fallback_combo is None:
            continue
        answer_combo = _combo_key(answers[race_id])
        fallback_combo = _combo_key(fallback_combo)
        fallback_exact = fallback_combo == answer_combo
        distinct_outputs: set[tuple[int, int, int]] = set()
        component_exact_available = False
        for component_name in component_names:
            combo = component_predictions[component_name].get(race_id)
            if combo is None:
                continue
            combo_key = _combo_key(combo)
            distinct_outputs.add(combo_key)
            component_exact = combo_key == answer_combo
            component_exact_available = component_exact_available or component_exact
            component_exact_counts[component_name]["count"] += 1
            component_exact_counts[component_name]["exact"] += int(component_exact)
            component_exact_counts[component_name]["current_miss_exact"] += int(
                (not fallback_exact) and component_exact
            )
        fallback_exact_values.append(fallback_exact)
        pool_values.append(fallback_exact or component_exact_available)
        current_miss_recovery_values.append((not fallback_exact) and component_exact_available)
        distinct_counts.append(float(len(distinct_outputs)))

    top_components: list[dict[str, Any]] = []
    for component_name, counts in component_exact_counts.items():
        count = max(int(counts["count"]), 1)
        top_components.append(
            {
                "component": component_name,
                "count": int(counts["count"]),
                "exact_rate": round(float(counts["exact"]) / count, 6),
                "current_miss_exact_count": int(counts["current_miss_exact"]),
            }
        )
    top_components.sort(
        key=lambda row: (
            row["current_miss_exact_count"],
            row["exact_rate"],
            row["component"],
        ),
        reverse=True,
    )
    fallback_miss_count = sum(not value for value in fallback_exact_values)
    return {
        "name": window_name,
        "race_count": len(fallback_exact_values),
        "component_count": len(component_names),
        "fallback_exact_rate": _rate(fallback_exact_values),
        "fallback_plus_broad_component_pool_exact_rate": _rate(pool_values),
        "current_miss_recovery_count": int(sum(current_miss_recovery_values)),
        "current_miss_recovery_rate": round(
            float(sum(current_miss_recovery_values)) / max(fallback_miss_count, 1),
            6,
        ),
        "avg_distinct_component_outputs": round(_safe_mean(distinct_counts), 3),
        "top_components_by_current_miss_exact": top_components[:12],
    }


def run_diagnostic(
    *,
    config_path: Path,
    cache_dir: Path,
    output_path: Path,
    source_artifact: Path,
    component_cache: Path,
    max_rank: int,
) -> dict[str, Any]:
    started = time.time()
    answers_by_window = _window_answers_only(
        config_path=config_path,
        cache_dir=cache_dir,
    )
    current_best_by_window = static_repair._load_source_predictions(source_artifact)
    broad_predictions, broad_payload = artifact_source._load_broad_predictions(
        component_cache=component_cache,
        max_rank=max_rank,
    )
    windows = [
        _summarize_window(
            window_name=window_name,
            answers=answers,
            current_best_predictions=current_best_by_window[window_name],
            component_predictions=broad_predictions[window_name],
        )
        for window_name, answers in answers_by_window.items()
    ]
    robust_pool = round(
        min(row["fallback_plus_broad_component_pool_exact_rate"] for row in windows),
        6,
    )
    payload = {
        "format_version": FORMAT_VERSION,
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Measures nonpromotion complement coverage when the exact "
            "current-best reproduction is used as fallback and every cached "
            "broad clean component output is added as a candidate alternative. "
            "Eval labels are used only for pool/complement diagnostics, not "
            "for deployable selection."
        ),
        "source_artifact": str(source_artifact),
        "component_cache": str(component_cache),
        "max_rank": max_rank,
        "component_count": int(broad_payload["component_count"]),
        "component_oracle_ceiling_summary": broad_payload["oracle_ceiling_summary"],
        "robust_fallback_plus_broad_component_pool_exact_rate": robust_pool,
        "windows": windows,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--source-artifact",
        type=Path,
        default=static_repair.DEFAULT_SOURCE_ARTIFACT,
    )
    parser.add_argument(
        "--component-cache",
        type=Path,
        default=artifact_source.DEFAULT_COMPONENT_CACHE,
    )
    parser.add_argument("--max-rank", type=int, default=10)
    args = parser.parse_args()
    payload = run_diagnostic(
        config_path=args.config,
        cache_dir=args.cache_dir,
        output_path=args.output,
        source_artifact=args.source_artifact,
        component_cache=args.component_cache,
        max_rank=args.max_rank,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "component_count": payload["component_count"],
                "robust_fallback_plus_broad_component_pool_exact_rate": payload[
                    "robust_fallback_plus_broad_component_pool_exact_rate"
                ],
                "elapsed_seconds": payload["elapsed_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
