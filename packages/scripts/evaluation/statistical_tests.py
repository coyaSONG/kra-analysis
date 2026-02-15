"""
Statistical testing module for rigorous evaluation of prediction systems.

Provides bootstrap confidence intervals, McNemar's test for paired
comparison, and expected value calculation for betting analysis.

Usage:
    # Compare two evaluation result files
    python3 evaluation/statistical_tests.py results_a.json results_b.json

    # Single file analysis with bootstrap CI
    python3 evaluation/statistical_tests.py results_a.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats


def bootstrap_confidence_interval(
    hit_rates: list[float],
    confidence: float = 0.95,
    n_bootstrap: int = 10_000,
) -> tuple[float, float, float]:
    """Compute bootstrap confidence interval for a sample of hit rates.

    Uses the percentile method with a fixed seed for reproducibility.

    Args:
        hit_rates: Binary hit indicators (1.0 for hit, 0.0 for miss)
            or continuous rate values per race/sample.
        confidence: Confidence level (default 0.95 for 95% CI).
        n_bootstrap: Number of bootstrap resamples.

    Returns:
        (mean, lower_bound, upper_bound) tuple.
    """
    if not hit_rates:
        return 0.0, 0.0, 0.0

    data = np.asarray(hit_rates, dtype=np.float64)
    n = len(data)
    rng = np.random.default_rng(seed=42)

    boot_means = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(data, size=n, replace=True)
        boot_means[i] = sample.mean()

    alpha = 1 - confidence
    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    mean = float(np.mean(boot_means))

    return mean, lower, upper


def mcnemar_test(
    predictions_a: list[bool],
    predictions_b: list[bool],
) -> dict[str, Any]:
    """McNemar's test for comparing two prediction systems on paired data.

    Both prediction lists must have the same length and correspond
    to the same test cases (same races in the same order).

    Uses continuity correction for small sample robustness.

    Args:
        predictions_a: Whether system A was correct on each case.
        predictions_b: Whether system B was correct on each case.

    Returns:
        dict with keys:
            statistic: chi-squared test statistic
            p_value: p-value from chi-squared distribution
            significant: whether p < 0.05
            n_discordant: total discordant pairs
            a_better: cases where only A was correct
            b_better: cases where only B was correct
    """
    if len(predictions_a) != len(predictions_b):
        raise ValueError(
            f"Length mismatch: {len(predictions_a)} vs {len(predictions_b)}. "
            "Both lists must correspond to the same test cases."
        )

    a = np.asarray(predictions_a, dtype=bool)
    b = np.asarray(predictions_b, dtype=bool)

    # Discordant pairs
    n10 = int(np.sum(a & ~b))  # A correct, B wrong
    n01 = int(np.sum(~a & b))  # A wrong, B correct

    if n10 + n01 == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "n_discordant": 0,
            "a_better": 0,
            "b_better": 0,
        }

    # McNemar's test with continuity correction
    statistic = (abs(n10 - n01) - 1) ** 2 / (n10 + n01)
    p_value = float(stats.chi2.sf(statistic, df=1))

    return {
        "statistic": float(statistic),
        "p_value": p_value,
        "significant": p_value < 0.05,
        "n_discordant": n10 + n01,
        "a_better": n10,
        "b_better": n01,
    }


def paired_bootstrap_mean_diff(
    series_a: list[float],
    series_b: list[float],
    confidence: float = 0.95,
    n_bootstrap: int = 10_000,
) -> dict[str, float]:
    """Paired bootstrap CI for mean(B - A) on aligned series."""
    n = min(len(series_a), len(series_b))
    if n == 0:
        return {"mean_diff": 0.0, "lower": 0.0, "upper": 0.0}

    a = np.asarray(series_a[:n], dtype=np.float64)
    b = np.asarray(series_b[:n], dtype=np.float64)
    rng = np.random.default_rng(seed=42)

    diffs = np.empty(n_bootstrap)
    indices = np.arange(n)
    for i in range(n_bootstrap):
        sampled_idx = rng.choice(indices, size=n, replace=True)
        diffs[i] = np.mean(b[sampled_idx] - a[sampled_idx])

    alpha = 1 - confidence
    return {
        "mean_diff": float(np.mean(diffs)),
        "lower": float(np.percentile(diffs, 100 * alpha / 2)),
        "upper": float(np.percentile(diffs, 100 * (1 - alpha / 2))),
    }


def compute_expected_value(
    predictions: list[dict],
    odds: list[float],
) -> float:
    """Calculate expected value (EV) per bet.

    For each prediction:
        EV = P(win) * (odds - 1) - P(lose) * stake
           = prob * (odds - 1) - (1 - prob)

    Args:
        predictions: List of dicts with "probability" key (float in [0, 1]).
        odds: Corresponding decimal odds for each prediction.
            Decimal odds = total payout per unit stake (e.g., 3.5 means
            bet 1, get 3.5 back on win).

    Returns:
        Average EV per bet. Positive means profitable in expectation.
    """
    if not predictions or not odds:
        return 0.0

    total_ev = 0.0
    n = min(len(predictions), len(odds))

    for i in range(n):
        prob = float(predictions[i].get("probability", 0.0))
        decimal_odds = float(odds[i])
        ev = prob * (decimal_odds - 1) - (1 - prob)
        total_ev += ev

    return total_ev / n


def evaluation_report(
    results_file_a: str,
    results_file_b: str | None = None,
) -> str:
    """Generate a formatted evaluation report with statistical testing.

    Single file: computes hit rate with bootstrap confidence interval.
    Two files: computes both CIs and McNemar's paired comparison test.

    Expected JSON format for result files::

        {
            "races": [
                {"hit": true, "predicted": [1,2,3], "actual": [1,3,5], ...},
                {"hit": false, "predicted": [2,4,6], "actual": [1,3,7], ...},
                ...
            ],
            "summary": {"hit_rate": 0.45, "total": 20, "hits": 9}
        }

    Also supports: {"results": [...]} or a bare list at top level.

    Args:
        results_file_a: Path to first evaluation results JSON.
        results_file_b: Optional path to second evaluation results JSON.

    Returns:
        Formatted report string.
    """
    data_a = _load_results(results_file_a)
    if data_a is None:
        return f"[ERROR] Could not load results from {results_file_a}"

    hits_a = _extract_hits(data_a)
    if not hits_a:
        return f"[ERROR] No race results found in {results_file_a}"

    rates_a = [1.0 if h else 0.0 for h in hits_a]

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Statistical Evaluation Report")
    lines.append("=" * 60)

    # System A report
    mean_a, lower_a, upper_a = bootstrap_confidence_interval(rates_a)
    lines.append(f"\nSystem A: {Path(results_file_a).name}")
    lines.append(f"  Races evaluated: {len(hits_a)}")
    lines.append(f"  Hits: {sum(hits_a)}")
    lines.append(
        f"  Hit rate: {mean_a * 100:.1f}% "
        f"(95% CI: [{lower_a * 100:.1f}%, {upper_a * 100:.1f}%])"
    )

    if results_file_b is not None:
        data_b = _load_results(results_file_b)
        if data_b is None:
            lines.append(f"\n[ERROR] Could not load results from {results_file_b}")
            return "\n".join(lines)

        hits_b = _extract_hits(data_b)
        if not hits_b:
            lines.append(f"\n[ERROR] No race results found in {results_file_b}")
            return "\n".join(lines)

        rates_b = [1.0 if h else 0.0 for h in hits_b]

        # System B report
        mean_b, lower_b, upper_b = bootstrap_confidence_interval(rates_b)
        lines.append(f"\nSystem B: {Path(results_file_b).name}")
        lines.append(f"  Races evaluated: {len(hits_b)}")
        lines.append(f"  Hits: {sum(hits_b)}")
        lines.append(
            f"  Hit rate: {mean_b * 100:.1f}% "
            f"(95% CI: [{lower_b * 100:.1f}%, {upper_b * 100:.1f}%])"
        )

        # McNemar's test (paired: must use same race subset)
        min_len = min(len(hits_a), len(hits_b))
        if min_len > 0:
            mc = mcnemar_test(hits_a[:min_len], hits_b[:min_len])
            lines.append(f"\nComparison (McNemar's Test, n={min_len}):")
            lines.append(f"  A better / B better: {mc['a_better']} / {mc['b_better']}")
            lines.append(f"  Test statistic: {mc['statistic']:.4f}")
            lines.append(f"  P-value: {mc['p_value']:.4f}")
            sig_str = "YES" if mc["significant"] else "No"
            lines.append(f"  Significant (p < 0.05): {sig_str}")

            diff = mean_b - mean_a
            lines.append(f"\n  Difference (B - A): {diff * 100:+.1f} percentage points")
            if mc["significant"]:
                winner = "B" if diff > 0 else "A"
                lines.append(f"  => System {winner} is significantly better.")
            else:
                lines.append("  => No statistically significant difference.")

            paired_ci = paired_bootstrap_mean_diff(rates_a[:min_len], rates_b[:min_len])
            lines.append(
                "  Paired bootstrap CI (B-A): "
                f"{paired_ci['mean_diff'] * 100:+.2f}pp "
                f"[{paired_ci['lower'] * 100:+.2f}, {paired_ci['upper'] * 100:+.2f}]"
            )

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_results(filepath: str) -> dict | list | None:
    """Load evaluation results JSON file."""
    try:
        path = Path(filepath)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _extract_hits(data: dict | list) -> list[bool]:
    """Extract hit/miss list from results data.

    Supports multiple formats:
    - {"races": [{"hit": true}, ...]}
    - {"results": [{"correct": true}, ...]}
    - [{"hit": true}, ...]  (list at top level)
    """
    if isinstance(data, list):
        return [bool(r.get("hit", r.get("correct", False))) for r in data]

    races = data.get("races", data.get("results", []))
    return [bool(r.get("hit", r.get("correct", False))) for r in races]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Statistical evaluation of prediction results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 evaluation/statistical_tests.py results_v1.json
  python3 evaluation/statistical_tests.py results_v1.json results_v2.json
        """,
    )
    parser.add_argument("file_a", help="First evaluation results JSON file")
    parser.add_argument(
        "file_b",
        nargs="?",
        default=None,
        help="Second results JSON file (for paired comparison)",
    )
    args = parser.parse_args()

    report = evaluation_report(args.file_a, args.file_b)
    print(report)
