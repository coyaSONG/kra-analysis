from datetime import date, timedelta
from fractions import Fraction

import numpy as np
import pytest

from autoresearch import condition_weekly_uncertainty as weekly
from autoresearch.condition_outcome_accounting import (
    OutcomeEvidence,
    PredictionEvidence,
)

FIRST = date(2030, 1, 7)
TARGET = ("9", "17", "23")
WRONG = ("2", "7", "11")


@pytest.fixture
def specimen():
    populations, outcomes, totals = {}, {}, []
    predictions = {"A24": {}, "B34": {}}
    for index in range(12):
        monday = (FIRST + timedelta(weeks=index)).strftime("%Y%m%d")
        n = 2 + (index % 4)
        a = (index + 1) % (n + 1)
        b = (index * 2 + 1) % (n + 1)
        ids = tuple(f"{monday}_1_{number}" for number in range(1, n + 1))
        populations[monday] = weekly.WeekPopulation(ids, "verified_racing")
        for number, rid in enumerate(ids):
            outcomes[rid] = OutcomeEvidence("unique_target", TARGET)
            for arm, hits in (("A24", a), ("B34", b)):
                predictions[arm][rid] = PredictionEvidence(
                    "timely_valid", TARGET[::-1] if number < hits else WRONG
                )
        totals.append((n, a, b))
    return populations, predictions, outcomes, totals


def summarize(populations, predictions, outcomes):
    return weekly.summarize_window(
        FIRST.strftime("%Y%m%d"), populations, predictions, outcomes
    )


