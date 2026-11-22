"""Select and replay a pinned public journal lineage, without certifying coverage."""

import argparse
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

from autoresearch import condition_population_chain as chain
from autoresearch import condition_population_ledger as ledger
from autoresearch.condition_historical_publication import archive, pin, read, relative
from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-population-checkpoint-index-v1"
GAP_STATES = {
    "not_observed",
    "transport_error",
    "auth_error",
    "rate_limited",
    "archive_unavailable",
}


def _report(expected_sha):
    return {
        "format_version": VERSION,
        "index_sha256": expected_sha,
        "scope": "pinned_candidate_index_only",
        "status": "pending_evidence",
        "selected": None,
        "candidates": [],
        "candidate_inventory_complete_verified": False,
        "full_population_verified": False,
        "denominator": None,
        "usable_for_scoring": False,
        "counts_as_70_percent_evidence": False,
        "outcomes_loaded": False,
        "registration_performed": False,
    }


def _read_index(path, expected_sha):
    index = parse_json(pin(path.parent, {"path": path.name, "sha256": expected_sha}))
    if (
        type(index) is not dict
        or set(index)
        != {
            "format_version",
            "evidence_as_of",
            "umbrella",
            "journal_document",
            "candidates",
            "observation_gaps",
        }
        or index["format_version"] != VERSION
        or type(index["candidates"]) is not list
        or type(index["observation_gaps"]) is not list
    ):
        raise ValueError("checkpoint_index_schema")
    as_of = timestamp(index["evidence_as_of"])
    if as_of > datetime.now(UTC):
        raise ValueError("checkpoint_future_evidence_boundary")
    relative(index["journal_document"])
    paths, digests = set(), set()
    for reference in index["candidates"]:
        if (
            type(reference) is not dict
            or set(reference) != {"path", "sha256"}
            or "/" in relative(reference["path"])
            or reference["path"] == path.name
        ):
            raise ValueError("checkpoint_candidate_manifest_pin")
        digest = checked_digest(reference["sha256"])
        if reference["path"] in paths or digest in digests:
            raise ValueError("checkpoint_duplicate_candidate_manifest")
        paths.add(reference["path"])
        digests.add(digest)
    seen = set()
    for gap in index["observation_gaps"]:
        if (
            type(gap) is not dict
            or set(gap) != {"expected_at", "status"}
            or gap["status"] not in GAP_STATES
        ):
            raise ValueError("checkpoint_observation_gap_schema")
        instant = timestamp(gap["expected_at"])
        if instant > as_of or instant in seen:
            raise ValueError("checkpoint_observation_gap_clock")
        seen.add(instant)
    return index, as_of


def _candidate(root, reference, index):
    manifest = parse_json(pin(root, reference))
    if (
        type(manifest) is not dict
        or set(manifest) != {"format_version", "umbrella", "journal", "snapshots"}
        or manifest["format_version"] != ledger.VERSION
        or type(manifest["snapshots"]) is not dict
        or encoded(manifest["umbrella"]) != encoded(index["umbrella"])
        or type(manifest["journal"]) is not dict
        or manifest["journal"].get("document") != index["journal_document"]
    ):
        raise ValueError("checkpoint_candidate_binding")
    for digest, snapshot in manifest["snapshots"].items():
        if (
            type(snapshot) is not dict
            or set(snapshot) != {"path", "sha256"}
            or snapshot["sha256"] != checked_digest(digest)
        ):
            raise ValueError("checkpoint_snapshot_pin")
        relative(snapshot["path"])
    return manifest


def _validate_lineage(eligible):
    for current, later in pairwise(eligible):
        current_at, _, current_hashes, current_pins = current
        later_at, _, later_hashes, later_pins = later
        if current_at == later_at:
            raise ValueError("checkpoint_ambiguous_merge_clock")
        prefix_len = len(current_hashes)
        # Each event digest also binds every previous event through the chain.
        if len(later_hashes) <= prefix_len or (
            prefix_len and later_hashes[prefix_len - 1] != current_hashes[-1]
        ):
            raise ValueError("checkpoint_non_append_only_history")
        if any(later_pins.get(digest) != pin for digest, pin in current_pins.items()):
            raise ValueError("checkpoint_replaced_snapshot_pin")


def audit(index_path, expected_sha):
    path = Path(index_path).absolute()
    index, as_of = _read_index(path, expected_sha)
    report = _report(expected_sha)
    report["verifier_sha256"] = sha256(read(Path(__file__)))
    report["evidence_as_of"] = as_of.isoformat()
    report["observation_gaps"] = index["observation_gaps"]
    scope, fact = archive(path.parent, index["umbrella"])
    report["umbrella_publication"] = fact
    if scope is None or timestamp(fact["witness"]["retrieved_at"]) > as_of:
        report["reason"] = "umbrella_not_witnessed_at_boundary"
        return report
    if index["umbrella"]["document"] == index["journal_document"]:
        raise ValueError("checkpoint_umbrella_is_journal")
    scope_at = timestamp(fact["witness"]["merged_at"])
    weeks, _ = ledger.expected_scopes(scope)
    report["declared_week_ids"] = sorted(weeks)
    eligible, pulls = [], set()
    waiting = bool(index["observation_gaps"])
    for reference in index["candidates"]:
        row = {"replay_manifest": reference, "status": "pending_manifest"}
        report["candidates"].append(row)
        try:
            candidate = _candidate(path.parent, reference, index)
        except FileNotFoundError:
            waiting = True
            continue
        journal_ref = candidate["journal"]
        number = journal_ref.get("pull_number")
        if type(number) is not int or number <= 0:
            raise ValueError("checkpoint_candidate_publication_number")
        if number in pulls:
            raise ValueError("checkpoint_duplicate_publication")
        pulls.add(number)
        journal, publication = archive(path.parent, journal_ref)
        row.update(status="pending_archive", publication=publication)
        if journal is None:
            waiting = True
            continue
        witness = publication["witness"]
        merged = timestamp(witness["merged_at"])
        if merged > as_of:
            row["status"] = "published_after_boundary"
            continue
        if timestamp(witness["retrieved_at"]) > as_of:
            row["status"] = "retrieved_after_boundary"
            waiting = True
            continue
        if merged < scope_at:
            raise ValueError("checkpoint_journal_before_umbrella")
        structure = chain.validate(journal, index["umbrella"]["sha256"], weeks, merged)
        if any(
            timestamp(item["event"]["recorded_at"]) < scope_at
            for item in structure["events"]
        ):
            raise ValueError("checkpoint_event_before_umbrella")
        row.update(
            status="verified_candidate",
            event_count=len(structure["events"]),
            head_sha256=structure["head_sha256"],
        )
        hashes = tuple(item["event_sha256"] for item in structure["events"])
        eligible.append((merged, row, hashes, candidate["snapshots"]))
    eligible.sort(key=lambda item: item[0])
    _validate_lineage(eligible)
    if waiting or not eligible:
        report["reason"] = (
            "incomplete_candidate_evidence" if waiting else "no_timely_candidate"
        )
        return report
    _, selected, _, _ = eligible[-1]
    reference = selected["replay_manifest"]
    replay = ledger.audit(path.parent / reference["path"], reference["sha256"])
    if replay["status"] != "observations_replayed":
        report["reason"] = "selected_replay_unavailable"
        return report
    report.update(status="checkpoint_selected", selected=selected, replay=replay)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.index, args.sha256)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        result = _report(args.sha256)
        result.update(status="blocked", reason=str(exc))
    print(encoded(result).decode(), end="")
    return 0 if result["status"] == "checkpoint_selected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
