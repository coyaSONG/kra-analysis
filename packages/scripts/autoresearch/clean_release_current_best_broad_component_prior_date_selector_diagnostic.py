"""Prior-date selector over current-best plus broad clean component outputs."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    adhoc_current_best_broad_component_output_complement_diagnostic as complement,
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
    "clean_release_current_best_broad_component_prior_date_selector_diagnostic.json"
)
CURRENT_SOURCE = "current_best"


@dataclass(slots=True)
class SourceStats:
    count: float = 0.0
    exact_sum: float = 0.0
    hit2_sum: float = 0.0
    match_sum: float = 0.0


@dataclass(frozen=True, slots=True)
class SelectorSpec:
    target: str
    model_c: float
    model_weight: float
    base_weight: float
    current_bias: float
    support_weight: float
    min_history_rows: int
    min_positive_rows: int

    @property
    def name(self) -> str:
        return (
            f"{self.target}/c{self.model_c:g}"
            f"/model{self.model_weight:g}"
            f"/base{self.base_weight:g}"
            f"/cur{self.current_bias:g}"
            f"/support{self.support_weight:g}"
            f"/min{self.min_history_rows}"
            f"/pos{self.min_positive_rows}"
        )


def _selector_specs() -> tuple[SelectorSpec, ...]:
    return tuple(
        SelectorSpec(
            target=target,
            model_c=model_c,
            model_weight=model_weight,
            base_weight=base_weight,
            current_bias=current_bias,
            support_weight=support_weight,
            min_history_rows=80,
            min_positive_rows=6,
        )
        for target in ("exact", "hit2")
        for model_c in (0.25, 1.0)
        for model_weight in (1.0, 3.0)
        for base_weight in (0.05, 0.20)
        for current_bias in (-0.08, -0.02, 0.0, 0.04)
        for support_weight in (0.0, 0.05)
    )


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _combo_key(combo: Any) -> tuple[int, int, int]:
    return tuple(sorted(int(chul_no) for chul_no in combo[:3]))


def _answer_combo(answers: dict[str, list[int]], race_id: str) -> tuple[int, int, int]:
    return _combo_key(answers[race_id])


def _race_date(race_id: str) -> str:
    return str(race_id)[:8]


def _date_groups(race_ids: list[str]) -> list[tuple[str, list[str]]]:
    grouped: dict[str, list[str]] = {}
    for race_id in sorted(race_ids):
        grouped.setdefault(_race_date(race_id), []).append(race_id)
    return [(race_date, grouped[race_date]) for race_date in sorted(grouped)]


def _match_value(combo: tuple[int, int, int], answer: tuple[int, int, int]) -> float:
    return len(set(combo) & set(answer)) / 3.0


def _hit2_value(combo: tuple[int, int, int], answer: tuple[int, int, int]) -> float:
    return float(len(set(combo) & set(answer)) >= 2)


def _update_stats(
    *,
    stats: SourceStats,
    combo: tuple[int, int, int],
    answer: tuple[int, int, int],
) -> None:
    stats.count += 1.0
    stats.exact_sum += float(combo == answer)
    stats.hit2_sum += _hit2_value(combo, answer)
    stats.match_sum += _match_value(combo, answer)


def _stats_rate(stats: SourceStats, metric: str) -> float:
    if stats.count <= 0.0:
        if metric == "exact":
            return 0.30
        if metric == "hit2":
            return 0.70
        return 2.0 / 3.0
    if metric == "exact":
        return stats.exact_sum / stats.count
    if metric == "hit2":
        return stats.hit2_sum / stats.count
    return stats.match_sum / stats.count


def _pair_key(left: int, right: int) -> tuple[int, int]:
    return tuple(sorted((int(left), int(right))))


def _source_support_features(
    *,
    sources: tuple[str, ...],
    component_names: tuple[str, ...],
) -> list[float]:
    source_set = set(sources)
    return [float(source_name in source_set) for source_name in component_names]


def _candidate_rows_for_race(
    *,
    race_id: str,
    answer: tuple[int, int, int],
    current_best_combo: tuple[int, int, int],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    source_stats: dict[str, SourceStats],
) -> list[dict[str, Any]]:
    combo_sources: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    combo_sources[current_best_combo].append(CURRENT_SOURCE)
    for source_name in component_names:
        combo_raw = component_predictions.get(source_name, {}).get(race_id)
        if combo_raw is None:
            continue
        combo_sources[_combo_key(combo_raw)].append(source_name)

    source_count = max(len(component_names), 1)
    horse_counts: Counter[int] = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()
    for combo, sources in combo_sources.items():
        support = sum(1 for source in sources if source != CURRENT_SOURCE)
        for horse in combo:
            horse_counts[horse] += support
        horses = list(combo)
        for left_index, left in enumerate(horses):
            for right in horses[left_index + 1 :]:
                pair_counts[_pair_key(left, right)] += support

    rows: list[dict[str, Any]] = []
    for combo, sources_raw in combo_sources.items():
        sources = tuple(sorted(set(sources_raw)))
        component_sources = tuple(
            source_name for source_name in sources if source_name != CURRENT_SOURCE
        )
        source_exact_rates = [
            _stats_rate(source_stats.get(source, SourceStats()), "exact")
            for source in sources
        ]
        source_hit2_rates = [
            _stats_rate(source_stats.get(source, SourceStats()), "hit2")
            for source in sources
        ]
        source_match_rates = [
            _stats_rate(source_stats.get(source, SourceStats()), "match")
            for source in sources
        ]
        source_counts = [
            source_stats.get(source, SourceStats()).count for source in sources
        ]
        combo_set = set(combo)
        current_overlap = len(combo_set & set(current_best_combo))
        pair_support = 0
        horses = list(combo)
        for left_index, left in enumerate(horses):
            for right in horses[left_index + 1 :]:
                pair_support += pair_counts[_pair_key(left, right)]
        horse_support = sum(horse_counts[horse] for horse in combo)
        support_count = len(component_sources)
        support_fraction = support_count / source_count
        source_exact_mean = float(np.mean(source_exact_rates))
        source_hit2_mean = float(np.mean(source_hit2_rates))
        source_match_mean = float(np.mean(source_match_rates))
        base_score = (
            0.25 * float(combo == current_best_combo)
            + 0.20 * (current_overlap / 3.0)
            + 0.20 * support_fraction
            + 0.15 * source_exact_mean
            + 0.10 * source_match_mean
            + 0.10 * (pair_support / max(3 * source_count, 1))
        )
        rows.append(
            {
                "race_id": race_id,
                "race_date": _race_date(race_id),
                "combo": combo,
                "sources": sources,
                "exact_label": float(combo == answer),
                "hit2_label": _hit2_value(combo, answer),
                "match_label": _match_value(combo, answer),
                "base_score": base_score,
                "support_count": float(support_count),
                "support_fraction": support_fraction,
                "distinct_count": float(len(combo_sources)),
                "horse_support_sum": float(horse_support),
                "pair_support_sum": float(pair_support),
                "is_current_best": float(combo == current_best_combo),
                "current_overlap": float(current_overlap),
                "source_exact_mean": source_exact_mean,
                "source_exact_max": float(max(source_exact_rates)),
                "source_hit2_mean": source_hit2_mean,
                "source_hit2_max": float(max(source_hit2_rates)),
                "source_match_mean": source_match_mean,
                "source_match_max": float(max(source_match_rates)),
                "source_count_mean": float(np.mean(source_counts)),
                "source_count_max": float(max(source_counts)),
            }
        )
    return rows


def _features(row: dict[str, Any], component_names: tuple[str, ...]) -> list[float]:
    source_count = max(len(component_names), 1)
    return [
        float(row["base_score"]),
        float(row["support_count"]),
        float(row["support_fraction"]),
        float(row["distinct_count"]) / (source_count + 1.0),
        float(row["horse_support_sum"]) / max(3 * source_count, 1),
        float(row["pair_support_sum"]) / max(3 * source_count, 1),
        float(row["is_current_best"]),
        float(row["current_overlap"]) / 3.0,
        float(row["source_exact_mean"]),
        float(row["source_exact_max"]),
        float(row["source_hit2_mean"]),
        float(row["source_hit2_max"]),
        float(row["source_match_mean"]),
        float(row["source_match_max"]),
        math.log1p(float(row["source_count_mean"])) / 5.0,
        math.log1p(float(row["source_count_max"])) / 5.0,
        *_source_support_features(
            sources=row["sources"],
            component_names=component_names,
        ),
    ]


def _label(row: dict[str, Any], target: str) -> int:
    if target == "exact":
        return int(float(row["exact_label"]) >= 1.0)
    if target == "hit2":
        return int(float(row["hit2_label"]) >= 1.0)
    raise ValueError(f"Unknown target: {target}")


def _fit_model(
    history_rows: list[dict[str, Any]],
    *,
    component_names: tuple[str, ...],
    spec: SelectorSpec,
) -> Pipeline | None:
    if len(history_rows) < spec.min_history_rows:
        return None
    labels = np.asarray([_label(row, spec.target) for row in history_rows], dtype=int)
    positives = int(np.sum(labels))
    negatives = int(labels.shape[0] - positives)
    if positives < spec.min_positive_rows or negatives < spec.min_positive_rows:
        return None
    matrix = np.asarray(
        [_features(row, component_names) for row in history_rows],
        dtype=float,
    )
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=spec.model_c,
                    class_weight="balanced",
                    max_iter=400,
                    random_state=20260530,
                ),
            ),
        ]
    )
    model.fit(matrix, labels)
    return model


def _probabilities(
    model: Pipeline | None,
    rows: list[dict[str, Any]],
    *,
    component_names: tuple[str, ...],
) -> np.ndarray:
    if not rows:
        return np.zeros((0,), dtype=float)
    if model is None:
        return np.zeros((len(rows),), dtype=float)
    matrix = np.asarray([_features(row, component_names) for row in rows], dtype=float)
    probabilities = model.predict_proba(matrix)
    if probabilities.shape[1] < 2:
        return np.asarray(probabilities[:, 0], dtype=float)
    return np.asarray(probabilities[:, 1], dtype=float)


def _predict_window(
    *,
    answers: dict[str, list[int]],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    spec: SelectorSpec,
) -> tuple[dict[str, tuple[int, int, int]], dict[str, Any]]:
    race_ids = sorted(
        race_id for race_id in answers if race_id in current_best_predictions
    )
    source_stats: dict[str, SourceStats] = defaultdict(SourceStats)
    history_rows: list[dict[str, Any]] = []
    predicted: dict[str, tuple[int, int, int]] = {}
    selected_current = 0
    exact_available = 0
    fit_dates = 0
    cold_dates = 0
    selected_probabilities: list[float] = []
    selected_support: list[float] = []
    distinct_counts: list[float] = []

    for _date_value, date_race_ids in _date_groups(race_ids):
        model = _fit_model(
            history_rows,
            component_names=component_names,
            spec=spec,
        )
        if model is None:
            cold_dates += 1
        else:
            fit_dates += 1
        date_rows: list[dict[str, Any]] = []
        pending_updates: list[tuple[str, tuple[int, int, int], tuple[int, int, int]]] = []
        for race_id in date_race_ids:
            answer = _answer_combo(answers, race_id)
            current_best_combo = _combo_key(current_best_predictions[race_id])
            rows = _candidate_rows_for_race(
                race_id=race_id,
                answer=answer,
                current_best_combo=current_best_combo,
                component_predictions=component_predictions,
                component_names=component_names,
                source_stats=source_stats,
            )
            if not rows:
                continue
            exact_available += int(
                any(float(row["exact_label"]) >= 1.0 for row in rows)
            )
            probabilities = _probabilities(
                model,
                rows,
                component_names=component_names,
            )
            scored = []
            for row, probability in zip(rows, probabilities, strict=False):
                score = (
                    spec.model_weight * float(probability)
                    + spec.base_weight * float(row["base_score"])
                    + spec.current_bias * float(row["is_current_best"])
                    + spec.support_weight * float(row["support_fraction"])
                )
                scored.append(
                    (
                        (
                            score,
                            float(probability),
                            float(row["base_score"]),
                            float(row["support_count"]),
                            float(row["current_overlap"]),
                            tuple(-chul_no for chul_no in row["combo"]),
                        ),
                        row,
                        float(probability),
                    )
                )
            _key, selected, probability = max(scored)
            predicted[race_id] = selected["combo"]
            selected_current += int(float(selected["is_current_best"]) >= 1.0)
            selected_probabilities.append(probability)
            selected_support.append(float(selected["support_count"]))
            distinct_counts.append(float(selected["distinct_count"]))
            date_rows.extend(rows)
            pending_updates.append((CURRENT_SOURCE, current_best_combo, answer))
            for source_name in component_names:
                combo_raw = component_predictions.get(source_name, {}).get(race_id)
                if combo_raw is None:
                    continue
                pending_updates.append((source_name, _combo_key(combo_raw), answer))
        history_rows.extend(date_rows)
        for source_name, combo, answer in pending_updates:
            _update_stats(stats=source_stats[source_name], combo=combo, answer=answer)

    race_count = max(len(predicted), 1)
    return predicted, {
        "pool_oracle_exact_rate": round(exact_available / race_count, 6),
        "fallback_plus_pool_oracle_exact_rate": round(exact_available / race_count, 6),
        "selected_current_best_rate": round(selected_current / race_count, 6),
        "fit_date_count": fit_dates,
        "cold_date_count": cold_dates,
        "history_row_count": len(history_rows),
        "avg_selected_probability": round(
            float(np.mean(selected_probabilities)) if selected_probabilities else 0.0,
            6,
        ),
        "avg_selected_support": round(
            float(np.mean(selected_support)) if selected_support else 0.0,
            3,
        ),
        "avg_distinct_outputs": round(
            float(np.mean(distinct_counts)) if distinct_counts else 0.0,
            3,
        ),
        "history_update": "completed_prior_eval_dates_only",
        "feature_contract": "current_best_plus_broad_clean_component_outputs",
        "selection_uses_labels": False,
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
    results: list[dict[str, Any]] = []

    for spec in specs:
        window_rows: list[dict[str, Any]] = []
        for window_name, answers in answers_by_window.items():
            predicted, diagnostics = _predict_window(
                answers=answers,
                current_best_predictions=current_best_by_window[window_name],
                component_predictions=broad_predictions[window_name],
                component_names=component_names,
                spec=spec,
            )
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
                    "clean_current_best_broad_component_prior_date_selector/"
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
            "current-best-broad-component-prior-date-selector-v1"
        ),
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Clean strict-prior-date selector over the exact current-best "
            "reproduction plus cached broad clean component outputs. Candidate "
            "features use race-time component agreement and source rates updated "
            "only after completed prior eval dates, then emit one unordered "
            "top-3 combination per race. Eval labels are otherwise used only "
            "for summaries and pool diagnostics."
        ),
        "selection_contract": (
            "clean_current_best_plus_broad_component_strict_prior_date_selector"
        ),
        "source_artifact": str(source_artifact),
        "component_cache": str(component_cache),
        "max_rank": max_rank,
        "component_count": len(component_names),
        "component_oracle_ceiling_summary": broad_payload["oracle_ceiling_summary"],
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
