"""Bind a fold to the results in one predeclared observation slot per week."""

import argparse
import json
from pathlib import Path

import kra_result_observation_inventory as custody
import kra_walk_forward_enrollment as enrollment
import kra_walk_forward_fold as fold
from autoresearch import condition_forward_publication as publication
from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    checked_digest,
    read_bytes,
)
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

PLAN = "kra-walk-forward-result-slot-plan-v1"
TERMINAL = "kra-walk-forward-result-slot-terminal-v1"
SLOT_KEYS = {"week", "opens_at", "closes_at", "receipt_pull", "api_request_budget"}


def rule_document(digest):
    return f"docs/research/result-slot-plans/{checked_digest(digest)}.json"


def rule_marker(digest):
    return encoded({"format": PLAN, "policy_sha256": checked_digest(digest)})


def slot_document(digest, week):
    enrollment._monday(week)
    return f"docs/research/result-slot-witnesses/{checked_digest(digest)}/{week}.json"


def terminal_marker(digest, week, terminal_sha256):
    enrollment._monday(week)
    return encoded(
        {
            "format": TERMINAL,
            "policy_sha256": checked_digest(digest),
            "week": week,
            "terminal_sha256": checked_digest(terminal_sha256),
        }
    )


def _published(root, directory, pull, document, expected, checked_at):
    for path in [directory, *(directory / f for f in publication.ARCHIVE_FILES)]:
        custody._path(root, path)
    content, proof = publication.replay(directory, pull, document, sha256(expected))
    fold.require(
        content == expected and timestamp(proof["retrieved_at"]) <= checked_at,
        "result_slot_publication_conflict",
    )
    return proof


def _rules(
    root, path, digest, rules, enrollment_sha, enrollment_report, pull, checked_at
):
    fold.require(
        set(rules) == {"format", "enrollment_sha256", "slots"}
        and rules["format"] == PLAN
        and rules["enrollment_sha256"] == enrollment_sha
        and type(rules["slots"]) is list
        and all(
            type(slot) is dict and set(slot) == SLOT_KEYS for slot in rules["slots"]
        )
        and [slot["week"] for slot in rules["slots"]]
        == enrollment_report["training_weeks"],
        "result_slot_not_original_enrollment",
    )
    numbers = [slot["receipt_pull"] for slot in rules["slots"]]
    fold.require(
        type(pull) is int
        and pull > 0
        and all(type(p) is int and p > 0 and p != pull for p in numbers)
        and len(set(numbers)) == len(numbers)
        and all(
            type(s["api_request_budget"]) is int
            and 1 <= s["api_request_budget"] <= 2000
            for s in rules["slots"]
        ),
        "result_slot_ambiguous_publication_slots",
    )
    proof = _published(
        root,
        path.with_name(f"result-slot-rules-publication-{digest}"),
        pull,
        rule_document(digest),
        rule_marker(digest),
        checked_at,
    )
    fold.require(
        timestamp(proof["merged_at"])
        < timestamp(enrollment_report["first_enrolled_cutoff"]),
        "result_slot_rules_not_published_before_original_cutoff",
    )
    return proof


def _run_holds(root, seed_root, view, request_budget):
    policy, digest = custody.history.load_plan(seed_root, require_current=False)
    fold.require(
        digest == view["api_plan_sha256"]
        and policy["request_budget"] == request_budget,
        "result_slot_original_request_budget_changed",
    )
    holds = []
    if len(list((seed_root / "requests").glob("*.json"))) != len(
        view["local_api_requests"]
    ):
        holds.append("designated_run_request_journal_changed")
    for item in view["api_units"]:
        unit = {k: item[k] for k in ("day", "meet")}
        attempts = custody.history.receipts(seed_root, unit)
        refs = {c["source"]: c["manifest"] for c in item["captures"]}
        if len(attempts) != (1 if refs else 0):
            holds.append("designated_run_attempt_count_conflict")
        elif attempts:
            path = custody._path(root, attempts[0])
            receipt = parse_json(read_bytes(path, limit=MAX_MANIFEST_BYTES))
            if receipt != {
                "plan_sha256": digest,
                "unit": unit,
                "result": refs.get("API214"),
                "entry": refs.get("API26"),
            }:
                holds.append("designated_run_attempt_pin_conflict")
    return sorted(set(holds))


def _required_source_holds(view, races):
    expected_units = {
        (day, int(meet)) for day, meet, _ in (rid.split("_") for rid in races)
    }
    observed_units = {
        (r["day"], r["meet"])
        for r in view["api_units"]
        if r["status"] == "api_reported_rows"
    }
    holds = []
    if not expected_units <= observed_units:
        holds.append("designated_api_scope_not_observed")
    if any(
        r["kind"] == "detail" and r["status"] != "captured"
        for r in view["official_captures"]
    ):
        holds.append("designated_official_detail_not_captured")
    return holds


