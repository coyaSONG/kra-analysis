"""Proposed A24/B34 arithmetic on normalized evidence, NOT an evidence verifier.

Internal preparation only: no CLI or connection to actual forward reports.
An independently reviewed adapter must verify source/hash/clock/roster evidence
and whole-population completeness before using these state labels. A boolean
or a status string supplied here does not establish that verification.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from shared.kra_race_identity import validate_race_identity

ARMS = ("A24", "B34")
FAILURES = frozenset({"proven_absent", "proven_late", "proven_invalid"})
PREDICTION_STATES = FAILURES | {"timely_valid", "pending_evidence"}
OUTCOME_STATES = frozenset({"unique_target", "pending_evidence", "undefined_target"})
SCORES = ("hit", "miss", "pending", "undefined")
CELLS = ("both_hit", "a24_only", "b34_only", "neither_hit")


def _triple(value):
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(
            type(horse) is not str
            or not horse.isascii()
            or not horse.isdecimal()
            or int(horse) <= 0
            for horse in value
        )
        or len({int(horse) for horse in value}) != 3
    ):
        raise ValueError("invalid_three_distinct_horse_ids")


@dataclass(frozen=True)
class PredictionEvidence:
    """Normalized state; never construct 'proven' states from missing files."""

    status: str = "pending_evidence"
    triple: tuple[str, str, str] | None = None

    def __post_init__(self):
        if self.status not in PREDICTION_STATES:
            raise ValueError("unknown_prediction_state")
        if self.status == "timely_valid":
            _triple(self.triple)
        elif self.triple is not None:
            raise ValueError("nonvalid_prediction_cannot_supply_scoring_triple")


@dataclass(frozen=True)
class OutcomeEvidence:
    """A target state normalized only after versioned source reconciliation."""

    status: str = "pending_evidence"
    triple: tuple[str, str, str] | None = None

    def __post_init__(self):
        if self.status not in OUTCOME_STATES:
            raise ValueError("unknown_outcome_state")
        if self.status == "unique_target":
            _triple(self.triple)
        elif self.triple is not None:
            raise ValueError("nonunique_outcome_cannot_supply_target")


def _classify(prediction, outcome, population_verified):
    # Outcome evidence has precedence even for a proven prediction failure.
    if outcome.status == "undefined_target":
        return "undefined"
    if outcome.status != "unique_target" or not population_verified:
        return "pending"
    if prediction.status in FAILURES:
        return "miss"
    if prediction.status == "timely_valid":
        return "hit" if set(prediction.triple) == set(outcome.triple) else "miss"
    return "pending"


def _race_id(value):
    if type(value) is not str:
        raise ValueError("noncanonical_race_id")
    try:
        day, meet, number = value.split("_")
        validate_race_identity(int(meet), day, int(number))
        if value != f"{day}_{int(meet)}_{int(number)}":
            raise ValueError("noncanonical_race_id")
    except (TypeError, ValueError) as exc:
        raise ValueError("noncanonical_race_id") from exc


def summarize(
    race_ids: Sequence[str],
    predictions: Mapping[str, Mapping[str, PredictionEvidence]],
    outcomes: Mapping[str, OutcomeEvidence],
    *,
    full_population_verified: bool,
):
    """Left-join an explicit universe; rates are conditional, not certification.

    `full_population_verified` is an external adapter precondition, not a
    completeness test. Unknown weeks/races must make it false. This function
    cannot discover omitted races or validate evidence authenticity.
    """
    if type(full_population_verified) is not bool:
        raise ValueError("population_verification_must_be_boolean")
    for race_id in race_ids:
        _race_id(race_id)
    universe = set(race_ids)
    if len(universe) != len(race_ids):
        raise ValueError("duplicate_population_race")
    if set(predictions) != set(ARMS):
        raise ValueError("both_model_mappings_required")
    if set(outcomes) - universe or any(
        set(predictions[arm]) - universe for arm in ARMS
    ):
        raise ValueError("evidence_outside_population")
    if any(type(row) is not OutcomeEvidence for row in outcomes.values()) or any(
        type(row) is not PredictionEvidence
        for arm in ARMS
        for row in predictions[arm].values()
    ):
        raise ValueError("normalized_evidence_types_required")
    ledger = []
    for race_id in sorted(universe):
        outcome = outcomes.get(race_id, OutcomeEvidence())
        row = {"race_id": race_id, "outcome_status": outcome.status, "arms": {}}
        for arm in ARMS:
            prediction = predictions[arm].get(race_id, PredictionEvidence())
            row["arms"][arm] = {
                "prediction_status": prediction.status,
                "score": _classify(prediction, outcome, full_population_verified),
                "protocol_failure": prediction.status in FAILURES,
            }
        ledger.append(row)
    n = len(universe) if full_population_verified else None
    arms = {}
    for arm in ARMS:
        counts = Counter(row["arms"][arm]["score"] for row in ledger)
        complete = (
            n is not None and n > 0 and not (counts["pending"] or counts["undefined"])
        )
        arms[arm] = {
            "counts": {score: counts[score] for score in SCORES},
            "exact_accuracy": counts["hit"] / n if complete else None,
            "complete": complete,
            "proven_prediction_failures": sum(
                row["arms"][arm]["protocol_failure"] for row in ledger
            ),
            "timely_valid_predictions": sum(
                row["arms"][arm]["prediction_status"] == "timely_valid"
                for row in ledger
            ),
        }
    cells = Counter()
    for row in ledger:
        a, b = (row["arms"][arm]["score"] for arm in ARMS)
        if a not in {"hit", "miss"} or b not in {"hit", "miss"}:
            cells["unresolved"] += 1
        else:
            cells[
                {
                    (True, True): "both_hit",
                    (True, False): "a24_only",
                    (False, True): "b34_only",
                    (False, False): "neither_hit",
                }[(a == "hit", b == "hit")]
            ] += 1
    complete = all(arms[arm]["complete"] for arm in ARMS)
    delta = (
        100 * (arms["B34"]["counts"]["hit"] - arms["A24"]["counts"]["hit"]) / n
        if complete
        else None
    )
    return {
        "scope": "normalized_input_arithmetic_only_not_prospective_evidence",
        "denominator": n,
        "known_ledger_races": len(ledger),
        "full_population_verified_by_caller": full_population_verified,
        "arms": arms,
        "paired_cells": {cell: cells[cell] for cell in (*CELLS, "unresolved")},
        "complete_paired_comparison": complete,
        "b34_minus_a24_pp": delta,
        "descriptive_winner": ("B34" if delta > 0 else "A24" if delta < 0 else "tie")
        if complete
        else None,
        "ledger": ledger,
    }
