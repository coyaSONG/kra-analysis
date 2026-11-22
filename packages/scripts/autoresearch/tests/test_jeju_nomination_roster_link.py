import pytest

from autoresearch.jeju_nomination_roster_link import audit_rosters

CONTEXT = {
    "race_date": "20261128",
    "meet": 2,
    "race_no": 5,
    "grade": "OPEN",
    "distance_m": 1610,
    "weight_type": "handicap",
}


def row(name="A B", **changes):
    return {
        "name": name,
        "sex": "male",
        "age": 5,
        "trainer": "C D",
        "owner": "owner",
        "rating": 0,
    } | changes


def weekly(n, **changes):
    return row(registration_number_not_gate=n, **changes)


def web(n, **changes):
    return row(nomination_position_not_gate=n, profile_id=f"{n:07d}", **changes)


def audit(weekly_rows, web_rows):
    return audit_rosters(CONTEXT | {"rows": weekly_rows}, CONTEXT | {"rows": web_rows})


def test_order_is_not_an_identity_or_feature_link():
    result = audit(
        [weekly(81), weekly(2, name="Other")],
        [web(1, name="AB", trainer="CD"), web(2, name="Other", rating=1)],
    )
    assert result["weekly_rows_by_state"] == {"corroborated_nomination_only": 2}
    a, b = result["groups"]
    assert a["detail_only_profile_ids"] == ["1"]
    assert a["checks"]["rating"] == "match"
    assert a["numeric_positions_equal_diagnostic_only"] is False
    assert b["checks"]["rating"] == "conflict"
    assert b["numeric_positions_equal_diagnostic_only"] is True
    assert result["direct_id_matches_in_both_sources"] == 0
    assert result["establishes_final_declaration_or_gate"] is False
    assert result["allows_training_or_predictions"] is False


def test_keep_ambiguous_disagreeing_and_source_only_rows():
    result = audit(
        [
            weekly(1),
            weekly(2, name="AB", age=8),
            weekly(3, name="B", owner=None, trainer="Different"),
            weekly(4, name="C", trainer=""),
            weekly(5, name="D"),
        ],
        [web(1), web(2, name="B"), web(3, name="C", rating=None), web(6, name="E")],
    )
    assert {k: v for k, v in result["weekly_rows_by_state"].items() if v} == {
        "ambiguous_name": 2,
        "identity_disagreement": 1,
        "identity_fields_missing": 1,
        "weekly_only": 1,
    }
    assert sum(result["web_rows_by_state"].values()) == 4
    assert result["web_rows_by_state"]["web_only"] == 1
    ambiguous, conflict, missing, *_ = result["groups"]
    assert not ambiguous["checks"]
    assert conflict["checks"]["owner"] == "missing"
    assert conflict["checks"]["trainer"] == "conflict"
    assert missing["checks"]["rating"] == "missing"


@pytest.mark.parametrize(
    "change", [{"race_no": 4}, {"distance_m": 1600}, {"grade": "3"}]
)
def test_scope_is_checked_before_comparing_names(change):
    with pytest.raises(ValueError, match="nomination_race_context_mismatch"):
        audit_rosters(
            CONTEXT | {"rows": [weekly(1)]},
            CONTEXT | change | {"rows": [web(1)]},
        )


@pytest.mark.parametrize(
    ("left", "right", "reason"),
    [
        ([], [web(1)], "empty_nomination_source_unconfirmed"),
        ([weekly(1), weekly(1, name="Other")], [web(1)], "duplicate_or_unidentified"),
        (
            [weekly(1)],
            [web(4), web(5) | {"profile_id": "4"}],
            "duplicate_or_unidentified",
        ),
        ([weekly(1, rating=True)], [web(1)], "invalid_nomination_number"),
    ],
)
def test_no_ambiguous_source_row_is_silently_dropped(left, right, reason):
    with pytest.raises(ValueError, match=reason):
        audit(left, right)
