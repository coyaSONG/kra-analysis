"""Structural preservation only; a valid event chain does not prove coverage."""

from __future__ import annotations

import re

from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, sha256

VERSION = "condition-population-journal-v1"
EVENT_VERSION = "condition-population-event-v1"
TYPES = {
    "week_inventory",
    "race_enrolled",
    "execution_binding",
    "race_change",
    "identity_link",
    "week_closure",
    "correction",
}
KEYS = {
    "format_version",
    "umbrella_sha256",
    "sequence",
    "previous_event_sha256",
    "event_type",
    "week_id",
    "slot_id",
    "recorded_at",
    "source_effective_at",
    "evidence_refs",
    "supersedes_event_sha256",
    "payload",
}


def identifier(value):
    if type(value) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", value):
        raise ValueError("population_invalid_identifier")
    return value


def validate(journal, umbrella_sha, weeks, published_at):
    """Return immutable events, never a shortened active-event replacement."""
    checked_digest(umbrella_sha)
    if (
        type(journal) is not dict
        or set(journal)
        != {"format_version", "umbrella_sha256", "event_count", "head_sha256", "events"}
        or journal["format_version"] != VERSION
        or journal["umbrella_sha256"] != umbrella_sha
        or type(journal["events"]) is not list
        or type(journal["event_count"]) is not int
        or journal["event_count"] != len(journal["events"])
    ):
        raise ValueError("population_journal_schema")
    prior_hash, prior_time, seen, superseded, output = None, None, {}, set(), []
    for number, event in enumerate(journal["events"], 1):
        if (
            type(event) is not dict
            or set(event) != KEYS
            or event["format_version"] != EVENT_VERSION
            or event["umbrella_sha256"] != umbrella_sha
            or type(event["sequence"]) is not int
            or event["sequence"] != number
            or event["previous_event_sha256"] != prior_hash
            or type(event["event_type"]) is not str
            or event["event_type"] not in TYPES
            or type(event["week_id"]) is not str
            or event["week_id"] not in weeks
            or type(event["payload"]) is not dict
        ):
            raise ValueError("population_event_schema_or_chain")
        recorded = timestamp(event["recorded_at"])
        if recorded > published_at or prior_time is not None and recorded < prior_time:
            raise ValueError("population_event_recording_clock")
        if event["source_effective_at"] is not None:
            timestamp(event["source_effective_at"])
        if event["slot_id"] is not None:
            identifier(event["slot_id"])
        if (
            event["event_type"]
            in {"race_enrolled", "execution_binding", "race_change", "identity_link"}
            and event["slot_id"] is None
        ):
            raise ValueError("population_race_event_without_slot")
        if event["event_type"] in {"week_inventory", "week_closure"} and (
            event["slot_id"] is not None
        ):
            raise ValueError("population_week_event_has_slot")
        refs = event["evidence_refs"]
        if (
            type(refs) is not list
            or not refs
            or any(type(ref) is not str for ref in refs)
            or refs != sorted(set(refs))
        ):
            raise ValueError("population_event_evidence_refs")
        for ref in refs:
            checked_digest(ref)
        target = event["supersedes_event_sha256"]
        if event["event_type"] == "correction":
            if type(target) is not str or target not in seen or target in superseded:
                raise ValueError("population_invalid_correction_parent")
            original = seen[target]
            if (original["week_id"], original["slot_id"]) != (
                event["week_id"],
                event["slot_id"],
            ):
                raise ValueError("population_correction_scope_mismatch")
            superseded.add(target)
        elif target is not None:
            raise ValueError("population_noncorrection_supersedes")
        event_hash = sha256(encoded(event))
        seen[event_hash] = event
        output.append({"event_sha256": event_hash, "event": event})
        prior_hash, prior_time = event_hash, recorded
    if journal["head_sha256"] != prior_hash:
        raise ValueError("population_ledger_head_mismatch")
    return {
        "scope": "event_chain_integrity_only",
        "events": output,
        "head_sha256": prior_hash,
        "superseded_event_hashes": sorted(superseded),
        "full_population_verified": False,
        "denominator": None,
    }
