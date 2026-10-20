"""Synthetic accounting only; 2099 IDs do not register actual races."""

from copy import deepcopy
from itertools import product

import pytest

from autoresearch.condition_outcome_accounting import (
    ARMS,
    FAILURES,
    OutcomeEvidence,
    PredictionEvidence,
    summarize,
)

RACE = "20990101_1_1"
SECOND = "20990101_2_1"
TARGET = ("001001", "001002", "001003")
OTHER = ("001001", "001002", "001004")
HIT = PredictionEvidence("timely_valid", TARGET)
MISS = PredictionEvidence("timely_valid", OTHER)
PENDING = PredictionEvidence()
OUTCOME = OutcomeEvidence("unique_target", TARGET)
VOID = OutcomeEvidence("undefined_target")


def evaluate(prediction, outcome, *, population=True):
    return summarize(
        [RACE],
        {arm: {RACE: prediction} for arm in ARMS},
        {RACE: outcome},
        full_population_verified=population,
    )


@pytest.mark.parametrize("population", [False, True])
@pytest.mark.parametrize(
    "prediction",
    [HIT, MISS, PENDING] + [PredictionEvidence(state) for state in sorted(FAILURES)],
)
@pytest.mark.parametrize("outcome", [OUTCOME, OutcomeEvidence(), VOID])
def test_state_table(prediction, outcome, population):
    report = evaluate(prediction, outcome, population=population)
    if outcome == VOID:
        expected = "undefined"
    elif outcome != OUTCOME or not population or prediction == PENDING:
        expected = "pending"
    elif prediction == HIT:
        expected = "hit"
    else:
        expected = "miss"
    for arm in ARMS:
        result = report["arms"][arm]
        assert result["counts"][expected] == 1
        assert sum(result["counts"].values()) == 1
        assert result["proven_prediction_failures"] == int(
            prediction.status in FAILURES
        )
        assert result["exact_accuracy"] == (
            float(expected == "hit") if expected in {"hit", "miss"} else None
        )
    assert report["complete_paired_comparison"] == (expected in {"hit", "miss"})
    assert report["paired_cells"]["unresolved"] == int(expected not in {"hit", "miss"})
    assert sum(report["paired_cells"].values()) == 1


def test_unordered_and_no_fallback_or_union():
    assert (
        evaluate(PredictionEvidence("timely_valid", tuple(reversed(TARGET))), OUTCOME)[
            "arms"
        ]["A24"]["counts"]["hit"]
        == 1
    )
    report = summarize(
        [RACE],
        {"A24": {RACE: MISS}, "B34": {RACE: HIT}},
        {RACE: OUTCOME},
        full_population_verified=True,
    )
    assert report["paired_cells"]["b34_only"] == 1
    assert report["b34_minus_a24_pp"] == 100
    assert report["descriptive_winner"] == "B34"


def test_partial_arm_failure_and_unknown_are_different():
    report = summarize(
        [RACE, SECOND],
        {
            "A24": {RACE: PredictionEvidence("proven_late")},
            "B34": {RACE: HIT, SECOND: HIT},
        },
        {RACE: OUTCOME, SECOND: OUTCOME},
        full_population_verified=True,
    )
    assert report["arms"]["A24"]["counts"] == {
        "hit": 0,
        "miss": 1,
        "pending": 1,
        "undefined": 0,
    }
    assert report["arms"]["A24"]["exact_accuracy"] is None
    assert report["arms"]["B34"]["exact_accuracy"] == 1
    assert report["paired_cells"]["b34_only"] == 1
    assert report["paired_cells"]["unresolved"] == 1
    assert report["b34_minus_a24_pp"] is None
    assert report["descriptive_winner"] is None


def test_missing_week_or_late_added_race_cannot_disappear():
    # Enrollment is a caller responsibility. Missing predictions are NOT proof
    # of failure; both known races remain pending until evidence is supplied.
    report = summarize(
        [RACE, SECOND],
        {arm: {} for arm in ARMS},
        {RACE: OUTCOME},
        full_population_verified=True,
    )
    assert report["denominator"] == 2
    assert report["arms"]["A24"]["counts"]["pending"] == 2
    assert report["arms"]["A24"]["exact_accuracy"] is None
    report = summarize(
        [RACE],
        {arm: {RACE: HIT} for arm in ARMS},
        {RACE: OUTCOME},
        full_population_verified=False,
    )
    assert report["denominator"] is None
    assert report["known_ledger_races"] == 1
    assert report["arms"]["A24"]["counts"]["pending"] == 1
    assert report["descriptive_winner"] is None


