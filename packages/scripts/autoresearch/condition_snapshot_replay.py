"""Replay archived condition inputs/numerics; never score outcomes or register."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from autoresearch import condition_historical_publication as history
from autoresearch import condition_snapshot_worker as worker
from autoresearch.condition_forward_contract import MODEL_HASHES, MODELS, RECEIPT_SHA
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-snapshot-replay-v1"


def base_result(expected):
    return {
        "format_version": VERSION,
        "manifest_sha256": expected,
        "audited_at": datetime.now(UTC).isoformat(),
        "scope": "original_input_and_numeric_replay_not_outcome_evaluation",
        "status": "pending_evidence",
        "verifier_sha256": sha256(history.read(Path(__file__))),
        "worker_sha256": sha256(history.read(Path(worker.__file__))),
        "raw_input_provenance": "not_verified",
        "submission_closure": "not_verified",
        "umbrella_population": "not_verified",
        "usable_for_scoring": False,
        "counts_as_70_percent_evidence": False,
        "actual_fit_count": 0,
        "outcomes_loaded": False,
    }


def child_environment(original):
    if type(original) is not dict or set(original) != set(worker.THREAD_VARIABLES):
        raise ValueError("snapshot_thread_settings_schema")
    env = dict(os.environ)
    for name, value in original.items():
        if value is None:
            env.pop(name, None)
        elif (
            type(value) is str
            and value.isascii()
            and value.isdecimal()
            and (0 < int(value) <= 1024)
        ):
            env[name] = value
        else:
            raise ValueError("snapshot_thread_setting_invalid")
    return env


def invoke(request, environment):
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(worker.__file__).absolute())],
        input=encoded(request),
        capture_output=True,
        env=environment,
        timeout=120,
        cwd=request["root"],
        check=False,
    )
    if completed.returncode != 0 or len(completed.stdout) > history.LIMIT:
        return {"status": "pending_worker", "reason": "worker_did_not_complete"}
    result = parse_json(completed.stdout)
    if type(result) is not dict or result.get("status") not in {
        "pending_environment",
        "pending_evidence",
        "replay_unverified",
        "replay_conflict",
        "numerically_replayed",
    }:
        raise ValueError("snapshot_invalid_worker_report")
    if result["status"] in ("numerically_replayed", "replay_conflict"):
        for name in ("matrix_bytes_match", "prediction_bytes_match"):
            if type(result.get(name)) is not bool:
                raise ValueError("snapshot_invalid_worker_comparison")
        if (result["status"] == "numerically_replayed") != (
            result["matrix_bytes_match"] and result["prediction_bytes_match"]
        ):
            raise ValueError("snapshot_inconsistent_worker_status")
    return result


def audit(manifest_path, expected_sha):
    path = Path(manifest_path).absolute()
    result = base_result(expected_sha)
    raw = history.pin(path.parent, {"path": path.name, "sha256": expected_sha})
    manifest = parse_json(raw)
    if (
        type(manifest) is not dict
        or set(manifest) != {"format_version", "publication", "snapshot", "matrix"}
        or manifest["format_version"] != VERSION
        or type(manifest["snapshot"]) is not dict
        or set(manifest["snapshot"]) != {"path", "files"}
    ):
        raise ValueError("snapshot_manifest_schema")
    pub_pin = manifest["publication"]
    pub_raw = history.pin(path.parent, pub_pin)
    pub_path = path.parent / pub_pin["path"]
    pub_manifest = parse_json(pub_raw)
    result["publication"] = history.audit(pub_path, pub_pin["sha256"])
    if result["publication"]["status"] != "public_chain_replayed":
        return result
    snapshot = manifest["snapshot"]
    root = path.parent / history.relative(snapshot["path"])
    files = snapshot["files"]
    matrix_path = history.relative(manifest["matrix"])
    try:
        worker.inventory(root, files)
    except FileNotFoundError:
        result["reason"] = "snapshot_missing_files"
        return result
    documents = {}
    for kind in history.KINDS:
        reference = pub_manifest[kind]
        name, digest = reference["document"], reference["sha256"]
        if files.get(name) != digest:
            raise ValueError("snapshot_public_document_not_bound")
        documents[kind] = parse_json(history.read(root / name))
    protocol, packet = documents["protocol"], documents["prediction"]
    worker.source_inventory(files, protocol["runtime"]["implementation"])
    required = {
        **protocol["runtime"]["implementation"],
        f"{MODELS}/receipt.json": RECEIPT_SHA,
        **{f"{MODELS}/{a}-model.json": h for a, h in MODEL_HASHES.items()},
        matrix_path: packet["matrix_sha256"],
    }
    for name, value in required.items():
        if files.get(name) != value:
            raise ValueError("snapshot_required_pin_mismatch")
    result["snapshot_inventory_sha256"] = sha256(encoded(files))
    result["original_environment_sha256"] = sha256(
        encoded(protocol["runtime"]["environment"])
    )
    request = {
        "root": str(root),
        "files": files,
        "matrix": matrix_path,
        "protocol": pub_manifest["protocol"]["document"],
        "prediction": pub_manifest["prediction"]["document"],
    }
    try:
        replay = invoke(
            request,
            child_environment(protocol["runtime"]["environment"]["thread_settings"]),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        replay = {"status": "pending_worker", "reason": type(exc).__name__}
    # A clean subprocess exit cannot erase evidence changed during execution.
    worker.inventory(root, files)
    history.pin(path.parent, {"path": path.name, "sha256": expected_sha})
    history.pin(path.parent, pub_pin)
    for kind in history.KINDS:
        document, _ = history.archive(pub_path.parent, pub_manifest[kind])
        if document is None:
            result["reason"] = "publication_evidence_lost_during_replay"
            return result
    result["replay"] = replay
    result["status"] = replay["status"]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.manifest, args.sha256)
    except FileNotFoundError:
        result = {**base_result(args.sha256), "reason": "missing_evidence"}
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        result = {**base_result(args.sha256), "status": "blocked", "reason": str(exc)}
    print(encoded(result).decode(), end="")
    return 0 if result["status"] == "numerically_replayed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
