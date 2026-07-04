"""Feature-extended source-pool ranker over all-allowed rank-pattern candidates."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_current_best_all_allowed_source_pool_ranker_prior_date_selector_diagnostic as base,
)

DEFAULT_OUTPUT = base.DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_ranker_feature_extension_"
    "prior_date_selector_diagnostic.json"
)
FORMAT_VERSION = "current-best-all-allowed-source-pool-ranker-feature-extension-v1"


def _rank_map(values: dict[tuple[int, int, int], float]) -> dict[tuple[int, int, int], float]:
    ordered = sorted(values, key=lambda combo: (values[combo], tuple(-c for c in combo)), reverse=True)
    denom = max(len(ordered) - 1, 1)
    return {combo: index / denom for index, combo in enumerate(ordered)}


def _enhanced_candidate_rows_for_race(
    *,
    race_id: str,
    race_rows: list[dict[str, Any]],
    sources: tuple[base.vote.SourcePolicy, ...],
    ranked_cache: dict[tuple[str, int], dict[str, list[int]]],
    spec: base.SourceGroupSpec,
    answer: list[int] | None,
    fallback_combo: tuple[int, int, int] | None,
) -> list[dict[str, Any]]:
    answer_combo = base.vote._combo_key(answer[:3]) if answer else None
    source_scores: dict[tuple[int, int, int], float] = defaultdict(float)
    source_counts: dict[tuple[int, int, int], int] = defaultdict(int)
    max_source_scores: dict[tuple[int, int, int], float] = defaultdict(float)
    min_source_ranks: dict[tuple[int, int, int], int] = {}
    rank_score_sums: dict[tuple[int, int, int], float] = defaultdict(float)
    horse_scores: dict[int, float] = defaultdict(float)
    horse_counts: dict[int, int] = defaultdict(int)
    pair_scores: dict[tuple[int, int], float] = defaultdict(float)
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)
    for policy in sources:
        ranked_chuls = ranked_cache[(policy.feature_name, policy.direction)].get(race_id)
        if not ranked_chuls:
            continue
        combo = base._combo_for_pattern(ranked_chuls, policy.pattern)
        weight = base._source_weight(policy, spec)
        source_scores[combo] += weight
        source_counts[combo] += 1
        max_source_scores[combo] = max(max_source_scores[combo], weight)
        min_source_ranks[combo] = min(
            min_source_ranks.get(combo, policy.source_rank),
            policy.source_rank,
        )
        rank_score_sums[combo] += policy.rank_score
        for chul_no in combo:
            horse = int(chul_no)
            horse_scores[horse] += weight
            horse_counts[horse] += 1
        for pair in itertools.combinations(combo, 2):
            pair_key = tuple(sorted(int(chul_no) for chul_no in pair))
            pair_scores[pair_key] += weight
            pair_counts[pair_key] += 1
    if fallback_combo is not None:
        source_scores.setdefault(fallback_combo, 0.0)
        source_counts.setdefault(fallback_combo, 0)
        max_source_scores.setdefault(fallback_combo, 0.0)
        min_source_ranks.setdefault(fallback_combo, len(sources) + 1)
        rank_score_sums.setdefault(fallback_combo, 0.0)
    total_sources = max(len(sources), 1)
    max_rank = max(len(sources), 1)
    score_ranks = _rank_map(source_scores)
    support_values = {combo: float(source_counts[combo]) for combo in source_scores}
    support_ranks = _rank_map(support_values)
    fallback_source_score = source_scores.get(fallback_combo or (), 0.0) / total_sources
    fallback_support = source_counts.get(fallback_combo or (), 0) / total_sources
    top_horses = set(
        sorted(
            horse_scores,
            key=lambda horse: (horse_scores[horse], horse_counts[horse], -horse),
            reverse=True,
        )[:5]
    )
    rows: list[dict[str, Any]] = []
    for combo in sorted(source_scores):
        support = source_counts[combo]
        score_sum = source_scores[combo]
        mean_score = score_sum / max(float(support), 1.0)
        normalized_score = score_sum / total_sources
        normalized_support = support / total_sources
        current_overlap = (
            len(set(combo) & set(fallback_combo)) if fallback_combo is not None else 0
        )
        combo_pairs = [tuple(sorted(pair)) for pair in itertools.combinations(combo, 2)]
        combo_pair_scores = [pair_scores[pair] for pair in combo_pairs]
        combo_pair_counts = [pair_counts[pair] for pair in combo_pairs]
        combo_horse_scores = [horse_scores[int(chul_no)] for chul_no in combo]
        combo_horse_counts = [horse_counts[int(chul_no)] for chul_no in combo]
        pair_score_sum = sum(combo_pair_scores) / total_sources
        horse_score_sum = sum(combo_horse_scores) / total_sources
        pair_count_sum = sum(combo_pair_counts) / total_sources
        horse_count_sum = sum(combo_horse_counts) / total_sources
        features = [
            normalized_score,
            mean_score,
            max_source_scores[combo],
            normalized_support,
            min_source_ranks[combo] / max_rank,
            rank_score_sums[combo] / max(float(support), 1.0),
            current_overlap / 3.0,
            float(fallback_combo is not None and combo == fallback_combo),
            score_ranks[combo],
            support_ranks[combo],
            normalized_score - fallback_source_score,
            normalized_support - fallback_support,
            pair_score_sum,
            min(combo_pair_scores) / total_sources if combo_pair_scores else 0.0,
            max(combo_pair_scores) / total_sources if combo_pair_scores else 0.0,
            pair_count_sum,
            min(combo_pair_counts) / total_sources if combo_pair_counts else 0.0,
            max(combo_pair_counts) / total_sources if combo_pair_counts else 0.0,
            horse_score_sum,
            min(combo_horse_scores) / total_sources if combo_horse_scores else 0.0,
            max(combo_horse_scores) / total_sources if combo_horse_scores else 0.0,
            horse_count_sum,
            min(combo_horse_counts) / total_sources if combo_horse_counts else 0.0,
            max(combo_horse_counts) / total_sources if combo_horse_counts else 0.0,
            len(set(combo) & top_horses) / 3.0,
            *base._combo_context_features(race_rows=race_rows, combo=combo),
        ]
        rows.append(
            {
                "race_id": race_id,
                "combo": combo,
                "features": features,
                "source_score": normalized_score,
                "source_support": support,
                "current_overlap": current_overlap,
                "is_fallback": bool(fallback_combo is not None and combo == fallback_combo),
                "exact_label": float(answer_combo is not None and combo == answer_combo),
            }
        )
    return rows


def run_probe(
    *,
    config_path: Path,
    source_artifact: Path,
    row_cache_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    original_builder = base._candidate_rows_for_race
    base._candidate_rows_for_race = _enhanced_candidate_rows_for_race
    try:
        payload = base.run_probe(
            config_path=config_path,
            source_artifact=source_artifact,
            row_cache_path=row_cache_path,
            output_path=output_path,
        )
    finally:
        base._candidate_rows_for_race = original_builder
    payload["format_version"] = FORMAT_VERSION
    payload["diagnostic_only_reason"] = (
        "Clean strict-prior-date feature-extended candidate-exact ranker over "
        "the full all-allowed rank-pattern source pool. This variant adds "
        "race-local source rank/support, fallback-margin, horse aggregate, and "
        "pair aggregate features while preserving the base selector's "
        "train_end-only source selection/model fitting and one unordered "
        "top-3 combo output contract. Eval labels are used only for summaries "
        "and pool diagnostics."
    )
    payload["feature_extension"] = {
        "adds_race_local_source_ranks": True,
        "adds_fallback_margins": True,
        "adds_horse_pair_aggregates": True,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=base.DEFAULT_CONFIG)
    parser.add_argument("--source-artifact", type=Path, default=base.DEFAULT_SOURCE_ARTIFACT)
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
