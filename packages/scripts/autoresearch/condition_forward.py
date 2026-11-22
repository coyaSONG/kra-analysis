"""Stored A24/B34 inference, append-only staging and external publication audit."""

from __future__ import annotations

import argparse
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from autoresearch import condition_forward_contract as contract
from autoresearch import condition_forward_publication as publication
from autoresearch.condition_forward_inputs import matrix_for
from autoresearch.condition_training import safe_destination, save, sync_directory
from autoresearch.condition_training_model import ARMS, score, select
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256


def now():
    return datetime.now(UTC)


def locations(study_id):
    common = Path(
        contract.training.git("rev-parse", "--git-common-dir").decode().strip()
    )
    if not common.is_absolute():
        common = contract.ROOT / common
    return (
        common.resolve() / "condition-forward-attempts" / study_id,
        contract.ROOT / ".cache/autoresearch/condition-forward-v1" / study_id,
    )


def document_path(study_id):
    return contract.prediction_document(study_id)


def deadline(protocol, observed):
    cutoff = min(timestamp(r["feature_cutoff_at"]) for r in protocol["races"])
    if not timestamp(protocol["created_at"]) <= observed < cutoff:
        raise ValueError("forward_whole_block_deadline")
    return cutoff


def paired(protocol, matrix, x, identities, models, completed):
    predictions = {
        arm: {
            r["race_id"]: r["horse_ids"]
            for r in select(identities, score(models[arm], x[:, : len(columns)]))
        }
        for arm, columns in ARMS.items()
    }
    return {
        "format_version": "condition-forward-paired-v1",
        "study_id": protocol["study_id"],
        "protocol_sha256": sha256(encoded(protocol)),
        "runtime_sha256": sha256(encoded(protocol["runtime"])),
        "model_hashes": contract.MODEL_HASHES,
        "training_receipt_sha256": contract.RECEIPT_SHA,
        "matrix_sha256": sha256(encoded(matrix)),
        "computed_at": completed.isoformat(),
        "race_count": len(protocol["races"]),
        "runner_count": len(identities),
        "null_counts": matrix["null_counts"],
        "races": [
            {
                "race_id": r["race_id"],
                "feature_cutoff_at": r["feature_cutoff_at"],
                "predictions": {arm: predictions[arm][r["race_id"]] for arm in ARMS},
            }
            for r in protocol["races"]
        ],
        "actual_fit_count": 0,
        "external_publication_verified": False,
        "counts_as_70_percent_evidence": False,
        "model_promoted": False,
    }


def unchanged(protocol, review, registry):
    current, current_review, current_registry = contract.admit(protocol["study_id"])
    if current != protocol or current_review != review or current_registry != registry:
        raise ValueError("forward_admission_changed_during_run")
    contract.load_models()


def protocol_witness(ledger, review, protocol, *, collect=False):
    directory = ledger / "protocol-publication"
    operation = publication.capture if collect else publication.replay
    _, witness = operation(
        directory,
        review["protocol_publication_pr"],
        review["protocol"]["path"],
        review["protocol"]["sha256"],
    )
    merged = timestamp(witness["merged_at"])
    if not timestamp(protocol["created_at"]) <= merged:
        raise ValueError("forward_protocol_publication_clock")
    deadline(protocol, merged)
    return witness