def test_all_nonempty_small_paired_tables():
    for counts in product(range(3), repeat=4):
        if not sum(counts):
            continue
        pairs = [
            pair
            for count, pair in zip(
                counts,
                [(HIT, HIT), (HIT, MISS), (MISS, HIT), (MISS, MISS)],
                strict=True,
            )
            for _ in range(count)
        ]
        ids = [f"20990101_1_{i + 1}" for i in range(len(pairs))]
        report = summarize(
            ids,
            {
                arm: {rid: pair[index] for rid, pair in zip(ids, pairs, strict=True)}
                for index, arm in enumerate(ARMS)
            },
            dict.fromkeys(ids, OUTCOME),
            full_population_verified=True,
        )
        both, a_only, b_only, neither = counts
        n = sum(counts)
        assert report["paired_cells"] == {
            "both_hit": both,
            "a24_only": a_only,
            "b34_only": b_only,
            "neither_hit": neither,
            "unresolved": 0,
        }
        assert report["arms"]["A24"]["exact_accuracy"] == (both + a_only) / n
        assert report["arms"]["B34"]["exact_accuracy"] == (both + b_only) / n
        assert report["b34_minus_a24_pp"] == 100 * (b_only - a_only) / n
        assert report["descriptive_winner"] == (
            "A24" if a_only > b_only else "B34" if b_only > a_only else "tie"
        )


@pytest.mark.parametrize("population", [True, False])
def test_empty_is_not_zero_percent(population):
    report = summarize(
        [],
        {arm: {} for arm in ARMS},
        {},
        full_population_verified=population,
    )
    assert report["arms"]["A24"]["exact_accuracy"] is None
    assert report["b34_minus_a24_pp"] is None
    assert report["descriptive_winner"] is None


@pytest.mark.parametrize(
    "triple",
    [
        None,
        [],
        TARGET[:2],
        (*TARGET, "4"),
        ("1", "1", "2"),
        ("01", "1", "2"),
        ("0", "1", "2"),
        ("-1", "1", "2"),
        ("1.0", "1", "2"),
        (1, "2", "3"),
        (True, "2", "3"),
        ("1 ", "2", "3"),
        ("\u0661", "2", "3"),
    ],
)
def test_reject_malformed_triples(triple):
    with pytest.raises(ValueError):
        PredictionEvidence("timely_valid", triple)
    with pytest.raises(ValueError):
        OutcomeEvidence("unique_target", triple)


def test_reject_unknown_and_contradictory_states():
    with pytest.raises(ValueError):
        PredictionEvidence("locally_timely_only", TARGET)
    with pytest.raises(ValueError):
        PredictionEvidence("proven_invalid", TARGET)
    with pytest.raises(ValueError):
        OutcomeEvidence("source_missing")
    with pytest.raises(ValueError):
        OutcomeEvidence("undefined_target", TARGET)


@pytest.mark.parametrize(
    "ids",
    [
        [RACE, RACE],
        ["20990230_1_1"],
        ["20990101_01_1"],
        ["20990101_1_21"],
        ["20990101_9_1"],
        [None],
        ["not_a_race"],
    ],
)
def test_reject_invalid_population(ids):
    with pytest.raises(ValueError):
        summarize(ids, {arm: {} for arm in ARMS}, {}, full_population_verified=True)


def test_reject_unbound_or_untyped_evidence():
    for arm in ARMS:
        predictions = {a: {} for a in ARMS}
        predictions[arm][SECOND] = HIT
        with pytest.raises(ValueError, match="outside_population"):
            summarize([RACE], predictions, {}, full_population_verified=True)
    with pytest.raises(ValueError, match="outside_population"):
        summarize(
            [RACE],
            {a: {} for a in ARMS},
            {SECOND: OUTCOME},
            full_population_verified=True,
        )
    with pytest.raises(ValueError, match="both_model_mappings"):
        summarize([RACE], {"A24": {}}, {}, full_population_verified=True)
    with pytest.raises(ValueError, match="normalized_evidence"):
        summarize(
            [RACE],
            {a: {RACE: {"status": "timely_valid"}} for a in ARMS},
            {},
            full_population_verified=True,
        )
    with pytest.raises(ValueError, match="normalized_evidence"):
        summarize(
            [RACE],
            {a: {} for a in ARMS},
            {RACE: {"status": "unique_target"}},
            full_population_verified=True,
        )
    with pytest.raises(ValueError, match="must_be_boolean"):
        summarize([RACE], {a: {} for a in ARMS}, {}, full_population_verified="yes")


def test_correction_does_not_mutate_evidence_or_previous_report():
    ids = [RACE]
    predictions = {arm: {RACE: HIT} for arm in ARMS}
    outcomes = {RACE: OUTCOME}
    originals = deepcopy((ids, predictions, outcomes))
    first = summarize(ids, predictions, outcomes, full_population_verified=True)
    preserved = deepcopy(first)
    corrected = summarize(
        ids,
        predictions,
        {RACE: OutcomeEvidence("unique_target", OTHER)},
        full_population_verified=True,
    )
    assert first == preserved
    assert (ids, predictions, outcomes) == originals
    assert first["arms"]["A24"]["counts"]["hit"] == 1
    assert corrected["arms"]["A24"]["counts"]["miss"] == 1
    assert first["scope"] == "normalized_input_arithmetic_only_not_prospective_evidence"
