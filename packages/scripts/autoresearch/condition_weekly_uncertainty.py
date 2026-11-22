"""Full-window A24/B34 arithmetic for the unregistered 12-week draft.

All admissions are preconditions of a future evidence adapter. This module
does not open a study, verify that a population is genuine, or promote a model.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from autoresearch import condition_outcome_accounting as accounting

WEEKS = 12
SEED = 20261020
REPLICATES = 10_000
POPULATION_STATES = {"pending_population", "verified_racing", "verified_no_racing"}


@dataclass(frozen=True)
class WeekPopulation:
    """The original week's race obligations and a normalized closure state."""

    race_ids: tuple[str, ...] = ()
    status: str = "pending_population"

    def __post_init__(self):
        if (
            self.status not in POPULATION_STATES
            or type(self.race_ids) is not tuple
            or any(type(value) is not str for value in self.race_ids)
            or (self.status == "verified_racing" and not self.race_ids)
            or (self.status == "verified_no_racing" and self.race_ids)
        ):
            raise ValueError("weekly_population_state_conflict")


def _calendar(first_monday: str) -> tuple[str, ...]:
    if (
        type(first_monday) is not str
        or len(first_monday) != 8
        or not first_monday.startswith("20")
        or not (first_monday.isascii() and first_monday.isdecimal())
    ):
        raise ValueError("weekly_requires_canonical_kst_monday")
    date = datetime.strptime(first_monday, "%Y%m%d")
    if date.weekday() != 0 or date.strftime("%Y%m%d") != first_monday:
        raise ValueError("weekly_requires_canonical_kst_monday")
    return tuple(
        (date + timedelta(weeks=index)).strftime("%Y%m%d") for index in range(WEEKS + 1)
    )


def _interval(numerators, denominators, scale=1):
    if np.all(numerators * denominators[0] == numerators[0] * denominators):
        return {"status": "degenerate_resample_distribution", "interval": None}
    quantiles = np.quantile(
        scale * numerators / denominators, [0.025, 0.975], method="linear"
    )
    return {"status": "descriptive", "interval": quantiles.tolist()}


def _bootstrap(weekly_totals, length):
    generator = np.random.Generator(np.random.PCG64(SEED))
    starts = generator.integers(
        0, WEEKS - length + 1, size=(REPLICATES, WEEKS // length)
    )
    indexes = starts[..., None] + np.arange(length)
    n, a, b = np.asarray(weekly_totals, dtype=np.int64)[indexes].sum(axis=(1, 2)).T
    return {
        "block_length_weeks": length,
        "intervals": {
            "a24_exact_accuracy": _interval(a, n),
            "b34_exact_accuracy": _interval(b, n),
            "b34_minus_a24_pp": _interval(b - a, n, scale=100),
        },
    }


def summarize_window(
    first_monday: str,
    populations: Mapping[str, WeekPopulation],
    predictions: Mapping[str, Mapping[str, accounting.PredictionEvidence]],
    outcomes: Mapping[str, accounting.OutcomeEvidence],
):
    """Use the frozen calendar, without any authority or mutable data lookups."""
    calendar = _calendar(first_monday)
    if set(populations) - set(calendar[:-1]) or any(
        type(week) is not WeekPopulation for week in populations.values()
    ):
        raise ValueError("weekly_population_outside_frozen_calendar")
    if set(predictions) != set(accounting.ARMS):
        raise ValueError("both_model_mappings_required")

    weeks, universe = [], set()
    for monday, next_monday in zip(calendar[:-1], calendar[1:], strict=True):
        scope = populations.get(monday, WeekPopulation())
        keys = set(scope.race_ids)
        if len(keys) != len(scope.race_ids) or universe & keys:
            raise ValueError("weekly_duplicate_original_race")
        if any(not monday <= race[:8] < next_monday for race in keys):
            raise ValueError("weekly_race_outside_original_week")
        universe.update(keys)
        weeks.append((monday, scope, keys))
    if set(outcomes) - universe or any(
        set(predictions[a]) - universe for a in accounting.ARMS
    ):
        raise ValueError("evidence_outside_population")

    paired, summaries, weekly_totals = Counter(), [], []
    total_counts = {arm: Counter() for arm in accounting.ARMS}
    failures = Counter()
    for monday, scope, keys in weeks:
        verified = scope.status != "pending_population"
        account = accounting.summarize(
            scope.race_ids,
            {
                arm: {
                    rid: predictions[arm][rid] for rid in keys & predictions[arm].keys()
                }
                for arm in accounting.ARMS
            },
            {rid: outcomes[rid] for rid in keys & outcomes.keys()},
            full_population_verified=verified,
        )
        for arm, arm_summary in account["arms"].items():
            total_counts[arm].update(arm_summary["counts"])
            failures[arm] += arm_summary["proven_prediction_failures"]
        paired.update(account["paired_cells"])
        counts = {arm: account["arms"][arm]["counts"] for arm in accounting.ARMS}
        summaries.append(
            {
                "monday_kst": monday,
                "population_status": scope.status,
                "known_race_ids": sorted(keys),
                "denominator": account["denominator"],
                "arms_counts": counts,
                "paired_cells": account["paired_cells"],
            }
        )
        weekly_totals.append((len(keys), counts["A24"]["hit"], counts["B34"]["hit"]))

    verified = all(scope.status != "pending_population" for _, scope, _ in weeks)
    denominator = len(universe) if verified else None
    complete = bool(denominator) and paired["unresolved"] == 0
    raced_weeks = sum(scope.status == "verified_racing" for _, scope, _ in weeks)
    arms = {}
    for arm, counts in total_counts.items():
        ready = bool(denominator) and counts["pending"] == counts["undefined"] == 0
        arms[arm] = {
            "counts": {key: counts[key] for key in accounting.SCORES},
            "exact_accuracy": counts["hit"] / denominator if ready else None,
            "proven_prediction_failures": failures[arm],
        }
    gap = total_counts["B34"]["hit"] - total_counts["A24"]["hit"]

    issues = []
    if not verified:
        issues.append("population_unverified")
    elif not denominator:
        issues.append("no_races_in_closed_window")
    if paired["unresolved"]:
        issues.append("pending_or_undefined_pair")
    if raced_weeks != WEEKS:
        issues.append("fewer_than_12_verified_race_bearing_weeks")
    can_resample = complete and not issues
    return {
        "scope": "normalized_arithmetic_only_not_prospective_evidence",
        "calendar_weeks": WEEKS,
        "verified_race_bearing_weeks": raced_weeks,
        "known_race_ids_count": len(universe),
        "denominator": denominator,
        "full_population_verified_by_caller": verified,
        "complete_paired_comparison": complete,
        "arms": arms,
        "paired_cells": {key: paired[key] for key in (*accounting.CELLS, "unresolved")},
        "b34_minus_a24_pp": 100 * gap / denominator if complete else None,
        "descriptive_winner": ("B34" if gap > 0 else "A24" if gap < 0 else "tie")
        if complete
        else None,
        "weeks": summaries,
        "uncertainty": {
            "method": "paired_fixed_nonwrapping_moving_block_bootstrap",
            "seed": SEED,
            "replicates_per_method": REPLICATES,
            "intervals_approximate_not_confirmatory": True,
            "withheld_reasons": issues,
            "primary": _bootstrap(weekly_totals, 2) if can_resample else None,
            "sensitivity": _bootstrap(weekly_totals, 3) if can_resample else None,
        },
        "counts_as_70_percent_evidence": False,
        "model_promoted": False,
    }
