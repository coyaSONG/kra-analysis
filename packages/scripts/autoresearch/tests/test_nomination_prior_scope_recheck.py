from copy import deepcopy

import pytest

from autoresearch.nomination_prior_scope_recheck import (
    BENEFITS,
    FORMAT,
    RETAINED,
    recheck,
)

DAY = "20261129"
OLD = "20261024_1"
CLOCK = "2026-11-26T04:30:00Z"
CUTOFF = "2026-11-29T01:15:00Z"
SHA = "a" * 64


def claim(race, horse, *gains, past=f"{OLD}_5"):
    return {
        "target_race_id": f"{DAY}_1_{race}",
        "horse_id": horse,
        "potential_gain": list(gains),
        "prior_race_ids": [past],
    }


def roster(race, state, *rows):
    return {
        "race_id": f"{DAY}_1_{race}",
        "state": state,
        "declarations": [
            {"gate": i, "horse_id": h, "state": reason}
            for i, (h, reason) in enumerate(rows, 1)
        ],
    }


def case():
    leads = {
        "format": FORMAT,
        "nomination_packet_sha256": SHA,
        "reference_published_at": "2026-11-23T00:00:00Z",
        "final_card_or_cutoff_known": False,
        "authorizes_source_request": False,
        "units": {
            OLD: [
                claim(1, "1", *BENEFITS[:2]),
                claim(1, "2", BENEFITS[1]),
                claim(1, "3", BENEFITS[1]),
                claim(2, "4", BENEFITS[0]),
                claim(3, "5", BENEFITS[0]),
            ]
        },
    }
    card = {
        "format": "kra-nomination-whole-card-diagnostic-v1",
        "nomination_packet_sha256": SHA,
        "training_or_prediction_allowed": False,
        "nomination_published_at": "2026-11-22T18:00:00Z",
        "whole_card_published_at": "2026-11-25T07:00:00Z",
        "audit_completed_at": "2026-11-26T04:00:00Z",
        "first_block_cutoff": CUTOFF,
        "schedule_sha256": "b" * 64,
        "whole_card_packet_sha256": "c" * 64,
        "race_count": 3,
        "declaration_count": 4,
        "races": [
            roster(
                1,
                "grade_distance_matched",
                ("1", "corroborated_id_and_name"),
                ("2", "same_id_name_conflict"),
            ),
            roster(2, "final_condition_conflict", ("4", "final_condition_conflict")),
            roster(
                4,
                "observed_preliminary_without_detail",
                ("3", "no_same_race_profile_id"),
            ),
        ],
    }
    return leads, card


def test_retains_only_confirmed_same_race_and_preserves_whole_card():
    leads, card = case()
    original = deepcopy((leads, card))
    result = recheck(leads, card, evaluated_at=CLOCK)
    assert (leads, card) == original
    assert result["complete_witness_race_ids"] == [f"{DAY}_1_{n}" for n in (1, 2, 4)]
    assert result["complete_witness_declarations"] == 4
    witness = result["source_units"][OLD]
    assert witness["before_witness"][BENEFITS[1]] == 3
    assert witness["retained_for_source_review"][BENEFITS[1]] == 1
    assert witness["statuses"] == {
        RETAINED: 1,
        "same_id_name_conflict": 1,
        "not_declared_in_this_witness": 1,
        "final_condition_conflict": 1,
        "race_not_in_witness_not_cancellation": 1,
    }
    assert result["request_or_feature_use_authorized"] is False


def test_late_or_unbound_sources_fail_closed():
    leads, card = case()
    with pytest.raises(ValueError, match="outside_original_window"):
        recheck(leads, card, evaluated_at=CUTOFF)
    with pytest.raises(ValueError, match="outside_original_window"):
        recheck(leads, card | {"whole_card_published_at": CUTOFF}, evaluated_at=CLOCK)
    with pytest.raises(ValueError, match="unbound_original_evidence"):
        recheck(
            leads | {"nomination_packet_sha256": "0" * 64}, card, evaluated_at=CLOCK
        )
    with pytest.raises(ValueError, match="unbound_original_evidence"):
        recheck(leads | {"authorizes_source_request": True}, card, evaluated_at=CLOCK)


def test_no_truncated_card_or_duplicate_claims():
    leads, card = case()
    with pytest.raises(ValueError, match="incomplete_whole_card"):
        recheck(leads, card | {"races": card["races"][:-1]}, evaluated_at=CLOCK)
    leads["units"][OLD].append(leads["units"][OLD][0])
    with pytest.raises(ValueError, match="duplicate_nomination_claim"):
        recheck(leads, card, evaluated_at=CLOCK)


def test_prior_scope_cannot_be_switched():
    leads, card = case()
    leads["units"][OLD][0] = claim(1, "1", BENEFITS[1], past="20261024_3_5")
    with pytest.raises(ValueError, match="wrong_historical_unit"):
        recheck(leads, card, evaluated_at=CLOCK)