def independent_interval(totals, length):
    generator = np.random.Generator(np.random.PCG64(20261020))
    starts = generator.integers(12 - length + 1, size=(10_000, 12 // length))
    values = {
        "a24_exact_accuracy": [],
        "b34_exact_accuracy": [],
        "b34_minus_a24_pp": [],
    }
    for sampled in starts:
        races = a_hits = b_hits = 0
        for start in sampled:
            for week in totals[int(start) : int(start) + length]:
                races += week[0]
                a_hits += week[1]
                b_hits += week[2]
        values["a24_exact_accuracy"].append(Fraction(a_hits, races))
        values["b34_exact_accuracy"].append(Fraction(b_hits, races))
        values["b34_minus_a24_pp"].append(Fraction(100 * (b_hits - a_hits), races))

    def percentile(data, p):
        index = p * (len(data) - 1)
        left = int(index)
        return float(data[left] + (index - left) * (data[left + 1] - data[left]))

    intervals = {}
    for metric, data in values.items():
        data.sort()
        intervals[metric] = [
            percentile(data, Fraction(1, 40)),
            percentile(data, Fraction(39, 40)),
        ]
    return intervals


def test_full_fixed_population_uses_pooled_counts_and_both_fixed_intervals(specimen):
    populations, predictions, outcomes, totals = specimen
    report = summarize(populations, predictions, outcomes)
    n, a, b = map(sum, zip(*totals, strict=True))
    assert report["denominator"] == report["known_race_ids_count"] == n
    assert report["verified_race_bearing_weeks"] == 12
    assert sum(report["paired_cells"].values()) == n
    assert report["arms"]["A24"]["exact_accuracy"] == a / n
    assert report["arms"]["B34"]["exact_accuracy"] == b / n
    assert a / n != pytest.approx(sum(a0 / n0 for n0, a0, _ in totals) / 12)
    assert report["b34_minus_a24_pp"] == 100 * (b - a) / n
    for kind, length in (("primary", 2), ("sensitivity", 3)):
        interval = report["uncertainty"][kind]
        assert interval["block_length_weeks"] == length
        for metric, independent in independent_interval(totals, length).items():
            assert interval["intervals"][metric]["interval"] == pytest.approx(
                independent, abs=1e-12
            )
    assert report == summarize(
        dict(reversed(list(populations.items()))), predictions, outcomes
    )
    assert report["counts_as_70_percent_evidence"] is report["model_promoted"] is False


def test_absent_week_stays_pending_without_substitute_accuracy(specimen):
    populations, predictions, outcomes, _ = specimen
    monday = next(iter(populations))
    missing = populations.pop(monday)
    for rid in missing.race_ids:
        outcomes.pop(rid)
        for arm in predictions:
            predictions[arm].pop(rid)
    report = summarize(populations, predictions, outcomes)
    assert len(report["weeks"]) == 12
    assert report["weeks"][0]["monday_kst"] == monday
    assert report["weeks"][0]["population_status"] == "pending_population"
    assert report["denominator"] is report["b34_minus_a24_pp"] is None
    assert report["descriptive_winner"] is report["uncertainty"]["primary"] is None
    assert report["arms"]["A24"]["counts"]["hit"] > 0
    assert report["arms"]["A24"]["exact_accuracy"] is None
    assert "population_unverified" in report["uncertainty"]["withheld_reasons"]


def test_unknown_population_marks_its_known_rows_pending(specimen):
    populations, predictions, outcomes, _ = specimen
    monday = next(iter(populations))
    populations[monday] = weekly.WeekPopulation(populations[monday].race_ids)
    report = summarize(populations, predictions, outcomes)
    assert report["denominator"] is None
    assert report["weeks"][0]["denominator"] is None
    assert report["weeks"][0]["arms_counts"]["B34"]["pending"] == 2
    assert report["paired_cells"]["unresolved"] == 2


def test_verified_no_racing_stays_in_calendar_but_has_no_interval(specimen):
    populations, predictions, outcomes, totals = specimen
    monday = next(iter(populations))
    for rid in populations[monday].race_ids:
        outcomes.pop(rid)
        for arm in predictions:
            predictions[arm].pop(rid)
    populations[monday] = weekly.WeekPopulation((), "verified_no_racing")
    report = summarize(populations, predictions, outcomes)
    assert report["denominator"] == sum(n for n, _, _ in totals[1:])
    assert report["weeks"][0]["denominator"] == 0
    assert report["complete_paired_comparison"]
    assert report["uncertainty"]["withheld_reasons"] == [
        "fewer_than_12_verified_race_bearing_weeks"
    ]
    assert (
        report["uncertainty"]["primary"] is report["uncertainty"]["sensitivity"] is None
    )


def test_unconfirmed_and_void_are_not_failed_predictions(specimen):
    populations, predictions, outcomes, _ = specimen
    a, b = next(iter(populations.values())).race_ids
    predictions["A24"][a] = predictions["A24"][b] = PredictionEvidence("proven_late")
    outcomes.pop(a)
    outcomes[b] = OutcomeEvidence("undefined_target")
    report = summarize(populations, predictions, outcomes)
    assert report["arms"]["A24"]["proven_prediction_failures"] == 2
    assert report["arms"]["A24"]["counts"]["pending"] == 1
    assert report["arms"]["A24"]["counts"]["undefined"] == 1
    assert report["arms"]["A24"]["exact_accuracy"] is None
    assert report["paired_cells"]["unresolved"] == 2
    assert report["b34_minus_a24_pp"] is report["uncertainty"]["primary"] is None


def test_late_with_unique_target_is_a_miss_for_that_arm_only(specimen):
    populations, predictions, outcomes, totals = specimen
    rid = next(iter(populations.values())).race_ids[0]
    predictions["A24"][rid] = PredictionEvidence("proven_late")
    report = summarize(populations, predictions, outcomes)
    n, a, b = map(sum, zip(*totals, strict=True))
    assert report["denominator"] == n
    assert report["arms"]["A24"]["proven_prediction_failures"] == 1
    assert report["arms"]["A24"]["counts"]["hit"] == a - 1
    assert report["arms"]["B34"]["counts"]["hit"] == b
    assert report["complete_paired_comparison"]


def test_no_interval_for_degenerate_paired_difference(specimen):
    populations, predictions, outcomes, _ = specimen
    predictions["B34"] = dict(predictions["A24"])
    report = summarize(populations, predictions, outcomes)
    assert (
        report["complete_paired_comparison"] and report["descriptive_winner"] == "tie"
    )
    for method in ("primary", "sensitivity"):
        intervals = report["uncertainty"][method]["intervals"]
        assert intervals["b34_minus_a24_pp"] == {
            "status": "degenerate_resample_distribution",
            "interval": None,
        }
        assert intervals["a24_exact_accuracy"]["interval"] is not None


def test_reject_adding_or_moving_races_and_fabricating_empty_population(specimen):
    populations, predictions, outcomes, _ = specimen
    monday, second = list(populations)[:2]
    first_scope = populations[monday]
    added = {**populations, "21000101": first_scope}
    with pytest.raises(ValueError, match="weekly_population_outside_frozen_calendar"):
        summarize(added, predictions, outcomes)
    moved = {**populations, monday: populations[second]}
    with pytest.raises(ValueError, match="weekly_race_outside_original_week"):
        summarize(moved, predictions, outcomes)
    with pytest.raises(ValueError, match="weekly_duplicate_original_race"):
        summarize(
            {**populations, monday: weekly.WeekPopulation(first_scope.race_ids * 2)},
            predictions,
            outcomes,
        )
    with pytest.raises(ValueError, match="weekly_population_state_conflict"):
        weekly.WeekPopulation((), "verified_racing")
    with pytest.raises(ValueError, match="evidence_outside_population"):
        summarize(
            populations,
            predictions,
            {**outcomes, f"{monday}_2_1": next(iter(outcomes.values()))},
        )
    with pytest.raises(ValueError, match="weekly_requires_canonical_kst_monday"):
        weekly.summarize_window("20300108", populations, predictions, outcomes)
