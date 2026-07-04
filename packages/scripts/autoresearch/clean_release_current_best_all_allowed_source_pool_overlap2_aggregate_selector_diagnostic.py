"""Overlap-2 aggregate selector over all-allowed source-pool candidates."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_prior_date_selector_diagnostic as base,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_source_meta_extension_prior_date_selector_diagnostic as source_meta,
)
from autoresearch.clean_release_direct_history_combo_probe import (  # noqa: E402
    _window_specs,
)
from autoresearch.clean_release_row_feature_rank_pattern_probe import (  # noqa: E402
    _build_rank_and_hit_caches,
    _race_rows,
)
from autoresearch.clean_top50_history_overlay_probe import (  # noqa: E402
    _candidate_key,
    _summarize_predictions,
    _window_answers,
)
from autoresearch.search_clean_model import _read_json  # noqa: E402

DEFAULT_SOURCE_ARTIFACT = base.DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_ranker_source_meta_extension_"
    "after_variant_calibration_prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_OUTPUT = base.DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_overlap2_aggregate_"
    "selector_diagnostic.json"
)
FORMAT_VERSION = "current-best-all-allowed-source-pool-overlap2-aggregate-selector-v1"
TARGET_EXACT_RATE = 0.70


@dataclass(frozen=True, slots=True)
class AggregateSpec:
    add_weight: float
    drop_weight: float
    pair_weight: float
    switch_bias: float

    @property
    def name(self) -> str:
        return (
            f"add{self.add_weight:g}"
            f"/drop{self.drop_weight:g}"
            f"/pair{self.pair_weight:g}"
            f"/bias{self.switch_bias:g}"
        )


def _source_group_specs() -> tuple[base.SourceGroupSpec, ...]:
    return (
        base.SourceGroupSpec(source_count=100, metric="match", rank_weight=0.0),
        base.SourceGroupSpec(source_count=200, metric="match", rank_weight=0.0),
        base.SourceGroupSpec(source_count=100, metric="exact", rank_weight=0.0),
        base.SourceGroupSpec(source_count=200, metric="exact", rank_weight=0.0),
    )


def _aggregate_specs() -> tuple[AggregateSpec, ...]:
    return tuple(
        AggregateSpec(
            add_weight=add_weight,
            drop_weight=drop_weight,
            pair_weight=pair_weight,
            switch_bias=switch_bias,
        )
        for add_weight in (0.0, 0.10, 0.25, 0.50, 1.0)
        for drop_weight in (0.0, 0.10, 0.25)
        for pair_weight in (0.0, 0.10, 0.25)
        for switch_bias in (0.0, 0.05, 0.10, 0.20, 0.40, 0.80)
    )


def _combo_key(combo: tuple[int, ...] | list[int]) -> tuple[int, int, int]:
    return tuple(sorted(int(chul_no) for chul_no in combo[:3]))


def _window_level_summary(window_rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = base._window_level_summary(window_rows)
    return {
        **summary,
        "robust_pool_oracle_exact_rate": summary["overfit_safe_exact_rate"],
    }


def _candidate_score(
    *,
    row: dict[str, Any],
    fallback_combo: tuple[int, int, int],
    horse_scores: dict[int, float],
    pair_scores: dict[tuple[int, int], float],
    spec: AggregateSpec,
) -> float:
    combo = row["combo"]
    fallback_set = set(fallback_combo)
    combo_set = set(combo)
    added = combo_set - fallback_set
    dropped = fallback_set - combo_set
    kept_pair = tuple(sorted(combo_set & fallback_set))
    return (
        float(row["source_score"])
        + spec.add_weight * sum(horse_scores[horse] for horse in added)
        - spec.drop_weight * sum(horse_scores[horse] for horse in dropped)
        + spec.pair_weight * pair_scores.get(kept_pair, 0.0)
    )


def _select_overlap2_predictions(
    *,
    rows_by_race: dict[str, list[dict[str, Any]]],
    fallback_predictions: dict[str, tuple[int, int, int]],
    source_group: base.SourceGroupSpec,
    spec: AggregateSpec,
) -> tuple[dict[str, tuple[int, int, int]], dict[str, Any]]:
    predictions: dict[str, tuple[int, int, int]] = {}
    switch_flags: list[float] = []
    switched_exact_flags: list[float] = []
    selected_scores: list[float] = []
    for race_id, fallback_combo in fallback_predictions.items():
        rows = rows_by_race.get(race_id, [])
        fallback_set = set(fallback_combo)
        horse_scores: dict[int, float] = defaultdict(float)
        pair_scores: dict[tuple[int, int], float] = defaultdict(float)
        for row in rows:
            combo = row["combo"]
            weight = (
                float(row["source_score"])
                + float(row["source_support"]) / max(source_group.source_count, 1)
            )
            for horse in combo:
                horse_scores[int(horse)] += weight
            for pair in itertools.combinations(combo, 2):
                pair_scores[tuple(sorted(int(chul_no) for chul_no in pair))] += weight
        fallback_score = next(
            (float(row["source_score"]) for row in rows if row["combo"] == fallback_combo),
            0.0,
        )
        candidates = [
            row
            for row in rows
            if row["combo"] != fallback_combo
            and len(set(row["combo"]) & fallback_set) == 2
        ]
        if not candidates:
            predictions[race_id] = fallback_combo
            switch_flags.append(0.0)
            switched_exact_flags.append(0.0)
            selected_scores.append(fallback_score)
            continue
        best = max(
            candidates,
            key=lambda row: (
                _candidate_score(
                    row=row,
                    fallback_combo=fallback_combo,
                    horse_scores=horse_scores,
                    pair_scores=pair_scores,
                    spec=spec,
                ),
                float(row["source_support"]),
                tuple(-int(chul_no) for chul_no in row["combo"]),
            ),
        )
        best_score = _candidate_score(
            row=best,
            fallback_combo=fallback_combo,
            horse_scores=horse_scores,
            pair_scores=pair_scores,
            spec=spec,
        )
        if best_score >= fallback_score + spec.switch_bias:
            predictions[race_id] = best["combo"]
            switch_flags.append(1.0)
            switched_exact_flags.append(float(best.get("exact_label", 0.0)))
            selected_scores.append(best_score)
        else:
            predictions[race_id] = fallback_combo
            switch_flags.append(0.0)
            switched_exact_flags.append(0.0)
            selected_scores.append(fallback_score)
    return predictions, {
        "selector": "overlap2_aggregate",
        "switch_rate": float(np.mean(switch_flags)) if switch_flags else 0.0,
        "switched_exact_rate": float(np.mean(switched_exact_flags))
        if switched_exact_flags
        else 0.0,
        "selected_score_mean": float(np.mean(selected_scores)) if selected_scores else 0.0,
        "selection_uses_labels": False,
    }


def run_probe(
    *,
    config_path: Path,
    source_artifact: Path,
    row_cache_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    started = time.time()
    config = _read_json(config_path)
    source_predictions = base.vote.current_best._load_source_predictions(source_artifact)
    row_cache = base.vote.current_best._load_row_cache(row_cache_path)
    rows = row_cache["rows"]
    answers = {
        str(race_id): list(answer[:3])
        for race_id, answer in row_cache["answers"].items()
    }
    dates = np.asarray([row["race_date"] for row in rows])
    windows = tuple(_window_specs(dates, config))
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

    source_group_specs = _source_group_specs()
    aggregate_specs = _aggregate_specs()
    answers_by_window: dict[str, dict[str, list[int]]] = {}
    fallback_by_window: dict[str, dict[str, tuple[int, int, int]]] = {}
    prepared: dict[tuple[str, str], dict[str, Any]] = {}
    for window in windows:
        eval_answers = _window_answers(
            answers,
            train_end=window.train_end,
            eval_start=window.eval_start,
            eval_end=window.eval_end,
        )
        answers_by_window[window.name] = eval_answers
        fallback_eval = {
            race_id: _combo_key(combo)
            for race_id, combo in source_predictions.get(window.name, {}).items()
            if race_id in eval_answers
        }
        fallback_by_window[window.name] = fallback_eval
        train_race_ids = [
            race_id
            for race_id in race_ids
            if str(race_id)[:8] <= window.train_end
        ]
        train_indices = [race_index_by_id[race_id] for race_id in train_race_ids]
        for source_group in source_group_specs:
            sources = base.vote._selected_sources(
                hit_cache=hit_cache,
                train_indices=train_indices,
                patterns=patterns,
                source_count=source_group.source_count,
                metric=source_group.metric,
            )
            eval_rows_by_race: dict[str, list[dict[str, Any]]] = {}
            for race_id, fallback_combo in fallback_eval.items():
                eval_rows_by_race[race_id] = (
                    source_meta._source_meta_candidate_rows_for_race(
                        race_id=race_id,
                        race_rows=rows_by_race.get(race_id, []),
                        sources=sources,
                        ranked_cache=ranked_cache,
                        spec=source_group,
                        answer=eval_answers.get(race_id),
                        fallback_combo=fallback_combo,
                    )
                )
            prepared[(window.name, source_group.name)] = {
                "eval_rows_by_race": eval_rows_by_race,
                "pool_oracle_exact_rate": base._pool_oracle_rate(
                    eval_rows_by_race=eval_rows_by_race,
                    fallback_predictions=fallback_eval,
                    eval_answers=eval_answers,
                ),
                "source_count": len(sources),
            }

    results: list[dict[str, Any]] = []
    fallback_window_rows: list[dict[str, Any]] = []
    for window in windows:
        summary = _summarize_predictions(
            fallback_by_window[window.name],
            answers_by_window[window.name],
        )
        fallback_window_rows.append(
            {
                "name": window.name,
                "summary": summary,
                "diagnostics": {
                    "selector": "fallback_only",
                    "switch_rate": 0.0,
                    "pool_oracle_exact_rate": summary["exact_3of3_rate"],
                    "selection_uses_labels": False,
                },
            }
        )
    results.append(
        {
            "candidate": "clean_current_best_all_allowed_source_pool_overlap2_aggregate/fallback_only",
            "source_group_spec": "fallback_only",
            "selector_spec": "fallback_only",
            "summary": _window_level_summary(fallback_window_rows),
            "windows": fallback_window_rows,
        }
    )
    predictions_by_candidate: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {}
    for source_group in source_group_specs:
        for aggregate_spec in aggregate_specs:
            window_rows: list[dict[str, Any]] = []
            predictions_by_window: dict[str, dict[str, tuple[int, int, int]]] = {}
            for window in windows:
                payload = prepared[(window.name, source_group.name)]
                selected, diagnostics = _select_overlap2_predictions(
                    rows_by_race=payload["eval_rows_by_race"],
                    fallback_predictions=fallback_by_window[window.name],
                    source_group=source_group,
                    spec=aggregate_spec,
                )
                predictions_by_window[window.name] = selected
                summary = _summarize_predictions(
                    selected,
                    answers_by_window[window.name],
                )
                window_rows.append(
                    {
                        "name": window.name,
                        "summary": summary,
                        "diagnostics": {
                            **diagnostics,
                            "pool_oracle_exact_rate": payload[
                                "pool_oracle_exact_rate"
                            ],
                            "source_count": payload["source_count"],
                        },
                    }
                )
            summary = _window_level_summary(window_rows)
            candidate_name = (
                "clean_current_best_all_allowed_source_pool_overlap2_aggregate/"
                f"{source_group.name}/{aggregate_spec.name}"
            )
            results.append(
                {
                    "candidate": candidate_name,
                    "source_group_spec": source_group.name,
                    "selector_spec": aggregate_spec.name,
                    "summary": {
                        **summary,
                        "robust_pool_oracle_exact_rate": round(
                            min(
                                row["diagnostics"]["pool_oracle_exact_rate"]
                                for row in window_rows
                            ),
                            6,
                        ),
                    },
                    "windows": window_rows,
                }
            )
            predictions_by_candidate[candidate_name] = predictions_by_window

    results.sort(key=_candidate_key, reverse=True)
    best = results[0]
    best_predictions_by_window = (
        fallback_by_window
        if best["selector_spec"] == "fallback_only"
        else predictions_by_candidate[best["candidate"]]
    )
    payload = {
        "format_version": FORMAT_VERSION,
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Clean strict-prior-date overlap-2 aggregate selector over the "
            "all-allowed source pool. Source policies are selected only from "
            "races at or before each locked train_end; per-race selection uses "
            "only clean source support aggregates, no target-window labels, "
            "and emits one unordered top-3 combo."
        ),
        "selection_contract": "one_unordered_top3_combo_per_race",
        "timing_contract": (
            "strict train_end source selection; no odds, no race-id key, no "
            "target-window labels in selection"
        ),
        "target_exact_rate": TARGET_EXACT_RATE,
        "source_artifact": str(source_artifact),
        "row_cache": str(row_cache_path),
        "row_cache_format_version": row_cache.get("format_version"),
        "feature_names": list(features),
        "excluded_feature_names": list(base.vote.EXCLUDED_FEATURE_NAMES),
        "source_group_spec_count": len(source_group_specs),
        "selector_spec_count": len(aggregate_specs),
        "candidate_count": len(results),
        "best": best,
        "max_test_exact_3of3_rate": max(
            row["summary"]["test_exact_3of3_rate"] for row in results
        ),
        "max_overfit_safe_exact_rate": max(
            row["summary"]["overfit_safe_exact_rate"] for row in results
        ),
        "max_robust_pool_oracle_exact_rate": max(
            row["summary"].get(
                "robust_pool_oracle_exact_rate",
                row["summary"]["overfit_safe_exact_rate"],
            )
            for row in results
        ),
        "ge_70_test_count": sum(
            1 for row in results if row["summary"]["test_exact_3of3_rate"] >= 0.70
        ),
        "ge_70_safe_count": sum(
            1 for row in results if row["summary"]["overfit_safe_exact_rate"] >= 0.70
        ),
        "predictions_by_window": {
            window_name: {
                race_id: list(combo)
                for race_id, combo in predictions.items()
            }
            for window_name, predictions in best_predictions_by_window.items()
        },
        "results": results,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=base.DEFAULT_CONFIG)
    parser.add_argument("--source-artifact", type=Path, default=DEFAULT_SOURCE_ARTIFACT)
    parser.add_argument("--row-cache", type=Path, default=base.DEFAULT_ROW_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = run_probe(
        config_path=args.config,
        source_artifact=args.source_artifact,
        row_cache_path=args.row_cache,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "candidate_count": payload["candidate_count"],
                "max_overfit_safe_exact_rate": payload[
                    "max_overfit_safe_exact_rate"
                ],
                "max_test_exact_3of3_rate": payload["max_test_exact_3of3_rate"],
                "max_robust_pool_oracle_exact_rate": payload[
                    "max_robust_pool_oracle_exact_rate"
                ],
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
