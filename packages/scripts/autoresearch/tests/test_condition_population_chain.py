"""Hash-chain consistency is deliberately weaker than population closure."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from autoresearch import condition_population_chain as chain
from autoresearch.restricted_cohort import encoded, sha256

UMBRELLA = "a" * 64
NOW = datetime(2026, 10, 20, 15, tzinfo=UTC)


def event():
    return {
        "format_version": chain.EVENT_VERSION,
        "umbrella_sha256": UMBRELLA,
        "sequence": 1,
        "previous_event_sha256": None,
        "event_type": "week_inventory",
        "week_id": "week-01",
        "slot_id": None,
        "recorded_at": NOW.isoformat(),
        "source_effective_at": None,
        "evidence_refs": ["b" * 64],
        "supersedes_event_sha256": None,
        "payload": {"complete": True},
    }


def journal(events):
    return {
        "format_version": chain.VERSION,
        "umbrella_sha256": UMBRELLA,
        "event_count": len(events),
        "head_sha256": sha256(encoded(events[-1])) if events else None,
        "events": events,
    }


def replay(value):
    return chain.validate(value, UMBRELLA, {"week-01"}, NOW)


def test_chain_does_not_certify_payload_assertions():
    value = journal([event()])
    before = deepcopy(value)
    result = replay(value)
    assert result["full_population_verified"] is False
    assert result["denominator"] is None
    assert value == before
    assert result["events"][0]["event"] == value["events"][0]


def test_empty_ledger_not_zero_races():
    result = replay(journal([]))
    assert result["events"] == []
    assert result["denominator"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("sequence", True),
        ("sequence", 2),
        ("previous_event_sha256", "c" * 64),
        ("umbrella_sha256", "c" * 64),
        ("format_version", "other"),
        ("event_type", "delete_race"),
        ("week_id", "week-02"),
        ("week_id", []),
        ("week_id", None),
        ("recorded_at", "2026-10-21T00:00:00Z"),
        ("recorded_at", "2026-10-20"),
        ("source_effective_at", "invalid"),
        ("slot_id", "unexpected-slot"),
        ("evidence_refs", []),
        ("evidence_refs", ["b" * 64, "b" * 64]),
        ("evidence_refs", ["invalid"]),
        ("supersedes_event_sha256", "c" * 64),
        ("payload", []),
    ],
)
def test_malformed_event_rejected(field, value):
    row = event()
    row[field] = value
    with pytest.raises(ValueError):
        replay(journal([row]))


def test_truncation_against_selected_public_head_rejected():
    first = event()
    second = {
        **first,
        "sequence": 2,
        "previous_event_sha256": sha256(encoded(first)),
    }
    value = journal([first, second])
    value["events"].pop()
    value["event_count"] = 1
    with pytest.raises(ValueError, match="head_mismatch"):
        replay(value)


def test_reordered_event_rejected():
    first = event()
    second = {
        **first,
        "sequence": 2,
        "previous_event_sha256": sha256(encoded(first)),
    }
    with pytest.raises(ValueError, match="schema_or_chain"):
        replay(journal([second, first]))


def test_linked_correction_retains_original_and_never_certifies_closure():
    first = event()
    digest = sha256(encoded(first))
    correction = {
        **first,
        "sequence": 2,
        "previous_event_sha256": digest,
        "event_type": "correction",
        "supersedes_event_sha256": digest,
        "payload": {"complete": False},
    }
    result = replay(journal([first, correction]))
    assert len(result["events"]) == 2
    assert result["superseded_event_hashes"] == [digest]
    assert result["denominator"] is None


def test_correction_fork_rejected():
    first = event()
    digest = sha256(encoded(first))
    correction = {
        **first,
        "sequence": 2,
        "previous_event_sha256": digest,
        "event_type": "correction",
        "supersedes_event_sha256": digest,
    }
    fork = {
        **correction,
        "sequence": 3,
        "previous_event_sha256": sha256(encoded(correction)),
    }
    with pytest.raises(ValueError, match="correction_parent"):
        replay(journal([first, correction, fork]))


def test_unhashable_correction_parent_rejected():
    row = event()
    row.update(event_type="correction", supersedes_event_sha256=[])
    with pytest.raises(ValueError, match="correction_parent"):
        replay(journal([row]))
