"""Reconcile one witnessed workout edition against a witnessed whole race card."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from autoresearch import kra_entry_scope_witness as card_witness
from autoresearch.kra_daily_workout_edition import EDITION_SHA256, verify_source
from autoresearch.kra_entry_scope_intake import _pinned, now
from autoresearch.kra_nomination_card_audit import _final_projections
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import horse_id, parse_json

RACE_VENUE_TO_MENU = {1: 1, 2: 2, 3: 3, 4: 3}
LINKED = "same_id_name_and_clock"


def require_source_before_cutoff(source, cutoff, as_of):
    if not source.observed < source.published <= as_of < cutoff:
        raise ValueError("workout_source_not_witnessed_before_original_cutoff")


def _compare(projected, source):
    meet = projected["meet"]
    race = projected["race_id"]
    event = datetime.strptime(race.split("_", 1)[0], "%Y%m%d").date()
    if event <= source.day:
        raise ValueError("workout_edition_not_earlier_than_event")
    lane = RACE_VENUE_TO_MENU[meet]
    durations, ids, gates = set(), set(), set()
    declarations = []
    for row in sorted(projected["roster"], key=lambda r: int(r["chulNo"])):
        hid, gate = horse_id(row["hrNo"]), int(row["chulNo"])
        if hid in ids or gate in gates or gate < 1:
            raise ValueError("workout_final_roster_identity_conflict")
        ids.add(hid)
        gates.add(gate)
        match = source.identities.get(hid)
        actual_lane, evidence = match if match is not None else (None, None)
        if evidence is None:
            state = "not_in_observed_edition"
        elif actual_lane != lane:
            state = "different_source_menu_held"
        elif evidence.workout.horse_name != row["hrName"]:
            state = "same_id_name_conflict_held"
        elif evidence.usable_minutes is None:
            state = "source_clock_conflict_held"
        else:
            state = LINKED
            durations.add(evidence.usable_minutes)
        declarations.append(
            {
                "gate": gate,
                "horse_id": hid,
                "state": state,
                "observed_menu_lane": actual_lane,
                "source_ordinal": None
                if evidence is None
                else evidence.workout.ordinal,
            }
        )
    if len(declarations) != projected["runner_count"]:
        raise ValueError("workout_final_roster_length_conflict")
    counts = dict(Counter(row["state"] for row in declarations))
    return {
        "race_id": race,
        "physical_meet": meet,
        "expected_source_menu_lane": lane,
        "distance_m": projected["distance_m"]["value"]
        if projected["distance_m"]["status"] == "observed"
        else None,
        "class_text": projected["class_text"]["value"]
        if projected["class_text"]["status"] == "observed"
        else None,
        "days_from_edition_date": (event - source.day).days,
        "declaration_count": len(declarations),
        "declaration_states": counts,
        "entire_field_linked": bool(declarations)
        and counts.get(LINKED, 0) == len(declarations),
        "varying_clock_checked_durations": len(durations) > 1,
        "declarations": declarations,
    }


def _group(fields, key):
    groups = defaultdict(list)
    for field in fields:
        key_value = field[key]
        groups["unknown" if key_value is None else str(key_value)].append(field)
    return {
        group: {
            "races": len(members),
            "declarations": sum(r["declaration_count"] for r in members),
            "linked": sum(r["declaration_states"].get(LINKED, 0) for r in members),
            "complete_coverage_races": sum(r["entire_field_linked"] for r in members),
        }
        for group, members in sorted(groups.items())
    }


def audit(
    root, edition_path, receipt, *, schedule_sha256, first_cutoff, packet_sha256, pull
):
    """Count links without exporting duration values, choosing features or scoring."""
    root = root.resolve()
    started, cutoff = now(), timestamp(first_cutoff)
    if started >= cutoff:
        raise ValueError("workout_audit_original_cutoff_elapsed")
    source = verify_source(root, edition_path)
    require_source_before_cutoff(source, cutoff, started)
    card = card_witness.verify(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        packet_sha256=packet_sha256,
        pull=pull,
    )
    published = timestamp(card["publication"]["merged_at"])
    if not card["before_cutoff"] or not published <= started < cutoff:
        raise ValueError("workout_entry_packet_not_witnessed_before_original_cutoff")
    receipt_path, _ = _pinned(root, receipt)
    _, raw = _pinned(
        root,
        {
            "path": receipt_path.with_name(card_witness.PACKET_NAME),
            "sha256": packet_sha256,
        },
    )
    members = parse_json(raw)["races"]
    expected = {row["race_id"]: row["declarations"] for row in members}
    if (
        len(expected) != len(members)
        or len(expected) != card["race_count"]
        or sum(expected.values()) != card["declaration_count"]
    ):
        raise ValueError("workout_final_population_scope_conflict")
    projections = _final_projections(root, receipt, expected)
    if projections.keys() != expected.keys():
        raise ValueError("workout_final_population_scope_conflict")
    fields = [_compare(projections[rid], source) for rid in sorted(projections)]
    statuses = Counter()
    for field in fields:
        statuses.update(field["declaration_states"])
    if (
        statuses.total() != card["declaration_count"]
        or {field["race_id"]: field["declaration_count"] for field in fields}
        != expected
    ):
        raise ValueError("workout_final_roster_length_conflict")
    completed = now()
    if not started <= completed < cutoff:
        raise ValueError("workout_audit_original_cutoff_elapsed")
    return {
        "format": "kra-witnessed-daily-workout-whole-card-diagnostic-v1",
        "schedule_sha256": schedule_sha256,
        "entry_receipt_sha256": receipt["sha256"],
        "whole_card_packet_sha256": packet_sha256,
        "first_block_cutoff": card["first_block_cutoff"],
        "whole_card_published_at": card["publication"]["merged_at"],
        "daily_edition_sha256": EDITION_SHA256,
        "daily_edition_date_kst": source.day.isoformat(),
        "last_daily_source_observation": source.observed.isoformat(),
        "daily_edition_published_at": source.published.isoformat(),
        "audit_completed_at": completed.isoformat(),
        "race_count": len(fields),
        "declaration_count": statuses.total(),
        "declaration_state_counts": dict(statuses),
        "complete_coverage_races": sum(r["entire_field_linked"] for r in fields),
        "complete_varying_coverage_races": sum(
            r["entire_field_linked"] and r["varying_clock_checked_durations"]
            for r in fields
        ),
        "coverage_by_original_context": {
            key: _group(fields, key)
            for key in ("physical_meet", "class_text", "distance_m")
        },
        "races": fields,
        "training_or_prediction_allowed": False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    modes = cli.add_subparsers(dest="mode", required=True)
    for name in ("source", "card"):
        mode = modes.add_parser(name)
        mode.add_argument("--edition", required=True, type=Path)
        if name == "card":
            mode.add_argument("--receipt", required=True)
            mode.add_argument("--receipt-sha256", required=True)
            mode.add_argument("--schedule-sha256", required=True)
            mode.add_argument("--first-cutoff", required=True)
            mode.add_argument("--packet-sha256", required=True)
            mode.add_argument("--pull", required=True, type=int)
    args = cli.parse_args(argv)
    root = Path.cwd()
    if args.mode == "source":
        source = verify_source(root, args.edition)
        result = {
            "daily_edition_sha256": EDITION_SHA256,
            "date_kst": source.day.isoformat(),
            "last_observation": source.observed.isoformat(),
            "edition_published_at": source.published.isoformat(),
            "unique_horse_ids": len(source.identities),
            "held_clocks": sum(
                r.usable_minutes is None for _, r in source.identities.values()
            ),
            "future_card_verified": False,
            "training_or_prediction_allowed": False,
        }
    else:
        result = audit(
            root,
            args.edition,
            {"path": args.receipt, "sha256": args.receipt_sha256},
            schedule_sha256=args.schedule_sha256,
            first_cutoff=args.first_cutoff,
            packet_sha256=args.packet_sha256,
            pull=args.pull,
        )
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
