"""Bind complete M0/API27 input bytes to the time of a GitHub merge."""

import argparse
import json
import sys
from pathlib import Path

from autoresearch import condition_forward_publication as publication
from autoresearch.kra_entry_scope_inputs import preflight
from autoresearch.kra_entry_scope_intake import _pinned, _utc, now
from autoresearch.kra_race_card_pdf_replay import archive_path, checked_digest
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

PACKET_FORMAT = "kra-api26-whole-card-input-packet-v1"
MARKER_FORMAT = "kra-api26-whole-card-input-witness-v1"
PACKET_NAME = "whole-card-input-packet.json"
ARCHIVE_NAME = "whole-card-input-publication"


def _packet(verified):
    return {
        "format": PACKET_FORMAT,
        **{
            key: verified[key]
            for key in (
                "first_block_cutoff",
                "intake_receipt",
                "schedule",
                "race_dates",
                "race_count",
                "declaration_count",
                "feature_missing_counts",
                "local_readback_at",
            )
        },
        "races": [
            {
                "race_id": binding["race"]["race_id"],
                "declarations": binding["race"]["runners"],
                "binding_sha256": sha256(encoded(binding)),
            }
            for binding in verified["bindings"]
        ],
    }


def publication_document(packet_digest):
    return f"docs/research/input-witnesses/{checked_digest(packet_digest)}.json"


def _marker(packet_digest):
    return encoded({"format": MARKER_FORMAT, "packet_sha256": packet_digest})


def stage(root, receipt, *, schedule_sha256, first_cutoff, clock=now):
    """Save one private packet; expose only the exact publication bytes."""
    root = root.resolve()
    verified = preflight(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        clock=clock,
    )
    packet = _packet(verified)
    ready = timestamp(packet["local_readback_at"])
    cutoff = timestamp(first_cutoff)
    started = _utc(clock())
    if not ready <= started < cutoff:
        raise ValueError("scope_witness_stage_outside_original_cutoff")
    path = (root / packet["intake_receipt"]["path"]).with_name(PACKET_NAME)
    digest = save(path, packet)
    if not started <= _utc(clock()) < cutoff:
        raise ValueError("scope_witness_stage_outside_original_cutoff")
    return _marker(digest)


def verify(
    root,
    receipt,
    *,
    schedule_sha256,
    first_cutoff,
    packet_sha256,
    pull,
    capture=False,
):
    """Replay source bytes and the exact provider document; never stage."""
    if type(pull) is not int or pull < 1:
        raise ValueError("scope_witness_invalid_pull")
    document = publication_document(packet_sha256)
    root = root.resolve()
    receipt_path, _ = _pinned(root, receipt)
    packet_path = receipt_path.with_name(PACKET_NAME)
    if packet_path.is_symlink():
        raise ValueError("scope_witness_packet_path_conflict")
    _, raw = _pinned(root, {"path": packet_path, "sha256": packet_sha256})
    saved = parse_json(raw)
    readback_at = timestamp(saved["local_readback_at"])
    if readback_at > now():
        raise ValueError("scope_witness_local_readback_in_future")

    # Reproduce an existing packet, not a new stage at a historical clock.
    verified = preflight(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        clock=lambda: readback_at,
    )
    if encoded(_packet(verified)) != raw:
        raise ValueError("scope_witness_packet_does_not_replay")
    directory = receipt_path.with_name(ARCHIVE_NAME)
    if archive_path(directory, archive_root=root) != directory or any(
        (directory / name).is_symlink() for name in publication.ARCHIVE_FILES
    ):
        raise ValueError("scope_witness_archive_path_conflict")
    read_publication = publication.capture if capture else publication.replay
    expected_marker = _marker(packet_sha256)
    published, witness = read_publication(
        directory, pull, document, sha256(expected_marker)
    )
    if published != expected_marker:
        raise ValueError("scope_witness_marker_conflict")
    merged_at = timestamp(witness["merged_at"])
    if merged_at < readback_at:
        raise ValueError("scope_witness_merge_before_readback")
    timely = merged_at < timestamp(first_cutoff)
    return {
        "state": (
            "content_bound_before_cutoff" if timely else "published_at_or_after_cutoff"
        ),
        "before_cutoff": timely,
        "packet_sha256": packet_sha256,
        "first_block_cutoff": saved["first_block_cutoff"],
        "schedule_sha256": saved["schedule"]["sha256"],
        "local_readback_at": saved["local_readback_at"],
        "race_dates": saved["race_dates"],
        "race_count": saved["race_count"],
        "declaration_count": saved["declaration_count"],
        "feature_missing_counts": saved["feature_missing_counts"],
        "provider_archive": str(directory.relative_to(root)),
        "publication": witness,
        "official_source_authenticated_by_publication": False,
        "training_or_study_approved": False,
        "prediction_publication_verified": False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    modes = cli.add_subparsers(dest="mode", required=True)
    for name in ("stage", "capture", "replay"):
        mode = modes.add_parser(name)
        mode.add_argument("--receipt", required=True)
        mode.add_argument("--receipt-sha256", required=True)
        mode.add_argument("--schedule-sha256", required=True)
        mode.add_argument("--first-cutoff", required=True)
        if name != "stage":
            mode.add_argument("--packet-sha256", required=True)
            mode.add_argument("--pull", type=int, required=True)
    args = cli.parse_args(argv)
    root = Path.cwd()
    ref = {"path": args.receipt, "sha256": args.receipt_sha256}
    original = {
        "schedule_sha256": args.schedule_sha256,
        "first_cutoff": args.first_cutoff,
    }
    if args.mode == "stage":
        sys.stdout.buffer.write(stage(root, ref, **original))
        return 0
    result = verify(
        root,
        ref,
        **original,
        packet_sha256=args.packet_sha256,
        pull=args.pull,
        capture=args.mode == "capture",
    )
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["before_cutoff"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
