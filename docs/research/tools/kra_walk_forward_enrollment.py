"""Replay advance enrollment of the Korean weeks used in a whole-card fold."""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import kra_walk_forward_fold as fold
from autoresearch import condition_forward_publication as publication
from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

POLICY = "kra-walk-forward-enrollment-v1"
MARKER = "kra-walk-forward-enrollment-witness-v1"
ARCHIVE_NAME = "walk-forward-enrollment-publication"


def _monday(value):
    fold.require(type(value) is str, "enrollment_invalid_week")
    try:
        day = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("enrollment_invalid_week") from exc
    fold.require(
        day.isoformat() == value and day.weekday() == 0, "enrollment_invalid_week"
    )
    return day


def _load_policy(root, ref):
    path, raw = fold._pinned(root, ref)
    policy = parse_json(raw)
    fold.require(
        set(policy) == {"format", "training_weeks", "evaluation_week"}
        and policy["format"] == POLICY
        and type(policy["training_weeks"]) is list
        and policy["training_weeks"],
        "enrollment_invalid_policy",
    )
    weeks = [_monday(w) for w in [*policy["training_weeks"], policy["evaluation_week"]]]
    fold.require(
        all(a < b for a, b in zip(weeks[:-1], weeks[1:], strict=True)),
        "enrollment_week_order_conflict",
    )
    return path, policy


def publication_document(digest):
    return (
        f"docs/research/walk-forward-enrollment-witnesses/{checked_digest(digest)}.json"
    )


def marker(digest):
    return encoded({"format": MARKER, "policy_sha256": checked_digest(digest)})


def _witness(root, policy_path, digest, pull, *, capture=False):
    fold.require(type(pull) is int and pull > 0, "enrollment_invalid_pull")
    directory = policy_path.with_name(f"{ARCHIVE_NAME}-{checked_digest(digest)}")
    for path in [directory, *(directory / f for f in publication.ARCHIVE_FILES)]:
        fold.private_path(root, path.relative_to(root).as_posix())
    expected = marker(digest)
    read = publication.capture if capture else publication.replay
    raw, proof = read(directory, pull, publication_document(digest), sha256(expected))
    fold.require(raw == expected, "enrollment_marker_conflict")
    return proof


def _week_for(race_dates):
    # The witnessed schedule already supplies dates in Korea Standard Time.
    days = [date.fromisoformat(day) for day in race_dates]
    mondays = {day - timedelta(days=day.weekday()) for day in days}
    fold.require(len(mondays) == 1, "enrollment_scope_not_one_week")
    return mondays.pop().isoformat()


def verify(root, policy_ref, plan_ref, *, pull):
    """Bind the exact plan's input roles, without reading any result pins."""
    root = root.resolve()
    checked_at = fold.now()
    policy_path, policy = _load_policy(root, policy_ref)
    plan, _ = fold._load_plan(root, plan_ref)
    specifications = [*(item["input"] for item in plan["training"]), plan["evaluation"]]
    weeks = [*policy["training_weeks"], policy["evaluation_week"]]
    fold.require(
        len(specifications) == len(weeks), "enrollment_plan_card_count_conflict"
    )

    proof = _witness(root, policy_path, policy_ref["sha256"], pull)
    fold.require(
        timestamp(proof["retrieved_at"]) <= checked_at, "enrollment_proof_in_future"
    )
    merged = timestamp(proof["merged_at"])
    cutoffs = []
    for spec, week in zip(specifications, weeks, strict=True):
        scope = fold._scope(root, spec, checked_at)
        fold.require(
            _week_for(scope["race_dates"]) == week, "enrollment_plan_week_conflict"
        )
        cutoffs.append(timestamp(scope["first_block_cutoff"]))
    first_cutoff = min(cutoffs)
    fold.require(
        merged < first_cutoff, "enrollment_publication_not_before_original_cutoff"
    )

    return {
        "state": "enrollment_membership_verified",
        "policy_sha256": policy_ref["sha256"],
        "plan_sha256": plan_ref["sha256"],
        "training_weeks": policy["training_weeks"],
        "evaluation_week": policy["evaluation_week"],
        "first_enrolled_cutoff": first_cutoff.isoformat(),
        "publication": proof,
        "result_version_selection_verified": False,
        **fold.NO_AUTHORITY,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="mode", required=True)
    for name in ("marker", "capture", "replay"):
        command = commands.add_parser(name)
        command.add_argument("--policy", required=True)
        command.add_argument("--policy-sha256", required=True)
        if name != "marker":
            command.add_argument("--pull", type=int, required=True)
        if name == "replay":
            command.add_argument("--plan", required=True)
            command.add_argument("--plan-sha256", required=True)
    args = cli.parse_args(argv)
    root = Path.cwd().resolve()
    policy = {"path": args.policy, "sha256": args.policy_sha256}
    if args.mode == "replay":
        plan = {"path": args.plan, "sha256": args.plan_sha256}
        report = verify(root, policy, plan, pull=args.pull)
    else:
        path, _ = _load_policy(root, policy)
        if args.mode == "marker":
            sys.stdout.buffer.write(marker(args.policy_sha256))
            return 0
        report = _witness(root, path, args.policy_sha256, args.pull, capture=True)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
