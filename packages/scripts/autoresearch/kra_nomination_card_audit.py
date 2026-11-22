"""Read-only coverage audit of the PR #164 nomination packet on a whole card."""

import argparse
import json
from collections import Counter
from pathlib import Path

from shared.kra_race_card_pdf import normalize_horse_name

from autoresearch import condition_forward_publication as publication
from autoresearch import kra_entry_scope_witness as card_witness
from autoresearch.kra_entry_scope_intake import _pinned, now
from autoresearch.kra_race_card_pdf_replay import replay_entry_pages
from autoresearch.prerace_conditions import (
    class_value,
    distance_value,
    project_conditions,
)
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import horse_id, parse_json

NOMINATION_PULL = 164
NOMINATION_DOCUMENT = "docs/research/2026-11-23-preliminary-nomination-witness.md"
NOMINATION_DOCUMENT_SHA = (
    "ef8b72caadb714ed53b13975ba2239073b53b14bccd10afd1e9f9061be73d967"
)
NOMINATION_PACKET_SHA = (
    "9e314fba0cfc59d945f0d6c1b0712b879d33976250a932e2e5094e3daa304e38"
)
NOMINATION_FORMAT = "kra-preliminary-nomination-input-packet-v1"
RANK_FIELDS = (
    "latest_start_date_as_printed",
    "recent_3_rank_literal",
    "recent_5_rank_literal",
    "recent_7_rank_literal",
)
PRIZE_FIELDS = ("recent_3_appearance_prize_won", "recent_6_appearance_prize_won")
FIELDS = ("rating_as_printed", *RANK_FIELDS, *PRIZE_FIELDS)


def verify_nomination(root, path):
    packet_ref = {"path": path, "sha256": NOMINATION_PACKET_SHA}
    packet_path, raw = _pinned(root, packet_ref)
    packet = parse_json(raw)
    if (
        packet["format"] != NOMINATION_FORMAT
        or packet["final_population_and_cutoff"] is not None
        or packet["eligible_training_or_prediction"] is not False
    ):
        raise ValueError("nomination_unexpected_source_packet")
    directory = packet_path.with_name("public-note-witness")
    if directory.is_symlink() or any(
        (directory / name).is_symlink() for name in publication.ARCHIVE_FILES
    ):
        raise ValueError("nomination_publication_path_conflict")
    document, witness = publication.replay(
        directory, NOMINATION_PULL, NOMINATION_DOCUMENT, NOMINATION_DOCUMENT_SHA
    )
    line = f"Nomination input packet SHA256: `{NOMINATION_PACKET_SHA}`."
    if document.decode("utf-8").splitlines().count(line) != 1:
        raise ValueError("nomination_publication_does_not_bind_packet")
    sources = [field["source"] for field in packet["detail_fields"].values()] + packet[
        "separate_weekly_reports"
    ]
    merged_at = timestamp(witness["merged_at"])
    for source in sources:
        if (
            source["http_status"] != 200
            or timestamp(source["observed_at"]) >= merged_at
        ):
            raise ValueError("nomination_source_not_observed_before_witness")
        for kind in ("request", "receipt", "own_parent", "raw"):
            _, pinned = _pinned(root, source[kind])
            if kind == "raw" and len(pinned) != source["byte_count"]:
                raise ValueError("nomination_source_byte_count_conflict")
    return packet, merged_at


def _source_index(field, meet):
    layout, unprinted = (
        ("jeju_printed_rank_summaries", PRIZE_FIELDS)
        if meet == 2
        else ("appearance_prizes", RANK_FIELDS)
    )
    not_printed = set(field["not_printed"])
    if (
        field["physical_meet"] != meet
        or field["feature_layout"] != layout
        or not_printed != set(unprinted)
    ):
        raise ValueError("nomination_race_layout_conflict")
    by_id = {}
    for row in field["rows"]:
        hid = horse_id(row["profile_id_as_printed"])
        if (
            hid != row["horse_id"]
            or hid in by_id
            or not normalize_horse_name(row["printed_name"])
            or {k for k in FIELDS if k not in row} != not_printed
        ):
            raise ValueError("nomination_source_row_conflict")
        by_id[hid] = row
    if not by_id or len(by_id) != field["detail_count"]:
        raise ValueError("nomination_source_count_conflict")
    return by_id, not_printed


