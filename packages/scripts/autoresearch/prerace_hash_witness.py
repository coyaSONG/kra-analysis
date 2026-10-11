"""Audit public pre-race hash commitments without approving model training."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

import httpx
from shared.operational_cutoff import classify_source_snapshot_for_t30

from autoresearch.kra_race_card_pdf_bundle import (
    BUNDLE_VERSION,
    PLAN_VERSION,
    SCOPE_BASIS,
    _feature_projection,
    _identity,
    implementation_fingerprint,
)
from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    parse_json,
    read_bytes,
    replay_race_card_snapshot,
    sha256,
)

REPOSITORY = "coyaSONG/kra-analysis"
DOCUMENT = "docs/research/2026-10-10-verified-pdf-feature-archive.md"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"


def timestamp(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("witness_timestamp_requires_timezone")
    return stamp.astimezone(UTC)


def validate_publication(
    pull: dict[str, Any], content: dict[str, Any], *, number: int, document: str
) -> tuple[bytes, dict[str, Any]]:
    if (
        pull.get("merged") is not True
        or pull.get("state") != "closed"
        or type(pull.get("number")) is not int
        or pull["number"] != number
        or pull.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY
        or pull.get("html_url") != f"https://github.com/{REPOSITORY}/pull/{number}"
    ):
        raise ValueError("invalid_publication_pull")
    commit = pull.get("merge_commit_sha")
    if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("invalid_merge_commit")
    merged = timestamp(pull["merged_at"])
    if (
        content.get("type") != "file"
        or content.get("encoding") != "base64"
        or content.get("path") != document
        or content.get("html_url")
        != f"https://github.com/{REPOSITORY}/blob/{commit}/{document}"
    ):
        raise ValueError("publication_document_identity_mismatch")
    raw = base64.b64decode("".join(content["content"].split()), validate=True)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if content.get("size") != len(raw) or content.get("sha") != blob:
        raise ValueError("publication_blob_mismatch")
    return raw, {
        "repository": REPOSITORY,
        "pull_number": number,
        "merge_commit_sha": commit,
        "merged_at": merged.isoformat(),
        "document_path": document,
        "document_sha256": sha256(raw),
        "document_git_blob_sha": blob,
        "trust_basis": "live_github_https_metadata_and_hash_preimage_resistance",
    }


def collect_publication(
    directory: Path, *, number: int, document: str, client: httpx.Client
) -> tuple[bytes, dict[str, Any]]:
    if (
        type(number) is not int
        or number < 1
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", document)
        or PurePosixPath(document).is_absolute()
        or any(part in (".", "..") for part in document.split("/"))
    ):
        raise ValueError("invalid_publication_request")

    def get(url: str, name: str) -> dict[str, Any]:
        with client.stream("GET", url) as response:
            if response.status_code != 200 or str(response.url) != url:
                raise ValueError("publication_fetch_failed")
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_MANIFEST_BYTES:
                    raise ValueError("publication_response_too_large")
                chunks.append(chunk)
        raw = b"".join(chunks)
        with (directory / name).open("xb") as stream:
            stream.write(raw)
        return parse_json(raw)

    pull = get(f"{API_ROOT}/pulls/{number}", "pull.json")
    commit = pull.get("merge_commit_sha")
    if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("invalid_merge_commit")
    content = get(
        f"{API_ROOT}/contents/{document}?ref={commit}", "document-response.json"
    )
    raw, witness = validate_publication(pull, content, number=number, document=document)
    observed = datetime.now(UTC)
    if timestamp(witness["merged_at"]) > observed:
        raise ValueError("publication_merge_in_future")
    with (directory / "published-document.md").open("xb") as stream:
        stream.write(raw)
    witness["retrieved_at"] = observed.isoformat()
    witness["pull_response_sha256"] = sha256((directory / "pull.json").read_bytes())
    witness["document_response_sha256"] = sha256(
        (directory / "document-response.json").read_bytes()
    )
    return raw, witness


def audit_archive(
    *,
    plan_bytes: bytes,
    bundle_bytes: bytes,
    document_bytes: bytes,
    witness: dict[str, Any],
    archive_root: Path,
) -> dict[str, Any]:
    """The caller must obtain witness metadata through the live collector."""
    plan_hash, bundle_hash = sha256(plan_bytes), sha256(bundle_bytes)
    published = set(re.findall(rb"`([a-f0-9]{64})`", document_bytes))
    if any(pin.encode() not in published for pin in (plan_hash, bundle_hash)):
        raise ValueError("artifact_hash_not_in_published_document")
    if witness["document_sha256"] != sha256(document_bytes):
        raise ValueError("publication_document_sha256_mismatch")
    merged = timestamp(witness["merged_at"])
    plan, bundle = parse_json(plan_bytes), parse_json(bundle_bytes)
    if (
        plan["format_version"] != PLAN_VERSION
        or bundle["format_version"] != BUNDLE_VERSION
        or plan["scope_basis"] != SCOPE_BASIS
        or bundle["scope_basis"] != SCOPE_BASIS
        or bundle["input_plan_sha256"] != plan_hash
        or plan["implementation"] != bundle["implementation"]
    ):
        raise ValueError("published_archive_contract_mismatch")
    if any(
        timestamp(stamp) > merged
        for stamp in (plan["pinned_at"], bundle["exported_at"])
    ):
        raise ValueError("archive_clock_after_publication")
    planned = {row["race_id"]: row for row in plan["races"]}
    archived = {row["race_id"]: row for row in bundle["races"]}
    if (
        not planned
        or len(planned) != len(plan["races"])
        or len(archived) != len(bundle["races"])
        or set(planned) != set(archived)
        or bundle["race_count"] != len(planned)
        or bundle["feature_row_count"] != len(bundle["feature_rows"])
    ):
        raise ValueError("published_inventory_mismatch")
    saved_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    for row in bundle["feature_rows"]:
        key = (row["race_id"], row["chulNo"])
        if key in seen or row["race_id"] not in planned:
            raise ValueError("invalid_published_feature_membership")
        seen.add(key)
        saved_rows[row["race_id"]].append(row)
    ledger = []
    for race_id, record in sorted(planned.items()):
        identity = _identity(race_id)
        if any(record[k] != value for k, value in identity.items()):
            raise ValueError("published_identity_mismatch")
        if any(
            not isinstance(record.get(key), str)
            or not re.fullmatch(r"[a-f0-9]{64}", record[key])
            for key in ("manifest_sha256", "pdf_sha256", "entry_manifest_sha256")
        ):
            raise ValueError("published_raw_pin_missing")
        replay = replay_race_card_snapshot(
            record["manifest_path"],
            archive_root=archive_root,
            expected_sha256=record["manifest_sha256"],
            expected_identity=identity,
            expected_pdf_sha256=record["pdf_sha256"],
            expected_entry_manifest_sha256=record["entry_manifest_sha256"],
        )
        evidence = replay["evidence"]
        chain_verified = bool(evidence.get("pdf") and evidence.get("entry"))
        timing = classify_source_snapshot_for_t30(
            race_date=identity["race_date"],
            scheduled_start_time=replay.get("scheduled_start_time"),
            source_snapshot_at=merged,
        )
        issues = list(replay["reasons"])
        if not chain_verified:
            issues.append("raw_chain_unverified")
        if not timing.passed:
            issues.append("publication_not_proven_before_cutoff")
        if (
            replay.get("features_available_at")
            and timestamp(replay["features_available_at"]) > merged
        ):
            issues.append("capture_clock_after_publication")
        projected = [_feature_projection(row, replay) for row in replay["feature_rows"]]
        parity = (
            sorted(projected, key=lambda r: r["chulNo"])
            == sorted(saved_rows[race_id], key=lambda r: r["chulNo"])
            and replay["eligible_for_prerace_features"]
            is archived[race_id]["eligible_for_prerace_features"]
        )
        if not parity:
            issues.append("published_feature_replay_drift")
        ledger.append(
            {
                "race_id": race_id,
                "raw_chain_verified": chain_verified,
                "content_bound_before_cutoff": chain_verified and timing.passed,
                "external_existence_bound_at": witness["merged_at"],
                "local_features_available_at": replay.get("features_available_at"),
                "operational_cutoff_at": timing.operational_cutoff_at,
                "original_feature_eligibility": archived[race_id][
                    "eligible_for_prerace_features"
                ],
                "current_replay_eligibility": replay["eligible_for_prerace_features"],
                "feature_projection_matches_publication": parity,
                "candidate_feature_rows": len(projected) if not issues else 0,
                "source_review_candidate": not issues and bool(projected),
                "reasons": sorted(set(issues)),
                "evidence": evidence,
            }
        )
    current = implementation_fingerprint()
    return {
        "format_version": "kra-prerace-hash-witness-v1",
        "audit_script_sha256": sha256(Path(__file__).read_bytes()),
        "witness": witness,
        "input_plan_sha256": plan_hash,
        "feature_bundle_sha256": bundle_hash,
        "scope_basis": SCOPE_BASIS,
        "race_count": len(ledger),
        "raw_chain_verified_count": sum(r["raw_chain_verified"] for r in ledger),
        "pre_cutoff_content_bound_count": sum(
            r["content_bound_before_cutoff"] for r in ledger
        ),
        "source_review_candidate_count": sum(
            r["source_review_candidate"] for r in ledger
        ),
        "candidate_feature_row_count": sum(r["candidate_feature_rows"] for r in ledger),
        "original_implementation": plan["implementation"],
        "current_implementation": current,
        "implementation_changed": current != plan["implementation"],
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
        "official_source_authenticated_by_github": False,
        "prediction_registration_proven": False,
        "unresolved_scope": plan["unresolved_scope"],
        "ledger": ledger,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--pull", type=int, default=61)
    parser.add_argument("--document", default=DOCUMENT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    directory = args.output_dir / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    )
    directory.mkdir(parents=True)
    try:
        plan_bytes = read_bytes(args.plan, limit=MAX_MANIFEST_BYTES)
        bundle_bytes = read_bytes(args.bundle, limit=MAX_MANIFEST_BYTES)
        with httpx.Client(
            timeout=30, follow_redirects=False, trust_env=False
        ) as client:
            document, witness = collect_publication(
                directory, number=args.pull, document=args.document, client=client
            )
        report = audit_archive(
            plan_bytes=plan_bytes,
            bundle_bytes=bundle_bytes,
            document_bytes=document,
            witness=witness,
            archive_root=args.archive_root,
        )
    except (ValueError, KeyError, TypeError, OSError, httpx.HTTPError) as exc:
        report = {
            "status": "witness_audit_failed",
            "error_type": type(exc).__name__,
            "training_approved": False,
        }
    with (directory / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "report_path": str(directory / "report.json"),
                **{
                    k: v
                    for k, v in report.items()
                    if k
                    not in (
                        "ledger",
                        "original_implementation",
                        "current_implementation",
                    )
                },
            },
            indent=2,
        )
    )
    return 0 if report.get("source_review_candidate_count", 0) else 2


if __name__ == "__main__":
    raise SystemExit(main())
