"""Recheck a frozen optional prior-result lead against the verified whole card."""

import argparse
import json
from collections import Counter
from pathlib import Path

from autoresearch import kra_nomination_card_audit as nomination
from autoresearch.kra_entry_scope_intake import now
from autoresearch.nomination_prior_coverage import SCOPE_DAY_WINDOW, race_parts, require
from autoresearch.observed_history_seed import pinned_path
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import horse_id, parse_json

FORMAT = "kra-frozen-prior-query-leads-v1"
CARD_FORMAT = "kra-nomination-whole-card-diagnostic-v1"
BENEFITS = (
    "similar_venue_grade_distance",
    "exact_venue_grade_distance",
    "two_exact_prior_days",
)
RETAINED = "conditional_prior_lead_retained"


def _card_index(card):
    races, declared = {}, 0
    for field in card["races"]:
        key = field["race_id"]
        race_parts(key)
        roster, gates = {}, set()
        for row in field["declarations"]:
            hid = horse_id(row["horse_id"])
            gate = row["gate"]
            require(
                type(gate) is int
                and gate > 0
                and gate not in gates
                and hid not in roster,
                "prior_leads_final_roster_conflict",
            )
            gates.add(gate)
            roster[hid] = row
        require(bool(roster) and key not in races, "prior_leads_final_race_conflict")
        races[key] = field, roster
        declared += len(roster)
    require(
        len(races) == card["race_count"] > 0 and declared == card["declaration_count"],
        "prior_leads_incomplete_whole_card",
    )
    return races


def _validate_claim(unit, claim):
    target_day, target_meet = race_parts(claim["target_race_id"])
    hid = horse_id(claim["horse_id"])
    gains, past = claim["potential_gain"], claim["prior_race_ids"]
    require(
        bool(past)
        and sorted(set(past)) == past
        and bool(gains)
        and [name for name in BENEFITS if name in gains] == gains
        and hid == claim["horse_id"],
        "prior_leads_malformed_claim",
    )
    for key in past:
        old_day, old_meet = race_parts(key)
        require(
            key.rsplit("_", 1)[0] == unit
            and old_meet == target_meet
            and 0 < (target_day - old_day).days <= SCOPE_DAY_WINDOW,
            "prior_leads_wrong_historical_unit",
        )
    return claim["target_race_id"], hid


def _state(races, target, hid):
    if target not in races:
        return "race_not_in_witness_not_cancellation"
    field, roster = races[target]
    if field["state"] != "grade_distance_matched":
        return field["state"]
    if hid not in roster:
        return "not_declared_in_this_witness"
    reason = roster[hid]["state"]
    return RETAINED if reason == "corroborated_id_and_name" else reason


def recheck(leads, card, *, evaluated_at):
    """Compare exact saved candidates, never authorize or execute a request."""
    due = timestamp(card["first_block_cutoff"])
    clock = timestamp(evaluated_at)
    require(
        leads["format"] == FORMAT
        and leads["final_card_or_cutoff_known"] is False
        and leads["authorizes_source_request"] is False
        and card["format"] == CARD_FORMAT
        and card["training_or_prediction_allowed"] is False
        and leads["nomination_packet_sha256"] == card["nomination_packet_sha256"],
        "prior_leads_unbound_original_evidence",
    )
    require(
        timestamp(leads["reference_published_at"]) <= clock < due
        and timestamp(card["nomination_published_at"]) <= clock
        and timestamp(card["whole_card_published_at"])
        <= timestamp(card["audit_completed_at"])
        <= clock,
        "prior_leads_outside_original_window",
    )
    races = _card_index(card)
    output = {}
    units = leads["units"]
    require(bool(units), "prior_leads_no_frozen_units")
    for unit, claims in sorted(units.items()):
        require(bool(claims), "prior_leads_empty_frozen_unit")
        status, before, after, rows, unique = Counter(), Counter(), Counter(), [], set()
        for claim in claims:
            target, hid = _validate_claim(unit, claim)
            require(
                (target, hid) not in unique, "prior_leads_duplicate_nomination_claim"
            )
            unique.add((target, hid))
            why = _state(races, target, hid)
            status[why] += 1
            before.update(claim["potential_gain"])
            if why == RETAINED:
                after.update(claim["potential_gain"])
            rows.append({**claim, "status": why})
        output[unit] = {
            "before_witness": {key: before[key] for key in BENEFITS},
            "retained_for_source_review": {key: after[key] for key in BENEFITS},
            "statuses": dict(status),
            "claims": rows,
        }
    return {
        "format": "kra-prior-query-lead-whole-card-recheck-v1",
        "complete_witness_race_ids": sorted(races),
        "complete_witness_declarations": card["declaration_count"],
        "original_cutoff": card["first_block_cutoff"],
        "schedule_sha256": card["schedule_sha256"],
        "whole_card_sha256": card["whole_card_packet_sha256"],
        "source_units": output,
        "request_or_feature_use_authorized": False,
        "verified_prediction_publication_not_established_here": True,
    }


def audit(root, leads_ref, nomination_path, receipt, **original):
    """Replay the current original whole-card witness without network or writes."""
    root = root.resolve()
    leads = parse_json(pinned_path(root, leads_ref).read_bytes())
    verified = nomination.audit(root, nomination_path, receipt, **original)
    return recheck(leads, verified, evaluated_at=now().isoformat()) | {
        "frozen_scope_sha256": leads_ref["sha256"],
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    for name in (
        "leads",
        "leads-sha256",
        "nomination-packet",
        "receipt",
        "receipt-sha256",
        "schedule-sha256",
        "first-cutoff",
        "packet-sha256",
    ):
        cli.add_argument("--" + name, required=True)
    cli.add_argument("--pull", type=int, required=True)
    args = cli.parse_args(argv)
    print(
        json.dumps(
            audit(
                Path.cwd(),
                {"path": args.leads, "sha256": args.leads_sha256},
                args.nomination_packet,
                {"path": args.receipt, "sha256": args.receipt_sha256},
                schedule_sha256=args.schedule_sha256,
                first_cutoff=args.first_cutoff,
                packet_sha256=args.packet_sha256,
                pull=args.pull,
            ),
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