def _condition_states(projected, field):
    grade, distance, *_ = field["printed_conditions"][0].split(maxsplit=2)
    if not distance.endswith("M"):
        raise ValueError("nomination_unrecognized_distance_literal")
    expected = {
        "class_text": class_value(grade),
        "distance_m": distance_value(distance[:-1]),
    }
    if None in expected.values():
        raise ValueError("nomination_unrecognized_conditions")
    return {
        k: (
            "unknown"
            if projected[k]["status"] != "observed"
            else "matched"
            if projected[k]["value"] == value
            else "conflict"
        )
        for k, value in expected.items()
    }


def _field_states(row, not_printed):
    return {
        key: (
            "not_printed"
            if key in not_printed
            else "missing"
            if row[key] is None
            else "observed_zero"
            if type(row[key]) is int and row[key] == 0
            else "observed"
        )
        for key in FIELDS
    }


def _compare(projected, field, observed):
    declarations = projected["roster"]
    final_ids = {horse_id(row["hrNo"]) for row in declarations}
    if len(final_ids) != len(declarations):
        raise ValueError("nomination_final_canonical_id_collision")
    source_only, conditions, linked, not_printed = [], None, {}, set()
    if field is None:
        state = (
            "observed_preliminary_without_detail"
            if observed
            else "no_preliminary_observation"
        )
    else:
        linked, not_printed = _source_index(field, projected["meet"])
        source_only = sorted(linked.keys() - final_ids, key=int)
        conditions = _condition_states(projected, field)
        if timestamp(field["source"]["observed_at"]) >= timestamp(
            projected["captured_at"]
        ):
            state = "nomination_not_earlier_than_final_observation"
        elif field["join_status"] != "profile_id_only_not_final_declared" or field[
            "earlier_list_count"
        ] != len(linked):
            state = "hold_nomination_detail"
        elif "conflict" in conditions.values():
            state = "final_condition_conflict"
        elif "unknown" in conditions.values():
            state = "final_condition_unknown"
        else:
            state = "grade_distance_matched"
    source_names = {
        normalize_horse_name(row["printed_name"]) for row in linked.values()
    }
    rows = []
    for declaration in declarations:
        hid = horse_id(declaration["hrNo"])
        prior = linked.get(hid)
        reason = state
        if state == "grade_distance_matched":
            name = normalize_horse_name(declaration["hrName"])
            if prior is None:
                reason = (
                    "same_name_different_id"
                    if name in source_names
                    else "no_same_race_profile_id"
                )
            elif normalize_horse_name(prior["printed_name"]) != name:
                reason = "same_id_name_conflict"
            else:
                reason = "corroborated_id_and_name"
        values = (
            _field_states(prior, not_printed)
            if reason == "corroborated_id_and_name"
            else dict.fromkeys(FIELDS, "no_verified_join")
        )
        rows.append(
            {
                "gate": declaration["chulNo"],
                "horse_id": hid,
                "state": reason,
                "operand_states": values,
            }
        )
    return {
        "race_id": projected["race_id"],
        "state": state,
        "api26_condition_comparison": conditions,
        "final_weight_rule_checked": False,
        "nomination_only_profile_ids": source_only,
        "declarations": rows,
    }


def _final_projections(root, receipt, expected):
    _, raw = _pinned(root, receipt)
    races = {}
    for scope in parse_json(raw)["scopes"]:
        meet, day = scope["meet"], scope["race_date"]
        ref, _ = _pinned(root, scope["evidence"]["manifest"])
        rows, manifest, _ = replay_entry_pages(
            ref,
            archive_root=root,
            meet=meet,
            race_date=day,
            expected_sha256=scope["evidence"]["manifest"]["sha256"],
        )
        for race in scope["races"]:
            field = project_conditions(
                rows,
                meet=meet,
                race_date=day,
                race_no=race["race_no"],
                collected_at=timestamp(manifest["collected_at"]),
            )
            rid = field["race_id"]
            if rid in races or field["runner_count"] != expected.get(rid):
                raise ValueError("nomination_full_card_roster_conflict")
            races[rid] = field
    if races.keys() != expected.keys():
        raise ValueError("nomination_full_card_population_conflict")
    return races


