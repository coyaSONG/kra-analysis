import json

import pytest

from services.forward_ledger import b0_payload, identifier

pytestmark = pytest.mark.unit


def payload(entries):
    return b0_payload(
        race_id="20261016_1_1",
        universe_sha256="a" * 64,
        entries=entries,
        source={"manifest_sha256": "b" * 64},
    )


def test_b0_sorts_numeric_gates_and_canonicalizes_stable_ids():
    rows = [{"chulNo": g, "hrNo": f"{g:07d}"} for g in (10, 3, 2, 1)]
    first = payload(rows)
    assert json.loads(first)["selection"] == ["1", "2", "3"]
    assert first == payload(list(reversed(rows)))


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"chulNo": 1, "hrNo": "1"}],
        [
            {"chulNo": 1, "hrNo": "1"},
            {"chulNo": 1, "hrNo": "2"},
            {"chulNo": 3, "hrNo": "3"},
        ],
        [
            {"chulNo": 1, "hrNo": "001"},
            {"chulNo": 2, "hrNo": "1"},
            {"chulNo": 3, "hrNo": "3"},
        ],
        [{"chulNo": True, "hrNo": "1"}],
        [{"chulNo": 1, "hrNo": "0"}],
    ],
)
def test_invalid_or_short_roster_cannot_invent_a_combination(rows):
    with pytest.raises(ValueError):
        payload(rows)


@pytest.mark.parametrize("value", ["public;drop", "a.b", "../escape", "", 'a"b'])
def test_schema_and_local_study_names_are_not_sql_or_path_input(value):
    with pytest.raises(ValueError):
        identifier(value)
