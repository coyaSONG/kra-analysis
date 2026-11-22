"""Freeze exact earlier-card candidates and a later input-only population."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from autoresearch import condition_forward_publication as publication
from autoresearch import fixed_pair_forward_contract as inputs
from autoresearch import kra_entry_scope_witness as input_witness
from autoresearch import kra_whole_card_learning as learning
from autoresearch.kra_entry_scope_intake import now
from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    archive_path,
    checked_digest,
    read_bytes,
)
from autoresearch.observed_history_seed import load_plan as load_seed_plan
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import API_COLUMNS, encoded, parse_json, sha256

PLAN = "kra-whole-card-walk-forward-plan-v1"
PACKET = "kra-whole-card-walk-forward-packet-v1"
MARKER = "kra-whole-card-walk-forward-witness-v1"
PACKET_NAME = "walk-forward-fold-packet.json"
ARCHIVE_NAME = "walk-forward-fold-publication"
INPUT_KEYS = {"receipt", "schedule_sha256", "first_cutoff", "packet_sha256", "input_pr"}
NO_AUTHORITY = {
    "study_registered": False,
    "training_approved": False,
    "prediction_publication_verified": False,
    "cross_fold_selection_rule_verified": False,
    "local_receipt_timestamps_independently_verified": False,
    "counts_as_70_percent_evidence": False,
}


def require(check, reason):
    if not check:
        raise ValueError(reason)


def private_path(root, relative):
    require(type(relative) is str and relative, "fold_invalid_archive_path")
    path = Path(relative)
    resolved = root / path
    require(
        not path.is_absolute()
        and path.parts
        and ".." not in path.parts
        and relative == path.as_posix()
        and resolved == archive_path(resolved, archive_root=root),
        "fold_noncanonical_archive_path",
    )
    return resolved


def _pinned(root, ref):
    require(type(ref) is dict and set(ref) == {"path", "sha256"}, "fold_invalid_pin")
    path = private_path(root, ref["path"])
    return path, _read_pin(path, ref["sha256"])


def _read_pin(path, expected):
    raw = read_bytes(path, limit=MAX_MANIFEST_BYTES)
    require(sha256(raw) == checked_digest(expected), "fold_pin_mismatch")
    return raw


def _load_plan(root, ref):
    _, raw = _pinned(root, ref)
    plan = parse_json(raw)
    require(
        set(plan) == {"format", "training", "evaluation"}
        and plan["format"] == PLAN
        and type(plan["training"]) is list
        and plan["training"]
        and all(
            type(item) is dict and set(item) == {"input", "result_plan", "candidate"}
            for item in plan["training"]
        ),
        "fold_invalid_plan",
    )
    for item in [plan["evaluation"], *(x["input"] for x in plan["training"])]:
        require(type(item) is dict and set(item) == INPUT_KEYS, "fold_invalid_input")
    receipt, _ = _pinned(root, plan["evaluation"]["receipt"])
    return plan, receipt.parent


def _scope(root, spec, checked_at):
    receipt, _ = _pinned(root, spec["receipt"])
    verified, bound = inputs.source(root, **spec)
    public_pin = bound["input_publication"]
    _, observed = publication.replay(
        receipt.with_name(input_witness.ARCHIVE_NAME),
        spec["input_pr"],
        input_witness.publication_document(spec["packet_sha256"]),
        public_pin["document_sha256"],
    )
    require(
        all(observed[key] == value for key, value in public_pin.items()),
        "fold_input_publication_changed",
    )
    races = [b["race"] for b in verified["bindings"]]
    ids = sorted(r["race_id"] for r in races)
    retrieved = timestamp(observed["retrieved_at"])
    require(
        races and len(set(ids)) == len(ids) == verified["race_count"],
        "fold_input_population_conflict",
    )
    require(retrieved <= checked_at, "fold_input_unavailable_at_assembly")
    return {
        "first_block_cutoff": verified["first_block_cutoff"],
        "last_scheduled_start_at": max(
            timestamp(r["scheduled_start_at"]) for r in races
        ).isoformat(),
        "race_dates": verified["race_dates"],
        "race_ids": ids,
        "population_sha256": sha256(encoded(ids)),
        "race_count": verified["race_count"],
        "declaration_count": verified["declaration_count"],
        "feature_missing_counts": verified["feature_missing_counts"],
        "input_witness_retrieved_at": retrieved.isoformat(),
        "input": bound | {"intake_receipt": verified["intake_receipt"]},
    }


def _training_seed(result_plan, evaluation_day):
    # The shared evaluator replays the whole archive before filtering dates.
    raw_plan, plan_sha = load_seed_plan(
        Path(result_plan["seed_root"]), require_current=False
    )
    require(raw_plan["end"] < evaluation_day, "fold_result_archive_reaches_evaluation")
    seed = parse_json(
        _read_pin(Path(result_plan["seed_path"]), result_plan["seed_sha256"])
    )
    require(seed["plan_sha256"] == plan_sha, "fold_result_seed_plan_changed")
    return seed


def _result_clocks(seed, report):
    # Seed rows retain the combined API and corroborating identity clock.
    exported = timestamp(seed["materialized_at"])
    race_ids = {row["race_id"] for row in report["ledger"]}
    combined = max(
        timestamp(row["source_available_at"])
        for row in seed["records"]
        if row["race_id"] in race_ids
    )
    api_capture = max(
        timestamp(api["capture_completed_at"])
        for row in report["ledger"]
        for api in row["api_result_captures"]
    )
    official = max(
        timestamp(row["official_result_evidence"]["capture"]["completed_at"])
        for row in report["ledger"]
    )
    require(api_capture <= combined <= exported, "fold_result_seed_clock_conflict")
    return {
        "latest_api_capture_completed_at": api_capture.isoformat(),
        "latest_combined_result_available_at": combined.isoformat(),
        "result_seed_materialized_at": exported.isoformat(),
        "latest_official_capture_completed_at": official.isoformat(),
        "result_evidence_available_at": max(exported, official).isoformat(),
    }


def _training(root, selection, scope, checked_at, evaluation_day):
    result_path, result_raw = _pinned(root, selection["result_plan"])
    result_plan = parse_json(result_raw)
    require(
        result_plan["race_dates"] == scope["race_dates"]
        and result_plan["schedule_sha256"] == scope["input"]["schedule_sha256"],
        "fold_result_plan_not_training_card",
    )
    seed = _training_seed(result_plan, evaluation_day)
    expected_path = (root / scope["input"]["intake_receipt"]["path"]).with_name(
        "development-candidate-" + selection["result_plan"]["sha256"] + ".json"
    )
    require(
        expected_path == private_path(root, selection["candidate"]["path"]),
        "fold_candidate_path_conflict",
    )
    _, raw = _pinned(root, selection["candidate"])
    old = parse_json(raw)
    materialized = timestamp(old["materialized_at"])
    readback = timestamp(old["report"]["readback_started_at"])
    require(
        timestamp(scope["last_scheduled_start_at"])
        <= readback
        <= materialized
        <= checked_at
        and timestamp(scope["input_witness_retrieved_at"]) <= readback,
        "fold_candidate_unavailable_at_assembly",
    )
    report, candidate = learning.replay(
        root,
        **selection["input"],
        result_plan=(result_path, selection["result_plan"]["sha256"]),
    )
    require(candidate is not None, "fold_training_card_not_complete")
    restated = candidate | {
        "report": report
        | {"readback_started_at": old["report"]["readback_started_at"]},
        "materialized_at": old["materialized_at"],
    }
    require(encoded(restated) == raw, "fold_candidate_does_not_replay")
    clocks = _result_clocks(seed, report)
    require(
        timestamp(clocks["result_evidence_available_at"]) <= readback,
        "fold_result_evidence_after_candidate_readback",
    )
    return scope | {
        "result_plan": selection["result_plan"],
        "candidate": selection["candidate"],
        "result_version": report["result_version"],
        "result_clocks": clocks,
        "candidate_readback_at": readback.isoformat(),
        "candidate_materialized_at": materialized.isoformat(),
    }


def _assemble(root, plan_ref, plan, checked_at):
    cutoff = timestamp(plan["evaluation"]["first_cutoff"])
    require(checked_at < cutoff, "fold_stage_not_before_original_cutoff")
    evaluation = _scope(root, plan["evaluation"], checked_at)
    earlier = [_scope(root, item["input"], checked_at) for item in plan["training"]]
    require(
        timestamp(evaluation["first_block_cutoff"]) == cutoff,
        "fold_original_evaluation_cutoff_conflict",
    )
    # Decide the split before opening any result plan, including a misassigned one.
    scopes = [*earlier, evaluation]
    require(
        all(
            a["race_dates"][-1] < b["race_dates"][0]
            for a, b in zip(scopes[:-1], scopes[1:], strict=True)
        )
        and all(timestamp(a["last_scheduled_start_at"]) < cutoff for a in earlier),
        "fold_card_order_or_population_overlap",
    )
    all_ids = [rid for item in scopes for rid in item["race_ids"]]
    require(len(all_ids) == len(set(all_ids)), "fold_duplicate_race_identity")
    training = [
        _training(root, item, scope, checked_at, evaluation["race_dates"][0])
        for item, scope in zip(plan["training"], earlier, strict=True)
    ]
    missing = Counter()
    for item in training:
        missing.update(item["feature_missing_counts"])
    return {
        "format": PACKET,
        "implementation_sha256": sha256(Path(__file__).read_bytes()),
        "plan": plan_ref,
        "eligibility_checked_as_of": checked_at.isoformat(),
        "training": training,
        "training_population_sha256": sha256(
            encoded(sorted(rid for item in training for rid in item["race_ids"]))
        ),
        "training_race_count": sum(t["race_count"] for t in training),
        "training_declaration_count": sum(t["declaration_count"] for t in training),
        "training_feature_missing_counts": dict(missing),
        "feature_columns": list(API_COLUMNS),
        "evaluation": evaluation,
        **NO_AUTHORITY,
    }


def publication_document(digest):
    return f"docs/research/walk-forward-witnesses/{checked_digest(digest)}.json"


def marker(digest):
    return encoded({"format": MARKER, "packet_sha256": checked_digest(digest)})


def stage(root, plan_ref):
    root = root.resolve()
    checked_at = now()
    plan, parent = _load_plan(root, plan_ref)
    path = parent / PACKET_NAME
    if path.exists() or path.is_symlink():
        raise FileExistsError("fold_packet_already_present")
    packet = _assemble(root, plan_ref, plan, checked_at)
    cutoff = timestamp(packet["evaluation"]["first_block_cutoff"])
    started = now()
    require(checked_at <= started < cutoff, "fold_stage_not_before_original_cutoff")
    digest = save(path, packet)
    require(started <= now() < cutoff, "fold_stage_not_before_original_cutoff")
    return marker(digest)


def verify(root, plan_ref, *, packet_sha256, pull, capture=False):
    root = root.resolve()
    plan, parent = _load_plan(root, plan_ref)
    packet_path = private_path(root, str((parent / PACKET_NAME).relative_to(root)))
    raw = _read_pin(packet_path, packet_sha256)
    saved = parse_json(raw)
    checked_at = timestamp(saved["eligibility_checked_as_of"])
    require(checked_at <= now(), "fold_assembly_in_future")
    packet = _assemble(root, plan_ref, plan, checked_at)
    require(encoded(packet) == raw, "fold_packet_does_not_replay")
    cutoff = timestamp(packet["evaluation"]["first_block_cutoff"])
    used = {
        item["input"]["input_publication"]["pull_number"]
        for item in [*packet["training"], packet["evaluation"]]
    }
    require(type(pull) is int and pull > 0 and pull not in used, "fold_invalid_pull")
    directory = parent / ARCHIVE_NAME
    for path in [directory, *(directory / f for f in publication.ARCHIVE_FILES)]:
        private_path(root, str(path.relative_to(root)))
    expected = marker(packet_sha256)
    read_publication = publication.capture if capture else publication.replay
    public, observed = read_publication(
        directory, pull, publication_document(packet_sha256), sha256(expected)
    )
    published = timestamp(observed["merged_at"])
    require(public == expected and checked_at <= published, "fold_publication_conflict")
    timely = published < cutoff
    return {
        "state": "fold_bound_before_cutoff" if timely else "fold_published_late",
        "before_cutoff": timely,
        "time_evidence": "exact_fold_marker_in_merging_commit",
        "first_block_cutoff": packet["evaluation"]["first_block_cutoff"],
        "packet_sha256": packet_sha256,
        "plan_sha256": plan_ref["sha256"],
        "training_card_count": len(packet["training"]),
        "training_race_count": packet["training_race_count"],
        "evaluation_race_count": packet["evaluation"]["race_count"],
        "evaluation_population_sha256": packet["evaluation"]["population_sha256"],
        "publication": observed,
        **NO_AUTHORITY,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="mode", required=True)
    for mode in ("stage", "capture", "replay"):
        sub = commands.add_parser(mode)
        sub.add_argument("--plan", required=True)
        sub.add_argument("--plan-sha256", required=True)
        if mode != "stage":
            sub.add_argument("--packet-sha256", required=True)
            sub.add_argument("--pull", required=True, type=int)
    args = cli.parse_args(argv)
    plan = {"path": args.plan, "sha256": args.plan_sha256}
    if args.mode == "stage":
        sys.stdout.buffer.write(stage(Path.cwd(), plan))
        return 0
    report = verify(
        Path.cwd(),
        plan,
        packet_sha256=args.packet_sha256,
        pull=args.pull,
        capture=args.mode == "capture",
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["before_cutoff"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
