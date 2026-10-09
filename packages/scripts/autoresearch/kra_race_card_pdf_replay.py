"""Revalidate local PDF/API evidence before exposing pre-race feature rows."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shared.kra_entry_sheet import (
    SOURCE_ID as ENTRY_SOURCE_ID,
)
from shared.kra_entry_sheet import build_entry_snapshot, parse_entry_sheet_page
from shared.kra_race_card_pdf import (
    MAX_PDF_BYTES,
    PARSER_VERSION,
    SOURCE_ID,
    parse_race_card_pdf,
    race_card_url,
    validate_identity,
)
from shared.kra_race_card_pdf_audit import audit_race_card_snapshot

from autoresearch.kra_entry_sheet_snapshot import (
    ENTRY_URL,
    MAX_PAGE_BYTES,
    PAGE_SIZE,
)
from autoresearch.kra_race_card_pdf_snapshot import SNAPSHOT_VERSION

REPLAY_VERSION = "kra-race-card-pdf-replay-v1"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
ENTRY_PROJECTION_KEYS = (
    "meet",
    "race_date",
    "race_no",
    "collected_at",
    "scheduled_start_time",
    "source_id",
    "source_manifest_path",
    "entries",
)


class ReplayError(ValueError):
    """A stable blocker code, never a credential-bearing exception string."""


def archive_path(value: Any, *, archive_root: Path) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise ReplayError("missing_archive_path")
    root = archive_root.resolve()
    path = Path(value)
    path = (path if path.is_absolute() else root / path).resolve()
    if not path.is_relative_to(root):
        raise ReplayError("archive_path_escapes_root")
    return path


def read_bytes(path: Path, *, limit: int) -> bytes:
    try:
        with path.open("rb") as stream:
            content = stream.read(limit + 1)
    except OSError as exc:
        raise ReplayError("archive_file_unavailable") from exc
    if len(content) > limit:
        raise ReplayError("archive_file_too_large")
    return content


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReplayError("duplicate_json_key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ReplayError("nonfinite_json_value")


def parse_json(content: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(
            content,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayError("invalid_archive_json") from exc
    if not isinstance(payload, dict):
        raise ReplayError("archive_json_not_object")
    return payload


def checked_digest(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ReplayError("invalid_expected_sha256")
    return value


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ReplayError("invalid_capture_timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReplayError("invalid_capture_timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReplayError("capture_timestamp_requires_timezone")
    return parsed.astimezone(UTC)


def _matching_identity(payload: dict[str, Any], identity: dict[str, Any]) -> None:
    if any(
        type(payload.get(key)) is not type(value) or payload.get(key) != value
        for key, value in identity.items()
    ):
        raise ReplayError("source_race_identity_mismatch")


def _checked_raw(
    record: dict[str, Any], *, parent: Path, archive_root: Path, limit: int
) -> tuple[bytes, dict[str, Any]]:
    digest = checked_digest(record.get("sha256"))
    path = archive_path(record.get("raw_path"), archive_root=archive_root)
    if path.parent != parent:
        raise ReplayError("raw_path_not_manifest_sibling")
    content = read_bytes(path, limit=limit)
    if sha256(content) != digest:
        raise ReplayError("raw_sha256_mismatch")
    if (
        type(record.get("byte_count")) is not int
        or len(content) != record["byte_count"]
    ):
        raise ReplayError("raw_byte_count_mismatch")
    return content, {"path": str(path), "sha256": digest, "byte_count": len(content)}


def _replay_entries(
    path: Path,
    *,
    archive_root: Path,
    identity: dict[str, Any],
    expected_sha256: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    content = read_bytes(path, limit=MAX_MANIFEST_BYTES)
    digest = sha256(content)
    if expected_sha256 is not None and digest != checked_digest(expected_sha256):
        raise ReplayError("entry_manifest_sha256_mismatch")
    manifest = parse_json(content)
    source_identity = {
        key: manifest.get(key) for key in ("meet", "race_date", "race_no")
    }
    validate_identity(**source_identity)
    _matching_identity(manifest, {key: identity[key] for key in ("meet", "race_date")})
    source_race_id = (
        f"{source_identity['race_date']}_{source_identity['meet']}_"
        f"{source_identity['race_no']}"
    )
    if path.name != "entry_capture.json" or path.parent.parent.name != source_race_id:
        raise ReplayError("entry_manifest_path_contract_mismatch")
    if (
        manifest.get("source_id") != ENTRY_SOURCE_ID
        or manifest.get("url") != ENTRY_URL
        or manifest.get("collection_status") != "captured"
        or archive_path(manifest.get("manifest_path"), archive_root=archive_root)
        != path
    ):
        raise ReplayError("entry_manifest_contract_mismatch")
    started = _timestamp(manifest.get("fetch_started_at"))
    captured = _timestamp(manifest.get("collected_at"))
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= 100:
        raise ReplayError("missing_or_invalid_entry_pages")
    rows: list[dict[str, Any]] = []
    evidence = []
    total = None
    previous = started
    for number, page in enumerate(pages, 1):
        if not isinstance(page, dict) or type(page.get("page_no")) is not int:
            raise ReplayError("invalid_entry_page_record")
        params = {
            "meet": identity["meet"],
            "rc_date": identity["race_date"],
            "rc_no": source_identity["race_no"],
            "numOfRows": PAGE_SIZE,
            "pageNo": number,
            "_type": "json",
        }
        stored_params = page.get("request_parameters")
        if (
            page["page_no"] != number
            or not isinstance(stored_params, dict)
            or set(stored_params) != set(params)
            or any(
                type(stored_params[key]) is not type(value)
                or stored_params[key] != value
                for key, value in params.items()
            )
        ):
            raise ReplayError("entry_page_request_mismatch")
        raw, raw_evidence = _checked_raw(
            page, parent=path.parent, archive_root=archive_root, limit=MAX_PAGE_BYTES
        )
        page_rows, page_total = parse_entry_sheet_page(
            parse_json(raw), page_no=number, page_size=PAGE_SIZE
        )
        if total is not None and total != page_total:
            raise ReplayError("entry_page_total_changed")
        total = page_total
        if type(page.get("row_count")) is not int or page["row_count"] != len(
            page_rows
        ):
            raise ReplayError("entry_page_row_count_mismatch")
        completed = _timestamp(page.get("collected_at"))
        if not previous <= completed <= captured:
            raise ReplayError("entry_capture_order_mismatch")
        previous = completed
        rows.extend(page_rows)
        evidence.append({**raw_evidence, "collected_at": completed.isoformat()})
    if (
        previous != captured
        or len(rows) != total
        or len(pages) != max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        or type(manifest.get("total_count")) is not int
        or manifest["total_count"] != total
    ):
        raise ReplayError("incomplete_entry_capture")
    rebuilt = build_entry_snapshot(rows, **source_identity, collected_at=captured)
    rebuilt["source_manifest_path"] = manifest["manifest_path"]
    if rebuilt != manifest.get("entry_snapshot"):
        raise ReplayError("entry_projection_mismatch")
    entry_path = archive_path(
        manifest.get("entry_snapshot_path"), archive_root=archive_root
    )
    if entry_path.parent != path.parent:
        raise ReplayError("entry_projection_path_not_sibling")
    entry_content = read_bytes(entry_path, limit=MAX_MANIFEST_BYTES)
    if parse_json(entry_content) != rebuilt:
        raise ReplayError("entry_projection_file_mismatch")
    target_entries = build_entry_snapshot(rows, **identity, collected_at=captured)
    target_entries["source_manifest_path"] = manifest["manifest_path"]
    return target_entries, {
        "manifest_path": str(path),
        "manifest_sha256": digest,
        "entry_projection_sha256": sha256(entry_content),
        "source_requested_identity": source_identity,
        "target_identity": identity,
        "pages": evidence,
    }


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
        if (
            not isinstance(saved_parsed, dict)
            or saved_parsed.get("parser_version") != PARSER_VERSION
        ):
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
