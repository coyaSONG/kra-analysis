"""Venue-4 replay isolated from hash-pinned M0/result-evaluation code.

The validation body deliberately mirrors the frozen legacy replay. Keep its
source guards in sync through tests; do not edit the legacy module to add a venue.
"""

from pathlib import Path
from typing import Any

from shared.kra_race_card_pdf import (
    MAX_PDF_BYTES,
    SOURCE_ID,
    parse_race_card_pdf,
    parser_version_for_meet,
    race_card_url,
    validate_identity,
)
from shared.kra_race_card_pdf_audit import audit_race_card_snapshot

from autoresearch.kra_race_card_pdf_replay import (
    ENTRY_PROJECTION_KEYS,
    MAX_MANIFEST_BYTES,
    ReplayError,
    _checked_raw,
    _matching_identity,
    _replay_entries,
    _timestamp,
    archive_path,
    checked_digest,
    parse_json,
    read_bytes,
    sha256,
)
from autoresearch.kra_race_card_pdf_snapshot import SNAPSHOT_VERSION

REPLAY_VERSION = "kra-yeongcheon-pdf-replay-v1"


def replay_race_card_snapshot(
    manifest_path: str | Path,
    *,
    archive_root: Path,
    expected_sha256: str,
    expected_identity: dict[str, Any],
    expected_pdf_sha256: str | None = None,
    expected_entry_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Never authorize saved eligibility flags without replaying the raw chain."""
    result: dict[str, Any] = {
        "replay_version": REPLAY_VERSION,
        "eligible_for_prerace_features": False,
        "reasons": [],
        "feature_rows": [],
        "evidence": {},
        "model_promoted": False,
    }
    try:
        validate_identity(**expected_identity)
        result.update(expected_identity)
        result["race_id"] = (
            f"{expected_identity['race_date']}_{expected_identity['meet']}_"
            f"{expected_identity['race_no']}"
        )
        path = archive_path(manifest_path, archive_root=archive_root)
        if path.name != "snapshot.json" or path.parent.parent.name != result["race_id"]:
            raise ReplayError("pdf_manifest_path_contract_mismatch")
        content = read_bytes(path, limit=MAX_MANIFEST_BYTES)
        digest = sha256(content)
        if digest != checked_digest(expected_sha256):
            raise ReplayError("pdf_manifest_sha256_mismatch")
        manifest = parse_json(content)
        _matching_identity(manifest, expected_identity)
        url = race_card_url(**expected_identity)
        if (
            manifest.get("snapshot_version") != SNAPSHOT_VERSION
            or manifest.get("source_id") != SOURCE_ID
            or manifest.get("race_id") != result["race_id"]
            or manifest.get("url") != url
            or manifest.get("final_url") != url
            or manifest.get("http_status") != 200
            or manifest.get("collection_status") != "captured"
            or manifest.get("timing_evidence")
            != "local_capture_completion_not_server_headers"
            or archive_path(manifest.get("manifest_path"), archive_root=archive_root)
            != path
        ):
            raise ReplayError("pdf_manifest_contract_mismatch")
        started = _timestamp(manifest.get("fetch_started_at"))
        captured = _timestamp(manifest.get("collected_at"))
        finished = _timestamp(manifest.get("attempt_finished_at"))
        if not started <= captured <= finished:
            raise ReplayError("pdf_capture_order_mismatch")
        raw, pdf_evidence = _checked_raw(
            manifest, parent=path.parent, archive_root=archive_root, limit=MAX_PDF_BYTES
        )
        if expected_pdf_sha256 is not None and pdf_evidence["sha256"] != checked_digest(
            expected_pdf_sha256
        ):
            raise ReplayError("planned_pdf_sha256_mismatch")
        saved_parsed = manifest.get("parsed")
        if not isinstance(saved_parsed, dict) or saved_parsed.get(
            "parser_version"
        ) != parser_version_for_meet(expected_identity["meet"]):
            raise ReplayError("parser_version_mismatch")
        try:
            parsed = parse_race_card_pdf(raw, **expected_identity)
        except Exception as exc:
            raise ReplayError("pdf_reparse_failed") from exc
        if parsed != saved_parsed:
            raise ReplayError("pdf_parser_output_mismatch")
        embedded = manifest.get("entry_snapshot")
        if not isinstance(embedded, dict) or not embedded.get("source_manifest_path"):
            raise ReplayError("missing_entry_capture_provenance")
        entry_path = archive_path(
            embedded["source_manifest_path"], archive_root=archive_root
        )
        if entry_path.parent.parent.parent != path.parent.parent.parent:
            raise ReplayError("entry_manifest_not_same_capture_archive")
        entries, entry_evidence = _replay_entries(
            entry_path,
            archive_root=archive_root,
            identity=expected_identity,
            expected_sha256=expected_entry_manifest_sha256,
        )
        if embedded != {key: entries.get(key) for key in ENTRY_PROJECTION_KEYS}:
            raise ReplayError("pdf_embedded_entry_projection_mismatch")
        if _timestamp(entries["collected_at"]) > started:
            raise ReplayError("entry_capture_after_pdf_fetch_started")
        audit = audit_race_card_snapshot(
            parsed,
            collected_at=captured,
            scheduled_start_time=manifest.get("scheduled_start_time"),
            entries=entries,
        )
        if (
            audit != manifest.get("audit")
            or manifest.get("eligible_for_prerace_features")
            is not audit["eligible_for_prerace_features"]
        ):
            raise ReplayError("saved_audit_mismatch")
        result.update(
            eligible_for_prerace_features=audit["eligible_for_prerace_features"],
            reasons=audit["reasons"],
            feature_rows=audit["feature_rows"],
            features_available_at=audit["features_available_at"],
            scheduled_start_time=entries["scheduled_start_time"],
            entry_horse_count=len(entries["entries"]),
            evidence={
                "pdf_manifest_path": str(path),
                "pdf_manifest_sha256": digest,
                "pdf": pdf_evidence,
                "entry": entry_evidence,
                "timing_evidence": "local_capture_completion_not_third_party_attestation",
            },
        )
    except ReplayError as exc:
        result["reasons"] = [str(exc)]
    except (ValueError, TypeError, KeyError, RuntimeError) as exc:
        result["reasons"] = ["source_replay_failed"]
        result["error_type"] = type(exc).__name__
    return result
