"""Rank-segment prior-date selector over current-best plus broad outputs."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    adhoc_current_best_broad_component_output_complement_diagnostic as complement,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_gain_loss_prior_date_selector_diagnostic as gain_loss,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_prior_date_selector_diagnostic as broad_selector,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_source_score_selector_diagnostic as source_score,
)
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
from autoresearch.clean_release_row_feature_full_policy_output_agreement_prior_date_classifier_switch_probe import (  # noqa: E501
    _window_summary,
)
from autoresearch.clean_top50_history_overlay_probe import (  # noqa: E402
    _candidate_key,
    _summarize_predictions,
)

DEFAULT_SOURCE_ARTIFACT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_top15_full_output_support_prior_date_"
    "classifier_selector_rerun_repro_diagnostic.json"
)
DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_rank_segment_prior_date_"
    "selector_diagnostic.json"
)


@dataclass(frozen=True, slots=True)
class ChoiceSpec:
    segment_profile: str
    min_rows: int
    min_gains: int
    shrink_rows: float
    loss_weight: float
    switch_margin: float
    max_surface_rank: int

    @property
    def name(self) -> str:
        return (
            f"seg{self.segment_profile}"
            f"/rows{self.min_rows}"
            f"/gains{self.min_gains}"
            f"/shrink{self.shrink_rows:g}"
            f"/loss{self.loss_weight:g}"
            f"/margin{self.switch_margin:g}"
            f"/maxrank{self.max_surface_rank}"
        )


@dataclass(slots=True)
class SegmentStats:
    count: int = 0
    exact_sum: float = 0.0
    fallback_exact_sum: float = 0.0
    gain_sum: float = 0.0
    loss_sum: float = 0.0
    delta_sum: float = 0.0


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _surface_specs() -> tuple[gain_loss.SurfaceSpec, ...]:
    return (
        gain_loss.SurfaceSpec("base/cur0/minsupport1", 2),
        gain_loss.SurfaceSpec("base/cur0/minsupport1", 3),
        gain_loss.SurfaceSpec("base/cur0/minsupport1", 5),
        gain_loss.SurfaceSpec("prior_exact/cur0.3/minsupport1", 3),
        gain_loss.SurfaceSpec("prior_exact/cur0.3/minsupport1", 5),
        gain_loss.SurfaceSpec("prior_hit2/cur0.3/minsupport1", 3),
        gain_loss.SurfaceSpec("prior_hit2/cur0.3/minsupport1", 5),
        gain_loss.SurfaceSpec("agreement_prior/cur0/minsupport1", 3),
    )


def _choice_specs(*, grid_name: str) -> tuple[ChoiceSpec, ...]:
    if grid_name == "focused":
        grid = {
            "segment_profiles": (
                "rank",
                "rank_support",
                "rank_overlap",
                "rank_support_overlap",
                "rank_score",
                "rank_prior",
            ),
            "min_rows": (5, 10, 20),
            "min_gains": (1, 2),
            "shrink_rows": (0.0, 12.0),
            "loss_weights": (0.75, 1.25),
            "switch_margins": (0.0, 0.03),
            "max_surface_ranks": (1, 2, 3),
        }
    elif grid_name == "aggressive":
        grid = {
            "segment_profiles": (
                "rank",
                "rank_support",
                "rank_overlap",
                "rank_score",
            ),
            "min_rows": (1, 3, 5, 10),
            "min_gains": (0, 1),
            "shrink_rows": (0.0,),
            "loss_weights": (0.0, 0.25, 0.75),
            "switch_margins": (-0.05, -0.02, 0.0),
            "max_surface_ranks": (1, 2, 3, 5),
        }
    else:
        raise ValueError(f"Unknown grid name: {grid_name}")

    return tuple(
        ChoiceSpec(
            segment_profile=segment_profile,
            min_rows=min_rows,
            min_gains=min_gains,
            shrink_rows=shrink_rows,
            loss_weight=loss_weight,
            switch_margin=switch_margin,
            max_surface_rank=max_surface_rank,
        )
        for segment_profile in grid["segment_profiles"]
        for min_rows in grid["min_rows"]
        for min_gains in grid["min_gains"]
        for shrink_rows in grid["shrink_rows"]
        for loss_weight in grid["loss_weights"]
        for switch_margin in grid["switch_margins"]
        for max_surface_rank in grid["max_surface_ranks"]
    )


def _score_spec_by_name() -> dict[str, source_score.SourceScoreSpec]:
    return {spec.name: spec for spec in source_score._selector_specs()}


def _prediction_payload(
    predictions: dict[str, tuple[int, int, int]],
) -> dict[str, list[int]]:
    return {race_id: list(combo) for race_id, combo in sorted(predictions.items())}


def _bucket(value: float, thresholds: tuple[float, ...]) -> int:
    for index, threshold in enumerate(thresholds):
        if value < threshold:
            return index
    return len(thresholds)


def _signed_bucket(value: float) -> str:
    if value <= -0.08:
        return "neg2"
    if value < -0.02:
        return "neg1"
    if value <= 0.02:
        return "flat"
    if value < 0.08:
        return "pos1"
    return "pos2"


def _support_bucket(row: dict[str, Any]) -> int:
    return _bucket(float(row["support_count"]), (1.5, 2.5, 3.5, 5.5, 8.5))


def _score_bucket(row: dict[str, Any]) -> int:
    return _bucket(float(row["surface_score"]), (0.20, 0.30, 0.40, 0.55, 0.75))


def _prior_bucket(row: dict[str, Any]) -> str:
    exact_bin = _bucket(float(row["source_exact_mean"]), (0.25, 0.35, 0.45))
    hit2_bin = _bucket(float(row["source_hit2_mean"]), (0.65, 0.75, 0.85))
    return f"e{exact_bin}:h{hit2_bin}"


def _segment_key(row: dict[str, Any], profile: str) -> str:
    rank = int(float(row["surface_rank"]))
    if profile == "rank":
        return f"r{rank}"
    if profile == "rank_support":
        return f"r{rank}:s{_support_bucket(row)}"
    if profile == "rank_overlap":
        return f"r{rank}:o{int(float(row['current_overlap']))}"
    if profile == "rank_support_overlap":
        return (
            f"r{rank}:s{_support_bucket(row)}"
            f":o{int(float(row['current_overlap']))}"
        )
    if profile == "rank_score":
        return (
            f"r{rank}:score{_score_bucket(row)}"
            f":d{_signed_bucket(float(row['surface_score_delta']))}"
        )
    if profile == "rank_prior":
        return f"r{rank}:prior{_prior_bucket(row)}"
    raise ValueError(f"Unknown segment profile: {profile}")


def _add_segment_row(stats: SegmentStats, row: dict[str, Any]) -> None:
    exact = float(row["exact_label"])
    fallback_exact = float(row["fallback_exact_label"])
    delta = exact - fallback_exact
    stats.count += 1
    stats.exact_sum += exact
    stats.fallback_exact_sum += fallback_exact
    stats.gain_sum += float(delta > 0.0)
    stats.loss_sum += float(delta < 0.0)
    stats.delta_sum += delta


def _segment_score(
    row: dict[str, Any],
    *,
    stats: SegmentStats,
    spec: ChoiceSpec,
) -> tuple[float, dict[str, float]]:
    if stats.count < spec.min_rows or stats.gain_sum < spec.min_gains:
        return float("-inf"), {
            "segment_count": float(stats.count),
            "segment_delta": 0.0,
            "segment_gain_rate": 0.0,
            "segment_loss_rate": 0.0,
            "segment_exact_rate": 0.0,
        }

    count = float(stats.count)
    shrunk_delta = stats.delta_sum / (count + spec.shrink_rows)
    gain_rate = stats.gain_sum / count
    loss_rate = stats.loss_sum / count
    exact_rate = stats.exact_sum / count
    fallback_exact_rate = stats.fallback_exact_sum / count
    score = (
        shrunk_delta
        + 0.35 * gain_rate
        - spec.loss_weight * loss_rate
        + 0.15 * (exact_rate - fallback_exact_rate)
        + 0.01 * float(row["surface_rank_score"])
        + 0.005 * float(row["support_fraction_delta"])
        - 0.004 * float(row["surface_rank"])
        - spec.switch_margin
    )
    return score, {
        "segment_count": count,
        "segment_delta": shrunk_delta,
        "segment_gain_rate": gain_rate,
        "segment_loss_rate": loss_rate,
        "segment_exact_rate": exact_rate,
    }


def _select_row(
    *,
    rows: list[dict[str, Any]],
    stats_by_key: dict[str, SegmentStats],
    spec: ChoiceSpec,
) -> tuple[dict[str, Any], float, dict[str, float]]:
    default_row = next(row for row in rows if float(row["is_current_best"]) >= 1.0)
    best_row = default_row
    best_score = 0.0
    best_details = {
        "segment_count": 0.0,
        "segment_delta": 0.0,
        "segment_gain_rate": 0.0,
        "segment_loss_rate": 0.0,
        "segment_exact_rate": 0.0,
    }
    for row in rows:
        if float(row["is_current_best"]) >= 1.0:
            continue
        if float(row["surface_rank"]) > spec.max_surface_rank:
            continue
        key = _segment_key(row, spec.segment_profile)
        score, details = _segment_score(
            row,
            stats=stats_by_key.get(key, SegmentStats()),
            spec=spec,
        )
        tie_key = (
            score,
            float(row["surface_score"]),
            float(row["support_count"]),
            float(row["current_overlap"]),
            tuple(-chul_no for chul_no in row["combo"]),
        )
        best_tie_key = (
            best_score,
            float(best_row.get("surface_score", 0.0)),
            float(best_row.get("support_count", 0.0)),
            float(best_row.get("current_overlap", 0.0)),
            tuple(-chul_no for chul_no in best_row["combo"]),
        )
        if score > 0.0 and tie_key > best_tie_key:
            best_row = row
            best_score = score
            best_details = details
    return best_row, best_score, best_details


def _predict_surface_window(
    *,
    answers: dict[str, list[int]],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    surface: gain_loss.SurfaceSpec,
    choice_specs: tuple[ChoiceSpec, ...],
) -> dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]]:
    source_stats: dict[str, broad_selector.SourceStats] = {}
    score_spec = _score_spec_by_name()[surface.score_spec_name]
    race_ids = sorted(
        race_id for race_id in answers if race_id in current_best_predictions
    )
    predicted_by_name: dict[str, dict[str, tuple[int, int, int]]] = {
        spec.name: {} for spec in choice_specs
    }
    metric_values: dict[str, dict[str, list[float]]] = {
        spec.name: {
            "switch": [],
            "switched_exact": [],
            "kept_default_exact": [],
            "selected_current": [],
            "selected_rank": [],
            "selected_score": [],
            "pool_available": [],
            "surface_candidate_count": [],
            "net_exact_delta": [],
            "selected_segment_count": [],
            "selected_segment_delta": [],
            "selected_segment_gain_rate": [],
            "selected_segment_loss_rate": [],
        }
        for spec in choice_specs
    }
    stats_by_spec: dict[str, dict[str, SegmentStats]] = {
        spec.name: defaultdict(SegmentStats) for spec in choice_specs
    }

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
            default_row = next(
                row for row in rows if float(row["is_current_best"]) >= 1.0
            )
            default_combo = broad_selector._combo_key(default_row["combo"])
            default_exact = float(default_row["exact_label"])
            exact_by_combo = {
                broad_selector._combo_key(row["combo"]): float(row["exact_label"])
                for row in rows
            }
            pool_available = float(any(value >= 1.0 for value in exact_by_combo.values()))

            for spec in choice_specs:
                selected_row, selected_score, details = _select_row(
                    rows=rows,
                    stats_by_key=stats_by_spec[spec.name],
                    spec=spec,
                )
                selected_combo = broad_selector._combo_key(selected_row["combo"])
                switched = selected_combo != default_combo
                exact = exact_by_combo.get(selected_combo, 0.0)
                predicted_by_name[spec.name][race_id] = selected_combo
                values = metric_values[spec.name]
                values["switch"].append(float(switched))
                values["switched_exact"].append(float(switched and exact >= 1.0))
                values["kept_default_exact"].append(
                    float((not switched) and exact >= 1.0)
                )
                values["selected_current"].append(float(not switched))
                values["selected_rank"].append(float(selected_row["surface_rank"]))
                values["selected_score"].append(float(selected_score))
                values["pool_available"].append(pool_available)
                values["surface_candidate_count"].append(float(len(rows)))
                values["net_exact_delta"].append(exact - default_exact)
                values["selected_segment_count"].append(details["segment_count"])
                values["selected_segment_delta"].append(details["segment_delta"])
                values["selected_segment_gain_rate"].append(
                    details["segment_gain_rate"]
                )
                values["selected_segment_loss_rate"].append(
                    details["segment_loss_rate"]
                )

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

        for spec in choice_specs:
            stats_for_spec = stats_by_spec[spec.name]
            for row in date_rows:
                if float(row["is_current_best"]) >= 1.0:
                    continue
                if float(row["surface_rank"]) > spec.max_surface_rank:
                    continue
                key = _segment_key(row, spec.segment_profile)
                _add_segment_row(stats_for_spec[key], row)
        for source_name, combo, answer in pending_updates:
            broad_selector._update_stats(
                stats=source_stats.setdefault(source_name, broad_selector.SourceStats()),
                combo=combo,
                answer=answer,
            )

    output: dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]] = {}
    for spec in choice_specs:
        values = metric_values[spec.name]
        output[spec.name] = (
            predicted_by_name[spec.name],
            {
                "choice_model": spec.name,
                "surface_spec": surface.name,
                "segment_profile": spec.segment_profile,
                "switch_rate": round(_safe_mean(values["switch"]), 6),
                "switched_exact_rate": round(
                    _safe_mean(values["switched_exact"]),
                    6,
                ),
                "kept_default_exact_rate": round(
                    _safe_mean(values["kept_default_exact"]),
                    6,
                ),
                "selected_current_best_rate": round(
                    _safe_mean(values["selected_current"]),
                    6,
                ),
                "avg_selected_surface_rank": round(
                    _safe_mean(values["selected_rank"]),
                    3,
                ),
                "avg_selected_score": round(
                    _safe_mean(values["selected_score"]),
                    6,
                ),
                "avg_surface_candidate_count": round(
                    _safe_mean(values["surface_candidate_count"]),
                    3,
                ),
                "avg_net_exact_delta": round(
                    _safe_mean(values["net_exact_delta"]),
                    6,
                ),
                "pool_exact_available_rate": round(
                    _safe_mean(values["pool_available"]),
                    6,
                ),
                "pool_oracle_exact_rate": round(
                    _safe_mean(values["pool_available"]),
                    6,
                ),
                "fallback_plus_pool_exact_available_rate": round(
                    _safe_mean(values["pool_available"]),
                    6,
                ),
                "fallback_plus_pool_oracle_exact_rate": round(
                    _safe_mean(values["pool_available"]),
                    6,
                ),
                "avg_selected_segment_count": round(
                    _safe_mean(values["selected_segment_count"]),
                    3,
                ),
                "avg_selected_segment_delta": round(
                    _safe_mean(values["selected_segment_delta"]),
                    6,
                ),
                "avg_selected_segment_gain_rate": round(
                    _safe_mean(values["selected_segment_gain_rate"]),
                    6,
                ),
                "avg_selected_segment_loss_rate": round(
                    _safe_mean(values["selected_segment_loss_rate"]),
                    6,
                ),
                "history_update": "completed_prior_eval_dates_only",
                "feature_contract": (
                    "current_best_broad_component_rank_segment_prior_date"
                ),
                "selection_uses_labels": False,
            },
        )
    return output


def run_diagnostic(
    *,
    config_path: Path,
    cache_dir: Path,
    output_path: Path,
    source_artifact: Path,
    component_cache: Path,
    max_rank: int,
    grid_name: str,
) -> dict[str, Any]:
    started = time.time()
    answers_by_window = complement._window_answers_only(
        config_path=config_path,
        cache_dir=cache_dir,
    )
    current_best_by_window = static_repair._load_source_predictions(source_artifact)
    broad_predictions, broad_payload = artifact_source._load_broad_predictions(
        component_cache=component_cache,
        max_rank=max_rank,
    )
    component_names = tuple(str(name) for name in broad_payload["components"])
    surfaces = _surface_specs()
    choice_specs = _choice_specs(grid_name=grid_name)

    predictions_by_window: dict[
        str,
        dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]],
    ] = {}
    for window_name, answers in answers_by_window.items():
        for surface in surfaces:
            rows = _predict_surface_window(
                answers=answers,
                current_best_predictions=current_best_by_window[window_name],
                component_predictions=broad_predictions[window_name],
                component_names=component_names,
                surface=surface,
                choice_specs=choice_specs,
            )
            predictions_by_window.setdefault(window_name, {}).update(
                {f"{surface.name}/{name}": value for name, value in rows.items()}
            )

    names = sorted(next(iter(predictions_by_window.values())).keys())
    results: list[dict[str, Any]] = []
    predictions_by_candidate: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {}
    for name in names:
        candidate = (
            "clean_current_best_broad_component_rank_segment_prior_date_selector/"
            f"grid{grid_name}/max{max_rank}/{name}"
        )
        window_rows: list[dict[str, Any]] = []
        predictions_by_candidate[candidate] = {}
        for window_name, answers in answers_by_window.items():
            predicted, diagnostics = predictions_by_window[window_name][name]
            predictions_by_candidate[candidate][window_name] = predicted
            window_rows.append(
                {
                    "name": window_name,
                    "summary": _summarize_predictions(predicted, answers),
                    "diagnostics": diagnostics,
                }
            )
        summary = _window_summary(window_rows)
        summary["robust_pool_exact_available_rate"] = round(
            min(
                row["diagnostics"]["pool_exact_available_rate"]
                for row in window_rows
            ),
            6,
        )
        summary["robust_fallback_plus_pool_exact_available_rate"] = summary[
            "robust_pool_exact_available_rate"
        ]
        results.append(
            {
                "candidate": candidate,
                "selector_spec": name,
                "summary": summary,
                "windows": window_rows,
            }
        )

    results.sort(key=_candidate_key, reverse=True)
    retained_results = results[:120]
    best_candidate = retained_results[0]["candidate"]
    payload = {
        "format_version": (
            "current-best-broad-component-rank-segment-prior-date-selector-v1"
        ),
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Clean strict-prior-date rank-segment selector over the "
            "current-best prediction artifact plus cached broad clean "
            "component outputs. Candidate outcomes are used only after each "
            "completed eval date has been predicted; active-date and future "
            "outcomes do not enter feature construction or selection."
        ),
        "selection_contract": (
            "clean_current_best_plus_broad_component_rank_segment_prior_date_selector"
        ),
        "source_artifact": str(source_artifact),
        "component_cache": str(component_cache),
        "max_rank": max_rank,
        "grid_name": grid_name,
        "component_count": len(component_names),
        "candidate_count": len(results),
        "retained_result_count": len(retained_results),
        "surface_spec_count": len(surfaces),
        "choice_spec_count": len(choice_specs),
        "best": retained_results[0],
        "max_overfit_safe_exact_rate": max(
            row["summary"]["overfit_safe_exact_rate"] for row in results
        ),
        "max_test_exact_3of3_rate": max(
            row["summary"]["test_exact_3of3_rate"] for row in results
        ),
        "max_robust_pool_exact_available_rate": max(
            row["summary"]["robust_pool_exact_available_rate"] for row in results
        ),
        "ge_70_test_count": sum(
            1 for row in results if row["summary"]["test_exact_3of3_rate"] >= 0.7
        ),
        "ge_70_safe_count": sum(
            1
            for row in results
            if row["summary"]["overfit_safe_exact_rate"] >= 0.7
        ),
        "predictions_by_window": {
            window_name: _prediction_payload(
                predictions_by_candidate[best_candidate][window_name]
            )
            for window_name in answers_by_window
        },
        "results": retained_results,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-artifact", type=Path, default=DEFAULT_SOURCE_ARTIFACT)
    parser.add_argument(
        "--component-cache",
        type=Path,
        default=artifact_source.DEFAULT_COMPONENT_CACHE,
    )
    parser.add_argument("--max-rank", type=int, default=10)
    parser.add_argument(
        "--grid",
        choices=("focused", "aggressive"),
        default="focused",
    )
    args = parser.parse_args()
    payload = run_diagnostic(
        config_path=args.config,
        cache_dir=args.cache_dir,
        output_path=args.output,
        source_artifact=args.source_artifact,
        component_cache=args.component_cache,
        max_rank=args.max_rank,
        grid_name=args.grid,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "candidate_count": payload["candidate_count"],
                "component_count": payload["component_count"],
                "max_overfit_safe_exact_rate": payload[
                    "max_overfit_safe_exact_rate"
                ],
                "max_test_exact_3of3_rate": payload["max_test_exact_3of3_rate"],
                "max_robust_pool_exact_available_rate": payload[
                    "max_robust_pool_exact_available_rate"
                ],
                "ge_70_safe_count": payload["ge_70_safe_count"],
                "elapsed_seconds": payload["elapsed_seconds"],
                "best": payload["best"]["candidate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
