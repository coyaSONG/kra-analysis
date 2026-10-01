"""Build a strict prior-date 19-option candidate surface for Laya."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.clean_horse_probability_ensemble_probe import (  # noqa: E402
    _base_key,
    _combine_member_probabilities,
)
from autoresearch.clean_horse_rank_pattern_decay_selector_probe import (  # noqa: E402
    _build_member_probabilities,
    _capped_model_candidates,
    _policy_pool,
)
from autoresearch.clean_sparse_multichoice_policy_selector_probe import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)
from autoresearch.clean_top50_history_overlay_probe import WindowSpec  # noqa: E402
from autoresearch.parameter_context import (  # noqa: E402
    load_evaluation_parameter_context,
)
from autoresearch.search_clean_model import (  # noqa: E402
    _feature_sets,
    _load_or_build_row_cache,
    _read_json,
)

FORMAT_VERSION = "single-combo-laya-strict-candidate-surface-v1"
TIMING_CONTRACT = "strict_prior_date_block_refit_no_active_labels_v1"
SELECTION_CONTRACT = "strict_prior_date_adaptive_rank_patterns_v1"
DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / "single_combo_laya_strict_candidate_surface.json"
DEFAULT_MIN_TRAIN_RACES = 500
DEFAULT_REFIT_DATE_STRIDE = 16
DEFAULT_CANDIDATE_COUNT = 19
DEFAULT_MAX_RANK = 10


@dataclass(frozen=True, slots=True)
class ReplayBlock:
    """One fit cutoff followed by one or more untouched evaluation dates."""

    name: str
    train_end: str
    eval_start: str
    eval_end: str
    eval_dates: tuple[str, ...]
    train_race_count: int
    eval_race_count: int


ProbabilityProvider = Callable[
    [list[dict[str, Any]], list[dict[str, Any]], ReplayBlock],
    dict[str, dict[str, dict[int, float]]],
]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _race_date(row: dict[str, Any]) -> str:
    explicit = str(row.get("race_date") or "").strip()
    if len(explicit) == 8 and explicit.isdigit():
        return explicit
    race_id = str(row.get("race_id") or "")
    prefix = race_id[:8]
    return prefix if len(prefix) == 8 and prefix.isdigit() else ""


def _answer(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, list | tuple) or len(value) < 3:
        return None
    try:
        answer = tuple(sorted(int(item) for item in value[:3]))
    except (TypeError, ValueError):
        return None
    return answer if len(set(answer)) == 3 else None


def _rows_by_race(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        race_id = str(row.get("race_id") or "").strip()
        if race_id:
            grouped[race_id].append(row)
    return dict(grouped)


def _race_ids_by_date(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        race_id = str(row.get("race_id") or "").strip()
        date = _race_date(row)
        if race_id and date:
            grouped[date].add(race_id)
    return {date: sorted(race_ids) for date, race_ids in grouped.items()}


def build_replay_blocks(
    rows: list[dict[str, Any]],
    *,
    min_train_races: int,
    refit_date_stride: int,
    max_blocks: int | None = None,
) -> tuple[list[ReplayBlock], list[str]]:
    """Create complete-date blocks whose fit cutoff is strictly earlier."""

    if min_train_races < 1:
        raise ValueError("min_train_races must be positive")
    if refit_date_stride < 1:
        raise ValueError("refit_date_stride must be positive")
    if max_blocks is not None and max_blocks < 1:
        raise ValueError("max_blocks must be positive when provided")

    race_ids_by_date = _race_ids_by_date(rows)
    dates = sorted(race_ids_by_date)
    prior_race_count = 0
    start_index: int | None = None
    for index, date in enumerate(dates):
        if prior_race_count >= min_train_races:
            start_index = index
            break
        prior_race_count += len(race_ids_by_date[date])
    if start_index is None or start_index == 0:
        return [], [race_id for date in dates for race_id in race_ids_by_date[date]]

    warmup_race_ids = [
        race_id for date in dates[:start_index] for race_id in race_ids_by_date[date]
    ]
    blocks: list[ReplayBlock] = []
    for block_index, index in enumerate(
        range(start_index, len(dates), refit_date_stride),
        start=1,
    ):
        if max_blocks is not None and len(blocks) >= max_blocks:
            break
        eval_dates = tuple(dates[index : index + refit_date_stride])
        train_dates = dates[:index]
        train_race_count = sum(len(race_ids_by_date[date]) for date in train_dates)
        eval_race_count = sum(len(race_ids_by_date[date]) for date in eval_dates)
        blocks.append(
            ReplayBlock(
                name=f"block_{block_index:03d}",
                train_end=train_dates[-1],
                eval_start=eval_dates[0],
                eval_end=eval_dates[-1],
                eval_dates=eval_dates,
                train_race_count=train_race_count,
                eval_race_count=eval_race_count,
            )
        )
    return blocks, warmup_race_ids


def _ranked_chuls(scores: dict[int, float]) -> list[int]:
    return sorted(
        scores,
        key=lambda chul_no: (float(scores[chul_no]), -int(chul_no)),
        reverse=True,
    )


def _rank_map(scores: dict[int, float]) -> dict[int, int]:
    return {
        chul_no: rank for rank, chul_no in enumerate(_ranked_chuls(scores), start=1)
    }


def _round(value: float) -> float:
    return round(float(value), 8)


def _pattern_name(ranks: tuple[int, int, int]) -> str:
    return "pattern" + "-".join(str(rank) for rank in ranks)


def _pattern_ranks(name: str) -> tuple[int, int, int]:
    raw = name.removeprefix("pattern").split("-")
    if len(raw) != 3:
        raise ValueError(f"invalid pattern name: {name}")
    ranks = tuple(int(item) for item in raw)
    if len(set(ranks)) != 3 or tuple(sorted(ranks)) != ranks:
        raise ValueError(f"invalid pattern ranks: {name}")
    return ranks


def _candidate_signal(
    *,
    ranks: tuple[int, int, int],
    combo: tuple[int, int, int],
    combined: dict[int, float],
    member_probabilities: list[dict[int, float]],
) -> dict[str, float | int]:
    selected_scores = [float(combined.get(chul_no, 0.0)) for chul_no in combo]
    member_values = [
        float(probabilities.get(chul_no, 0.0))
        for probabilities in member_probabilities
        for chul_no in combo
    ]
    member_ranks = [
        float(rank_lookup.get(chul_no, len(probabilities) + 1))
        for probabilities in member_probabilities
        for rank_lookup in [_rank_map(probabilities)]
        for chul_no in combo
    ]
    return {
        "rank_1": ranks[0],
        "rank_2": ranks[1],
        "rank_3": ranks[2],
        "rank_sum": sum(ranks),
        "reciprocal_rank_sum": _round(sum(1.0 / rank for rank in ranks)),
        "top3_member_count": sum(rank <= 3 for rank in ranks),
        "top5_member_count": sum(rank <= 5 for rank in ranks),
        "combined_probability_mean": _round(mean(selected_scores)),
        "combined_probability_min": _round(min(selected_scores)),
        "combined_probability_max": _round(max(selected_scores)),
        "combined_probability_product": _round(
            math.prod(max(score, 1e-9) for score in selected_scores)
        ),
        "combined_probability_log_sum": _round(
            sum(math.log(max(score, 1e-9)) for score in selected_scores)
        ),
        "member_probability_mean": _round(mean(member_values)),
        "member_probability_std": _round(pstdev(member_values)),
        "member_rank_mean": _round(mean(member_ranks)),
        "member_rank_std": _round(pstdev(member_ranks)),
    }


def build_all_candidates(
    *,
    member_probabilities_by_key: dict[str, dict[str, dict[int, float]]],
    member_keys: tuple[str, ...],
    race_id: str,
    method: str,
    max_rank: int,
) -> dict[str, dict[str, Any]]:
    """Build every valid rank-pattern candidate without consulting labels."""

    if max_rank < 3:
        raise ValueError("max_rank must be at least three")
    member_probabilities = [
        member_probabilities_by_key[member_key][race_id] for member_key in member_keys
    ]
    combined = _combine_member_probabilities(
        member_probs=member_probabilities,
        method=method,
    )
    ranked = _ranked_chuls(combined)
    usable_rank = min(max_rank, len(ranked))
    candidates: dict[str, dict[str, Any]] = {}
    for ranks in itertools.combinations(range(1, usable_rank + 1), 3):
        combo = tuple(sorted(int(ranked[rank - 1]) for rank in ranks))
        name = _pattern_name(ranks)
        candidates[name] = {
            "policy_name": name,
            "combo": list(combo),
            "signals": _candidate_signal(
                ranks=ranks,
                combo=combo,
                combined=combined,
                member_probabilities=member_probabilities,
            ),
        }
    return candidates


def _pattern_history_score(
    name: str,
    history: dict[str, dict[str, float]],
) -> tuple[float, float, float, tuple[int, int, int]]:
    stats = history.get(name, {})
    race_count = float(stats.get("race_count", 0.0))
    exact_count = float(stats.get("exact_count", 0.0))
    match_sum = float(stats.get("match_sum", 0.0))
    ranks = _pattern_ranks(name)
    exact_rate = (exact_count + 0.25) / (race_count + 1.0)
    match_rate = (match_sum + 0.5) / (race_count + 1.0)
    rank_score = sum(1.0 / rank for rank in ranks)
    return exact_rate, match_rate, rank_score, tuple(-rank for rank in ranks)


def ordered_pattern_names(
    names: list[str],
    history: dict[str, dict[str, float]],
) -> list[str]:
    return sorted(
        names,
        key=lambda name: _pattern_history_score(name, history),
        reverse=True,
    )


def select_candidates(
    *,
    all_candidates: dict[str, dict[str, Any]],
    history: dict[str, dict[str, float]],
    candidate_count: int,
) -> list[dict[str, Any]]:
    """Select unique options using only history supplied by prior blocks."""

    if candidate_count < 1:
        raise ValueError("candidate_count must be positive")
    selected: list[dict[str, Any]] = []
    seen_combos: set[tuple[int, int, int]] = set()
    for name in ordered_pattern_names(list(all_candidates), history):
        candidate = all_candidates[name]
        combo = tuple(sorted(int(item) for item in candidate["combo"]))
        if combo in seen_combos:
            continue
        selected.append(candidate)
        seen_combos.add(combo)
        if len(selected) >= candidate_count:
            break
    return selected


def update_pattern_history(
    *,
    history: dict[str, dict[str, float]],
    all_candidates_by_race: dict[str, dict[str, dict[str, Any]]],
    answers: dict[str, tuple[int, int, int]],
) -> None:
    """Apply labels only after every candidate in the replay block is frozen."""

    for race_id, candidates in all_candidates_by_race.items():
        answer = answers.get(race_id)
        if answer is None:
            continue
        answer_set = set(answer)
        for name, candidate in candidates.items():
            combo = {int(item) for item in candidate["combo"]}
            hit_count = len(combo & answer_set)
            stats = history.setdefault(
                name,
                {"race_count": 0.0, "exact_count": 0.0, "match_sum": 0.0},
            )
            stats["race_count"] += 1.0
            stats["exact_count"] += float(hit_count == 3)
            stats["match_sum"] += float(hit_count) / 3.0


def _history_race_count(history: dict[str, dict[str, float]]) -> int:
    return int(
        max((stats.get("race_count", 0.0) for stats in history.values()), default=0.0)
    )


def build_strict_candidate_surface(
    *,
    row_cache: dict[str, Any],
    probability_provider: ProbabilityProvider,
    member_keys: tuple[str, ...],
    probability_method: str,
    base_specs: list[dict[str, str]],
    min_train_races: int = DEFAULT_MIN_TRAIN_RACES,
    refit_date_stride: int = DEFAULT_REFIT_DATE_STRIDE,
    candidate_count: int = DEFAULT_CANDIDATE_COUNT,
    max_rank: int = DEFAULT_MAX_RANK,
    max_blocks: int | None = None,
) -> dict[str, Any]:
    started = time.time()
    raw_rows = row_cache.get("rows")
    raw_answers = row_cache.get("answers")
    if not isinstance(raw_rows, list) or not all(
        isinstance(row, dict) for row in raw_rows
    ):
        raise ValueError("row cache rows must be a list of dictionaries")
    if not isinstance(raw_answers, dict):
        raise ValueError("row cache answers must be a dictionary")
    if not member_keys:
        raise ValueError("member_keys must not be empty")

    rows = [dict(row) for row in raw_rows]
    answers = {
        str(race_id): answer
        for race_id, value in raw_answers.items()
        if (answer := _answer(value)) is not None
    }
    rows_by_race = _rows_by_race(rows)
    race_ids_by_date = _race_ids_by_date(rows)
    blocks, warmup_race_ids = build_replay_blocks(
        rows,
        min_train_races=min_train_races,
        refit_date_stride=refit_date_stride,
        max_blocks=max_blocks,
    )
    all_planned_eval_race_ids = [
        race_id
        for block in blocks
        for date in block.eval_dates
        for race_id in race_ids_by_date[date]
    ]
    source_race_ids = sorted(rows_by_race)
    replay_complete = max_blocks is None and set(source_race_ids) == set(
        warmup_race_ids
    ) | set(all_planned_eval_race_ids)

    candidates_by_race: dict[str, dict[str, Any]] = {}
    pattern_history: dict[str, dict[str, float]] = {}
    block_rows: list[dict[str, Any]] = []
    missing_probability_race_ids: list[str] = []
    short_candidate_race_ids: list[str] = []
    oracle_hits = 0
    oracle_races = 0

    for block in blocks:
        train_rows = [row for row in rows if _race_date(row) <= block.train_end]
        eval_date_set = set(block.eval_dates)
        eval_rows = [row for row in rows if _race_date(row) in eval_date_set]
        safe_eval_rows = [{**row, "target": 0} for row in eval_rows]
        probabilities = probability_provider(train_rows, safe_eval_rows, block)
        expected_race_ids = [
            race_id for date in block.eval_dates for race_id in race_ids_by_date[date]
        ]
        history_count_before = _history_race_count(pattern_history)
        block_all_candidates: dict[str, dict[str, dict[str, Any]]] = {}
        block_candidate_race_ids: list[str] = []
        block_oracle_hits = 0
        block_oracle_races = 0

        for race_id in expected_race_ids:
            if any(race_id not in probabilities.get(key, {}) for key in member_keys):
                missing_probability_race_ids.append(race_id)
                continue
            all_candidates = build_all_candidates(
                member_probabilities_by_key=probabilities,
                member_keys=member_keys,
                race_id=race_id,
                method=probability_method,
                max_rank=max_rank,
            )
            selected = select_candidates(
                all_candidates=all_candidates,
                history=pattern_history,
                candidate_count=candidate_count,
            )
            if len(selected) != candidate_count:
                short_candidate_race_ids.append(race_id)
                continue
            race_date = _race_date(rows_by_race[race_id][0])
            candidates_by_race[race_id] = {
                "race_id": race_id,
                "race_date": race_date,
                "timing": {
                    "timing_contract": TIMING_CONTRACT,
                    "fit_through_date": block.train_end,
                    "eval_block": block.name,
                    "selection_uses_active_date_labels": False,
                    "selection_uses_active_block_labels": False,
                    "selection_uses_future_labels": False,
                },
                "candidate_selection": {
                    "selection_contract": SELECTION_CONTRACT,
                    "candidate_count": len(selected),
                    "pattern_history_race_count": history_count_before,
                    "pattern_history_scope": "completed_prior_refit_blocks_only",
                },
                "candidates": selected,
            }
            block_all_candidates[race_id] = all_candidates
            block_candidate_race_ids.append(race_id)
            answer = answers.get(race_id)
            if answer is not None:
                oracle_races += 1
                block_oracle_races += 1
                hit = any(
                    tuple(sorted(int(item) for item in candidate["combo"])) == answer
                    for candidate in selected
                )
                oracle_hits += int(hit)
                block_oracle_hits += int(hit)

        # Labels become visible only after the whole block's options are frozen.
        update_pattern_history(
            history=pattern_history,
            all_candidates_by_race=block_all_candidates,
            answers=answers,
        )
        block_rows.append(
            {
                "name": block.name,
                "train_end": block.train_end,
                "eval_start": block.eval_start,
                "eval_end": block.eval_end,
                "eval_dates": list(block.eval_dates),
                "train_race_count": block.train_race_count,
                "expected_eval_race_count": len(expected_race_ids),
                "candidate_race_count": len(block_candidate_race_ids),
                "pattern_history_race_count_before": history_count_before,
                "pattern_history_race_count_after": _history_race_count(
                    pattern_history
                ),
                "candidate_oracle_exact_rate": round(
                    block_oracle_hits / block_oracle_races,
                    6,
                )
                if block_oracle_races
                else None,
                "selection_uses_active_block_labels": False,
            }
        )

    candidate_race_ids = sorted(candidates_by_race)
    missing_eligible_race_ids = sorted(
        set(all_planned_eval_race_ids) - set(candidate_race_ids)
    )
    timing_violations = sorted(
        race_id
        for race_id, row in candidates_by_race.items()
        if str(row["timing"]["fit_through_date"]) >= str(row["race_date"])
    )
    passed = (
        bool(blocks)
        and bool(candidate_race_ids)
        and not missing_eligible_race_ids
        and not timing_violations
        and not short_candidate_race_ids
    )
    block_oracle_rates = [
        float(row["candidate_oracle_exact_rate"])
        for row in block_rows
        if row["candidate_oracle_exact_rate"] is not None
    ]
    overall_oracle_rate = oracle_hits / oracle_races if oracle_races else None
    min_block_oracle_rate = min(block_oracle_rates, default=None)
    meets_candidate_floor = (
        overall_oracle_rate is not None
        and min_block_oracle_rate is not None
        and overall_oracle_rate >= 0.70
        and min_block_oracle_rate >= 0.70
    )
    return {
        "format_version": FORMAT_VERSION,
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "dataset": row_cache.get("dataset"),
        "timing_contract": TIMING_CONTRACT,
        "selection_contract": SELECTION_CONTRACT,
        "selection_uses_active_or_future_labels": False,
        "pattern_history_uses_completed_prior_blocks_only": True,
        "candidate_count": candidate_count,
        "max_rank": max_rank,
        "min_train_races": min_train_races,
        "refit_date_stride": refit_date_stride,
        "max_blocks": max_blocks,
        "replay_complete": replay_complete,
        "probability_method": probability_method,
        "member_keys": list(member_keys),
        "base_specs": base_specs,
        "coverage": {
            "source_race_count": len(source_race_ids),
            "warmup_skipped_race_count": len(warmup_race_ids),
            "eligible_race_count": len(all_planned_eval_race_ids),
            "candidate_race_count": len(candidate_race_ids),
            "eligible_coverage_rate": round(
                len(candidate_race_ids) / len(all_planned_eval_race_ids),
                6,
            )
            if all_planned_eval_race_ids
            else None,
            "missing_eligible_race_ids": missing_eligible_race_ids,
            "missing_probability_race_ids": sorted(set(missing_probability_race_ids)),
            "short_candidate_race_ids": sorted(set(short_candidate_race_ids)),
            "warmup_race_ids": warmup_race_ids,
        },
        "timing_audit": {
            "passed": not timing_violations,
            "strict_prior_date_race_count": len(candidate_race_ids)
            - len(timing_violations),
            "violation_race_ids": timing_violations,
            "active_eval_targets_replaced_with_zero_before_probability_provider": True,
            "same_day_label_update_count": 0,
            "active_block_label_update_count": 0,
        },
        "candidate_oracle": {
            "race_count": oracle_races,
            "exact_hit_count": oracle_hits,
            "exact_rate": round(overall_oracle_rate, 6)
            if overall_oracle_rate is not None
            else None,
            "min_block_exact_rate": round(min_block_oracle_rate, 6)
            if min_block_oracle_rate is not None
            else None,
            "meets_70_percent_overall_and_block_floor": meets_candidate_floor,
            "diagnostic_only": True,
            "uses_labels_for_evaluation_only": True,
        },
        "blocks": block_rows,
        "candidates_by_race": candidates_by_race,
        "elapsed_seconds": round(time.time() - started, 2),
        "recommended_next_action": (
            "export_laya_temporal_jsonl"
            if passed and replay_complete and meets_candidate_floor
            else (
                "replace_with_higher_coverage_strict_candidate_surface"
                if passed and replay_complete
                else "complete_or_repair_strict_candidate_replay"
            )
        ),
    }


def _production_probability_provider(
    *,
    config_path: Path,
) -> tuple[ProbabilityProvider, tuple[str, ...], str, list[dict[str, str]]]:
    config = _read_json(config_path)
    context = load_evaluation_parameter_context(config_path=config_path)
    model_by_name = {
        candidate.name: candidate for candidate in _capped_model_candidates(config)
    }
    feature_by_name = {
        feature_set.name: feature_set for feature_set in _feature_sets(config)
    }
    pool = _policy_pool()
    member_keys = tuple(_base_key(base_spec) for base_spec in pool.base_specs)
    base_specs = [
        {
            "model_name": base_spec.model_name,
            "feature_set_name": base_spec.feature_set_name,
        }
        for base_spec in pool.base_specs
    ]

    def provider(
        train_rows: list[dict[str, Any]],
        safe_eval_rows: list[dict[str, Any]],
        block: ReplayBlock,
    ) -> dict[str, dict[str, dict[int, float]]]:
        if any(float(row.get("target", 0)) != 0.0 for row in safe_eval_rows):
            raise ValueError("active evaluation labels must be removed before scoring")
        window = WindowSpec(
            block.name,
            block.train_end,
            block.eval_start,
            block.eval_end,
        )
        return _build_member_probabilities(
            model_by_name=model_by_name,
            feature_by_name=feature_by_name,
            rows=[*train_rows, *safe_eval_rows],
            window=window,
            base_specs=pool.base_specs,
            random_state=context.runtime_params.model_random_state,
        )

    return provider, member_keys, pool.method, base_specs


def build_artifact(
    *,
    config_path: Path = DEFAULT_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    min_train_races: int = DEFAULT_MIN_TRAIN_RACES,
    refit_date_stride: int = DEFAULT_REFIT_DATE_STRIDE,
    candidate_count: int = DEFAULT_CANDIDATE_COUNT,
    max_rank: int = DEFAULT_MAX_RANK,
    max_blocks: int | None = None,
) -> dict[str, Any]:
    row_cache = _load_or_build_row_cache(
        config_path=config_path,
        cache_dir=cache_dir,
        refresh_cache=False,
    )
    provider, member_keys, method, base_specs = _production_probability_provider(
        config_path=config_path
    )
    payload = build_strict_candidate_surface(
        row_cache=row_cache,
        probability_provider=provider,
        member_keys=member_keys,
        probability_method=method,
        base_specs=base_specs,
        min_train_races=min_train_races,
        refit_date_stride=refit_date_stride,
        candidate_count=candidate_count,
        max_rank=max_rank,
        max_blocks=max_blocks,
    )
    payload["config_path"] = str(config_path)
    payload["cache_dir"] = str(cache_dir)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--min-train-races", type=int, default=DEFAULT_MIN_TRAIN_RACES)
    parser.add_argument(
        "--refit-date-stride",
        type=int,
        default=DEFAULT_REFIT_DATE_STRIDE,
    )
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--max-rank", type=int, default=DEFAULT_MAX_RANK)
    parser.add_argument("--max-blocks", type=int)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    payload = build_artifact(
        config_path=args.config,
        cache_dir=args.cache_dir,
        min_train_races=args.min_train_races,
        refit_date_stride=args.refit_date_stride,
        candidate_count=args.candidate_count,
        max_rank=args.max_rank,
        max_blocks=args.max_blocks,
    )
    payload["output_path"] = str(args.output)
    _write_json(args.output, payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": payload["status"],
                "replay_complete": payload["replay_complete"],
                "block_count": len(payload["blocks"]),
                "eligible_race_count": payload["coverage"]["eligible_race_count"],
                "candidate_race_count": payload["coverage"]["candidate_race_count"],
                "candidate_oracle_exact_rate": payload["candidate_oracle"][
                    "exact_rate"
                ],
                "elapsed_seconds": payload["elapsed_seconds"],
                "counts_as_70_percent_evidence": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.require_pass and payload["status"] != "passed":
        return 1
    if args.require_complete and not payload["replay_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
