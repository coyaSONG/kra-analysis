"""Evaluation metrics utilities for prompt prediction quality."""

from __future__ import annotations

import math
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
    for y, p in zip(y_true, y_prob):
        p_clipped = _clip_probability(p)
        losses.append(-(y * math.log(p_clipped) + (1 - y) * math.log(1 - p_clipped)))
    return sum(losses) / len(losses)


def _brier_score(y_true: list[int], y_prob: list[float]) -> float:
    if not y_true:
        return 0.0
    return sum((p - y) ** 2 for y, p in zip(y_true, y_prob)) / len(y_true)


def _ece(y_true: list[int], y_prob: list[float], bins: int = 10) -> float:
    if not y_true:
        return 0.0

    bin_pairs: dict[int, list[tuple[int, float]]] = {i: [] for i in range(bins)}
    for y, p in zip(y_true, y_prob):
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


def _topk_metrics(results: list[dict[str, Any]], topk_values: tuple[int, ...]) -> dict[str, float]:
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
) -> dict[str, Any]:
    """Compute quality metrics from detailed evaluation results.

    The current dataset primarily provides top-3 picks and confidence values,
    so log loss / brier / ECE are computed on a binary event:
    "predicted top-1 horse is actual winner".
    """

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
        }

    confidences = [_extract_confidence_probability(r) for r in usable_results]
    if defer_threshold is not None:
        kept = [
            (result, confidence)
            for result, confidence in zip(usable_results, confidences)
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
    for result, confidence in zip(filtered_results, filtered_confidences):
        winner = _winner_number(result)
        predicted = _predicted_numbers(result)
        if winner is None or not predicted:
            continue
        y_true.append(1 if predicted[0] == winner else 0)
        y_prob.append(confidence)

    coverage = (len(filtered_results) / len(usable_results)) if usable_results else 0.0

    return {
        "log_loss": _binary_log_loss(y_true, y_prob),
        "brier": _brier_score(y_true, y_prob),
        "ece": _ece(y_true, y_prob, bins=ece_bins),
        "topk": _topk_metrics(filtered_results, topk_values),
        "roi": _roi_metrics(filtered_results),
        "coverage": coverage,
        "deferred_count": deferred_count,
        "samples": len(usable_results),
    }