def audit(
    root,
    nomination_path,
    receipt,
    *,
    schedule_sha256,
    first_cutoff,
    packet_sha256,
    pull,
):
    """Keep every declared row; return status only, never an input feature."""
    root = root.resolve()
    due = timestamp(first_cutoff)
    started = now()
    if started >= due:
        raise ValueError("nomination_audit_original_cutoff_elapsed")
    nomination, merged_at = verify_nomination(root, nomination_path)
    if not merged_at <= started < due:
        raise ValueError("nomination_packet_not_witnessed_in_time")
    card = card_witness.verify(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        packet_sha256=packet_sha256,
        pull=pull,
    )
    if (
        not card["before_cutoff"]
        or timestamp(card["publication"]["merged_at"]) > started
    ):
        raise ValueError("nomination_final_card_not_witnessed_in_time")
    receipt_path, _ = _pinned(root, receipt)
    _, raw = _pinned(
        root,
        {
            "path": receipt_path.with_name(card_witness.PACKET_NAME),
            "sha256": packet_sha256,
        },
    )
    race_rows = parse_json(raw)["races"]
    expected = {row["race_id"]: row["declarations"] for row in race_rows}
    if len(expected) != len(race_rows) or len(expected) != card["race_count"]:
        raise ValueError("nomination_full_card_population_conflict")
    if sum(expected.values()) != card["declaration_count"]:
        raise ValueError("nomination_full_card_roster_conflict")

    observed = set(nomination["observed_fields"])
    detailed = nomination["detail_fields"]
    if (
        len(observed) != len(nomination["observed_fields"])
        or not detailed.keys() <= observed
        or set(nomination["without_detail"]) != observed - detailed.keys()
    ):
        raise ValueError("nomination_source_scope_conflict")
    if not any(rid.split("_")[0] in card["race_dates"] for rid in observed):
        raise ValueError("nomination_card_outside_observed_dates")
    final = _final_projections(root, receipt, expected)
    races = [
        _compare(final[rid], detailed.get(rid), rid in observed)
        for rid in sorted(final)
    ]
    rows = [row for race in races for row in race["declarations"]]
    completed = now()
    if not started <= completed < due:
        raise ValueError("nomination_audit_original_cutoff_elapsed")
    return {
        "format": "kra-nomination-whole-card-diagnostic-v1",
        "schedule_sha256": schedule_sha256,
        "entry_receipt_sha256": receipt["sha256"],
        "first_block_cutoff": card["first_block_cutoff"],
        "whole_card_packet_sha256": packet_sha256,
        "whole_card_published_at": card["publication"]["merged_at"],
        "nomination_packet_sha256": NOMINATION_PACKET_SHA,
        "nomination_published_at": merged_at.isoformat(),
        "audit_completed_at": completed.isoformat(),
        "race_count": len(races),
        "declaration_count": len(rows),
        "race_state_counts": dict(Counter(race["state"] for race in races)),
        "declaration_state_counts": dict(Counter(row["state"] for row in rows)),
        "operand_state_counts": {
            k: dict(Counter(row["operand_states"][k] for row in rows)) for k in FIELDS
        },
        "preliminary_keys_not_in_verified_card": sorted(observed - expected.keys()),
        "races": races,
        "training_or_prediction_allowed": False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--nomination-packet", required=True)
    cli.add_argument("--receipt", required=True)
    cli.add_argument("--receipt-sha256", required=True)
    cli.add_argument("--schedule-sha256", required=True)
    cli.add_argument("--first-cutoff", required=True)
    cli.add_argument("--packet-sha256", required=True)
    cli.add_argument("--pull", type=int, required=True)
    args = cli.parse_args(argv)
    print(
        json.dumps(
            audit(
                Path.cwd(),
                args.nomination_packet,
                {"path": args.receipt, "sha256": args.receipt_sha256},
                schedule_sha256=args.schedule_sha256,
                first_cutoff=args.first_cutoff,
                packet_sha256=args.packet_sha256,
                pull=args.pull,
            ),
            indent=2,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