def _terminal(root, directory, digest, slot, scope, eval_cutoff, checked_at):
    name = slot["week"]
    opening, closing = timestamp(slot["opens_at"]), timestamp(slot["closes_at"])
    fold.require(
        timestamp(scope["last_scheduled_start_at"]) < opening < closing < eval_cutoff,
        "result_slot_window_not_between_cards",
    )
    folder = custody._path(root, name, parent=directory)
    record_path = custody._path(root, "terminal.json", parent=folder)
    raw = read_bytes(record_path, limit=MAX_MANIFEST_BYTES)
    record = parse_json(raw)
    fold.require(
        set(record)
        == {
            "format",
            "policy_sha256",
            "week",
            "schedule_sha256",
            "population_sha256",
            "closed_at",
            "state",
            "result_plan_sha256",
            "inventory_sha256",
        }
        and record["format"] == TERMINAL
        and record["policy_sha256"] == digest
        and record["week"] == name
        and record["schedule_sha256"] == scope["input"]["schedule_sha256"]
        and record["population_sha256"] == scope["population_sha256"]
        and record["state"] in ("observed", "failed", "not_run"),
        "result_slot_terminal_scope_or_state_conflict",
    )
    record_hash = sha256(raw)
    witness = _published(
        root,
        folder / "terminal-publication",
        slot["receipt_pull"],
        slot_document(digest, name),
        terminal_marker(digest, name, record_hash),
        checked_at,
    )
    closed_at = timestamp(record["closed_at"])
    fold.require(
        closing <= closed_at <= timestamp(witness["merged_at"]) < eval_cutoff,
        "result_slot_terminal_not_timely_between_boundaries",
    )
    checked = {
        "week": name,
        "terminal_sha256": record_hash,
        "publication": witness,
        "recorded_state": record["state"],
    }
    if record["state"] != "observed":
        fold.require(
            record["result_plan_sha256"] is None and record["inventory_sha256"] is None,
            "result_slot_failed_record_offers_a_replacement",
        )
        return checked | {
            "holds": [f"designated_slot_{record['state']}"],
            "result_plan": None,
        }

    plan_path = custody._path(root, "outcome-plan.json", parent=folder)
    ref = {
        "path": plan_path.relative_to(root).as_posix(),
        "sha256": checked_digest(record["result_plan_sha256"]),
    }
    plan = parse_json(fold._read_pin(plan_path, ref["sha256"]))
    seed_root = custody._path(root, "history", parent=folder)
    fold.require(
        custody._path(root, plan["seed_root"]) == seed_root
        and custody._path(root, plan["seed_path"]) == seed_root / "selected-seed.json"
        and custody._path(root, plan["official_directory"]) == folder / "official",
        "result_slot_archive_not_from_designated_run",
    )
    view = custody.inventory(
        root,
        ref,
        race_dates=scope["race_dates"],
        race_ids=scope["race_ids"],
        schedule_sha256=scope["input"]["schedule_sha256"],
    )
    fold.require(
        sha256(encoded(view)) == checked_digest(record["inventory_sha256"])
        and timestamp(view["api_seed_materialized_at"]) <= closed_at,
        "result_slot_bound_inventory_changed_or_late",
    )
    holds = [
        *custody.window_holds(
            view, opens_at=slot["opens_at"], closes_at=slot["closes_at"]
        ),
        *_required_source_holds(view, scope["race_ids"]),
        *_run_holds(root, seed_root, view, slot["api_request_budget"]),
    ]
    return checked | {"holds": holds, "result_plan": None if holds else ref}


def verify(root, rules_ref, enrollment_ref, fold_ref, *, rules_pull, enrollment_pull):
    """Resolve designated plans, or withhold all; never admit result labels."""
    root = root.resolve()
    checked_at = fold.now()
    rule_path, raw = fold._pinned(root, rules_ref)
    digest = rules_ref["sha256"]
    rules = parse_json(raw)
    enrolled = enrollment.verify(root, enrollment_ref, fold_ref, pull=enrollment_pull)
    proof = _rules(
        root,
        rule_path,
        digest,
        rules,
        enrollment_ref["sha256"],
        enrolled,
        rules_pull,
        checked_at,
    )
    plan, _ = fold._load_plan(root, fold_ref)
    cutoff = timestamp(plan["evaluation"]["first_cutoff"])
    parent = rule_path.with_name(f"result-observation-slots-{digest}")
    states = []
    for slot, chosen in zip(rules["slots"], plan["training"], strict=True):
        scope = fold._scope(root, chosen["input"], checked_at)
        status = _terminal(root, parent, digest, slot, scope, cutoff, checked_at)
        fold.require(
            status["result_plan"] is None
            or status["result_plan"] == chosen["result_plan"],
            "result_slot_fold_requests_another_version",
        )
        states.append(status)
    ready = not any(row["holds"] for row in states)
    return {
        "state": "documented_slot_versions_bound" if ready else "result_slots_held",
        "fold_plan_sha256": fold_ref["sha256"],
        "rule_sha256": digest,
        "rule_publication": proof,
        "slots": [
            {k: v for k, v in state.items() if k != "result_plan"} for state in states
        ],
        "selected_result_plans": [row["result_plan"] for row in states]
        if ready
        else None,
        "independent_collection_clock_verified": False,
        "result_targets_admitted": False,
        "current_official_corrections_reviewed": False,
        **fold.NO_AUTHORITY,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("rules", "enrollment", "fold-plan"):
        parser.add_argument(f"--{name}", required=True)
        parser.add_argument(f"--{name}-sha256", required=True)
    parser.add_argument("--rules-pull", type=int, required=True)
    parser.add_argument("--enrollment-pull", type=int, required=True)
    args = parser.parse_args(argv)
    report = verify(
        Path.cwd(),
        {"path": args.rules, "sha256": args.rules_sha256},
        {"path": args.enrollment, "sha256": args.enrollment_sha256},
        {"path": args.fold_plan, "sha256": args.fold_plan_sha256},
        rules_pull=args.rules_pull,
        enrollment_pull=args.enrollment_pull,
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["selected_result_plans"] is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
