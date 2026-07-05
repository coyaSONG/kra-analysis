"""Prior-date source-score selector over current-best plus broad components."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import time
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
    clean_release_current_best_broad_component_prior_date_selector_diagnostic as broad_selector,
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

DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_source_score_selector_diagnostic.json"
)


@dataclass(frozen=True, slots=True)
class ScoreProfile:
    name: str
    base_weight: float
    support_weight: float
    exact_weight: float
    exact_max_weight: float
    hit2_weight: float
    match_weight: float
    pair_weight: float
    horse_weight: float
    overlap_weight: float
    distinct_weight: float


@dataclass(frozen=True, slots=True)
class SourceScoreSpec:
    profile: ScoreProfile
    current_bias: float
    min_component_support: int

    @property
    def name(self) -> str:
        return (
            f"{self.profile.name}"
            f"/cur{self.current_bias:g}"
            f"/minsupport{self.min_component_support}"
        )


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _score_profiles() -> tuple[ScoreProfile, ...]:
    return (
        ScoreProfile(
            name="base",
            base_weight=1.0,
            support_weight=0.0,
            exact_weight=0.0,
            exact_max_weight=0.0,
            hit2_weight=0.0,
            match_weight=0.0,
            pair_weight=0.0,
            horse_weight=0.0,
            overlap_weight=0.0,
            distinct_weight=0.0,
        ),
        ScoreProfile(
            name="support_pair",
            base_weight=0.15,
            support_weight=1.0,
            exact_weight=0.0,
            exact_max_weight=0.0,
            hit2_weight=0.0,
            match_weight=0.2,
            pair_weight=0.5,
            horse_weight=0.25,
            overlap_weight=0.0,
            distinct_weight=0.05,
        ),
        ScoreProfile(
            name="prior_exact",
            base_weight=0.2,
            support_weight=0.35,
            exact_weight=1.0,
            exact_max_weight=0.5,
            hit2_weight=0.0,
            match_weight=0.25,
            pair_weight=0.1,
            horse_weight=0.0,
            overlap_weight=0.0,
            distinct_weight=0.0,
        ),
        ScoreProfile(
            name="prior_hit2",
            base_weight=0.2,
            support_weight=0.35,
            exact_weight=0.25,
            exact_max_weight=0.0,
            hit2_weight=0.75,
            match_weight=0.5,
            pair_weight=0.1,
            horse_weight=0.0,
            overlap_weight=0.0,
            distinct_weight=0.0,
        ),
        ScoreProfile(
            name="agreement_prior",
            base_weight=0.15,
            support_weight=0.6,
            exact_weight=0.5,
            exact_max_weight=0.25,
            hit2_weight=0.25,
            match_weight=0.35,
            pair_weight=0.35,
            horse_weight=0.2,
            overlap_weight=0.1,
            distinct_weight=0.05,
        ),
    )


def _selector_specs() -> tuple[SourceScoreSpec, ...]:
    return tuple(
        SourceScoreSpec(
            profile=profile,
            current_bias=current_bias,
            min_component_support=min_component_support,
        )
        for profile in _score_profiles()
        for current_bias in (-0.30, -0.12, -0.04, 0.0, 0.04, 0.12, 0.30)
        for min_component_support in (0, 1, 2)
    )


def _candidate_score(
    *,
    row: dict[str, Any],
    spec: SourceScoreSpec,
    component_count: int,
) -> float:
    profile = spec.profile
    denominator = max(float(component_count), 1.0)
    return (
        profile.base_weight * float(row["base_score"])
        + profile.support_weight * float(row["support_fraction"])
        + profile.exact_weight * float(row["source_exact_mean"])
        + profile.exact_max_weight * float(row["source_exact_max"])
        + profile.hit2_weight * float(row["source_hit2_mean"])
        + profile.match_weight * float(row["source_match_mean"])
        + profile.pair_weight * float(row["pair_support_sum"]) / max(3.0 * denominator, 1.0)
        + profile.horse_weight * float(row["horse_support_sum"]) / max(3.0 * denominator, 1.0)
        + profile.overlap_weight * float(row["current_overlap"]) / 3.0
        + profile.distinct_weight * float(row["distinct_count"]) / (denominator + 1.0)
        + spec.current_bias * float(row["is_current_best"])
    )


def _eligible_rows(
    *,
    rows: list[dict[str, Any]],
    spec: SourceScoreSpec,
) -> list[dict[str, Any]]:
    if spec.min_component_support <= 0:
        return rows
    eligible = [
        row
        for row in rows
        if float(row["is_current_best"]) >= 1.0
        or int(float(row["support_count"])) >= spec.min_component_support
    ]
    return eligible if eligible else rows


def _predict_window(
    *,
    answers: dict[str, list[int]],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    specs: tuple[SourceScoreSpec, ...],
) -> dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]]:
    predicted_by_name: dict[str, dict[str, tuple[int, int, int]]] = {
        spec.name: {} for spec in specs
    }
    metric_values: dict[str, dict[str, list[float]]] = {
        spec.name: {
            "selected_current": [],
            "selected_exact": [],
            "pool_oracle": [],
            "selected_support": [],
            "distinct_count": [],
            "selected_score": [],
        }
        for spec in specs
    }
    source_stats: dict[str, broad_selector.SourceStats] = {}
    race_ids = sorted(
        race_id for race_id in answers if race_id in current_best_predictions
    )

    for _date_value, date_race_ids in broad_selector._date_groups(race_ids):
        pending_updates: list[tuple[str, tuple[int, int, int], tuple[int, int, int]]] = []
        for race_id in date_race_ids:
            answer = broad_selector._answer_combo(answers, race_id)
            current_best_combo = broad_selector._combo_key(
                current_best_predictions[race_id]
            )
            rows = broad_selector._candidate_rows_for_race(
                race_id=race_id,
                answer=answer,
                current_best_combo=current_best_combo,
                component_predictions=component_predictions,
                component_names=component_names,
                source_stats=source_stats,
            )
            if not rows:
                continue
            pool_oracle = float(any(float(row["exact_label"]) >= 1.0 for row in rows))
            for spec in specs:
                eligible = _eligible_rows(rows=rows, spec=spec)
                scored = [
                    (
                        _candidate_score(
                            row=row,
                            spec=spec,
                            component_count=len(component_names),
                        ),
                        row,
                    )
                    for row in eligible
                ]
                score, selected = max(
                    scored,
                    key=lambda item: (
                        item[0],
                        float(item[1]["support_count"]),
                        float(item[1]["base_score"]),
                        float(item[1]["current_overlap"]),
                        tuple(-chul_no for chul_no in item[1]["combo"]),
                    ),
                )
                predicted_by_name[spec.name][race_id] = selected["combo"]
                values = metric_values[spec.name]
                values["selected_current"].append(float(selected["is_current_best"]))
                values["selected_exact"].append(float(selected["exact_label"]))
                values["pool_oracle"].append(pool_oracle)
                values["selected_support"].append(float(selected["support_count"]))
                values["distinct_count"].append(float(selected["distinct_count"]))
                values["selected_score"].append(float(score))
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
        for source_name, combo, answer in pending_updates:
            broad_selector._update_stats(
                stats=source_stats.setdefault(source_name, broad_selector.SourceStats()),
                combo=combo,
                answer=answer,
            )

    output: dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]] = {}
    for spec in specs:
        values = metric_values[spec.name]
        output[spec.name] = (
            predicted_by_name[spec.name],
            {
                "selector_spec": spec.name,
                "selected_current_best_rate": round(
                    _safe_mean(values["selected_current"]),
                    6,
                ),
                "selected_exact_rate": round(
                    _safe_mean(values["selected_exact"]),
                    6,
                ),
                "pool_oracle_exact_rate": round(
                    _safe_mean(values["pool_oracle"]),
                    6,
                ),
                "fallback_plus_pool_oracle_exact_rate": round(
                    _safe_mean(values["pool_oracle"]),
                    6,
                ),
                "avg_selected_support": round(
                    _safe_mean(values["selected_support"]),
                    3,
                ),
                "avg_distinct_outputs": round(
                    _safe_mean(values["distinct_count"]),
                    3,
                ),
                "avg_selected_score": round(
                    _safe_mean(values["selected_score"]),
                    6,
                ),
                "history_update": "completed_prior_eval_dates_only",
                "feature_contract": "source_score_current_best_plus_broad_components",
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
    specs = _selector_specs()
    predictions_by_window = {
        window_name: _predict_window(
            answers=answers,
            current_best_predictions=current_best_by_window[window_name],
            component_predictions=broad_predictions[window_name],
            component_names=component_names,
            specs=specs,
        )
        for window_name, answers in answers_by_window.items()
    }
    results: list[dict[str, Any]] = []
    for spec in specs:
        window_rows: list[dict[str, Any]] = []
        for window_name, answers in answers_by_window.items():
            predicted, diagnostics = predictions_by_window[window_name][spec.name]
            summary = _summarize_predictions(predicted, answers)
            window_rows.append(
                {
                    "name": window_name,
                    "summary": summary,
                    "diagnostics": diagnostics,
                }
            )
        summary = _window_summary(window_rows)
        summary["robust_pool_oracle_exact_rate"] = round(
            min(row["diagnostics"]["pool_oracle_exact_rate"] for row in window_rows),
            6,
        )
        results.append(
            {
                "candidate": (
                    "clean_current_best_broad_component_source_score_selector/"
                    f"max{max_rank}/{spec.name}"
                ),
                "selector_spec": spec.name,
                "summary": summary,
                "windows": window_rows,
            }
        )

    results.sort(key=_candidate_key, reverse=True)
    payload = {
        "format_version": (
            "current-best-broad-component-source-score-selector-v1"
        ),
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Clean source-score selector over the exact current-best "
            "reproduction plus cached broad clean component outputs. It uses "
            "only race-time component agreement and completed-prior-date source "
            "performance summaries, then emits one unordered top-3 combination "
            "per race. Eval labels are otherwise used only for summaries and "
            "pool diagnostics."
        ),
        "selection_contract": (
            "clean_current_best_plus_broad_component_source_score_selector"
        ),
        "source_artifact": str(source_artifact),
        "component_cache": str(component_cache),
        "max_rank": max_rank,
        "component_count": len(component_names),
        "candidate_count": len(results),
        "selector_spec_count": len(specs),
        "best": results[0],
        "max_overfit_safe_exact_rate": max(
            row["summary"]["overfit_safe_exact_rate"] for row in results
        ),
        "max_test_exact_3of3_rate": max(
            row["summary"]["test_exact_3of3_rate"] for row in results
        ),
        "max_robust_pool_oracle_exact_rate": max(
            row["summary"]["robust_pool_oracle_exact_rate"] for row in results
        ),
        "ge_70_test_count": sum(
            1 for row in results if row["summary"]["test_exact_3of3_rate"] >= 0.7
        ),
        "ge_70_safe_count": sum(
            1
            for row in results
            if row["summary"]["overfit_safe_exact_rate"] >= 0.7
        ),
        "results": results,
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
                "candidate_count": payload["candidate_count"],
                "component_count": payload["component_count"],
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


if __name__ == "__main__":
    main()