def run(study_id):
    protocol, review, registry = contract.admit(study_id)
    models, _ = contract.load_models()
    ledger, output = locations(study_id)
    safe_destination(ledger)
    safe_destination(output)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    sync_directory(ledger.parent.parent)
    ledger.mkdir(exist_ok=False)
    sync_directory(ledger.parent)
    save(
        ledger / "reservation.json",
        {
            "study_id": study_id,
            "protocol_sha256": review["protocol"]["sha256"],
            "race_ids": [r["race_id"] for r in protocol["races"]],
            "started_at": now().isoformat(),
            "actual_fit_count": 0,
            "retry_allowed": False,
        },
    )
    try:
        save(ledger / "registry.json", parse_json(registry))
        deadline(protocol, now())
        witness = protocol_witness(ledger, review, protocol, collect=True)
        created = now()
        deadline(protocol, created)
        matrix, x, identities = matrix_for(protocol, created)
        # Set the computation clock only after inference has completed.
        packet = paired(protocol, matrix, x, identities, models, created)
        completed = now()
        deadline(protocol, completed)
        packet["computed_at"] = completed.isoformat()
        unchanged(protocol, review, registry)
        replayed, _, _ = matrix_for(protocol, created)
        if replayed != matrix:
            raise ValueError("forward_inputs_changed_during_run")
        deadline(protocol, now())
        output.mkdir(parents=True, exist_ok=False)
        sync_directory(output.parent)
        save(output / "matrix.json", matrix)
        packet_sha = save(output / "paired.json", packet)
        observed = now()
        deadline(protocol, observed)
        if (
            not completed <= observed
            or sha256(contract.training.read(output / "paired.json")) != packet_sha
        ):
            raise ValueError("forward_saved_prediction_clock_or_hash")
        receipt = {
            "format_version": "condition-forward-local-receipt-v1",
            "study_id": study_id,
            "protocol_sha256": review["protocol"]["sha256"],
            "registry_sha256": sha256(registry),
            "protocol_publication": witness,
            "matrix_sha256": packet["matrix_sha256"],
            "paired_sha256": packet_sha,
            "observed_at": observed.isoformat(),
            "actual_fit_count": 0,
            "status": "locally_complete_not_public",
        }
        receipt_sha = save(output / "receipt.json", receipt)
        deadline(protocol, now())
        save(ledger / "complete.json", {"receipt_sha256": receipt_sha})
        return receipt
    except BaseException as exc:
        save(
            ledger / "failure.json",
            {
                "failed_at": now().isoformat(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "retry_allowed": False,
                "race_ids": [r["race_id"] for r in protocol["races"]],
                "actual_fit_count": 0,
            },
        )
        raise


def verify_local(study_id):
    protocol, review, registry = contract.admit(study_id)
    models, _ = contract.load_models()
    ledger, output = locations(study_id)
    if (ledger / "failure.json").exists():
        raise ValueError("forward_failed_attempt_not_publishable")
    witness = protocol_witness(ledger, review, protocol)
    receipt_raw = contract.training.read(output / "receipt.json")
    receipt = parse_json(receipt_raw)
    complete = parse_json(contract.training.read(ledger / "complete.json"))
    original_registry = contract.training.read(ledger / "registry.json")
    original_reviews = parse_json(original_registry)["approved_studies"]
    packet_raw = contract.training.read(output / "paired.json")
    packet = parse_json(packet_raw)
    matrix_raw = contract.training.read(output / "matrix.json")
    matrix = parse_json(matrix_raw)
    created, completed, observed = (
        timestamp(value)
        for value in (
            matrix["created_at"],
            packet["computed_at"],
            receipt["observed_at"],
        )
    )
    if (
        complete["receipt_sha256"] != sha256(receipt_raw)
        or receipt["paired_sha256"] != sha256(packet_raw)
        or receipt["matrix_sha256"] != sha256(matrix_raw)
        or receipt["protocol_sha256"] != review["protocol"]["sha256"]
        or receipt["registry_sha256"] != sha256(original_registry)
        or [r for r in original_reviews if r["study_id"] == study_id] != [review]
        or receipt["format_version"] != "condition-forward-local-receipt-v1"
        or receipt["study_id"] != study_id
        or receipt["protocol_publication"] != witness
        or receipt["actual_fit_count"] != 0
        or receipt["status"] != "locally_complete_not_public"
        or not timestamp(witness["retrieved_at"])
        <= created
        <= completed
        <= observed
        <= now()
    ):
        raise ValueError("forward_local_receipt_conflict")
    deadline(protocol, observed)
    rebuilt, x, identities = matrix_for(protocol, created)
    if matrix != rebuilt or packet != paired(
        protocol, rebuilt, x, identities, models, completed
    ):
        raise ValueError("forward_saved_prediction_replay_conflict")
    return protocol, packet_raw, receipt


def stage(study_id):
    protocol, raw, receipt = verify_local(study_id)
    _, output = locations(study_id)
    try:
        deadline(protocol, now())
        path = contract.local_path(document_path(study_id))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if contract.training.read(path) != raw:
                raise ValueError("forward_existing_staged_bytes_differ")
        else:
            save(path, parse_json(raw))
        deadline(protocol, now())
    except (ValueError, OSError) as exc:
        save(
            output / f"staging-failure-{uuid4().hex}.json",
            {
                "observed_at": now().isoformat(),
                "status": "staging_failed",
                "error": str(exc),
                "actual_fit_count": 0,
            },
        )
        raise
    return {
        "document": document_path(study_id),
        "publication_slot": contract.publication_slot(protocol),
        "sha256": receipt["paired_sha256"],
        "status": "staged_not_public",
        "actual_fit_count": 0,
    }


def witness(study_id, number):
    protocol, _, _ = contract.admit(study_id)
    if (
        type(number) is not int
        or number != contract.publication_slot(protocol)["pull_number"]
    ):
        raise ValueError("forward_prediction_slot_mismatch")
    protocol, raw, receipt = verify_local(study_id)
    if number != contract.publication_slot(protocol)["pull_number"]:
        raise ValueError("forward_prediction_slot_mismatch")
    _, output = locations(study_id)
    directory = (
        output
        / "publications"
        / (now().strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12])
    )
    try:
        public, evidence = publication.capture(
            directory, number, document_path(study_id), sha256(raw)
        )
        _, checked, _ = verify_local(study_id)
        if (
            public != raw
            or checked != raw
            or timestamp(evidence["merged_at"]) < timestamp(receipt["observed_at"])
        ):
            raise ValueError("forward_publication_bytes_or_clock_conflict")
        cutoff = min(timestamp(r["feature_cutoff_at"]) for r in protocol["races"])
        report = {
            "publication_slot": contract.publication_slot(protocol),
            "status": "published_before_cutoff"
            if timestamp(evidence["merged_at"]) < cutoff
            else "published_after_cutoff",
            "witness": evidence,
            "paired_sha256": sha256(raw),
            "race_count": len(protocol["races"]),
            "actual_fit_count": 0,
            "counts_as_70_percent_evidence": False,
            "model_promoted": False,
        }
    except (ValueError, OSError, KeyError, TypeError, httpx.HTTPError) as exc:
        directory.mkdir(parents=True, exist_ok=True)
        report = {
            "status": "publication_unverified",
            "error_type": type(exc).__name__,
            "actual_fit_count": 0,
            "counts_as_70_percent_evidence": False,
        }
    save(directory / "report.json", report)
    return {"report_path": str(directory / "report.json"), **report}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect")
    for name in ("run", "verify", "stage", "witness"):
        sub = commands.add_parser(name)
        sub.add_argument("--study", required=True)
        if name == "witness":
            sub.add_argument("--pull", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            contract.load_models()
            registry = parse_json(
                contract.training.read(contract.ROOT / contract.REGISTRY)
            )
            result = {
                "runtime": contract.runtime(),
                "registered_studies": [
                    r["study_id"] for r in registry["approved_studies"]
                ],
                "actual_fit_count": 0,
            }
        elif args.command == "run":
            result = run(args.study)
        elif args.command == "stage":
            result = stage(args.study)
        elif args.command == "witness":
            result = witness(args.study, args.pull)
        else:
            _, _, result = verify_local(args.study)
        print(encoded(result).decode(), end="")
        return (
            2
            if result.get("status")
            in ("publication_unverified", "published_after_cutoff")
            else 0
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        httpx.HTTPError,
    ) as exc:
        print(
            encoded(
                {"status": "blocked", "reason": str(exc), "actual_fit_count": 0}
            ).decode(),
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
