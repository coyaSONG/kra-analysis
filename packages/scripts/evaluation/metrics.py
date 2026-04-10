"""Evaluation metrics utilities for prompt prediction quality."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


def _clip_probability(value: float) -> float:
    return min(max(value, 1e-6), 1 - 1e-6)


def _extract_confidence_probability(result: dict[str, Any]) -> float:
    confidence = result.get("confidence", 50)
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        confidence_float = 50.0

    if confidence_float > 1.0:
        confidence_float /= 100.0

    return _clip_probability(confidence_float)


def _winner_number(result: dict[str, Any]) -> int | None:
    actual = result.get("actual") or []
    if isinstance(actual, list) and actual:
        try:
            return int(actual[0])
        except (TypeError, ValueError):
            return None
    return None


def _predicted_numbers(result: dict[str, Any]) -> list[int]:
    predicted = result.get("predicted") or []
    out: list[int] = []
    for item in predicted:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def _binary_log_loss(y_true: list[int], y_prob: list[float]) -> float:
    if not y_true:
        return 0.0

    losses = []
    for y, p in zip(y_true, y_prob, strict=False):
        p_clipped = _clip_probability(p)
        losses.append(-(y * math.log(p_clipped) + (1 - y) * math.log(1 - p_clipped)))
    return sum(losses) / len(losses)


def _brier_score(y_true: list[int], y_prob: list[float]) -> float:
    if not y_true:
        return 0.0
    return sum((p - y) ** 2 for y, p in zip(y_true, y_prob, strict=False)) / len(y_true)


def _ece(y_true: list[int], y_prob: list[float], bins: int = 10) -> float:
    if not y_true:
        return 0.0

    bin_pairs: dict[int, list[tuple[int, float]]] = {i: [] for i in range(bins)}
    for y, p in zip(y_true, y_prob, strict=False):
        idx = min(int(p * bins), bins - 1)
        bin_pairs[idx].append((y, p))

    total = len(y_true)
    error = 0.0
    for pairs in bin_pairs.values():
        if not pairs:
            continue
        accuracy = sum(y for y, _ in pairs) / len(pairs)
        confidence = sum(p for _, p in pairs) / len(pairs)
        error += (len(pairs) / total) * abs(accuracy - confidence)
    return error


def _topk_metrics(
    results: list[dict[str, Any]], topk_values: tuple[int, ...]
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if not results:
        for k in topk_values:
            metrics[f"top_{k}"] = 0.0
        return metrics

    for k in topk_values:
        hits = 0
        total = 0
        for result in results:
            winner = _winner_number(result)
            predicted = _predicted_numbers(result)
            if winner is None or not predicted:
                continue
            total += 1
            effective_k = min(k, len(predicted))
            if winner in predicted[:effective_k]:
                hits += 1
        metrics[f"top_{k}"] = (hits / total) if total > 0 else 0.0

    return metrics


def _actual_numbers(result: dict[str, Any]) -> list[int]:
    """Extract actual top-3 horse numbers from result."""
    actual = result.get("actual") or []
    out: list[int] = []
    for item in actual:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def _set_match_score(predicted: list[int], actual: list[int], k: int = 3) -> float:
    """Top-k intersection ratio between predicted and actual (0.0 ~ 1.0)."""
    pred_set = set(predicted[:k])
    actual_set = set(actual[:k])
    if not actual_set:
        return 0.0
    return len(pred_set & actual_set) / k


def is_unordered_topk_exact_match(
    predicted: list[int], actual: list[int], k: int = 3
) -> bool:
    """Whether predicted/actual top-k sets match exactly, ignoring order."""
    pred_set = set(predicted[:k])
    actual_set = set(actual[:k])
    if len(pred_set) != k or len(actual_set) != k:
        return False
    return pred_set == actual_set


def is_ordered_topk_exact_match(
    predicted: list[int], actual: list[int], k: int = 3
) -> bool:
    """Whether predicted/actual top-k sequence matches exactly, preserving order."""
    pred_slice = predicted[:k]
    actual_slice = actual[:k]
    if len(pred_slice) != k or len(actual_slice) != k:
        return False
    return pred_slice == actual_slice


def _is_race_hit(result: dict[str, Any], k: int = 3) -> bool:
    explicit_hit = result.get("hit")
    if isinstance(explicit_hit, bool):
        return explicit_hit

    reward = result.get("reward") or {}
    if "unordered_top3_exact_match" in reward:
        return bool(reward.get("unordered_top3_exact_match"))

    predicted = _predicted_numbers(result)
    actual = _actual_numbers(result)
    if not predicted or not actual:
        return False

    return is_unordered_topk_exact_match(predicted, actual, k=k)


def _is_ordered_race_hit(result: dict[str, Any], k: int = 3) -> bool:
    explicit_hit = result.get("ordered_hit")
    if isinstance(explicit_hit, bool):
        return explicit_hit

    reward = result.get("reward") or {}
    if "ordered_top3_exact_match" in reward:
        return bool(reward.get("ordered_top3_exact_match"))

    predicted = _predicted_numbers(result)
    actual = _actual_numbers(result)
    if not predicted or not actual:
        return False

    return is_ordered_topk_exact_match(predicted, actual, k=k)


def _race_hit_metrics(
    detailed_results: list[dict[str, Any]], k: int = 3
) -> dict[str, float | int]:
    total_races = len(detailed_results)
    race_hit_count = sum(1 for result in detailed_results if _is_race_hit(result, k=k))
    return {
        "race_hit_count": race_hit_count,
        "race_hit_rate": (race_hit_count / total_races) if total_races > 0 else 0.0,
    }


def _ordered_race_hit_metrics(
    detailed_results: list[dict[str, Any]], k: int = 3
) -> dict[str, float | int]:
    total_races = len(detailed_results)
    ordered_race_hit_count = sum(
        1 for result in detailed_results if _is_ordered_race_hit(result, k=k)
    )
    return {
        "ordered_race_hit_count": ordered_race_hit_count,
        "ordered_race_hit_rate": (ordered_race_hit_count / total_races)
        if total_races > 0
        else 0.0,
    }


def _normalize_race_id(value: object) -> str | None:
    race_id = str(value or "").strip()
    return race_id or None


def _collect_unique_race_ids(
    race_ids: Sequence[object] | None,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    if race_ids is None:
        return normalized

    for value in race_ids:
        race_id = _normalize_race_id(value)
        if race_id is None or race_id in seen:
            continue
        seen.add(race_id)
        normalized.append(race_id)
    return normalized


def _has_prediction_output(result: dict[str, Any]) -> bool:
    return result.get("prediction") is not None or bool(_predicted_numbers(result))


def _compute_prediction_coverage_validation(
    detailed_results: list[dict[str, Any]],
    *,
    reference_race_ids: Sequence[object] | None = None,
) -> dict[str, Any]:
    reference_ids = _collect_unique_race_ids(reference_race_ids)
    if not reference_ids:
        reference_ids = _collect_unique_race_ids(
            result.get("race_id") for result in detailed_results
        )

    predicted_ids = _collect_unique_race_ids(
        result.get("race_id")
        for result in detailed_results
        if _has_prediction_output(result)
    )

    reference_set = set(reference_ids)
    predicted_set = set(predicted_ids)
    missing_prediction_race_ids = [
        race_id for race_id in reference_ids if race_id not in predicted_set
    ]
    unexpected_prediction_race_ids = [
        race_id for race_id in predicted_ids if race_id not in reference_set
    ]
    predicted_race_count = sum(
        1 for race_id in reference_ids if race_id in predicted_set
    )
    expected_race_count = len(reference_ids)

    return {
        "prediction_coverage": (
            predicted_race_count / expected_race_count if expected_race_count else 0.0
        ),
        "expected_race_count": expected_race_count,
        "predicted_race_count": predicted_race_count,
        "missing_prediction_count": len(missing_prediction_race_ids),
        "missing_prediction_race_ids": missing_prediction_race_ids,
        "unexpected_prediction_count": len(unexpected_prediction_race_ids),
        "unexpected_prediction_race_ids": unexpected_prediction_race_ids,
    }


def _ndcg_at_k(predicted: list[int], actual: list[int], k: int = 3) -> float:
    """NDCG@k - measures ranking quality of predicted vs actual.

    Relevance: horse gets score based on actual position.
    actual[0] (winner) = relevance 3, actual[1] = 2, actual[2] = 1
    Others = 0.
    """
    if not actual or not predicted:
        return 0.0

    # Build relevance map: actual position -> score
    relevance = {}
    for i, horse in enumerate(actual[:k]):
        try:
            relevance[int(horse)] = k - i  # winner=3, 2nd=2, 3rd=1
        except (TypeError, ValueError):
            continue

    if not relevance:
        return 0.0

    # DCG for predicted ranking
    dcg = 0.0
    for i, horse in enumerate(predicted[:k]):
        try:
            rel = relevance.get(int(horse), 0)
        except (TypeError, ValueError):
            rel = 0
        dcg += rel / math.log2(i + 2)  # i+2 because position is 1-indexed, log2(1)=0

    # Ideal DCG: sort relevance scores descending
    ideal_rels = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_rels))

    if idcg == 0:
        return 0.0

    return dcg / idcg


def _brier_set_match(results: list[dict[str, Any]], k: int = 3) -> float:
    """Brier score for set match: (confidence - set_match_score)^2."""
    scores = []
    for result in results:
        predicted = _predicted_numbers(result)
        actual = _actual_numbers(result)
        if not predicted or not actual:
            continue
        confidence = _extract_confidence_probability(result)
        match_score = _set_match_score(predicted, actual, k)
        scores.append((confidence - match_score) ** 2)

    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _roi_metrics(results: list[dict[str, Any]]) -> dict[str, float | int]:
    bets = 0
    wins = 0
    total_profit = 0.0

    for result in results:
        winner = _winner_number(result)
        predicted = _predicted_numbers(result)
        if winner is None or not predicted:
            continue

        predicted_top1 = predicted[0]
        entries = result.get("race_data", {}).get("entries", [])
        odds_lookup: dict[int, float] = {}
        for entry in entries:
            try:
                horse_no = int(entry.get("horse_no"))
                odds_lookup[horse_no] = float(entry.get("win_odds"))
            except (TypeError, ValueError):
                continue

        odds = odds_lookup.get(predicted_top1)
        if odds is None or odds <= 0:
            continue

        bets += 1
        if predicted_top1 == winner:
            wins += 1
            total_profit += odds - 1.0
        else:
            total_profit -= 1.0

    avg_roi = total_profit / bets if bets > 0 else 0.0

    return {
        "avg_roi": avg_roi,
        "bets": bets,
        "wins": wins,
        "total_profit": total_profit,
    }


def compute_prediction_quality_metrics(
    detailed_results: list[dict[str, Any]],
    topk_values: tuple[int, ...] = (1, 3),
    ece_bins: int = 10,
    defer_threshold: float | None = None,
    reference_race_ids: Sequence[object] | None = None,
) -> dict[str, Any]:
    """Compute quality metrics from detailed evaluation results.

    The current dataset primarily provides top-3 picks and confidence values,
    so log loss / brier / ECE are computed on a binary event:
    "predicted top-1 horse is actual winner".
    """

    race_hit_summary = _race_hit_metrics(detailed_results)
    ordered_race_hit_summary = _ordered_race_hit_metrics(detailed_results)
    prediction_coverage_validation = _compute_prediction_coverage_validation(
        detailed_results,
        reference_race_ids=reference_race_ids,
    )

    usable_results = [
        r
        for r in detailed_results
        if r.get("prediction") is not None or _predicted_numbers(r)
    ]

    if not usable_results:
        return {
            "log_loss": 0.0,
            "brier": 0.0,
            "ece": 0.0,
            "topk": {f"top_{k}": 0.0 for k in topk_values},
            "roi": {"avg_roi": 0.0, "bets": 0, "wins": 0, "total_profit": 0.0},
            "coverage": 0.0,
            "deferred_count": 0,
            "samples": 0,
            **prediction_coverage_validation,
            **race_hit_summary,
            **ordered_race_hit_summary,
        }

    confidences = [_extract_confidence_probability(r) for r in usable_results]
    if defer_threshold is not None:
        kept = [
            (result, confidence)
            for result, confidence in zip(usable_results, confidences, strict=False)
            if confidence >= defer_threshold
        ]
        deferred_count = len(usable_results) - len(kept)
        filtered_results = [result for result, _ in kept]
        filtered_confidences = [confidence for _, confidence in kept]
    else:
        deferred_count = 0
        filtered_results = usable_results
        filtered_confidences = confidences

    y_true: list[int] = []
    y_prob: list[float] = []
    for result, confidence in zip(filtered_results, filtered_confidences, strict=False):
        winner = _winner_number(result)
        predicted = _predicted_numbers(result)
        if winner is None or not predicted:
            continue
        y_true.append(1 if predicted[0] == winner else 0)
        y_prob.append(confidence)

    coverage = (len(filtered_results) / len(usable_results)) if usable_results else 0.0

    # New v6 metrics
    set_match_scores = []
    ndcg_scores = []
    for result in filtered_results:
        predicted = _predicted_numbers(result)
        actual = _actual_numbers(result)
        if predicted and actual:
            set_match_scores.append(_set_match_score(predicted, actual))
            ndcg_scores.append(_ndcg_at_k(predicted, actual))

    return {
        "log_loss": _binary_log_loss(y_true, y_prob),
        "brier": _brier_score(y_true, y_prob),
        "ece": _ece(y_true, y_prob, bins=ece_bins),
        "topk": _topk_metrics(filtered_results, topk_values),
        "roi": _roi_metrics(filtered_results),
        "coverage": coverage,
        "deferred_count": deferred_count,
        "samples": len(usable_results),
        **prediction_coverage_validation,
        "set_match_rate": sum(set_match_scores) / len(set_match_scores)
        if set_match_scores
        else 0.0,
        "ndcg3": sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0,
        "brier_set": _brier_set_match(filtered_results),
        **race_hit_summary,
        **ordered_race_hit_summary,
    }


def compute_stratified_metrics(
    detailed_results: list[dict[str, Any]],
    dimensions: list[str] | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    """Compute metrics stratified by different dimensions.

    Returns: {dimension: {subgroup: {metric: value}}}
    """
    if dimensions is None:
        dimensions = ["distance", "field_size", "meet"]

    stratified: dict[str, dict[str, dict[str, float]]] = {}

    for dim in dimensions:
        groups: dict[str, list[dict]] = {}

        for result in detailed_results:
            predicted = _predicted_numbers(result)
            actual = _actual_numbers(result)
            if not predicted or not actual:
                continue

            race_data = result.get("race_data", {})
            race_info = race_data.get("raceInfo", {})

            if dim == "distance":
                dist = 0
                try:
                    dist = int(race_info.get("rcDist", 0))
                except (TypeError, ValueError):
                    pass
                if dist < 1200:
                    group_key = "sprint"
                elif dist <= 1800:
                    group_key = "mid"
                else:
                    group_key = "route"
            elif dim == "field_size":
                horses = race_data.get("horses", race_data.get("entries", []))
                size = len(horses)
                if size <= 8:
                    group_key = "small"
                elif size <= 12:
                    group_key = "medium"
                else:
                    group_key = "large"
            elif dim == "meet":
                meet = race_info.get("meet", result.get("meet", "unknown"))
                group_key = str(meet)
            else:
                group_key = "unknown"

            groups.setdefault(group_key, []).append(result)

        dim_metrics: dict[str, dict[str, float]] = {}
        for group_key, group_results in groups.items():
            sm_scores = []
            ndcg_scores_g = []
            for r in group_results:
                p = _predicted_numbers(r)
                a = _actual_numbers(r)
                if p and a:
                    sm_scores.append(_set_match_score(p, a))
                    ndcg_scores_g.append(_ndcg_at_k(p, a))

            full_match = sum(
                1
                for r in group_results
                if is_unordered_topk_exact_match(
                    _predicted_numbers(r),
                    _actual_numbers(r),
                )
            )
            dim_metrics[group_key] = {
                "count": len(group_results),
                "success_rate": (full_match / len(sm_scores) * 100)
                if sm_scores
                else 0.0,
                "set_match_rate": sum(sm_scores) / len(sm_scores) if sm_scores else 0.0,
                "ndcg3": sum(ndcg_scores_g) / len(ndcg_scores_g)
                if ndcg_scores_g
                else 0.0,
            }

        stratified[dim] = dim_metrics

    return stratified
