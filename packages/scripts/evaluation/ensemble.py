"""
Self-Consistency Ensemble with Ranked Voting (Borda count).
Multiple predictions are aggregated to reduce LLM stochastic variance.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class SelfConsistencyEnsemble:
    """Self-Consistency with Ranked Voting for top-3 prediction."""

    def __init__(self, k: int = 5, temperature: float = 0.7):
        self.k = k
        self.temperature = temperature

    def aggregate_predictions(self, predictions: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate K predictions using Borda count.

        Each prediction's predicted=[h1, h2, h3]:
          - 1st place gets 3 points
          - 2nd place gets 2 points
          - 3rd place gets 1 point

        Sum across all K predictions, select top-3 by total score.

        Args:
            predictions: List of prediction dicts, each with "predicted" key.

        Returns:
            Aggregated prediction dict.
        """
        if not predictions:
            return {
                "predicted": [],
                "confidence": 0,
                "individual_predictions": [],
                "vote_counts": {},
                "consistency_score": 0.0,
            }

        if len(predictions) == 1:
            pred = predictions[0]
            return {
                "predicted": pred.get("predicted", []),
                "confidence": pred.get("confidence", 50),
                "individual_predictions": predictions,
                "vote_counts": {},
                "consistency_score": 1.0,
            }

        # Borda count scoring
        scores: dict[int, int] = defaultdict(int)
        borda_weights = [3, 2, 1]  # 1st, 2nd, 3rd place points

        for pred in predictions:
            predicted = pred.get("predicted", [])
            for rank, horse in enumerate(predicted[:3]):
                try:
                    horse_no = int(horse)
                    scores[horse_no] += borda_weights[rank] if rank < 3 else 0
                except (TypeError, ValueError):
                    continue

        # Sort by score descending, take top-3
        sorted_horses = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top3 = [h for h, _ in sorted_horses[:3]]

        # Consistency score
        consistency = self.compute_consistency_score(predictions)

        # Average confidence from individual predictions
        confidences = []
        for pred in predictions:
            try:
                conf = float(pred.get("confidence", 50))
                confidences.append(conf)
            except (TypeError, ValueError):
                pass
        avg_confidence = sum(confidences) / len(confidences) if confidences else 50

        # Scale confidence by consistency
        adjusted_confidence = avg_confidence * consistency

        return {
            "predicted": top3,
            "confidence": int(adjusted_confidence),
            "individual_predictions": predictions,
            "vote_counts": dict(scores),
            "consistency_score": consistency,
        }

    def compute_consistency_score(self, predictions: list[dict[str, Any]]) -> float:
        """Compute prediction consistency score.

        Score = average frequency of top-3 horses across all K predictions / K.
        """
        if not predictions or len(predictions) <= 1:
            return 1.0

        k = len(predictions)
        # Count how many times each horse appears across all predictions
        horse_counts: Counter[int] = Counter()
        for pred in predictions:
            for horse in pred.get("predicted", [])[:3]:
                try:
                    horse_counts[int(horse)] += 1
                except (TypeError, ValueError):
                    continue

        if not horse_counts:
            return 0.0

        # Top-3 most common horses
        top3_counts = [count for _, count in horse_counts.most_common(3)]
        # Average frequency of top-3 horses / K
        return sum(top3_counts) / (len(top3_counts) * k) if top3_counts else 0.0

    def should_abstain(self, consistency_score: float, threshold: float = 0.6) -> bool:
        """Determine if prediction should be deferred due to low consistency."""
        return consistency_score < threshold
