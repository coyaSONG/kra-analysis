"""Confidence calibration using histogram binning.

Provides post-hoc calibration for LLM confidence scores by learning
the mapping between raw confidence and actual success rates.
"""

from __future__ import annotations

from typing import Any


class ConfidenceCalibrator:
    """Histogram-binning confidence calibrator.

    Uses simple binning with linear interpolation instead of sklearn's
    IsotonicRegression to avoid heavy dependencies.
    """

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self.is_fitted = False
        self._bin_edges: list[float] = []
        self._bin_means: list[float] = []  # avg confidence per bin
        self._bin_actuals: list[float] = []  # avg actual rate per bin

    def fit(self, confidences: list[float], actuals: list[int]) -> None:
        """Learn calibration mapping from validation set.

        Args:
            confidences: Raw confidence probabilities (0-1 scale).
            actuals: Binary outcomes (1 = success, 0 = failure).
        """
        if not confidences or not actuals or len(confidences) != len(actuals):
            return

        pairs = sorted(zip(confidences, actuals))
        n = len(pairs)
        bin_size = max(1, n // self.n_bins)

        self._bin_edges = []
        self._bin_means = []
        self._bin_actuals = []

        for i in range(0, n, bin_size):
            chunk = pairs[i : i + bin_size]
            if not chunk:
                continue
            confs = [c for c, _ in chunk]
            acts = [a for _, a in chunk]
            self._bin_edges.append(min(confs))
            self._bin_means.append(sum(confs) / len(confs))
            self._bin_actuals.append(sum(acts) / len(acts))

        self.is_fitted = bool(self._bin_edges)

    def calibrate(self, confidence: float) -> float:
        """Map raw confidence to calibrated probability.

        Uses linear interpolation between learned bin actual rates.
        """
        if not self.is_fitted:
            return confidence

        # Find surrounding bins by confidence value
        if confidence <= self._bin_means[0]:
            return self._bin_actuals[0]
        if confidence >= self._bin_means[-1]:
            return self._bin_actuals[-1]

        # Linear interpolation
        for i in range(len(self._bin_means) - 1):
            if self._bin_means[i] <= confidence <= self._bin_means[i + 1]:
                span = self._bin_means[i + 1] - self._bin_means[i]
                if span == 0:
                    return self._bin_actuals[i]
                t = (confidence - self._bin_means[i]) / span
                return (
                    self._bin_actuals[i] * (1 - t) + self._bin_actuals[i + 1] * t
                )

        return confidence

    def reliability_diagram(
        self,
        confidences: list[float],
        actuals: list[int],
        bins: int = 10,
    ) -> dict[str, Any]:
        """Generate reliability diagram data.

        Returns:
            Dict with bin_centers, bin_accuracies, bin_confidences, bin_counts,
            and overall ECE.
        """
        if not confidences or not actuals:
            return {
                "bin_centers": [],
                "bin_accuracies": [],
                "bin_confidences": [],
                "bin_counts": [],
                "ece": 0.0,
            }

        bin_width = 1.0 / bins
        bin_centers: list[float] = []
        bin_accuracies: list[float] = []
        bin_confidences: list[float] = []
        bin_counts: list[int] = []

        total = len(confidences)
        ece = 0.0

        for b in range(bins):
            lo = b * bin_width
            hi = (b + 1) * bin_width

            indices = [
                i
                for i, c in enumerate(confidences)
                if lo <= c < hi or (b == bins - 1 and c == hi)
            ]
            count = len(indices)
            bin_counts.append(count)
            bin_centers.append(lo + bin_width / 2)

            if count == 0:
                bin_accuracies.append(0.0)
                bin_confidences.append(0.0)
                continue

            acc = sum(actuals[i] for i in indices) / count
            conf = sum(confidences[i] for i in indices) / count
            bin_accuracies.append(acc)
            bin_confidences.append(conf)
            ece += (count / total) * abs(acc - conf)

        return {
            "bin_centers": bin_centers,
            "bin_accuracies": bin_accuracies,
            "bin_confidences": bin_confidences,
            "bin_counts": bin_counts,
            "ece": ece,
        }
